"""GitHub 资讯雷达: 搜索新项目/新模型仓库(GitHub Search API,免token)"""
import json, os, urllib.request, urllib.parse
from .base import Adapter

class GitHubRadar(Adapter):
    name = "github"

    def __init__(self, proxy="http://127.0.0.1:7890"):
        self.proxy = proxy

    def _opener(self):
        handlers = []
        if self.proxy:
            handlers.append(urllib.request.ProxyHandler({"http": self.proxy, "https": self.proxy}))
        return urllib.request.build_opener(*handlers)

    def health(self) -> bool:
        try:
            with self._opener().open("https://api.github.com", timeout=8) as r:
                return r.status == 200
        except Exception:
            return False

    def search_repos(self, query, sort="stars", order="desc", per_page=15):
        """搜索仓库。query 例: 'qwen created:>2026-08-10' """
        url = ("https://api.github.com/search/repositories?q=" +
               urllib.parse.quote(query) +
               f"&sort={sort}&order={order}&per_page={per_page}")
        try:
            with self._opener().open(url, timeout=20) as r:
                d = json.loads(r.read())
        except Exception as e:
            raise RuntimeError(f"github_search: {e}")
        out = []
        for item in d.get("items", []):
            out.append({
                "name": item["full_name"],
                "stars": item["stargazers_count"],
                "desc": (item.get("description") or "")[:120],
                "url": item["html_url"],
                "lang": item.get("language"),
                "created": item.get("created_at", "")[:10],
                "pushed": item.get("pushed_at", "")[:10],
            })
        return out

    def new_models(self, days=7):
        """近 N 天创建的 AI 相关仓库(按 star 排序)"""
        import datetime
        since = (datetime.date.today() - datetime.timedelta(days=days)).isoformat()
        return self.search_repos(
            f"AI OR agent OR llm OR model created:>{since} stars:>50", per_page=20)
