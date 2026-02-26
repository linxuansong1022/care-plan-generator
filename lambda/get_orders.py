# lambda/get_orders.py
import json
import psycopg2
from psycopg2.extras import RealDictCursor
import os

def get_db_connection():
    return psycopg2.connect(
        host=os.environ['DB_HOST'],
        database=os.environ['DB_NAME'],
        user=os.environ['DB_USER'],
        password=os.environ['DB_PASSWORD'],
        port=os.environ.get('DB_PORT', '5432'),
        connect_timeout=5
    )

def lambda_handler(event, context):
    print(f"Received event: {json.dumps(event)}")
    
    # 允许 API Gateway 的 query string 参数
    order_id = event.get('queryStringParameters', {}).get('order_id')
    
    if not order_id:
        return {
            'statusCode': 400,
            'body': json.dumps({'message': 'order_id or MRN is required'})
        }

    try:
        conn = get_db_connection()
        cur = conn.cursor(cursor_factory=RealDictCursor)
        
        # 智能化查询：如果 order_id 是数字，匹配 ID；如果不是，匹配 MRN
        query = """
            SELECT 
                o.id as order_id, o.status, o.created_at,
                p.first_name || ' ' || p.last_name as patient_name,
                p.mrn,
                pr.name as provider_name,
                cp.content as care_plan
            FROM orders_order o
            JOIN orders_patient p ON o.patient_id = p.id
            JOIN orders_provider pr ON o.provider_id = pr.id
            LEFT JOIN orders_careplan cp ON o.id = cp.order_id
            WHERE (o.id::text = %s OR p.mrn = %s)
            ORDER BY o.created_at DESC
        """
        cur.execute(query, (order_id, order_id))
        results = cur.fetchall()
        
        # 返回列表，兼容前端的 Table 渲染
        return {
            'statusCode': 200,
            'headers': {
                'Access-Control-Allow-Origin': '*',
                'Content-Type': 'application/json'
            },
            'body': json.dumps(results, default=str)
        }

    except Exception as e:
        print(f"ERROR: {str(e)}")
        return {
            'statusCode': 500,
            'headers': {
                'Access-Control-Allow-Origin': '*',
                'Content-Type': 'application/json'
            },
            'body': json.dumps({'error': str(e)})
        }
    finally:
        if 'conn' in locals():
            conn.close()