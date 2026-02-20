# backend/orders/serializers.py
# Serializer（序列化器）的作用：
# 1. 把前端发来的 JSON 转换成 Python 对象（反序列化）
# 2. 把 Python 对象转换成 JSON 返回给前端（序列化）
# 
# 类比：翻译官，在前端（说 JSON）和后端（说 Python）之间翻译

from rest_framework import serializers
from .models import Order, Patient, Provider


class OrderSerializer(serializers.ModelSerializer):
    # 手动定义这些不属于 Order 表的字段 (write_only=True 表示只接收，不返回)
    # 这些字段必须和前端发来的 JSON key 完全一致
    patient_first_name = serializers.CharField(write_only=True)
    patient_last_name = serializers.CharField(write_only=True)
    patient_mrn = serializers.CharField(write_only=True)
    patient_dob = serializers.DateField(write_only=True)
    
    provider_name = serializers.CharField(write_only=True)
    provider_npi = serializers.CharField(write_only=True)

    class Meta:
        model = Order
        fields = '__all__'
        read_only_fields = ['id', 'status', 'order_date', 'created_at', 'patient', 'provider']

    def create(self, validated_data):
        # 1. 把平铺的数据拆出来
        # .pop() 会把这些字段从 validated_data 里拿出来并删掉
        # 这样剩下的 validated_data 就全是属于 Order 表的字段了
        patient_data = {
            'first_name': validated_data.pop('patient_first_name'),
            'last_name': validated_data.pop('patient_last_name'),
            'mrn': validated_data.pop('patient_mrn'),
            'dob': validated_data.pop('patient_dob'),
        }
        
        provider_data = {
            'name': validated_data.pop('provider_name'),
            'npi': validated_data.pop('provider_npi'),
        }

        # 2. 查找或创建 Patient (避免重复创建)
        # get_or_create: 根据 mrn 查找，如果找不到就用 defaults 里的数据创建一个新的
        patient, created = Patient.objects.get_or_create(
            mrn=patient_data['mrn'], 
            defaults=patient_data
        )

        # 3. 查找或创建 Provider
        # 同理，根据 npi 查找医生
        provider, created = Provider.objects.get_or_create(
            npi=provider_data['npi'],
            defaults=provider_data
        )

        # 4. 创建 Order (关联刚才拿到的 patient 和 provider 对象)
        # 这里的 **validated_data 里只剩下 medication_name, primary_diagnosis 等字段了
        order = Order.objects.create(
            patient=patient, 
            provider=provider, 
            **validated_data
        )
        return order

    # 动态获取关联表里的 CarePlan 内容
    care_plan_content = serializers.SerializerMethodField()

    def get_care_plan_content(self, obj):
        # 如果这个订单有关联的 care_plan，就返回内容；否则返回 None
        if hasattr(obj, 'care_plan'):
            return obj.care_plan.content
        return None
