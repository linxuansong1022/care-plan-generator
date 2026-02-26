# backend/careplan_backend/urls.py
# URL 路由：决定"哪个 URL 交给哪段代码处理"
# 类比：餐厅前台，看你要吃什么菜，把你带到对应的桌子

from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/', include('orders.urls')),  # 保持旧路径兼容
    path('', include('orders.urls')),      # 新路径适配 Lambda: /orders
    path('', include('django_prometheus.urls')),
]
