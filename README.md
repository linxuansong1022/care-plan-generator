# CarePlan Generator - MVP (Day 2)

CVS Specialty Pharmacy 自动 Care Plan 生成系统

## 快速启动

### 前提条件
- Docker Desktop 已安装并运行
- 一个 Anthropic API Key（从 https://console.anthropic.com 获取）

### 启动步骤

```bash
# 1. 把你的 API Key 填到 .env 文件里
#    打开 .env，把 sk-ant-xxxxx 替换成你的真实 key
cp .env.example .env  # 或者直接编辑 .env

# 2. 一键启动所有服务
docker compose up --build

# 3. 等所有容器启动完毕后，打开浏览器
#    前端：http://localhost:3000
#    后端 API：http://localhost:8000/api/orders/
```

### 测试数据

在前端表单里填写：
- Patient First Name: `Jane`
- Patient Last Name: `Doe`
- MRN: `123456`
- DOB: `1979-06-08`
- Provider: `Dr. Smith`
- NPI: `1234567890`
- Medication: `IVIG`
- Primary Diagnosis: `G70.01`

点 Submit，等待 10-30 秒后应该能看到生成的 Care Plan。

### 停止服务

```bash
docker compose down          # 停止容器
docker compose down -v       # 停止容器 + 删除数据库数据
```

## 项目结构

```
careplan-mvp/
├── docker-compose.yml       # 定义所有容器
├── .env                     # 环境变量（API Key 等）
├── backend/
│   ├── Dockerfile
│   ├── requirements.txt
│   ├── manage.py
│   ├── careplan_backend/    # Django 项目配置
│   │   ├── settings.py
│   │   └── urls.py
│   └── orders/              # 业务逻辑
│       ├── models.py        # 数据库表定义
│       ├── views.py         # API 处理逻辑 + LLM 调用
│       ├── serializers.py   # JSON 序列化
│       └── urls.py          # URL 路由
└── frontend/
    ├── Dockerfile
    ├── package.json
    ├── public/index.html
    └── src/
        ├── index.js
        └── App.js           # 整个前端（表单 + 结果显示）
```

## 已知限制（Day 2 故意留下的，后续会逐步修复）

- ⏳ 同步调 LLM，提交后要等 10-30 秒
- 📦 所有数据在一张表里，没有分 Patient/Provider/Order
- ❌ 没有输入验证（MRN 格式、NPI 格式、ICD-10 格式）
- ❌ 没有重复检测
- ❌ 没有 error handling（LLM 报错就炸了）
- ❌ 所有逻辑在一个文件里，没有分层
