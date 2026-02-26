# lambda/get_orders.py
import json
import psycopg2
import os

def get_db_connection():
    """从环境变量读取数据库配置，本地测试和 AWS 都用这个"""
    return psycopg2.connect(
        host=os.environ['DB_HOST'],
        database=os.environ['DB_NAME'],
        user=os.environ['DB_USER'],
        password=os.environ['DB_PASSWORD'],
        port=os.environ.get('DB_PORT', 5432)
    )

def lambda_handler(event, context):
    # 1. 解析请求参数（API Gateway 把 URL 参数放在这里）
    params = event.get('queryStringParameters') or {}
    order_id = params.get('order_id')

    if not order_id:
        return {
            "statusCode": 400,
            "body": json.dumps({"error": "order_id is required"})
        }

    # 2. 查询数据库
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        # 查 order 基本信息
        cursor.execute("""
            SELECT o.id, o.status, o.created_at,
                p.first_name, p.last_name, p.mrn,
                pr.name as provider_name
            FROM orders_order o
            JOIN orders_patient p ON o.patient_id = p.id
            JOIN orders_provider pr ON o.provider_id = pr.id
            WHERE o.id = %s
        """, (order_id,))
            
        order = cursor.fetchone()
        if not order:
            return {
                "statusCode": 404,
                "body": json.dumps({"error": "Order not found"})
            }

        # 查 care plan（如果有）
        cursor.execute("""
            SELECT content, created_at
            FROM orders_careplan
            WHERE order_id = %s
        """, (order_id,))
        
        careplan = cursor.fetchone()

        cursor.close()
        conn.close()

    except Exception as e:
        # 注意：不能暴露原始错误信息，可能包含 PHI 或数据库细节
        print(f"Database error: {str(e)}")  # 只打印到 CloudWatch log
        return {
            "statusCode": 500,
            "body": json.dumps({"error": "Internal server error"})
        }

    # 3. 组装返回结果
    result = {
        "order_id": order[0],
        "status": order[1],
        "created_at": str(order[2]),
        "patient_name": f"{order[3]} {order[4]}", 
        "mrn": order[5],
        "provider_name": order[6],
        "care_plan": {
            "content": careplan[0],
            "created_at": str(careplan[1])
        } if careplan else None
    }

    return {
        "statusCode": 200,
        "body": json.dumps(result)
    }