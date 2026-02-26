# lambda/post_orders.py
#
# 职责：接收新订单 → 验证输入 → 存到 RDS → 发消息到 SQS
#
# 调用方式：API Gateway POST /orders
# 请求 body（JSON）：
# {
#   "patient": {
#     "first_name": "Jane",
#     "last_name": "Doe",
#     "mrn": "123456",        # 6 位
#     "dob": "1979-06-08"     # YYYY-MM-DD
#   },
#   "provider": {
#     "name": "Dr. Smith",
#     "npi": "1234567890"     # 10 位
#   },
#   "medication_name": "IVIG",
#   "primary_diagnosis": "G70.01",
#   "additional_diagnoses": [],     # 可选，默认 []
#   "medication_history": [],       # 可选，默认 []
#   "patient_records": ""           # 可选，默认 ""
# }

import json
import os
import re
from datetime import date, datetime

import boto3
import psycopg2
import psycopg2.extras  # 让 cursor 返回 dict 而不是 tuple


# ============================================================
# 工具函数
# ============================================================

def get_db_connection():
    """从环境变量读取数据库配置"""
    return psycopg2.connect(
        host=os.environ['DB_HOST'],
        database=os.environ['DB_NAME'],
        user=os.environ['DB_USER'],
        password=os.environ['DB_PASSWORD'],
        port=os.environ.get('DB_PORT', 5432)
    )


def response(status_code, body):
    """统一返回格式"""
    return {
        "statusCode": status_code,
        "headers": {"Content-Type": "application/json"},
        "body": json.dumps(body)
    }


# ============================================================
# 输入验证
# ============================================================

def validate_input(body):
    """
    验证必填字段和格式。
    返回 (cleaned_data, error_message)
    成功时 error_message 为 None
    失败时 cleaned_data 为 None
    """
    errors = []

    # --- Patient ---
    patient = body.get("patient")
    if not patient:
        errors.append("'patient' object is required")
    else:
        for field in ["first_name", "last_name", "mrn", "dob"]:
            if not patient.get(field):
                errors.append(f"patient.{field} is required")

        mrn = patient.get("mrn", "")
        if mrn and not re.fullmatch(r"\d{6}", mrn):
            errors.append(f"patient.mrn must be exactly 6 digits, got: '{mrn}'")

        dob = patient.get("dob", "")
        if dob:
            try:
                datetime.strptime(dob, "%Y-%m-%d")
            except ValueError:
                errors.append(f"patient.dob must be YYYY-MM-DD format, got: '{dob}'")

    # --- Provider ---
    provider = body.get("provider")
    if not provider:
        errors.append("'provider' object is required")
    else:
        for field in ["name", "npi"]:
            if not provider.get(field):
                errors.append(f"provider.{field} is required")

        npi = provider.get("npi", "")
        if npi and not re.fullmatch(r"\d{10}", npi):
            errors.append(f"provider.npi must be exactly 10 digits, got: '{npi}'")

    # --- Order fields ---
    if not body.get("medication_name"):
        errors.append("'medication_name' is required")

    if not body.get("primary_diagnosis"):
        errors.append("'primary_diagnosis' is required")

    if errors:
        return None, errors

    # 整理后的数据（带默认值）
    cleaned = {
        "patient": {
            "first_name": patient["first_name"].strip(),
            "last_name": patient["last_name"].strip(),
            "mrn": patient["mrn"].strip(),
            "dob": patient["dob"].strip(),
        },
        "provider": {
            "name": provider["name"].strip(),
            "npi": provider["npi"].strip(),
        },
        "medication_name": body["medication_name"].strip(),
        "primary_diagnosis": body["primary_diagnosis"].strip(),
        "additional_diagnoses": body.get("additional_diagnoses", []),
        "medication_history": body.get("medication_history", []),
        "patient_records": body.get("patient_records", ""),
    }
    return cleaned, None


# ============================================================
# 数据库操作
# ============================================================

