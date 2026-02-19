# backend/orders/views.py

from google import genai
from django.conf import settings
from django.http import HttpResponse
from django.db.models import Q
from rest_framework import generics, status
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import Order
from .serializers import OrderSerializer


def generate_care_plan(order):
    """调用 Google Gemini API 生成 Care Plan（同步）"""
    prompt = f"""You are a clinical pharmacist creating a care plan for a specialty pharmacy patient.

Patient Information:
- Name: {order.patient_first_name} {order.patient_last_name}
- Date of Birth: {order.patient_dob}
- MRN: {order.patient_mrn}

Provider: {order.provider_name} (NPI: {order.provider_npi})

Medication: {order.medication_name}
Primary Diagnosis (ICD-10): {order.primary_diagnosis}
Additional Diagnoses: {', '.join(order.additional_diagnoses) if order.additional_diagnoses else 'None'}
Medication History: {', '.join(order.medication_history) if order.medication_history else 'None'}
Patient Records/Notes: {order.patient_records if order.patient_records else 'None provided'}

Please generate a comprehensive pharmaceutical care plan with EXACTLY these four sections:

1. **Problem List / Drug Therapy Problems (DTPs)**
   - Identify potential drug therapy problems related to the prescribed medication and diagnoses

2. **Goals (SMART format)**
   - Specific, Measurable, Achievable, Relevant, Time-bound goals for this patient

3. **Pharmacist Interventions / Plan**
   - Specific actions the pharmacist should take
   - Patient education points
   - Coordination with the prescribing provider

4. **Monitoring Plan & Lab Schedule**
   - Labs to monitor and frequency
   - Clinical parameters to track
   - Follow-up schedule

Be specific and clinically relevant to the medication and diagnoses provided."""

    try:
        # 配置 Google Gemini 客户端并调用 API
        # 注意：如果是 Vertex AI 的 Key，SDK 会自动识别，前提是你的 Project 里启用了 API
        PROJECT_ID = "cph-beer-map-dev"  # 👈 这里必须改！
        LOCATION = "us-central1"      # 通常用这个
        
        client = genai.Client(
            vertexai=True,
            project=PROJECT_ID,
            location=LOCATION,
            # Vertex AI 通常不需要 API Key，而是通过 gcloud auth 认证
            # 但如果你用了 API Key 方式连接 Vertex AI，也可以传
            # api_key=settings.GOOGLE_API_KEY 
        )
        
        response = client.models.generate_content(
            model='gemini-2.0-flash',
            contents=prompt,
        )
        
        # 从响应中提取文本内容
        return response.text
    except Exception:
        # 异常可在日志中查看，或生产环境记录到监控系统
        return None


class OrderListCreate(generics.ListCreateAPIView):
    """
    GET  /api/orders/              → 返回所有订单
    GET  /api/orders/?search=jane  → 搜索订单（按姓名、MRN、药名）
    POST /api/orders/              → 创建新订单
    """
    serializer_class = OrderSerializer

    def get_queryset(self):
        """
        重写 get_queryset 来支持搜索
        
        Q 对象是 Django ORM 的"条件组合器"：
        Q(a=1) | Q(b=2) 表示 "a=1 OR b=2"
        icontains = case-insensitive 模糊匹配（SQL 的 LIKE '%xxx%'）
        """
        queryset = Order.objects.all().order_by('-created_at')
        
        search = self.request.query_params.get('search', '').strip()
        if search:
            queryset = queryset.filter(
                Q(patient_first_name__icontains=search) |
                Q(patient_last_name__icontains=search) |
                Q(patient_mrn__icontains=search) |
                Q(medication_name__icontains=search)
            )
        
        return queryset

    def create(self, request, *args, **kwargs):
        """创建订单 + 同步调 LLM"""
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        order = serializer.save(status='processing')

        care_plan_content = generate_care_plan(order)

        if care_plan_content:
            order.care_plan_content = care_plan_content
            order.status = 'completed'
        else:
            order.status = 'failed'
        order.save()

        result_serializer = self.get_serializer(order)
        return Response(result_serializer.data, status=status.HTTP_201_CREATED)


class OrderDetail(generics.RetrieveAPIView):
    """GET /api/orders/{id}/ → 单个订单详情"""
    queryset = Order.objects.all()
    serializer_class = OrderSerializer

class CarePlanView(APIView):
    """GET /api/orders/{id}/careplan → 获取 Care Plan 内容"""
    def get(self, request, pk):
        try:
            order = Order.objects.get(pk=pk)
        except Order.DoesNotExist:
            return Response({'error': 'Order does not exist'}, status = status.HTTP_404_NOT_FOUND)
        if order.status != 'completed' or not order.care_plan_content:
            return Response({'error': 'Care plan not available'}, status = status.HTTP_404_NOT_FOUND)
        return Response({
            'order_id':order.id,
            'status': order.status,
            'patient_name':f"{order.patient_first_name} {order.patient_last_name}",
            'medication': order.medication_name,
            'care_plan_content':order.care_plan_content,
            })

class CarePlanDownload(APIView):
    """
    GET /api/orders/{id}/careplan/download → 下载 Care Plan 为 .txt 文件
    
    关键是 Content-Disposition header：
    告诉浏览器"这是一个附件，请弹下载框"，而不是直接显示在页面上。
    类比：同一张纸，装进信封就变成了"附件下载"。
    """
    
    def get(self, request, pk):
        try:
            order = Order.objects.get(pk=pk)
        except Order.DoesNotExist:
            return Response({'error': 'Order not found'}, status=status.HTTP_404_NOT_FOUND)
        
        if order.status != 'completed' or not order.care_plan_content:
            return Response({'error': 'Care plan not available'}, status=status.HTTP_404_NOT_FOUND)
        
        # 组装文件内容：头部信息 + care plan 正文
        file_content = f"""PHARMACEUTICAL CARE PLAN
{'='*50}
Patient: {order.patient_first_name} {order.patient_last_name}
MRN: {order.patient_mrn}
DOB: {order.patient_dob}
Provider: {order.provider_name} (NPI: {order.provider_npi})
Medication: {order.medication_name}
Primary Diagnosis: {order.primary_diagnosis}
Generated: {order.created_at.strftime('%Y-%m-%d %H:%M')}
{'='*50}

{order.care_plan_content}
"""
        
        filename = f"careplan_{order.patient_mrn}_{order.medication_name}_{order.order_date}.txt"
        filename = filename.replace(' ', '_').replace('/', '_')
        
        response = HttpResponse(file_content, content_type='text/plain; charset=utf-8')
        response['Content-Disposition'] = f'attachment; filename="{filename}"'
        return response
