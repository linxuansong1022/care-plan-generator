# lambda/generate_care_plan.py
#
# 职责：从 SQS 接收 order_id → 查 RDS 获取订单详情 → 调 Gemini 生成 care plan
#       → 把结果写回 RDS（orders_careplan 表）→ 更新 order.status
#
# 触发方式：SQS 自动触发（每收到一条消息就调用一次 lambda_handler）
# 重试策略：Gemini 失败最多重试 3 次（指数退避），全部失败后订单状态变为 failed
#
# 环境变量：
#   DB_HOST, DB_NAME, DB_USER, DB_PASSWORD, DB_PORT
#   GOOGLE_API_KEY     ← Gemini API Key（从 AWS Secrets Manager 或 Lambda 环境变量读取）

import json
import os

from google import genai
from google.genai import types
import psycopg2


# ============================================================
# 数据库连接
# ============================================================

def get_db_connection():
    return psycopg2.connect(
        host=os.environ['DB_HOST'],
        database=os.environ['DB_NAME'],
        user=os.environ['DB_USER'],
        password=os.environ['DB_PASSWORD'],
        port=os.environ.get('DB_PORT', 5432)
    )


# ============================================================
# 数据库操作
# ============================================================

def get_order_details(cursor, order_id):
    """
    查询订单完整信息（JOIN patient 和 provider）
    返回一个 dict，字段名和 base.py 里 prompt 用到的一致
    """
    cursor.execute("""
        SELECT
            o.id,
            o.medication_name,
            o.primary_diagnosis,
            o.additional_diagnoses,
            o.medication_history,
            o.patient_records,
            o.status,
            p.first_name,
            p.last_name,
            p.mrn,
            p.dob,
            pr.name AS provider_name,
            pr.npi  AS provider_npi
        FROM orders_order o
        JOIN orders_patient  p  ON o.patient_id  = p.id
        JOIN orders_provider pr ON o.provider_id = pr.id
        WHERE o.id = %s
    """, (order_id,))

    row = cursor.fetchone()
    if not row:
        return None

    return {
        "id":                  row[0],
        "medication_name":     row[1],
        "primary_diagnosis":   row[2],
        "additional_diagnoses": row[3] or [],   # jsonb → Python list
        "medication_history":  row[4] or [],
        "patient_records":     row[5] or "",
        "status":              row[6],
        "patient_first_name":  row[7],
        "patient_last_name":   row[8],
        "patient_mrn":         row[9],
        "patient_dob":         str(row[10]),
        "provider_name":       row[11],
        "provider_npi":        row[12],
    }


def set_order_status(cursor, order_id, status):
    cursor.execute(
        "UPDATE orders_order SET status = %s WHERE id = %s",
        (status, order_id)
    )


def save_care_plan(cursor, order_id, content):
    """
    INSERT INTO orders_careplan
    如果已存在（因为重试）用 ON CONFLICT 更新内容
    """
    cursor.execute("""
        INSERT INTO orders_careplan (order_id, content, created_at)
        VALUES (%s, %s, NOW())
        ON CONFLICT (order_id) DO UPDATE SET content = EXCLUDED.content
    """, (order_id, content))


# ============================================================
# Gemini 调用（直接从 base.py 移植 prompt 逻辑）
# ============================================================

def build_prompt(order):
    """
    与 backend/orders/LLMServices/base.py 中的 _build_prompt 保持完全一致
    """
    additional = ', '.join(order["additional_diagnoses"]) if order["additional_diagnoses"] else 'None'
    history    = ', '.join(order["medication_history"])   if order["medication_history"]   else 'None'
    records    = order["patient_records"] if order["patient_records"] else 'None provided'

    return f"""You are a clinical pharmacist creating a care plan for a specialty pharmacy patient.

    Patient Information:
    - Name: {order["patient_first_name"]} {order["patient_last_name"]}
    - Date of Birth: {order["patient_dob"]}
    - MRN: {order["patient_mrn"]}

    Provider: {order["provider_name"]} (NPI: {order["provider_npi"]})

    Medication: {order["medication_name"]}
    Primary Diagnosis (ICD-10): {order["primary_diagnosis"]}
    Additional Diagnoses: {additional}
    Medication History: {history}
    Patient Records/Notes: {records}

    Please generate a comprehensive pharmaceutical care plan with EXACTLY these four sections:

    1. **Problem List / Drug Therapy Problems (DTPs)**
    - Identify potential drug therapy problems related to the prescribed medication and diagnoses

    2. **Goals (SMART format)**
    - Specific, Measurable, Achievable, Relevant, Time-bound goals for this patient

    3. **Pharmacist Interventions / Plan**
    - Specific actions the pharmacist should take
    - Patient education points
    - Coordination with the prescribing provider

    4. **Monitoring Plan & Lab Schedule**
    - Labs to monitor and frequency
    - Clinical parameters to track
    - Follow-up schedule

    Be specific and clinically relevant to the medication and diagnoses provided."""


