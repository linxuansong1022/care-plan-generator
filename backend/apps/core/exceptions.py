"""
Custom exception handling for the API.
HIPAA compliant - never expose PHI or stack traces to clients.
"""

import logging

from django.core.exceptions import ValidationError as DjangoValidationError
from rest_framework import status
from rest_framework.exceptions import APIException
from rest_framework.response import Response
from rest_framework.views import exception_handler

logger = logging.getLogger(__name__)


class DuplicateWarningException(APIException):
    """
    Exception for potential duplicate detection.
    Returns 409 Conflict with warnings.
    """
    status_code = status.HTTP_409_CONFLICT
    default_detail = "Potential duplicate detected"
    default_code = "duplicate_warning"
    
    def __init__(self, warnings: list, data: dict = None):
        self.warnings = warnings
        self.data = data or {}
        super().__init__(detail=self.default_detail)


class DuplicateBlockedException(APIException):
    """
    Exception when duplicate is confirmed and blocked.
    Returns 409 Conflict.
    """
    status_code = status.HTTP_409_CONFLICT
    default_detail = "Duplicate detected and blocked"
    default_code = "duplicate_blocked"


class LLMServiceException(APIException):
    """Exception for LLM service errors."""
    status_code = status.HTTP_503_SERVICE_UNAVAILABLE
    default_detail = "Care plan generation service temporarily unavailable"
    default_code = "llm_service_error"


class StorageException(APIException):
    """Exception for storage service errors."""
    status_code = status.HTTP_503_SERVICE_UNAVAILABLE
    default_detail = "File storage service temporarily unavailable"
    default_code = "storage_error"


def custom_exception_handler(exc, context):
    """
    Custom exception handler for DRF.
    
    HIPAA Compliance:
    - Never expose PHI in error messages
    - Never expose stack traces
    - Log errors internally with request context
    """
    
    # Get request info for logging (no PHI)
    request = context.get("request")
    view = context.get("view")
    
    log_context = {
        "path": request.path if request else "unknown",
        "method": request.method if request else "unknown",
        "view": view.__class__.__name__ if view else "unknown",
    }
    
    # Handle DuplicateWarningException specially
    if isinstance(exc, DuplicateWarningException):
        return Response(
            {
                "code": "DUPLICATE_WARNING",
                "message": "Potential duplicate detected. Please review and confirm.",
                "warnings": exc.warnings,
                "requires_confirmation": True,
                "data": exc.data,
            },
            status=status.HTTP_409_CONFLICT,
        )
    
    # Handle DuplicateBlockedException
    if isinstance(exc, DuplicateBlockedException):
        return Response(
            {
                "code": "DUPLICATE_BLOCKED",
                "message": str(exc.detail),
                "warnings": [],
            },
            status=status.HTTP_409_CONFLICT,
        )
    
    # Handle Django ValidationError
    if isinstance(exc, DjangoValidationError):
        logger.warning(f"Validation error: {log_context}")
        return Response(
            {
                "code": "VALIDATION_ERROR",
                "message": "Validation failed",
                "details": exc.messages if hasattr(exc, "messages") else [str(exc)],
            },
            status=status.HTTP_400_BAD_REQUEST,
        )
    
    # Get standard DRF response
    response = exception_handler(exc, context)
    
    if response is not None:
        # Log API exceptions
        logger.warning(f"API exception: {exc.__class__.__name__} - {log_context}")
        
        # Standardize error response format
        response.data = {
            "code": getattr(exc, "default_code", "ERROR"),
            "message": str(exc.detail) if hasattr(exc, "detail") else "An error occurred",
            "details": response.data if isinstance(response.data, list) else None,
        }
        
        return response
    
    # Handle unexpected exceptions - NEVER expose internals
    logger.exception(f"Unexpected error: {log_context}")
    
    return Response(
        {
            "code": "INTERNAL_ERROR",
            "message": "An unexpected error occurred. Please try again or contact support.",
        },
        status=status.HTTP_500_INTERNAL_SERVER_ERROR,
    )
