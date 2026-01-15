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
            "is_uploaded",
            "uploaded_at",
            "created_at",
        ]
        read_only_fields = fields


class CarePlanUploadSerializer(serializers.Serializer):
    """Serializer for uploading a custom care plan."""

    content = serializers.CharField(
        required=False,
        allow_blank=True,
        help_text="Care plan text content (provide either content or file)",
    )
    file = serializers.FileField(
        required=False,
        help_text="Care plan file (txt format)",
    )

    def validate(self, data):
        """Ensure either content or file is provided."""
        content = data.get("content")
        file = data.get("file")

        if not content and not file:
            raise serializers.ValidationError(
                "Either 'content' or 'file' must be provided."
            )

        if file:
            # Read file content
            try:
                data["content"] = file.read().decode("utf-8")
            except UnicodeDecodeError:
                raise serializers.ValidationError(
                    "File must be a valid UTF-8 text file."
                )

        return data


class CarePlanStatusSerializer(serializers.Serializer):
    """Serializer for care plan status check."""
    
    order_id = serializers.UUIDField()
    status = serializers.CharField()
    care_plan_available = serializers.BooleanField()
    error_message = serializers.CharField(allow_null=True, required=False)
