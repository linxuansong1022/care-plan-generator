# ========== 框架部分 ==========
from celery import shared_task                    # 框架：导入 Celery 的装饰器
from celery.exceptions import MaxRetriesExceededError  # 框架：导入重试用完的异常

# ========== 你的业务代码 ==========
from .models import Order, CarePlan               # 你的：数据库模型
           # 你的：LLM 调用逻辑


# ========== 框架部分 ==========
@shared_task(bind=True, max_retries=3)            # 框架：这个装饰器做了三件事
                                                  #   1. 把普通函数注册为 Celery 任务
                                                  #   2. bind=True 让你能用 self
                                                  #   3. max_retries=3 设置最大重试次数
def generate_care_plan_task(self, order_id):       # 框架：self 是 Celery 注入的任务实例
    from .views import generate_care_plan  
    # ========== 以下全是你的业务逻辑 ==========
    try:
        order = Order.objects.get(id=order_id)
    except Order.DoesNotExist:
        print(f"❌ Order {order_id} not found, skipping")
        return

    try:
        order.status = 'processing'
        order.save()
        content = generate_care_plan(order)

        if content is None:
            raise Exception("LLM returned None")  # 你的：手动抛异常触发重试

        CarePlan.objects.create(order=order, content=content)
        order.status = 'completed'
        order.save()

    # ========== 框架部分 ==========
    except MaxRetriesExceededError:               # 框架：Celery 在重试用完时自动抛这个
        # ========== 你的业务逻辑 ==========
        order.status = 'failed'
        order.save()

    except Exception as e:
        # ========== 框架部分 ==========
        raise self.retry(                         # 框架：self.retry() 做了三件事
            exc=e,                                #   1. 把任务重新放回 Redis 队列
            countdown=2 ** self.request.retries    #   2. 设置等多久后重新执行
        )                                         #   3. self.request.retries 自动计数