# backend/orders/tasks.py
"""
Celery 异步任务
==============
Worker 从 Redis 队列取任务，调用 services 层的业务逻辑
"""
from celery import shared_task
from celery.exceptions import MaxRetriesExceededError

from .models import Order, CarePlan


@shared_task(bind=True, max_retries=3)
def generate_care_plan_task(self, order_id):
    from .services import CarePlanService

    try:
        order = Order.objects.get(id=order_id)
    except Order.DoesNotExist:
        print(f"❌ Order {order_id} not found, skipping")
        return

    try:
        order.status = 'processing'
        order.save()
        services = CarePlanService()
        content = services.generate_care_plan(order)

        if content is None:
            raise Exception("LLM returned None")

        CarePlan.objects.create(order=order, content=content)
        order.status = 'completed'
        order.save()

    except MaxRetriesExceededError:
        order.status = 'failed'
        order.save()

    except Exception as e:
        raise self.retry(
            exc=e,
            countdown=2 ** self.request.retries
        )
