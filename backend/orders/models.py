# backend/orders/models.py
# Model 定义了数据库表的结构
# Django ORM 会根据这个 Python class 自动帮你创建 SQL 表
#
# 【Day 2 故意的简化】
# 现在把所有数据塞在一张表里（Order），没有分 Patient、Provider 表
# 你会发现：如果同一个患者下了 3 个订单，患者信息被存了 3 遍
# 这就是 Day 3 要解决的问题——数据库范式化（Normalization）

from django.db import models


class Order(models.Model):
    """
    订单表：一个订单 = 一个患者 + 一种药 + 一份 Care Plan
    
    MVP 阶段把所有字段平铺在一张表里，不做分表。
    """

    # ---------- 状态选项 ----------
    # Django 的 choices 机制：限制字段只能取这几个值
    STATUS_CHOICES = [
        ('pending', 'Pending'),         # 刚提交，等待处理
        ('processing', 'Processing'),   # 正在调 LLM
        ('completed', 'Completed'),     # Care Plan 生成成功
        ('failed', 'Failed'),           # 生成失败
    ]

    # ---------- 患者信息 ----------
    patient_first_name = models.CharField(max_length=100)
    patient_last_name = models.CharField(max_length=100)
    patient_mrn = models.CharField(max_length=6)      # Medical Record Number
    patient_dob = models.DateField()                    # Date of Birth

    # ---------- 医生信息 ----------
    provider_name = models.CharField(max_length=200)
    provider_npi = models.CharField(max_length=10)     # National Provider Identifier

    # ---------- 药物 & 诊断 ----------
    medication_name = models.CharField(max_length=200)
    primary_diagnosis = models.CharField(max_length=20)  # ICD-10 code
    # JSONField: 存 Python list/dict，PostgreSQL 原生支持 JSON 类型
    additional_diagnoses = models.JSONField(default=list, blank=True)
    medication_history = models.JSONField(default=list, blank=True)
    patient_records = models.TextField(blank=True, default='')

    # ---------- 订单元数据 ----------
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    order_date = models.DateField(auto_now_add=True)  # 自动设为创建当天
    created_at = models.DateTimeField(auto_now_add=True)

    # ---------- Care Plan ----------
    # 直接存在 Order 表里（Day 3 会拆成单独的 CarePlan 表）
    care_plan_content = models.TextField(blank=True, default='')

    def __str__(self):
        return f"Order #{self.id} - {self.patient_last_name}, {self.patient_first_name} - {self.medication_name}"
