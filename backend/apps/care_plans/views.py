"""
Care Plan views.
"""

import os

from django.http import FileResponse, Http404
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from apps.orders.models import Order

from .models import CarePlan
from .serializers import CarePlanSerializer, CarePlanStatusSerializer


class CarePlanViewSet(viewsets.ReadOnlyModelViewSet):
    """
    ViewSet for CarePlan model.
    
    Read-only - care plans are created by background tasks.
    """
    
    queryset = CarePlan.objects.select_related("order").all()
    serializer_class = CarePlanSerializer
    
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
