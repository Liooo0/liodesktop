"""应用错误体系: 统一错误码 + 用户可读消息

对外只暴露 code/message,真实异常进日志。
"""
from core.logger import get_logger

log = get_logger("errors")


class AppError(Exception):
    """应用错误基类。code: 机器可读错误码;http_status: 对应 HTTP 状态。"""

    code = "INTERNAL_ERROR"
    http_status = 500

    def __init__(self, message="", detail=None):
        super().__init__(message)
        self.message = message
        self.detail = detail


class NetworkError(AppError):
    code = "NETWORK_ERROR"
    http_status = 502
    message = "网络请求失败"


class AuthError(AppError):
    code = "AUTH_FAILED"
    http_status = 401
    message = "API Key 无效或未配置"


class RateLimitError(AppError):
    code = "RATE_LIMITED"
    http_status = 429
    message = "请求过于频繁,请稍后再试"


class ProviderError(AppError):
    code = "PROVIDER_ERROR"
    http_status = 502
    message = "模型服务异常"


class ValidationError(AppError):
    code = "VALIDATION_ERROR"
    http_status = 400
    message = "请求参数不合法"


def to_error_response(e):
    """把任意异常转成 {code, message} 响应体;真实异常记日志。"""
    if isinstance(e, AppError):
        return {"ok": False, "code": e.code, "message": e.message}, e.http_status
    log.exception("unhandled error")
    return {"ok": False, "code": "INTERNAL_ERROR", "message": "服务内部错误"}, 500
