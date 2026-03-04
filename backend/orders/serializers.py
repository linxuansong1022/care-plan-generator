# backend/orders/serializers.py
from rest_framework import serializers
from .models import Order, Patient, Provider

class PatientInputSerializer(serializers.Serializer):
    first_name = serializers.CharField()
    last_name = serializers.CharField()
    mrn = serializers.CharField()
    dob = serializers.DateField()

class ProviderInputSerializer(serializers.Serializer):
    name = serializers.CharField()
    npi = serializers.CharField()

class OrderSerializer(serializers.ModelSerializer):
    # 改为嵌套接收，匹配前端 payload 的嵌套结构 (patient.first_name 等)
    patient = PatientInputSerializer(required=False)
    provider = ProviderInputSerializer(required=False)

    # 动态获取关联的 CarePlan 内容 (只读)
    care_plan_content = serializers.SerializerMethodField()
    # 增加 order_id 字段，匹配 Lambda 返回结果
    order_id = serializers.IntegerField(source='id', read_only=True)

    # 兼容字段：Lambda 返回结果里是 patient_name
    patient_name = serializers.SerializerMethodField()
    provider_name_display = serializers.SerializerMethodField()

    class Meta:
        model = Order
        fields = '__all__'
        read_only_fields = ['id', 'status', 'order_date', 'created_at']

    def get_care_plan_content(self, obj):
        if hasattr(obj, 'care_plan'):
            return obj.care_plan.content
        return None

    def get_patient_name(self, obj):
        return f"{obj.patient.first_name} {obj.patient.last_name}" if obj.patient else ""

    def get_provider_name_display(self, obj):
        return obj.provider.name if obj.provider else ""

    def create(self, validated_data):
        from .services import create_order
        from .adapters.base import InternalOrder, InternalPatient, InternalProvider
        
        confirm = self.context.get('confirm', False)
        
        # 处理嵌套数据
        patient_data = validated_data.pop('patient', {})
        provider_data = validated_data.pop('provider', {})
        
        internal_order = InternalOrder(
            patient=InternalPatient(
                first_name=patient_data.get('first_name', ''),
                last_name=patient_data.get('last_name', ''),
                mrn=patient_data.get('mrn', ''),
                dob=str(patient_data.get('dob', ''))
            ),
            provider=InternalProvider(
                name=provider_data.get('name', ''),
                npi=provider_data.get('npi', '')
            ),
            medication_name=validated_data.get('medication_name', ''),
            primary_diagnosis=validated_data.get('primary_diagnosis', ''),
            additional_diagnoses=validated_data.get('additional_diagnoses', []),
            medication_history=validated_data.get('medication_history', []),
            patient_records=validated_data.get('patient_records', ''),
            confirm=confirm
        )
        
        return create_order(internal_order)

class PatientSerializer(serializers.ModelSerializer):
    class Meta:
        model = Patient
        fields = [
            'id', 'first_name', 'last_name', 'mrn',
            'dob', 'sex', 'weight_kg', 'allergies',
            'primary_diagnosis', 'additional_diagnoses', 'created_at'
        ]
        read_only_fields = ['id', 'created_at']

    def validate_mrn(self,value):
        if not value.isdigit() or len(value) !=6:
            raise serializers.ValidationError("MRN must be exactly 6 digits")
        return value

    def validate_weight_kg(self, value):
        # weight_kg 必须大于 0
        if value is not None and value <= 0:
            raise serializers.ValidationError("Weight must be greater than 0")
        return value

    def validate_primary_diagnosis(self, value):
        # ICD-10 格式：1个字母 + 2位数字 + 可选小数点和更多数字
        # 例如：G70.00 ✅   R51 ✅   abc ❌
        import re
        if value and not re.match(r'^[A-Z][0-9]{2}(\.[0-9]+)?$', value):
            raise serializers.ValidationError("Invalid ICD-10 format")
        return value
