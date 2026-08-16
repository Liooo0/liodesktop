"""DeepSeek 问答适配器(通用AI问答+资讯核验分析)"""
import json, os, urllib.request
from .base import Adapter

class DeepSeekAdapter(Adapter):
    name = "deepseek"

    def __init__(self, config):
        self.config = config

    def _key(self):
        return self.config.get("deepseek", {}).get("api_key", "")

    def health(self) -> bool:
        return bool(self._key())

    def ask(self, question, system=None, temperature=0.3, max_tokens=800):
        key = self._key()
        if not key:
            raise RuntimeError("auth: 未配置 DeepSeek API Key,请到设置页配置")
        payload = json.dumps({
            "model": "deepseek-chat",
            "messages": [
                {"role": "system", "content": system or "你是 LioDesktop 的 AI 助手,回答简洁准确,用中文。"},
                {"role": "user", "content": question},
            ],
            "max_tokens": max_tokens, "temperature": temperature,
        }).encode()
        req = urllib.request.Request(
            self.config.get("deepseek", {}).get("base_url", "https://api.deepseek.com") + "/chat/completions",
            data=payload, headers={"Content-Type": "application/json",
                                   "Authorization": f"Bearer {key}"})
        try:
            with urllib.request.urlopen(req, timeout=120) as r:
                return json.loads(r.read())["choices"][0]["message"]["content"].strip()
        except urllib.error.HTTPError as e:
            body = e.read().decode()[:200]
            if e.code == 401:
                raise RuntimeError("auth: API Key 无效")
            if e.code == 429:
                raise RuntimeError("limit: 请求过于频繁")
            raise RuntimeError(f"service: DeepSeek {e.code} {body}")
        except urllib.error.URLError:
            raise RuntimeError("network: 无法连接 DeepSeek")
