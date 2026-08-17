"""Config Manager: ~/.liodesktop/config.json(权限600),首次启动引导

配置合并用 deep_merge:用户配置缺省时保留 DEFAULTS 的嵌套默认值
(如 deepseek.base_url),而不是整体覆盖。
"""
import json
import os
import stat
import threading

DATA_DIR = os.path.expanduser("~/.liodesktop")
CONFIG_PATH = os.path.join(DATA_DIR, "config.json")
CONFIG_VERSION = 1

DEFAULTS = {
    "config_version": CONFIG_VERSION,
    "deepseek": {"api_key": "", "base_url": "https://api.deepseek.com"},
    "port": 0,          # 0 = 动态分配
    "theme": "dark",
    "first_run": True,
}

_lock = threading.Lock()


def deep_merge(base, override):
    """递归合并:override 为 dict 时逐键与 base 合并,非 dict 值直接覆盖。"""
    out = dict(base)
    for k, v in (override or {}).items():
        if isinstance(v, dict) and isinstance(out.get(k), dict):
            out[k] = deep_merge(out[k], v)
        else:
            out[k] = v
    return out


class ConfigManager:
    def __init__(self, path=None, defaults=None):
        self.path = path or CONFIG_PATH
        self.defaults = defaults if defaults is not None else dict(DEFAULTS)
        self.data = deep_merge(self.defaults, {})
        self.load()

    def load(self):
        if os.path.exists(self.path):
            try:
                with open(self.path, encoding="utf-8") as f:
                    user = json.load(f)
                self.data = deep_merge(self.defaults, user)
                if "deepseek" in self.data and "api_key" in self.data.get("deepseek", {}):
                    self.data["deepseek"]["api_key"] = str(
                        self.data["deepseek"].get("api_key") or "").strip()
            except Exception:
                # 配置损坏时保留默认值,不崩溃;save() 会覆盖坏文件
                self.data = deep_merge(self.defaults, {})

    def _save_locked(self):
        """写盘(调用方需已持锁)。"""
        os.makedirs(os.path.dirname(self.path), exist_ok=True)
        tmp = self.path + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(self.data, f, ensure_ascii=False, indent=2)
        os.chmod(tmp, stat.S_IRUSR | stat.S_IWUSR)  # 600
        os.replace(tmp, self.path)

    def save(self):
        with _lock:
            self._save_locked()

    def get(self, key, default=None):
        return self.data.get(key, default)

    def set(self, key, value):
        with _lock:
            self.data[key] = value
            self._save_locked()

    def update_deepseek(self, api_key):
        """更新 deepseek.api_key,保留其他嵌套默认(base_url)。"""
        with _lock:
            self.data["deepseek"] = deep_merge(
                self.data.get("deepseek", {}), {"api_key": api_key.strip()})
            self._save_locked()
