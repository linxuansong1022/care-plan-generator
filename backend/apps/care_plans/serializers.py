"""
Care Plan serializers.
"""

from rest_framework import serializers

from .models import CarePlan


class CarePlanSerializer(serializers.ModelSerializer):
    """Full serializer for CarePlan model."""
    
    total_tokens = serializers.IntegerField(read_only=True)
    
    class Meta:
        model = CarePlan
        fields = [
            "id",
            "order_id",
            "content",
            "file_path",
            "file_format",
            "llm_model",
            "llm_prompt_tokens",
            "llm_completion_tokens",
            "total_tokens",
            "generation_time_ms",
            "generated_at",
            "created_at",
        ]
        read_only_fields = fields


class CarePlanStatusSerializer(serializers.Serializer):
    """Serializer for care plan status check."""
    
    order_id = serializers.UUIDField()
    status = serializers.CharField()
    care_plan_available = serializers.BooleanField()
    error_message = serializers.CharField(allow_null=True, required=False)
