"""
Patient views.
"""

from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from .models import Patient
from .serializers import PatientListSerializer, PatientSerializer


class PatientViewSet(viewsets.ModelViewSet):
    """
    ViewSet for Patient model.
    
    list: List all patients
    retrieve: Get a single patient
    create: Create a new patient
    update: Update a patient
    """
    
    queryset = Patient.objects.prefetch_related("diagnoses", "medication_history").all()
    serializer_class = PatientSerializer
    
    def get_serializer_class(self):
        if self.action == "list":
            return PatientListSerializer
        return PatientSerializer
    
    @action(detail=False, methods=["get"], url_path="by-mrn/(?P<mrn>[0-9]{6})")
    def by_mrn(self, request, mrn=None):
        """Get patient by MRN."""
        try:
            patient = Patient.objects.prefetch_related(
                "diagnoses", "medication_history"
            ).get(mrn=mrn)
            serializer = PatientSerializer(patient)
            return Response(serializer.data)
        except Patient.DoesNotExist:
            return Response(
                {"detail": "Patient not found"},
                status=status.HTTP_404_NOT_FOUND,
            )
    
    @action(detail=True, methods=["get"])
    def history(self, request, pk=None):
        """Get patient's order and care plan history."""
        patient = self.get_object()
        
        from apps.orders.models import Order
        from apps.orders.serializers import OrderListSerializer
        
        orders = Order.objects.filter(patient=patient).select_related(
            "provider", "care_plan"
        ).order_by("-created_at")
        
        serializer = OrderListSerializer(orders, many=True)
        return Response(serializer.data)
