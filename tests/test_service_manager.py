"""ServiceManager 测试: 状态机与错误处理"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from core.service_manager import (  # noqa: E402
    STATUS_ERROR,
    STATUS_OFFLINE,
    STATUS_ONLINE,
    STATUS_UNKNOWN,
    ServiceManager,
)


def test_unknown_before_probe():
    sm = ServiceManager()
    sm.register("x", check=lambda: True)
    assert sm.services["x"].status == STATUS_UNKNOWN


def test_probe_online():
    sm = ServiceManager()
    sm.register("x", check=lambda: True)
    assert sm.probe("x") == STATUS_ONLINE


def test_probe_offline():
    sm = ServiceManager()
    sm.register("x", check=lambda: False)
    assert sm.probe("x") == STATUS_OFFLINE


def test_probe_error_keeps_message():
    sm = ServiceManager()
    sm.register("x", check=lambda: (_ for _ in ()).throw(RuntimeError("boom")))
    assert sm.probe("x") == STATUS_ERROR
    assert "boom" in sm.services["x"].last_error


def test_probe_unknown_service():
    sm = ServiceManager()
    assert sm.probe("nope") is None


def test_probe_all_and_status_map():
    sm = ServiceManager()
    sm.register("a", check=lambda: True)
    sm.register("b", check=lambda: False)
    sm.probe_all()
    m = sm.status_map()
    assert m["a"]["status"] == STATUS_ONLINE
    assert m["b"]["status"] == STATUS_OFFLINE
    assert "error" in m["a"]