"""
Custom middleware for request/response logging.
"""

import time
import uuid

import structlog

logger = structlog.get_logger("request")


class RequestLoggingMiddleware:
    """
    Middleware to log all HTTP requests with detailed information.

    Provides much richer logging than Django's default, including:
    - Request ID (for distributed tracing)
    - HTTP method and path
    - Response status code and category
    - Request duration in ms
    - Client IP (supports X-Forwarded-For)
    - User agent
    - Request/Response content length
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # Generate unique request ID for tracing
        request_id = str(uuid.uuid4())[:8]
        request.request_id = request_id

        # Start timing
        start_time = time.time()

        # Get client IP (handle proxy/load balancer)
        x_forwarded_for = request.META.get("HTTP_X_FORWARDED_FOR")
        if x_forwarded_for:
            client_ip = x_forwarded_for.split(",")[0].strip()
        else:
            client_ip = request.META.get("REMOTE_ADDR", "unknown")

        # Process the request
        response = self.get_response(request)

        # Calculate duration
        duration_ms = round((time.time() - start_time) * 1000, 2)

        # Determine status category and log level
        status_code = response.status_code
        if status_code >= 500:
            log_func = logger.error
            status_category = "server_error"
        elif status_code >= 400:
            log_func = logger.warning
            status_category = "client_error"
        elif status_code >= 300:
            log_func = logger.info
            status_category = "redirect"
        else:
            log_func = logger.info
            status_category = "success"

        # Skip noisy endpoints (health checks, metrics)
        path = request.path
        if path in ["/health/", "/metrics", "/metrics/"]:
            return response

        # Get request size safely (body may already be read)
        try:
            request_size = len(request.body) if hasattr(request, '_body') else 0
        except Exception:
            request_size = int(request.META.get("CONTENT_LENGTH", 0) or 0)

        # Build log entry with rich context
        log_func(
            "http_request",
            request_id=request_id,
            method=request.method,
            path=path,
            status_code=status_code,
            status_category=status_category,
            duration_ms=duration_ms,
            client_ip=client_ip,
            user_agent=request.META.get("HTTP_USER_AGENT", "")[:100],
            content_type=request.content_type or None,
            request_size=request_size,
            response_size=int(response.get("Content-Length", 0) or 0),
            query_params=request.META.get("QUERY_STRING", "")[:200] or None,
        )

        # Add request ID to response header (useful for debugging)
        response["X-Request-ID"] = request_id

        return response
