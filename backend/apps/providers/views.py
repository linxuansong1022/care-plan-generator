"""
Provider views.
"""

from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from .models import Provider
from .serializers import ProviderListSerializer, ProviderSerializer


class ProviderViewSet(viewsets.ModelViewSet):
    """
    ViewSet for Provider model.
    
    list: List all providers
    retrieve: Get a single provider
    create: Create a new provider
    update: Update a provider
    """
    
    queryset = Provider.objects.all()
    serializer_class = ProviderSerializer
    
    def get_serializer_class(self):
        if self.action == "list":
            return ProviderListSerializer
        return ProviderSerializer
    
    @action(detail=False, methods=["get"], url_path="by-npi/(?P<npi>[0-9]{10})")
    def by_npi(self, request, npi=None):
        """Get provider by NPI."""
        try:
            provider = Provider.objects.get(npi=npi)
            serializer = self.get_serializer(provider)
            return Response(serializer.data)
        except Provider.DoesNotExist:
            return Response(
                {"detail": "Provider not found"},
                status=status.HTTP_404_NOT_FOUND,
            )
