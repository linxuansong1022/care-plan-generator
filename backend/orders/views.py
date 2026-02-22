# backend/orders/views.py
"""
Controller 层（views.py）
========================
只负责：接收 HTTP 请求 → 调 serializer 校验 → 调 service 处理 → 返回 HTTP 响应
不做任何业务逻辑（不直接操作数据库、不调 LLM、不知道 Redis/Celery 的存在）
"""
from django.http import HttpResponse
from django.db.models import Q
from rest_framework import generics, status
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import Order
from .serializers import OrderSerializer
from . import services


class OrderListCreate(generics.ListCreateAPIView):
    """
    GET  /api/orders/              → 返回所有订单
    GET  /api/orders/?search=jane  → 搜索订单（按姓名、MRN、药名）
    POST /api/orders/              → 创建新订单
    """
    serializer_class = OrderSerializer

    def get_queryset(self):
        queryset = Order.objects.all().order_by('-created_at')

        search = self.request.query_params.get('search', '').strip()
        if search:
            queryset = queryset.filter(
                Q(patient__first_name__icontains=search) |
                Q(patient__last_name__icontains=search) |
                Q(patient__mrn__icontains=search) |
                Q(medication_name__icontains=search)
            )

        return queryset

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(
            data=request.data,
            context={'confirm': request.data.get('confirm', False)}  # 传给 serializer
        )
        serializer.is_valid(raise_exception=True)
        
        # serializer.save() 会触发 serializer 的 create() 
        # 进而触发 services.create_order()，遇到任何校验失败都会抛出异常，被全局异常处理器捕获
        order = serializer.save(status='pending')
        
        services.submit_care_plan_task(order.id)
        result_serializer = self.get_serializer(order)
        return Response(result_serializer.data, status=status.HTTP_202_ACCEPTED)

class OrderDetail(generics.RetrieveAPIView):
    """GET /api/orders/{id}/ → 单个订单详情"""
    queryset = Order.objects.all()
    serializer_class = OrderSerializer


class OrderStatusView(APIView):
    """GET /api/orders/{id}/status/ → 专门给前端轮询用的状态接口"""

    def get(self, request, pk):
        data = services.get_order_status(pk)
        if data is None:
            return Response({'error': 'Order not found'}, status=status.HTTP_404_NOT_FOUND)
        return Response(data, status=status.HTTP_200_OK)


class CarePlanView(APIView):
    """GET /api/orders/{id}/careplan → 获取 Care Plan 内容"""

    def get(self, request, pk):
        result = services.get_care_plan_detail(pk)
        if 'error' in result:
            return Response(result, status=status.HTTP_404_NOT_FOUND)
        return Response(result, status=status.HTTP_200_OK)


class CarePlanDownload(APIView):
    """GET /api/orders/{id}/careplan/download → 下载 Care Plan 为 .txt 文件"""

    def get(self, request, pk):
        file_content, filename = services.build_care_plan_file(pk)
        if file_content is None:
            return Response({'error': filename}, status=status.HTTP_404_NOT_FOUND)

        response = HttpResponse(file_content, content_type='text/plain; charset=utf-8')
        response['Content-Disposition'] = f'attachment; filename="{filename}"'
        return response
