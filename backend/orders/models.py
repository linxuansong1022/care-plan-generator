# backend/orders/models.py
#
# Day 3：数据库范式化（Normalization）
# 把 Day 2 的一张大表拆成 4 张表：Patient, Provider, Order, CarePlan
#
# 为什么要拆？
# Day 2 里同一个患者下 3 个订单 → 患者信息存了 3 遍（浪费+不一致风险）
# 现在 Patient 表只存 1 条 → 3 个 Order 通过外键指向它

from django.db import models


class Patient(models.Model):
    """
    患者表
    
    唯一标识：MRN（Medical Record Number）
    一个患者可以有多个订单（一对多关系）
    """
    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100)
    mrn = models.CharField(max_length=6, unique=True)  # unique=True → 数据库层面保证不重复
    dob = models.DateField()                             # Date of Birth
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.last_name}, {self.first_name} (MRN: {self.mrn})"


class Provider(models.Model):
    """
    医生/处方者表
    
    唯一标识：NPI（National Provider Identifier）
    一个医生可以关联多个订单（一对多关系）
    """
    name = models.CharField(max_length=200)
    npi = models.CharField(max_length=10, unique=True)   # 10 位数字，唯一
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.name} (NPI: {self.npi})"


class Order(models.Model):
    """
    订单表
    
    一个订单 = 一个患者 + 一个医生 + 一种药物
    
    ForeignKey 就是"外键"——指向另一张表的某条记录
    类比：订单上写了"患者编号: 3"，去 Patient 表查编号 3 就能找到对应患者
    
    on_delete=models.CASCADE：如果患者被删了，他的订单也跟着删
    （CASCADE = 级联删除，像多米诺骨牌一样连锁）
    """

    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('processing', 'Processing'),
        ('completed', 'Completed'),
        ('failed', 'Failed'),
    ]

    # ---------- 外键关系 ----------
    patient = models.ForeignKey(Patient, on_delete=models.CASCADE, related_name='orders')
    provider = models.ForeignKey(Provider, on_delete=models.CASCADE, related_name='orders')
    # related_name='orders' 让你可以反向查询：patient.orders.all() → 这个患者的所有订单

    # ---------- 药物 & 诊断 ----------
    medication_name = models.CharField(max_length=200)
    primary_diagnosis = models.CharField(max_length=20)    # ICD-10 code
    additional_diagnoses = models.JSONField(default=list, blank=True)
    medication_history = models.JSONField(default=list, blank=True)
    patient_records = models.TextField(blank=True, default='')

    # ---------- 订单元数据 ----------
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    order_date = models.DateField(auto_now_add=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Order #{self.id} - {self.patient} - {self.medication_name}"


class CarePlan(models.Model):
    """
    Care Plan 表
    
    一个订单对应一个 Care Plan（一对一关系）
    OneToOneField = ForeignKey + unique 约束
    
    只有当 LLM 成功生成 care plan 后，才会创建这条记录
    所以 Order.status='pending' 时，CarePlan 记录不存在
    """
    order = models.OneToOneField(Order, on_delete=models.CASCADE, related_name='care_plan')
    # OneToOneField：一个 Order 只能有一个 CarePlan，反过来也是
    # related_name='care_plan' → order.care_plan 就能拿到对应的 CarePlan

    content = models.TextField()           # LLM 生成的 care plan 正文
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"CarePlan for Order #{self.order_id}"
