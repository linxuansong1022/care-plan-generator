# backend/orders/views.py
"""
Controller 层（views.py）
========================
只负责：接收 HTTP 请求 → 调 serializer 校验 → 调 service 处理 → 返回 HTTP 响应
不做任何业务逻辑（不直接操作数据库、不调 LLM、不知道 Redis/Celery 的存在）
"""
from django.template.defaultfilters import first
from django.http import HttpResponse
from django.db.models import Q
from rest_framework import generics, status
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import Order
from .models import Order, Patient
from .serializers import OrderSerializer, PatientSerializer
from . import services
from .serializers import OrderSerializer, PatientSerializer, ProviderSerializer
from .models import Order, Patient, Provider


class OrderListCreate(generics.ListCreateAPIView):
    """
    GET  /api/orders/              → 返回所有订单
    GET  /api/orders/?search=jane  → 搜索订单（按姓名、MRN、药名）
    POST /api/orders/              → 创建新订单
    """
    serializer_class = OrderSerializer

    def get_queryset(self):
        queryset = Order.objects.all().order_by('-created_at')

        # 优先处理 order_id（匹配 Lambda 的单接口参数名）
        order_id = self.request.query_params.get('order_id', '').strip()
        if order_id:
            # 尝试作为 ID 匹配，或者作为 MRN 匹配
            if order_id.isdigit():
                queryset = queryset.filter(Q(id=order_id) | Q(patient__mrn=order_id))
            else:
                queryset = queryset.filter(Q(patient__mrn=order_id))
            return queryset

        # 保持对旧 search 参数的支持
        search = self.request.query_params.get('search', '').strip()
        if search:
            queryset = queryset.filter(
                Q(patient__first_name__icontains=search) |
                Q(patient__last_name__icontains=search) |
                Q(patient__mrn__icontains=search) |
                Q(medication_name__icontains=search)
            )
        
        status_filter = self.request.query_params.get('status','').strip()
        if status_filter:
            queryset = queryset.filter(status = status_filter)
        
        patient_name = self.request.query_params.get('patient_name','').strip()
        if patient_name:
            queryset = queryset.filter(
                Q(patient__first_name__icontains = patient_name) |
                Q(patient__last_name__icontains = patient_name)
            )

        return queryset

    # ── 新增：override list() 加分页 ─────────────────────────────
    def list(self, request, *args, **kwargs):
        queryset = self.get_queryset()

        # 读参数，做好防御
        try:
            page = max(1, int(request.query_params.get('page', 1)))
            page_size = min(100, max(1, int(request.query_params.get('page_size', 20))))
        except (ValueError, TypeError):
            page = 1
            page_size = 20

        # 先算总数，再切片（顺序不能反！）
        total_count = queryset.count()
        start = (page - 1) * page_size
        orders = queryset[start : start + page_size]

        serializer = self.get_serializer(orders, many=True)
        return Response({
            'count': total_count,
            'page': page,
            'page_size': page_size,
            'results': serializer.data
        })

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


class ExternalIntakeView(APIView):
    """
    Webhook: 接收外部异构系统的数据 (POST /api/intake/?source=xxx)
    """
    authentication_classes = [] 
    permission_classes = []
    
    def post(self, request, *args, **kwargs):
        from .adapters import get_adapter
        from .adapters.base import AdapterError
        from .services import create_order
        
        source = request.query_params.get('source')
        if not source:
            return Response({"error": "Missing 'source' parameter"}, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            # 1. adapter 转换
            adapter = get_adapter(source)
            if source in ("pharmacorp", "nordic"):
                raw = request.body
            else:
                raw = request.data
            internal_order = adapter.process(raw)
            
            # 2. 过 serializer 验证（MRN 6位、NPI 10位等）
            serializer = OrderSerializer(
                data=internal_order.to_serializer_format(),
                context={'confirm': internal_order.confirm}
            )
            serializer.is_valid(raise_exception=True)

            # 3. 验证通过 → 走正常的创建流程
            order = serializer.save(status='pending')

            # 4. 触发异步任务（你之前漏掉的）
            services.submit_care_plan_task(order.id)
            
            return Response({
                "message": f"Order created via {source}", 
                "order_id": order.id
            }, status=status.HTTP_201_CREATED)
            
        except ValueError as e: 
            # 找不到对应的 source (比如传错了名字)
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)
            
        except AdapterError as e: 
            # 数据转换失败 (比如必填项缺失，数据格式不对)
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)

