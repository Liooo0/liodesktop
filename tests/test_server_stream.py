"""端到端: /api/chat/stream 的 SSE 协议(假上游 + 临时 HOME, 不触真实配置/数据)。"""
import json
import os
import sys
import tempfile
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

# 必须在 import core.server 之前把 HOME 指到临时目录(ConfigManager/db 都基于 HOME)
os.environ["HOME"] = tempfile.mkdtemp(prefix="liodesktop-test-home-")
sys.path.insert(0, str(Path(__file__).parent.parent))

import pytest

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


def test_stream_endpoint_protocol(upstream):
    from core import server as srvmod

    port = upstream.server_port
    srvmod.llm.upsert("local", f"http://127.0.0.1:{port}/v1", "", "mx")
    srvmod.llm.set_active("local")

    client = srvmod.app.test_client()
    r = client.post("/api/chat/stream", json={"q": "hi"})
    assert r.status_code == 200
    assert r.mimetype == "text/event-stream"
    body = r.get_data(as_text=True)
    assert "你好" in body                  # 增量事件
    assert "[DONE]" in body                # 结束事件
    assert "event: error" not in body


def test_stream_endpoint_error_protocol(upstream):
    from core import server as srvmod

    srvmod.llm.upsert("bad", "https://remote.example.com/v1", "", "mx")
    srvmod.llm.set_active("bad")

    client = srvmod.app.test_client()
    r = client.post("/api/chat/stream", json={"q": "hi"})
    assert r.status_code == 200            # SSE 通道本身 200, 错误走 event
    body = r.get_data(as_text=True)
    assert "event: error" in body
    assert '"code"' in body