"""
统一异常体系
===========
所有业务异常都继承 BaseAppException。
exception_handler 只认这个基类，统一转成 JSON 响应。

设计原则：
- service 层遇到问题 → raise 对应的异常
- view 层完全不写 try-except，不写 if-else 判断错误
- exception_handler 统一捕获，统一格式返回前端
- 前端只需要检查 response.type 就知道发生了什么
"""


# ============================================================
# 基类
# ============================================================
class BaseAppException(Exception):
    """
    所有自定义异常的基类

    统一格式：
    {
        "type": "error" | "warning",
        "code": "PROVIDER_NPI_CONFLICT",     # 机器可读的错误码
        "message": "人类可读的简短描述",
        "detail": ["具体的详细信息1", "具体的详细信息2"],
        "http_status": 409
    }
    """
    type = "error"            # 子类覆盖
    code = "UNKNOWN_ERROR"    # 子类覆盖
    http_status = 500         # 子类覆盖
    message = "An unexpected error occurred"

    def __init__(self, message=None, detail=None, code=None):
        # 允许实例化时覆盖默认值
        if message:
            self.message = message
        if code:
            self.code = code

        # detail 统一成列表，方便前端遍历
        if detail is None:
            self.detail = []
        elif isinstance(detail, str):
            self.detail = [detail]
        else:
            self.detail = list(detail)

        super().__init__(self.message)

    def to_dict(self):
        """转成 JSON 可序列化的 dict"""
        return {
            "type": self.type,
            "code": self.code,
            "message": self.message,
            "detail": self.detail,
        }


# ============================================================
# 子类 1：验证错误（格式不对）
# ============================================================
class AppValidationError(BaseAppException):
    """
    输入格式验证失败
    例：NPI 不是 10 位、MRN 不是 6 位、ICD-10 格式不对

    注意：命名为 AppValidationError 而不是 ValidationError，
    避免和 DRF 的 rest_framework.exceptions.ValidationError 冲突。
    """
    type = "error"
    code = "VALIDATION_ERROR"
    http_status = 400
    message = "Input validation failed"


# ============================================================
# 子类 2：业务阻止（不允许继续）
# ============================================================
class BlockError(BaseAppException):
    """
    业务规则明确阻止操作
    例：NPI 已被其他 Provider 使用、同患者同药同天重复下单

    用户不能通过 confirm 跳过，必须修改输入。
    """
    type = "error"
    code = "BUSINESS_BLOCK"
    http_status = 409
    message = "Operation blocked by business rules"


# ============================================================
# 子类 3：业务警告（允许确认后继续）
# ============================================================
class WarningException(BaseAppException):
    """
    疑似问题，用户可以确认后继续
    例：MRN 对应的名字不一致、同患者同药但不同天

    前端收到后弹确认框，用户确认后带 confirm=True 重新提交。
    """
    type = "warning"
    code = "BUSINESS_WARNING"
    http_status = 200
    message = "Please confirm to continue"
