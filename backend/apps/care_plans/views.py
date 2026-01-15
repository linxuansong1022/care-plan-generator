"""
Care Plan views.
"""

import os
from datetime import datetime

import structlog
from django.http import FileResponse, Http404
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.parsers import FormParser, JSONParser, MultiPartParser
from rest_framework.response import Response

from apps.orders.models import Order

from .models import CarePlan
from .serializers import CarePlanSerializer, CarePlanStatusSerializer, CarePlanUploadSerializer

logger = structlog.get_logger(__name__)


class CarePlanViewSet(viewsets.ReadOnlyModelViewSet):
    """
    ViewSet for CarePlan model.

    Supports both LLM-generated and manually uploaded care plans.
    """

    queryset = CarePlan.objects.select_related("order").all()
    serializer_class = CarePlanSerializer
    parser_classes = [JSONParser, MultiPartParser, FormParser]
    
    @action(detail=False, methods=["get"], url_path="by-order/(?P<order_id>[^/.]+)")
    def by_order(self, request, order_id=None):
        """Get care plan by order ID."""
        try:
            care_plan = CarePlan.objects.get(order_id=order_id)
            serializer = self.get_serializer(care_plan)
            return Response(serializer.data)
        except CarePlan.DoesNotExist:
            return Response(
                {"detail": "Care plan not found or not yet generated"},
                status=status.HTTP_404_NOT_FOUND,
            )
    
    @action(detail=False, methods=["get"], url_path="status/(?P<order_id>[^/.]+)")
    def status_check(self, request, order_id=None):
        """Get care plan generation status for an order."""
        try:
            order = Order.objects.get(id=order_id)
        except Order.DoesNotExist:
            return Response(
                {"detail": "Order not found"},
                status=status.HTTP_404_NOT_FOUND,
            )
        
        care_plan_available = hasattr(order, "care_plan")
        
        data = {
            "order_id": order_id,
            "status": order.status,
            "care_plan_available": care_plan_available,
            "error_message": order.error_message if order.status == "failed" else None,
        }
        
        serializer = CarePlanStatusSerializer(data=data)
        serializer.is_valid()
        return Response(serializer.data)
    
    @action(detail=False, methods=["get"], url_path="download/(?P<order_id>[^/.]+)")
    def download(self, request, order_id=None):
        """Download care plan file."""
        try:
            care_plan = CarePlan.objects.get(order_id=order_id)
        except CarePlan.DoesNotExist:
            raise Http404("Care plan not found")
        
        if not care_plan.file_path:
            # No file saved, return content directly
            response = Response(care_plan.content, content_type="text/plain")
            response["Content-Disposition"] = f'attachment; filename="care_plan_{order_id}.txt"'
            return response
        
        # Check if file exists
        if not os.path.exists(care_plan.file_path):
            raise Http404("Care plan file not found")
        
        # Return file
        return FileResponse(
            open(care_plan.file_path, "rb"),
            as_attachment=True,
            filename=os.path.basename(care_plan.file_path),
        )

    @action(detail=False, methods=["post"], url_path="upload/(?P<order_id>[^/.]+)")
    def upload(self, request, order_id=None):
        """
        Upload a custom care plan for an order.

        This replaces any existing care plan (LLM-generated or previously uploaded).
        Accepts either:
        - JSON body with "content" field
        - Multipart form with "file" field (txt file)
        """
        # Verify order exists
        try:
            order = Order.objects.get(id=order_id)
        except Order.DoesNotExist:
            return Response(
                {"detail": "Order not found"},
                status=status.HTTP_404_NOT_FOUND,
            )

        # Validate input
        serializer = CarePlanUploadSerializer(data=request.data)
        if not serializer.is_valid():
            logger.warning(
                "care_plan_upload_validation_failed",
                order_id=order_id,
                errors=serializer.errors,
            )
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        content = serializer.validated_data["content"]

        # Delete existing care plan if any
        existing_care_plan = None
        if hasattr(order, "care_plan"):
            existing_care_plan = order.care_plan
            logger.info(
                "care_plan_upload_replacing_existing",
                order_id=order_id,
                was_uploaded=existing_care_plan.is_uploaded,
            )
            existing_care_plan.delete()

        # Create new care plan
        care_plan = CarePlan.objects.create(
            order=order,
            content=content,
            file_format="txt",
            is_uploaded=True,
            uploaded_at=datetime.now(),
            # Clear LLM fields since this is manually uploaded
            llm_model=None,
            llm_prompt_tokens=None,
            llm_completion_tokens=None,
            generation_time_ms=None,
            generated_at=None,
        )

        # Update order status to completed
        order.status = "completed"
        order.error_message = None
        order.save(update_fields=["status", "error_message", "updated_at"])

        logger.info(
            "care_plan_uploaded_success",
            order_id=order_id,
            care_plan_id=str(care_plan.id),
            content_length=len(content),
        )

        return Response(
            {
                "message": "Care plan uploaded successfully",
                "care_plan": CarePlanSerializer(care_plan).data,
            },
            status=status.HTTP_201_CREATED,
        )
