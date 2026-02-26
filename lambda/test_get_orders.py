# test_get_orders.py
import os
os.environ['DB_HOST'] = 'localhost'
os.environ['DB_NAME'] = 'careplan'
os.environ['DB_PASSWORD'] = 'postgres'
os.environ['DB_USER'] = 'postgres'
os.environ['DB_PORT'] = '5434'

from get_orders import lambda_handler

# 模拟 API Gateway 发过来的 event
fake_event = {
    "queryStringParameters": {
        "order_id": "1"
    }
}

result = lambda_handler(fake_event, None)
print(result)