class PatientCreateView(APIView):
    def post(self, request):
        # 第1步：验证数据
        serializer = PatientSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(
                {"error": "Validation failed", "details": serializer.errors},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # 第2步：检查重复（同名+同生日）
        first_name = request.data.get('first_name')
        last_name  = request.data.get('last_name')
        dob        = request.data.get('dob')
        
        existing = Patient.objects.filter(
            first_name=first_name,
            last_name=last_name,
            dob=dob
        ).first()
        
        if existing:
            return Response(
                {
                    "warning": "A patient with the same name and date of birth already exists",
                    "existing_patient_id": existing.id
                },
                status=status.HTTP_409_CONFLICT
            )
        
        # 第3步：存数据库，返回 201
        patient = serializer.save()
        return Response(serializer.data, status=status.HTTP_201_CREATED)
    
    def get(self,request):
        queryset = Patient.objects.all().order_by('-created_at')
        #按照名字搜索
        search = request.query_params.get('search','').strip()
        #如果有search 过滤名字 模糊查询
        if search:
            queryset = queryset.filter(
                Q(first_name__icontains=search) |
                Q(last_name__icontains=search)
            )
        #4 读分页参数
        page = max(1,int(request.query_params.get('page',1)))
        page_size = min(100, max(1, int(request.query_params.get('page_size', 20))))

        #5算总数
        total_count = queryset.count()

        #6 切片
        start = (page - 1) * page_size
        patients = queryset[start:start+page_size]
        #7 序列化 
        serializer = PatientSerializer(patients ,many=True)

        return Response({
            'count':total_count,
            'page':page,
            'page_size':page_size,
            'results':serializer.data,
        })

class PatientDetail(APIView):
    """GET /api/patient/id/ → 单个患者详情"""
    def get(self,request,pk):
        patient = Patient.objects.filter(pk=pk).first()
        if not patient:
            return Response({'error':'Patient not found'},status =404)
        serializer = PatientSerializer(patient)
        return Response(serializer.data)

    def put(self,request,pk):
        patient = Patient.objects.filter(pk=pk).first()
        if not patient:
            return Response({'error':'Patient not found'},status =404)
        
        if 'mrn' in request.data:
            return Response(
                {'error': 'Validation failed','details':{'mrn': 'MRN cannot be modified'}},
                status = 400
            )
        
        serializer = PatientSerializer(patient, data = request.data, partial = True)
        if not serializer.is_valid():
            return Response(
                {'error': 'Validation failed','details':serializer.errors},
                status = 400
            )
        serializer.save()
        return Response(serializer.data,status=200)
    
    def delete(self, request, pk):
        # 第1步：找患者
        patient = Patient.objects.filter(pk=pk).first()
        if not patient:
            return Response({'error': 'Patient not found'}, status=404)
        
        # 第2步：检查有没有 pending/processing 的订单
        active_orders = Order.objects.filter(
            patient=patient,
            status__in=['pending', 'processing']
        )
        if active_orders.exists():
            return Response({
                'error': 'Cannot delete patient with active orders',
                'active_orders': list(active_orders.values_list('id', flat=True))
            }, status=409)
        
        # 第3步：删除
        patient.delete()
        return Response(status=204)
    
class ProviderCreateView(APIView):
    def post(self, request):
        # 第1步：验证
        serializer = ProviderSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(
                {'error': 'Validation failed', 'details': serializer.errors},
                status=400
            )
        
        # 第2步：同名不同NPI → 警告
        name = request.data.get('name')
        npi  = request.data.get('npi')
        existing = Provider.objects.filter(name=name).exclude(npi=npi).first()
        if existing:
            return Response({
                'warning': f"A provider named '{name}' already exists with NPI {existing.npi}. Please verify this is not a duplicate.",
                'existing_provider_id': existing.id
            }, status=409)
        
        # 第3步：创建
        provider = serializer.save()
        return Response(serializer.data, status=201)
# ─── Ticket 8: GET /patients/{id}/orders ────────────────────
class PatientOrdersView(APIView):
    def get(self, request, pk):
        patient = Patient.objects.filter(pk=pk).first()
        if not patient:
            return Response({'error': 'Patient not found'}, status=404)
        
        orders = Order.objects.filter(patient=patient).order_by('-created_at')
        return Response({
            'patient_id': patient.id,
            'patient_name': f"{patient.first_name} {patient.last_name}",
            'orders': [
                {
                    'id': o.id,
                    'medication_name': o.medication_name,
                    'status': o.status,
                    'created_at': o.created_at,
                }
                for o in orders
            ]
        })
# ─── Ticket 11: POST /orders/{id}/retry ─────────────────────
class OrderRetryView(APIView):
    def post(self, request, pk):
        order = Order.objects.filter(pk=pk).first()
        if not order:
            return Response({'error': 'Order not found'}, status=404)
        
        # 只有 failed 才能重试
        if order.status != 'failed':
            return Response({
                'error': 'Order is not in failed status',
                'current_status': order.status
            }, status=409)
        
        # 重置状态，重新触发任务
        order.status = 'pending'
        order.save()
        services.submit_care_plan_task(order.id)
        
        return Response({
            'order_id': order.id,
            'status': 'processing',
            'message': 'CarePlan generation restarted'
        }, status=202)

