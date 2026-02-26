"""
Care Plan model.
"""

import uuid

from django.db import models

from apps.orders.models import Order


class CarePlan(models.Model):
    """
    Generated care plan for an order.
    
    One-to-one relationship with Order.
    """
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    order = models.OneToOneField(
        Order,
        on_delete=models.CASCADE,
        related_name="care_plan",
    )
    
    content = models.TextField(
        help_text="Generated care plan text content",
    )
    
    file_path = models.CharField(
        max_length=500,
        blank=True,
        null=True,
        help_text="Path to the downloadable file (S3 key or local path)",
    )
    
    file_format = models.CharField(
        max_length=10,
        default="txt",
        help_text="File format (txt, pdf, docx)",
    )
    
    # LLM metadata for cost tracking
    llm_model = models.CharField(
        max_length=50,
        blank=True,
        null=True,
        help_text="LLM model used for generation",
    )
    
    llm_prompt_tokens = models.IntegerField(
        blank=True,
        null=True,
        help_text="Number of input tokens",
    )
    
    llm_completion_tokens = models.IntegerField(
        blank=True,
        null=True,
        help_text="Number of output tokens",
    )
    
    generation_time_ms = models.IntegerField(
        blank=True,
        null=True,
        help_text="Time taken to generate in milliseconds",
    )

    generated_at = models.DateTimeField(
        blank=True,
        null=True,
        help_text="When the LLM completed generation",
    )

    # Track if this was manually uploaded vs LLM-generated
    is_uploaded = models.BooleanField(
        default=False,
        help_text="True if care plan was manually uploaded, False if LLM-generated",
    )

    uploaded_at = models.DateTimeField(
        blank=True,
        null=True,
        help_text="When the care plan was manually uploaded",
    )

    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = "care_plans"
        indexes = [
            models.Index(fields=["order"]),
            models.Index(fields=["generated_at"]),
        ]
    
    def __str__(self):
        return f"CarePlan for Order {self.order_id}"
    
    @property
    def total_tokens(self):
        if self.llm_prompt_tokens and self.llm_completion_tokens:
            return self.llm_prompt_tokens + self.llm_completion_tokens
        return None
