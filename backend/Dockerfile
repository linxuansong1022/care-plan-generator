# backend/Dockerfile
# Python 环境，安装依赖

FROM python:3.12-slim

WORKDIR /app

# 先复制 requirements.txt 单独安装依赖
# 这样改代码时不需要重新安装依赖（Docker 缓存层的概念）
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8000
