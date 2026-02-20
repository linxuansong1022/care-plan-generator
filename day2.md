# Day 2: MVP

## API设计
提交信息-》生成careplan POST
查询careplan-》拿到结果 GET 包括状态，careplan内容（如果生成成功）
POST /api/orders/      → 提交信息
GET  /api/orders/{id}  → 拿结果

如何验证API设计正确
第一步：我填好了表单，点提交
        → POST /api/orders/ 发送病人信息
        → 后端说："收到了，订单号是 123"

第二步：我想知道 care plan 好了没
        → GET /api/orders/123
        → 后端说："还在生成中（processing）"

第三步：过了一会儿我再查
        → GET /api/orders/123
        → 后端说："好了！这是你的 care plan：[内容]"

walkthrough，就是在antigravity中跑完代码生成的文件，能用嘴流畅说完这个流程，在面试中要体现这个思考过程

## 系统设计面试
20%明确需求 40%数据库设计 40%API设计