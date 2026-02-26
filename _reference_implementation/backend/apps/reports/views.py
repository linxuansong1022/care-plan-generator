"""
Report export views.
"""

import io
from datetime import date

from django.http import HttpResponse
from rest_framework import status
from rest_framework.decorators import api_view
from rest_framework.response import Response

from .services import ReportService


@api_view(["GET"])
def export_all(request):
    """
    Export all orders with care plans for pharma reporting.

    GET /api/v1/export/

    Returns CSV with columns:
    - order_id, order_date
    - patient_mrn, patient_first_name, patient_last_name, patient_date_of_birth
    - provider_npi, provider_name
    - medication_name, primary_diagnosis_code
    - care_plan_status, care_plan_content
    """
    try:
        service = ReportService()
        file_bytes, filename, content_type = service.export_all_orders_with_care_plans()

        response = HttpResponse(file_bytes, content_type=content_type)
        response["Content-Disposition"] = f'attachment; filename="{filename}"'
        return response

    except Exception as e:
        return Response(
            {"error": f"Export failed: {str(e)}"},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )


@api_view(["GET"])
def export_orders(request):
    """
    Export orders report.
    
    Query params:
    - format: csv or xlsx (default: csv)
    - start_date: Filter from date (YYYY-MM-DD)
    - end_date: Filter until date (YYYY-MM-DD)
    - status: Filter by status
    - provider_npi: Filter by provider NPI
    """
    format_type = request.query_params.get("format", "csv")
    if format_type not in ["csv", "xlsx"]:
        return Response(
            {"error": "Invalid format. Use 'csv' or 'xlsx'"},
            status=status.HTTP_400_BAD_REQUEST,
        )
    
    start_date = _parse_date(request.query_params.get("start_date"))
    end_date = _parse_date(request.query_params.get("end_date"))
    order_status = request.query_params.get("status")
    provider_npi = request.query_params.get("provider_npi")
    
    try:
        service = ReportService()
        file_bytes, filename, content_type = service.export_orders(
            format=format_type,
            start_date=start_date,
            end_date=end_date,
            status=order_status,
            provider_npi=provider_npi,
        )
        
        response = HttpResponse(file_bytes, content_type=content_type)
        response["Content-Disposition"] = f'attachment; filename="{filename}"'
        return response
    
    except Exception as e:
        return Response(
            {"error": f"Export failed: {str(e)}"},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )


@api_view(["GET"])
def export_provider_report(request):
    """
    Export provider summary report.
    
    Query params:
    - format: csv or xlsx (default: xlsx)
    - start_date: Filter from date (YYYY-MM-DD)
    - end_date: Filter until date (YYYY-MM-DD)
    """
    format_type = request.query_params.get("format", "xlsx")
    if format_type not in ["csv", "xlsx"]:
        return Response(
            {"error": "Invalid format. Use 'csv' or 'xlsx'"},
            status=status.HTTP_400_BAD_REQUEST,
        )
    
    start_date = _parse_date(request.query_params.get("start_date"))
    end_date = _parse_date(request.query_params.get("end_date"))
    
    try:
        service = ReportService()
        file_bytes, filename, content_type = service.export_provider_report(
            format=format_type,
            start_date=start_date,
            end_date=end_date,
        )
        
        response = HttpResponse(file_bytes, content_type=content_type)
        response["Content-Disposition"] = f'attachment; filename="{filename}"'
        return response
    
    except Exception as e:
        return Response(
            {"error": f"Export failed: {str(e)}"},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )


@api_view(["GET"])
def export_patient_history(request, mrn):
    """
    Export patient history.
    
    Query params:
    - format: csv or xlsx (default: xlsx)
    """
    format_type = request.query_params.get("format", "xlsx")
    if format_type not in ["csv", "xlsx"]:
        return Response(
            {"error": "Invalid format. Use 'csv' or 'xlsx'"},
            status=status.HTTP_400_BAD_REQUEST,
        )
    
    try:
        service = ReportService()
        file_bytes, filename, content_type = service.export_patient_history(
            patient_mrn=mrn,
            format=format_type,
        )
        
        response = HttpResponse(file_bytes, content_type=content_type)
        response["Content-Disposition"] = f'attachment; filename="{filename}"'
        return response
    
    except ValueError as e:
        return Response(
            {"error": str(e)},
            status=status.HTTP_404_NOT_FOUND,
        )
    except Exception as e:
        return Response(
            {"error": f"Export failed: {str(e)}"},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )


@api_view(["GET"])
def export_medication_summary(request):
    """
    Export medication summary report.
    
    Query params:
    - format: csv or xlsx (default: xlsx)
    - start_date: Filter from date (YYYY-MM-DD)
    - end_date: Filter until date (YYYY-MM-DD)
    """
    format_type = request.query_params.get("format", "xlsx")
    if format_type not in ["csv", "xlsx"]:
        return Response(
            {"error": "Invalid format. Use 'csv' or 'xlsx'"},
            status=status.HTTP_400_BAD_REQUEST,
        )
    
    start_date = _parse_date(request.query_params.get("start_date"))
    end_date = _parse_date(request.query_params.get("end_date"))
    
    try:
        service = ReportService()
        file_bytes, filename, content_type = service.export_medication_summary(
            format=format_type,
            start_date=start_date,
            end_date=end_date,
        )
        
        response = HttpResponse(file_bytes, content_type=content_type)
        response["Content-Disposition"] = f'attachment; filename="{filename}"'
        return response
    
    except Exception as e:
        return Response(
            {"error": f"Export failed: {str(e)}"},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )


def _parse_date(date_str: str) -> date:
    """Parse date string (YYYY-MM-DD) to date object."""
    if not date_str:
        return None
    try:
        return date.fromisoformat(date_str)
    except ValueError:
        return None
