"""ConfigManager 测试: deep_merge 行为 / 权限 / 损坏文件兜底"""
import json
import os
import stat
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from core.config import ConfigManager, deep_merge  # noqa: E402


def test_deep_merge_nested():
    base = {"deepseek": {"api_key": "", "base_url": "https://api.deepseek.com"}, "theme": "dark"}
    user = {"deepseek": {"api_key": "sk-123"}}
    out = deep_merge(base, user)
    assert out["deepseek"]["api_key"] == "sk-123"
    assert out["deepseek"]["base_url"] == "https://api.deepseek.com", "嵌套默认值不应被覆盖"
    assert out["theme"] == "dark"


def test_deep_merge_scalar_override():
    out = deep_merge({"a": 1, "b": {"c": 2}}, {"a": 99, "b": {"c": 3}})
    assert out == {"a": 99, "b": {"c": 3}}


def test_config_load_keeps_defaults(tmp_path):
    p = tmp_path / "config.json"
    p.write_text(json.dumps({"deepseek": {"api_key": "sk-x"}}), encoding="utf-8")
    cm = ConfigManager(path=str(p), defaults={"deepseek": {"api_key": "", "base_url": "https://api.deepseek.com"},
                                              "theme": "dark", "first_run": True})
    assert cm.get("deepseek")["api_key"] == "sk-x"
    assert cm.get("deepseek")["base_url"] == "https://api.deepseek.com"
    assert cm.get("first_run") is True


def test_config_save_permission_600(tmp_path):
    p = tmp_path / "config.json"
    cm = ConfigManager(path=str(p))
    cm.set("theme", "light")
    mode = stat.S_IMODE(os.stat(p).st_mode)
    assert mode == stat.S_IRUSR | stat.S_IWUSR


def test_config_corrupt_file_falls_back(tmp_path):
    p = tmp_path / "config.json"
    p.write_text("{broken json", encoding="utf-8")
    cm = ConfigManager(path=str(p), defaults={"theme": "dark", "port": 0})
    assert cm.get("theme") == "dark"
    assert cm.get("port") == 0


def test_config_missing_file_ok(tmp_path):
    cm = ConfigManager(path=str(tmp_path / "nope.json"), defaults={"theme": "dark"})
    assert cm.get("theme") == "dark"


def test_update_deepseek_preserves_base_url(tmp_path):
    p = tmp_path / "config.json"
    cm = ConfigManager(path=str(p), defaults={
        "deepseek": {"api_key": "", "base_url": "https://api.deepseek.com"}})
    cm.update_deepseek("  sk-new  ")
    assert cm.get("deepseek")["api_key"] == "sk-new"
    assert cm.get("deepseek")["base_url"] == "https://api.deepseek.com"