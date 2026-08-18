"""端到端: /api/chat/stream 的 SSE 协议(假上游)。

隔离策略: 显式替换 server 模块里的 config/llm 实例指向临时文件,
并 monkeypatch db_add —— 绝不触碰真实的 ~/.liodesktop 配置与数据库。
"""
import json
import sys
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import pytest

from adapters.llm import LLMProvider
from core.config import ConfigManager

SSE_CHUNKS = [
    "data: " + json.dumps({"choices": [{"delta": {"content": "你好"}}]}) + "\n\n",
    "data: " + json.dumps({"choices": [{"delta": {"content": ", 世界!"}}]}) + "\n\n",
    "data: [DONE]\n\n",
]


class Handler(BaseHTTPRequestHandler):
    def do_POST(self):
        length = int(self.headers.get("Content-Length", 0))
        self.rfile.read(length)
        self.send_response(200)
        self.send_header("Content-Type", "text/event-stream")
        self.end_headers()
        for chunk in SSE_CHUNKS:
            self.wfile.write(chunk.encode())
            self.wfile.flush()

    def log_message(self, *args):
        pass


@pytest.fixture(scope="module")
def upstream():
    srv = HTTPServer(("127.0.0.1", 0), Handler)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    yield srv
    srv.shutdown()


@pytest.fixture()
def isolated_server(tmp_path, monkeypatch):
    """替换 server 模块的全局 config/llm/db_add, 与真实环境完全隔离。"""
    from core import server as srvmod

    saved_config, saved_llm = srvmod.config, srvmod.llm
    srvmod.config = ConfigManager(path=str(tmp_path / "cfg.json"), defaults={})
    srvmod.llm = LLMProvider(srvmod.config)
    monkeypatch.setattr(srvmod, "db_add", lambda *a, **k: None)
    yield srvmod
    srvmod.config, srvmod.llm = saved_config, saved_llm


def test_stream_endpoint_protocol(upstream, isolated_server):
    port = upstream.server_port
    isolated_server.llm.upsert("local", f"http://127.0.0.1:{port}/v1", "", "mx")
    isolated_server.llm.set_active("local")

    client = isolated_server.app.test_client()
    r = client.post("/api/chat/stream", json={"q": "hi"})
    assert r.status_code == 200
    assert r.mimetype == "text/event-stream"
    body = r.get_data(as_text=True)
    assert "你好" in body                  # 增量事件
    assert "[DONE]" in body                # 结束事件
    assert "event: error" not in body


def test_stream_endpoint_error_protocol(upstream, isolated_server):
    isolated_server.llm.upsert("bad", "https://remote.example.com/v1", "", "mx")
    isolated_server.llm.set_active("bad")

    client = isolated_server.app.test_client()
    r = client.post("/api/chat/stream", json={"q": "hi"})
    assert r.status_code == 200            # SSE 通道本身 200, 错误走 event
    body = r.get_data(as_text=True)
    assert "event: error" in body
    assert '"code"' in body