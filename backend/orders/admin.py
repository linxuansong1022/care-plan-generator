# backend/orders/admin.py
from django.contrib import admin
from .models import Order

# 注册到 Django Admin，方便你在浏览器里直接查看/管理数据
# 访问 http://localhost:8000/admin/ 就能看到
admin.site.register(Order)
