# backend/orders/serializers.py
# Serializer（序列化器）的作用：
# 1. 把前端发来的 JSON 转换成 Python 对象（反序列化）
# 2. 把 Python 对象转换成 JSON 返回给前端（序列化）
# 
# 类比：翻译官，在前端（说 JSON）和后端（说 Python）之间翻译

from rest_framework import serializers
from .models import Order


class OrderSerializer(serializers.ModelSerializer):
    """
    自动根据 Order model 的字段生成序列化规则
    ModelSerializer 会自动帮你：
    - 为每个字段创建验证规则
    - 实现 create() 和 update() 方法
    """

    class Meta:
        model = Order
        fields = '__all__'         # 暴露所有字段（MVP 先这样，后续可以精细控制）
        read_only_fields = [       # 这些字段前端不能直接写，由后端控制
            'id',
            'status',
            'order_date',
            'created_at',
            'care_plan_content',
        ]
