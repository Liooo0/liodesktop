"""Config Manager: ~/.liodesktop/config.json(权限600),首次启动引导"""
import json, os, stat

DATA_DIR = os.path.expanduser("~/.liodesktop")
CONFIG_PATH = os.path.join(DATA_DIR, "config.json")

DEFAULTS = {
    "deepseek": {"api_key": "", "base_url": "https://api.deepseek.com"},
    "port": 0,          # 0 = 动态分配
    "theme": "dark",
    "first_run": True,
}

class ConfigManager:
    def __init__(self):
        os.makedirs(DATA_DIR, exist_ok=True)
        self.data = dict(DEFAULTS)
        self.load()

    def load(self):
        if os.path.exists(CONFIG_PATH):
            try:
                with open(CONFIG_PATH, encoding="utf-8") as f:
                    self.data.update(json.load(f))
            except Exception:
                pass

    def save(self):
        tmp = CONFIG_PATH + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(self.data, f, ensure_ascii=False, indent=2)
        os.chmod(tmp, stat.S_IRUSR | stat.S_IWUSR)  # 600
        os.replace(tmp, CONFIG_PATH)

    def get(self, key, default=None):
        return self.data.get(key, default)

    def set(self, key, value):
        self.data[key] = value
        self.save()
