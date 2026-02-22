# backend/orders/serializers.py
"""
Serializer（序列化器）
====================
只负责：前端 JSON ↔ 后端 Python 对象 的格式转换和字段声明
不做业务逻辑（get_or_create 等操作已搬到 services.py）
"""
from rest_framework import serializers
from .models import Order, Patient, Provider


class OrderSerializer(serializers.ModelSerializer):
    # 前端发来的平铺字段（write_only=True 表示只接收，不返回）
    patient_first_name = serializers.CharField(write_only=True)
    patient_last_name = serializers.CharField(write_only=True)
    patient_mrn = serializers.CharField(write_only=True)
    patient_dob = serializers.DateField(write_only=True)

    provider_name = serializers.CharField(write_only=True)
    provider_npi = serializers.CharField(write_only=True)

    # 动态获取关联的 CarePlan 内容（read_only，返回给前端用）
    care_plan_content = serializers.SerializerMethodField()

    class Meta:
        model = Order
        fields = '__all__'
        read_only_fields = ['id', 'status', 'order_date', 'created_at', 'patient', 'provider']

    def get_care_plan_content(self, obj):
        """如果这个订单有关联的 care_plan，就返回内容；否则返回 None"""
        if hasattr(obj, 'care_plan'):
            return obj.care_plan.content
        return None

    def create(self, validated_data):
        from .services import create_order
        from .adapters.base import InternalOrder, InternalPatient, InternalProvider
        
        confirm = self.context.get('confirm', False)
        
        # 将 DRF 吐出的平铺字典，装配成业务层要求的 InternalOrder 数据包 
        internal_order = InternalOrder(
            patient=InternalPatient(
                first_name=validated_data.get('patient_first_name', ''),
                last_name=validated_data.get('patient_last_name', ''),
                mrn=validated_data.get('patient_mrn', ''),
                # dob 是 DateField，转出来是 datetime.date 对象，我们需要 string
                dob=str(validated_data.get('patient_dob', ''))
            ),
            provider=InternalProvider(
                name=validated_data.get('provider_name', ''),
                npi=validated_data.get('provider_npi', '')
            ),
            medication_name=validated_data.get('medication_name', ''),
            primary_diagnosis=validated_data.get('primary_diagnosis', ''),
            additional_diagnoses=validated_data.get('additional_diagnoses', []),
            medication_history=validated_data.get('medication_history', []),
            patient_records=validated_data.get('patient_records', ''),
            confirm=confirm
        )
        
        # 将组装好的公文包，递给纯洁的内核业务函数！
        return create_order(internal_order)
