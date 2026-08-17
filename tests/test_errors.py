"""错误体系测试: 错误码映射与响应体"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from core.errors import AppError, AuthError, NetworkError, RateLimitError, ValidationError, to_error_response


def test_auth_error_response():
    body, status = to_error_response(AuthError("key 无效"))
    assert body["code"] == "AUTH_FAILED"
    assert status == 401
    assert "key" in body["message"]


def test_rate_limit_error_response():
    body, status = to_error_response(RateLimitError())
    assert body["code"] == "RATE_LIMITED"
    assert status == 429


def test_validation_error_response():
    body, status = to_error_response(ValidationError("参数错误"))
    assert body["code"] == "VALIDATION_ERROR"
    assert status == 400


def test_network_error_response():
    body, status = to_error_response(NetworkError())
    assert body["code"] == "NETWORK_ERROR"
    assert status == 502


def test_unknown_error_masked():
    body, status = to_error_response(RuntimeError("secret internal detail"))
    assert body["code"] == "INTERNAL_ERROR"
    assert "secret" not in body["message"], "内部细节不应泄漏给前端"
    assert status == 500


def test_app_error_default():
    body, status = to_error_response(AppError("generic"))
    assert body["code"] == "INTERNAL_ERROR"
    assert status == 500