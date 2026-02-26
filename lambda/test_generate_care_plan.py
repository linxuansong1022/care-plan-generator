# lambda/test_generate_care_plan.py
#
# 本地测试 generate_care_plan Lambda（直连 Docker 数据库 + 真实 Gemini API）
# 运行：python test_generate_care_plan.py

import os

# ---- 数据库配置（使用系统变量或默认值） ----
os.environ.setdefault('DB_HOST', 'localhost')
os.environ.setdefault('DB_NAME', 'careplan')
os.environ.setdefault('DB_USER', 'postgres')
os.environ.setdefault('DB_PASSWORD', 'postgres')
os.environ.setdefault('DB_PORT', '5434')

# ---- Gemini API Key ----
# 必须设置系统环境变量 GOOGLE_API_KEY 后才能运行
# 或者运行前：export GOOGLE_API_KEY='your-key'
if 'GOOGLE_API_KEY' not in os.environ:
    os.environ.setdefault('GOOGLE_API_KEY', 'YOUR_KEY_HERE')

from generate_care_plan import lambda_handler

# ============================================================
# 测试用例 1：处理一个真实存在的订单（从 post_orders 测试里创建的）
# ============================================================
print("=" * 50)
print("Test 1: 生成 Care Plan（用真实 Gemini API）")
print("=" * 50)

import json

# order_id=2 是 test_post_orders.py 创建的那个
fake_sqs_event = {
    "Records": [
        {
            "messageId": "test-msg-001",
            "body": json.dumps({"order_id": 2, "created_at": "2026-02-26T00:00:00"})
        }
    ]
}

result = lambda_handler(fake_sqs_event, None)
print(f"Result: {result}")
# 期望：{"batchItemFailures": []}  ← 空列表表示全部成功

# ============================================================
# 测试用例 2：订单不存在（应该跳过，不报错）
# ============================================================
print()
print("=" * 50)
print("Test 2: 订单不存在（应跳过）")
print("=" * 50)

fake_sqs_event_missing = {
    "Records": [
        {
            "messageId": "test-msg-002",
            "body": json.dumps({"order_id": 99999})
        }
    ]
}

result2 = lambda_handler(fake_sqs_event_missing, None)
print(f"Result: {result2}")
# 期望：{"batchItemFailures": []}  ← 订单不存在时跳过，不算失败
