# lambda/test_post_orders.py
#
# 本地测试 post_orders Lambda（直连 Docker 数据库）
# 运行：python test_post_orders.py

import os

# 请在本地设置环境变量或使用 .env 文件，不要在这里写死
os.environ.setdefault('DB_HOST', 'localhost')
os.environ.setdefault('DB_NAME', 'careplan')
os.environ.setdefault('DB_USER', 'postgres')
os.environ.setdefault('DB_PASSWORD', 'postgres')
os.environ.setdefault('DB_PORT', '5434')
os.environ.setdefault('SQS_QUEUE_URL', 'https://sqs.xxx.amazonaws.com/xxx/xxx')
os.environ.setdefault('AWS_REGION', 'eu-north-1')

# 如果你没有真实的 AWS 凭证，boto3 会报错
# 临时解决：设置假的凭证让 boto3 不崩溃（只适合本地测试）
os.environ['AWS_ACCESS_KEY_ID'] = 'fake'
os.environ['AWS_SECRET_ACCESS_KEY'] = 'fake'

from post_orders import lambda_handler

# ============================================================
# 测试用例 1：正常创建订单
# ============================================================
print("=" * 50)
print("Test 1: 正常创建订单")
print("=" * 50)

import json

fake_event = {
    "body": json.dumps({
        "patient": {
            "first_name": "Test",
            "last_name": "Lambda",
            "mrn": "999001",
            "dob": "1990-01-01"
        },
        "provider": {
            "name": "Dr. Lambda",
            "npi": "9990000001"
        },
        "medication_name": "TestDrug",
        "primary_diagnosis": "Z00.0"
    })
}

result = lambda_handler(fake_event, None)
print(f"Status: {result['statusCode']}")
print(f"Body:   {result['body']}")

# ============================================================
# 测试用例 2：MRN 格式错误（不是6位）
# ============================================================
print()
print("=" * 50)
print("Test 2: MRN 格式错误")
print("=" * 50)

fake_event_bad = {
    "body": json.dumps({
        "patient": {
            "first_name": "Bad",
            "last_name": "Patient",
            "mrn": "12",      # 只有2位，应该报错
            "dob": "1990-01-01"
        },
        "provider": {
            "name": "Dr. X",
            "npi": "1234567890"
        },
        "medication_name": "Aspirin",
        "primary_diagnosis": "R50.9"
    })
}

result2 = lambda_handler(fake_event_bad, None)
print(f"Status: {result2['statusCode']}")
print(f"Body:   {result2['body']}")

# ============================================================
# 测试用例 3：缺少必填字段
# ============================================================
print()
print("=" * 50)
print("Test 3: 缺少 medication_name")
print("=" * 50)

fake_event_missing = {
    "body": json.dumps({
        "patient": {
            "first_name": "Jane",
            "last_name": "Doe",
            "mrn": "123456",
            "dob": "1979-06-08"
        },
        "provider": {
            "name": "Dr. Smith",
            "npi": "1234567890"
        }
        # 没有 medication_name 和 primary_diagnosis
    })
}

result3 = lambda_handler(fake_event_missing, None)
print(f"Status: {result3['statusCode']}")
print(f"Body:   {result3['body']}")
