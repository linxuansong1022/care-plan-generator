# backend/orders/urls.py

from django.urls import path
from . import views

urlpatterns = [
    # POST /api/orders/                      → 创建新订单
    # GET  /api/orders/                      → 获取所有订单
    # GET  /api/orders/?search=jane          → 搜索订单
    path('orders/', views.OrderListCreate.as_view(), name='order-list-create'),

    # GET /api/orders/42/                    → 单个订单详情
    path('orders/<int:pk>/', views.OrderDetail.as_view(), name='order-detail'),

    # GET /api/orders/42/careplan/download   → 下载 Care Plan 文件
    path('orders/<int:pk>/careplan/download', views.CarePlanDownload.as_view(), name='careplan-download'),
    # GET /api/orders/42/careplan            → 获取 Care Plan 内容
    path('orders/<int:pk>/careplan', views.CarePlanView.as_view(), name='careplan-view')
]
