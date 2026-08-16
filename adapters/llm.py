"""通用 LLM Provider(OpenAI 兼容协议): 一套代码覆盖市面大多数 API
预设: DeepSeek / 阿里百炼Qwen / OpenAI / Kimi / GLM / Ollama / OpenRouter
错误分层: auth / limit / network / service
"""
import json, urllib.request, urllib.error
from .base import Adapter

PRESETS = {
    "deepseek":  {"label": "DeepSeek",   "base_url": "https://api.deepseek.com",           "model": "deepseek-chat"},
    "qwen":      {"label": "阿里百炼Qwen", "base_url": "https://dashscope.aliyuncs.com/compatible-mode/v1", "model": "qwen-plus"},
    "openai":    {"label": "OpenAI",      "base_url": "https://api.openai.com/v1",          "model": "gpt-4o-mini"},
    "kimi":      {"label": "Kimi",        "base_url": "https://api.moonshot.cn/v1",         "model": "moonshot-v1-8k"},
    "glm":       {"label": "智谱GLM",     "base_url": "https://open.bigmodel.cn/api/paas/v4", "model": "glm-4-flash"},
    "ollama":    {"label": "Ollama本地",  "base_url": "http://127.0.0.1:11434/v1",           "model": "qwen2.5:7b"},
    "openrouter": {"label": "OpenRouter", "base_url": "https://openrouter.ai/api/v1",        "model": "openai/gpt-4o-mini"},
}

class LLMProvider(Adapter):
    name = "llm"

    def __init__(self, config):
        self.config = config

    def active(self):
        """当前激活的 provider 配置"""
        providers = self.config.get("providers", {})
        active = self.config.get("active_provider", "deepseek")
        return providers.get(active, {})

    def health(self) -> bool:
        p = self.active()
        return bool(p.get("api_key") or p.get("base_url", "").startswith("http://127.0.0.1"))

    def list_providers(self):
        providers = self.config.get("providers", {})
        return [{"name": k, **{kk: vv for kk, vv in v.items() if kk != "api_key"},
                 "has_key": bool(v.get("api_key"))} for k, v in providers.items()]

    def upsert(self, name, base_url, api_key, model):
        providers = self.config.get("providers", {})
        providers[name] = {"base_url": base_url.strip(), "api_key": api_key.strip(),
                           "model": model.strip()}
        self.config.set("providers", providers)

    def set_active(self, name):
        self.config.set("active_provider", name)

    def ask(self, question, system=None, temperature=0.3, max_tokens=800):
        p = self.active()
        if not p:
            raise RuntimeError("auth: 未配置任何 API,请到设置页配置")
        if not (p.get("api_key") or p.get("base_url", "").startswith(("http://127.0.0.1", "http://localhost"))):
            raise RuntimeError("auth: 当前供应商缺少 API Key,请到设置页配置")
        base = p["base_url"].rstrip("/")
        url = base + "/chat/completions"
        payload = json.dumps({
            "model": p.get("model", "deepseek-chat"),
            "messages": [
                {"role": "system", "content": system or "你是 LioDesktop 的 AI 助手,回答简洁准确,用中文。"},
                {"role": "user", "content": question},
            ],
            "max_tokens": max_tokens, "temperature": temperature,
        }).encode()
        headers = {"Content-Type": "application/json"}
        if p.get("api_key"):
            headers["Authorization"] = f"Bearer {p['api_key']}"
        req = urllib.request.Request(url, data=payload, headers=headers)
        try:
            with urllib.request.urlopen(req, timeout=120) as r:
                return json.loads(r.read())["choices"][0]["message"]["content"].strip()
        except urllib.error.HTTPError as e:
            body = e.read().decode()[:200]
            if e.code == 401:
                raise RuntimeError(f"auth: API Key 无效({p.get('label', '')})")
            if e.code == 402:
                raise RuntimeError(f"limit: 余额不足({p.get('label', '')})")
            if e.code == 429:
                raise RuntimeError(f"limit: 请求过于频繁({p.get('label', '')})")
            raise RuntimeError(f"service: {p.get('label', '')} {e.code} {body}")
        except urllib.error.URLError as e:
            raise RuntimeError(f"network: 无法连接 {p.get('label', '')}({e.reason})")
