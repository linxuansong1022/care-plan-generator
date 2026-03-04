# backend/orders/urls.py

from django.urls import path
from . import views

urlpatterns = [
    # ==========================================
    # Orders (订单路由)
    # ==========================================
    # POST /api/orders/              → 创建新订单
    # GET  /api/orders/              → 获取所有订单
    # GET  /api/orders/?search=jane  → 搜索订单
    path('orders/', views.OrderListCreate.as_view(), name='order-list-create'),

    # GET /api/orders/<id>/          → 获取单个订单详情
    path('orders/<int:pk>/', views.OrderDetail.as_view(), name='order-detail'),

    # POST /api/orders/<id>/retry/   → 重新触发生成 Care Plan 任务（仅支持 failed 状态的订单）
    path('orders/<int:pk>/retry/', views.OrderRetryView.as_view(), name='order-retry'),


    # ==========================================
    # Care Plan & Status (护理计划与状态)
    # ==========================================
    # GET /api/orders/<id>/status/   → 专门留给前端轮询订单生成状态的接口
    path('orders/<int:pk>/status/', views.OrderStatusView.as_view(), name='order-status'),

    # GET /api/orders/<id>/careplan  → 获取生成的 Care Plan 的内容预览
    path('orders/<int:pk>/careplan', views.CarePlanView.as_view(), name='careplan-view'),

    # GET /api/orders/<id>/careplan/download → 下载 Care Plan 为文本文件 (.txt)
    path('orders/<int:pk>/careplan/download', views.CarePlanDownload.as_view(), name='careplan-download'),


    # ==========================================
    # Patients (患者路由)
    # ==========================================
    # POST /api/patients/            → 注册/创建新患者数据
    # GET  /api/patients/            → 分页查询患者列表 (支持 ?search= 模糊搜索名字)
    path('patients/', views.PatientCreateView.as_view(), name='patient-create'),

    # GET    /api/patients/<id>/     → 获取具体的某位患者详情
    # PUT    /api/patients/<id>/     → 更新具体的某位患者信息 (不允许改 MRN)
    # DELETE /api/patients/<id>/     → 删除该患者 (如果有处于 pending/processing 的订单则阻止删除)
    path('patients/<int:pk>/', views.PatientDetail.as_view(), name='patient-detail'),

    # GET /api/patients/<id>/orders/ → 查询该患者所有关联的历史订单
    path('patients/<int:pk>/orders/', views.PatientOrdersView.as_view(), name='patient-orders'),


    # ==========================================
    # Providers (医生路由)
    # ==========================================
    # POST /api/providers/           → 创建新医生信息 (强制校验 NPI 是否重复)
    path('providers/', views.ProviderCreateView.as_view(), name='provider-create'),


    # ==========================================
    # External Integrations (第三方系统接入)
    # ==========================================
    # POST /api/intake/?source=xxx   → 提供给外部系统的通用接收入口 (Webhook)
    path('intake/', views.ExternalIntakeView.as_view(), name='external-intake'),
]
