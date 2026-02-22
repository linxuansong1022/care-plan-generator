"""
统一异常处理器（Exception Handler）
=================================
DRF 允许你注册一个全局的 exception handler，
所有 view 里没被 try-except 捕获的异常都会到这里。

工作流程：
1. View 里的 service 调用 raise 了异常
2. DRF 发现 view 没有处理这个异常
3. DRF 把异常交给这个 handler
4. 这个 handler 转成统一格式的 JSON 返回前端

这样 view 里就永远不需要写 try-except 或 if-else 判断错误了。
"""
from rest_framework.views import exception_handler as drf_exception_handler
from rest_framework.response import Response
from rest_framework import status

from .exceptions import BaseAppException


def unified_exception_handler(exc, context):
    """
    统一异常处理入口

    处理两类异常：
    1. BaseAppException（我们自己定义的） → 用我们的统一格式
    2. DRF 自带的异常（如 serializer 的 ValidationError） → 转成我们的统一格式
    """

    # ────────────────────────────────────────────
    # 情况 1：我们自定义的异常
    # ────────────────────────────────────────────
    if isinstance(exc, BaseAppException):
        return Response(
            exc.to_dict(),
            status=exc.http_status
        )

    # ────────────────────────────────────────────
    # 情况 2：DRF 自带的异常（serializer.is_valid 抛出的）
    # 先让 DRF 默认处理，然后包装成我们的统一格式
    # ────────────────────────────────────────────
    response = drf_exception_handler(exc, context)

    if response is not None:
        # DRF 认识这个异常（ValidationError, NotFound, PermissionDenied 等）
        # 把它包装成我们的格式

        # DRF ValidationError 的 response.data 可能是：
        #   {"npi": ["This field is required."]}        ← dict
        #   ["Some error"]                              ← list
        #   "Some error"                                ← str
        # 我们统一放到 detail 里

        detail = []
        if isinstance(response.data, dict):
            for field, messages in response.data.items():
                if isinstance(messages, list):
                    for msg in messages:
                        detail.append(f"{field}: {msg}")
                else:
                    detail.append(f"{field}: {messages}")
        elif isinstance(response.data, list):
            detail = response.data
        else:
            detail = [str(response.data)]

        return Response(
            {
                "type": "error",
                "code": "VALIDATION_ERROR",
                "message": "Input validation failed",
                "detail": detail,
            },
            status=response.status_code
        )

    # ────────────────────────────────────────────
    # 情况 3：DRF 也不认识（比如 500 错误）
    # 返回通用错误，不暴露 stack trace
    # ────────────────────────────────────────────
    return Response(
        {
            "type": "error",
            "code": "INTERNAL_ERROR",
            "message": "An unexpected error occurred",
            "detail": [],
        },
        status=status.HTTP_500_INTERNAL_SERVER_ERROR
    )