def call_gemini(prompt, max_retries=3):
    """
    调 Gemini API，最多重试 max_retries 次（指数退避）。
    成功返回 content 字符串，全部失败抛 RuntimeError。
    """
    import time

    client = genai.Client(api_key=os.environ['GOOGLE_API_KEY'])

    for attempt in range(1, max_retries + 1):
        try:
            response = client.models.generate_content(
                model='gemini-flash-latest',
                contents=prompt
            )
            return response.text
        except Exception as e:
            print(f"[Gemini] Attempt {attempt}/{max_retries} failed: {e}")
            if attempt < max_retries:
                time.sleep(2 ** attempt)   # 2s, 4s, 8s 退避
            else:
                raise RuntimeError(f"Gemini failed after {max_retries} attempts: {e}")


# ============================================================
# Lambda 核心处理逻辑（处理单条订单）
# ============================================================

def process_order(order_id):
    """
    完整处理一个订单：
    1. 查 RDS 取订单详情
    2. status → processing
    3. 调 Gemini 生成 care plan
    4. 写回 orders_careplan 表
    5. status → completed
    遇到任何异常直接抛出，让上层决定是报错还是标 failed
    """
    conn = get_db_connection()
    try:
        with conn:
            with conn.cursor() as cursor:
                # 1. 查订单
                order = get_order_details(cursor, order_id)
                if not order:
                    print(f"[WARN] Order {order_id} not found, skipping")
                    return

                # 已经处理过的订单跳过（防止重复消费）
                if order["status"] == "completed":
                    print(f"[INFO] Order {order_id} already completed, skipping")
                    return

                # 2. 更新状态为 processing
                set_order_status(cursor, order_id, "processing")

        # ← 事务这里 commit（processing 状态先写进去）

        # 3. 调 Gemini（在事务外，因为网络调用可能很慢）
        prompt  = build_prompt(order)
        content = call_gemini(prompt)

        # 4+5. 写 care plan + 更新状态为 completed（同一个事务，原子）
        with conn:
            with conn.cursor() as cursor:
                save_care_plan(cursor, order_id, content)
                set_order_status(cursor, order_id, "completed")

        print(f"[OK] Order {order_id} care plan generated successfully")

    except Exception as e:
        # 出错 → 标记为 failed
        print(f"[ERROR] Order {order_id} failed: {e}")
        try:
            with conn:
                with conn.cursor() as cursor:
                    set_order_status(cursor, order_id, "failed")
        except Exception as db_err:
            print(f"[ERROR] Could not update status to failed: {db_err}")
        raise   # 重新抛出，让 SQS 知道这条消息处理失败（会进死信队列）

    finally:
        conn.close()


# ============================================================
# Lambda 入口（SQS 可能批量传多条消息）
# ============================================================

def lambda_handler(event, context):
    """
    SQS 触发时，event["Records"] 是一个列表（batch）。
    每条 Record 的 body 是 post_orders 发出的 JSON：{"order_id": 123}
    
    失败处理策略：
    - 某一条失败时，把它的 messageId 加入 batchItemFailures
    - SQS 只会重新投递失败的那条，成功的不会重试
    """
    failures = []

    for record in event.get("Records", []):
        message_id = record["messageId"]
        try:
            body     = json.loads(record["body"])
            order_id = body["order_id"]
            print(f"[START] Processing order_id={order_id} (messageId={message_id})")
            process_order(order_id)

        except Exception as e:
            print(f"[FAIL] messageId={message_id} error: {e}")
            failures.append({"itemIdentifier": message_id})

    # 返回失败列表（空列表 = 全部成功）
    return {"batchItemFailures": failures}