def upsert_patient(cursor, patient_data):
    """
    按 MRN 查找 Patient，找到就返回 id，找不到就创建。
    对应 Django services.py 里的 check_patient（简化版，Lambda 不做警告逻辑）
    """
    cursor.execute(
        "SELECT id FROM orders_patient WHERE mrn = %s",
        (patient_data["mrn"],)
    )
    row = cursor.fetchone()
    if row:
        return row[0]  # 已存在，直接返回 id

    # 创建新 Patient
    cursor.execute(
        """
        INSERT INTO orders_patient (first_name, last_name, mrn, dob, created_at)
        VALUES (%s, %s, %s, %s, NOW())
        RETURNING id
        """,
        (
            patient_data["first_name"],
            patient_data["last_name"],
            patient_data["mrn"],
            patient_data["dob"],
        )
    )
    return cursor.fetchone()[0]


def upsert_provider(cursor, provider_data):
    """
    按 NPI 查找 Provider，找到就返回 id，找不到就创建。
    """
    cursor.execute(
        "SELECT id FROM orders_provider WHERE npi = %s",
        (provider_data["npi"],)
    )
    row = cursor.fetchone()
    if row:
        return row[0]

    cursor.execute(
        """
        INSERT INTO orders_provider (name, npi, created_at)
        VALUES (%s, %s, NOW())
        RETURNING id
        """,
        (provider_data["name"], provider_data["npi"])
    )
    return cursor.fetchone()[0]


def insert_order(cursor, patient_id, provider_id, data):
    """
    插入新订单，status 默认 'pending'。
    """
    cursor.execute(
        """
        INSERT INTO orders_order (
            patient_id, provider_id,
            medication_name, primary_diagnosis,
            additional_diagnoses, medication_history,
            patient_records,
            status, order_date, created_at
        )
        VALUES (%s, %s, %s, %s, %s, %s, %s, 'pending', CURRENT_DATE, NOW())
        RETURNING id
        """,
        (
            patient_id,
            provider_id,
            data["medication_name"],
            data["primary_diagnosis"],
            json.dumps(data["additional_diagnoses"]),   # jsonb 列需要序列化
            json.dumps(data["medication_history"]),
            data["patient_records"],
        )
    )
    return cursor.fetchone()[0]


# ============================================================
# SQS
# ============================================================

def send_to_sqs(order_id):
    """
    把 order_id 发到 SQS，下游 generate_care_plan Lambda 会消费它。
    SQS_QUEUE_URL 从环境变量读取。
    """
    sqs = boto3.client("sqs", region_name=os.environ.get("AWS_REGION", "eu-north-1"))
    queue_url = os.environ["SQS_QUEUE_URL"]

    message = {
        "order_id": order_id,
        "created_at": datetime.utcnow().isoformat()
    }

    sqs.send_message(
        QueueUrl=queue_url,
        MessageBody=json.dumps(message)
    )
    print(f"[SQS] Message sent for order_id={order_id}")


# ============================================================
# Lambda 入口
# ============================================================

def lambda_handler(event, context):
    # 1. 解析请求 body
    try:
        body = json.loads(event.get("body") or "{}")
    except json.JSONDecodeError:
        return response(400, {"error": "Request body must be valid JSON"})

    # 2. 验证输入
    data, errors = validate_input(body)
    if errors:
        return response(400, {"error": "Validation failed", "details": errors})

    # 3. 存到 RDS（patient → provider → order，用事务保证原子性）
    conn = None
    try:
        conn = get_db_connection()
        with conn:                          # with 块结束自动 commit；异常时自动 rollback
            with conn.cursor() as cursor:
                patient_id  = upsert_patient(cursor, data["patient"])
                provider_id = upsert_provider(cursor, data["provider"])
                order_id    = insert_order(cursor, patient_id, provider_id, data)

    except Exception as e:
        print(f"[DB ERROR] {str(e)}")
        return response(500, {"error": "Database error, please try again later"})
    finally:
        if conn:
            conn.close()

    # 4. 发消息到 SQS
    try:
        send_to_sqs(order_id)
    except Exception as e:
        # SQS 失败不应该让已经存好的订单消失
        # 这里只记录日志，order 还在 DB 里，后续可以补偿
        print(f"[SQS ERROR] Failed to send message for order {order_id}: {str(e)}")

    # 5. 返回成功
    return response(202, {
        "message": "Order accepted",
        "order_id": order_id,
        "status": "pending"
    })
