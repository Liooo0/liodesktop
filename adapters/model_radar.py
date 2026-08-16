"""模型情报雷达: HuggingFace 新模型追踪 + 消息真伪核验(证据收集→LLM评级)"""
import json, re, urllib.request, urllib.parse
from .base import Adapter

class ModelRadar(Adapter):
    name = "models"

    def __init__(self, proxy="http://127.0.0.1:7890"):
        self.proxy = proxy

    def _opener(self):
        handlers = []
        if self.proxy:
            handlers.append(urllib.request.ProxyHandler({"http": self.proxy, "https": self.proxy}))
        return urllib.request.build_opener(*handlers)

    def health(self) -> bool:
        try:
            with self._opener().open("https://huggingface.co/api/models?limit=1", timeout=8) as r:
                return r.status == 200
        except Exception:
            return False

    def recent_models(self, limit=15, days=7):
        """近 N 天更新的模型(按最后修改排序)"""
        import datetime
        since = datetime.date.today() - datetime.timedelta(days=days)
        url = ("https://huggingface.co/api/models?sort=lastModified&direction=-1"
               f"&limit={limit * 3}")
        try:
            with self._opener().open(url, timeout=20) as r:
                items = json.loads(r.read())
        except Exception as e:
            raise RuntimeError(f"hf_recent: {e}")
        out = []
        for it in items:
            mod = (it.get("lastModified") or "")[:10]
            try:
                mod_date = datetime.date.fromisoformat(mod)
            except Exception:
                continue
            if mod_date < since:
                continue
            tags = it.get("tags", [])
            size = next((t for t in tags if re.fullmatch(r"\d+[MBK]?", t)), "")
            out.append({
                "id": it.get("id", ""),
                "downloads": it.get("downloads", 0),
                "likes": it.get("likes", 0),
                "size": size,
                "modified": mod,
                "url": f"https://huggingface.co/{it.get('id', '')}",
                "pipeline": next((t for t in tags if t.startswith(("text-generation", "text-to-speech",
                                                                  "image", "audio", "automatic"))), ""),
            })
            if len(out) >= limit:
                break
        return out

    def lookup_model(self, model_id):
        """查单个模型元数据;401/404 时用 search 兜底(真实id常带org)"""
        url = "https://huggingface.co/api/models/" + urllib.parse.quote(model_id)
        try:
            with self._opener().open(url, timeout=15) as r:
                it = json.loads(r.read())
        except urllib.error.HTTPError as e:
            if e.code not in (401, 404):
                return {"error": str(e.code)}
            # search 兜底: 找最匹配的模型
            try:
                su = ("https://huggingface.co/api/models?search=" +
                      urllib.parse.quote(model_id) + "&limit=1")
                with self._opener().open(su, timeout=15) as r:
                    arr = json.loads(r.read())
                if not arr:
                    return None
                it = arr[0]
            except Exception as e2:
                return {"error": f"search: {e2}"}
        except Exception as e:
            return {"error": str(e)}
        tags = it.get("tags", [])
        return {
            "id": it.get("id", ""),
            "downloads": it.get("downloads", 0),
            "likes": it.get("likes", 0),
            "modified": it.get("lastModified", "")[:10],
            "library": next((t for t in tags if t in ("transformers", "vllm", "safetensors", "gguf", "diffusers")), ""),
            "license": next((t for t in tags if t.startswith("license:")), "")[8:],
            "size": next((t for t in tags if re.fullmatch(r"\d+[MBK]?", t)), ""),
            "url": f"https://huggingface.co/{it.get('id', '')}",
        }

    def extract_model_names(self, text):
        """从消息文本提取候选模型名(如 qwen3.8-27b / deepseek-v4 / llama-4-27b)"""
        pats = [
            r"[a-z][a-z0-9-]*(?:-\d+(?:\.\d+)?(?:[a-z-]+\d*[bBmM]?)?)",
            r"qwen[0-9.]*-[0-9]+[a-z]*\d*[bB]",
        ]
        names = set()
        for pat in pats:
            for m in re.finditer(pat, text.lower()):
                s = m.group(0)
                if any(k in s for k in ("qwen", "deepseek", "llama", "gemma", "mistral", "gpt", "claude",
                                        "glm", "kimi", "yi", "phi", "olmo", "minicpm", "ernie", "doubao")):
                    names.add(s)
        return list(names)[:3]

    def verify(self, text, github_radar, deepseek_adapter):
        """核验消息: 提取模型名→HF查证→GitHub查官方repo→LLM评级"""
        names = self.extract_model_names(text)
        evidence = []
        for n in names:
            info = self.lookup_model(n)
            if info and "error" not in info:
                evidence.append(f"HF模型[{n}]: 下载{info['downloads']} 许可{info.get('license','?')} "
                                f"库{info.get('library','?')} 大小{info.get('size','?')} 更新{info['modified']}")
            else:
                evidence.append(f"HF模型[{n}]: 未找到或查询失败({info if isinstance(info,dict) else '404'})")
            # GitHub 官方 repo
            try:
                repos = github_radar.search_repos(n, per_page=3)
                for rp in repos[:2]:
                    evidence.append(f"GitHub[{rp['name']}]: ★{rp['stars']} {rp['lang'] or ''} 更新{rp['pushed']}")
            except Exception as e:
                evidence.append(f"GitHub查询[{n}]失败: {e}")

        if not names:
            return {"ok": True, "models": [], "evidence": [],
                    "report": "未在消息中识别出已知模型名(仅支持 qwen/deepseek/llama/claude 等常见系列)。"}

        prompt = f"""请核验以下关于 AI 模型的传闻,输出简洁中文报告。

传闻: {text}

收集到的证据:
{chr(10).join(evidence) if evidence else '(无)'}

要求:
1. 逐条判断传闻中的说法: 属实 / 部分属实 / 存疑 / 不实
2. 每条给出依据(证据里的数字)
3. 指出常见误区(如"媲美XX旗舰"通常是营销话术)
4. 最后给一句总结: 这条消息值不值得信,关键看哪几个数据
用 Markdown 列表输出。"""
        try:
            report = deepseek_adapter.ask(prompt, temperature=0.2, max_tokens=900)
        except Exception as e:
            report = f"(LLM核验失败: {e}) 以下为原始证据:\n" + "\n".join(evidence)
        return {"ok": True, "models": names, "evidence": evidence, "report": report}
