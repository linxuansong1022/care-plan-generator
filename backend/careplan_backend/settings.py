# backend/careplan_backend/settings.py
# Django 项目的"总配置文件"，所有设置都在这里

import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent

# SECRET_KEY: Django 用来加密 session、CSRF token 等的密钥
# 生产环境要用环境变量，MVP 先硬编码
SECRET_KEY = 'django-insecure-mvp-dev-key-change-this-in-production'

DEBUG = True  # 开发模式，显示详细错误。生产环境要设 False

ALLOWED_HOSTS = ['*']  # MVP 先允许所有 host

# ============================================================
# 安装的 App
# ============================================================
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    # 第三方
    'rest_framework',   # Django REST Framework，帮你快速写 API
    'corsheaders',      # 处理跨域请求（前端 3000 端口 → 后端 8000 端口）
    # 我们的 App
    'orders',           # 订单相关的所有逻辑
]

# ============================================================
# Middleware（中间件）
# 可以理解为"请求进来时经过的一道道关卡"
# ============================================================
MIDDLEWARE = [
    'corsheaders.middleware.CorsMiddleware',  # 必须放最前面！处理跨域
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

# ============================================================
# CORS 设置
# CORS（跨域资源共享）：浏览器安全策略，默认不允许从一个域名请求另一个域名
# 我们前端在 localhost:3000，后端在 localhost:8000，属于跨域
# ============================================================
CORS_ALLOW_ALL_ORIGINS = True  # MVP 先全开，生产环境要限制

ROOT_URLCONF = 'careplan_backend.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

# ============================================================
# 数据库配置
# ============================================================
import dj_database_url

DATABASES = {
    'default': dj_database_url.config(
        default='postgresql://postgres:postgres@db:5432/careplan',
        conn_max_age=600
    )
}

# ============================================================
# REST Framework 配置
# ============================================================
REST_FRAMEWORK = {
    'DEFAULT_RENDERER_CLASSES': [
        'rest_framework.renderers.JSONRenderer',       # 返回 JSON
        'rest_framework.renderers.BrowsableAPIRenderer', # 浏览器访问时显示漂亮的 API 界面
    ],
    'EXCEPTION_HANDLER': 'orders.exception_handler.unified_exception_handler',
}

LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'UTC'
USE_I18N = True
USE_TZ = True

STATIC_URL = 'static/'
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# ============================================================
# Anthropic API Key
# ============================================================
GOOGLE_API_KEY = os.environ.get('GOOGLE_API_KEY', '')


# ============================================================
# Redis 配置（Day 4：消息队列）
# ============================================================
REDIS_URL = os.environ.get('REDIS_URL', 'redis://localhost:6379/0')

# ---- Celery 配置 ----
CELERY_BROKER_URL = REDIS_URL  # 复用你已有的 Redis 连接
CELERY_RESULT_BACKEND = REDIS_URL