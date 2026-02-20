# frontend/Dockerfile
FROM node:20-slim

WORKDIR /app

# 先复制 package.json 安装依赖（利用 Docker 缓存）
COPY package.json package-lock.json* ./
RUN npm install

COPY . .

EXPOSE 3000

# React 开发服务器
CMD ["npm", "start"]
