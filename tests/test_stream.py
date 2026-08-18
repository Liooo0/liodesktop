"""ask_stream 解析测试: 本地 SSE 模拟服务器, 不触真实 API。"""
import json
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer

import pytest

from adapters.llm import LLMProvider
from core.config import ConfigManager

SSE_CHUNKS = [
    "data: " + json.dumps({"choices": [{"delta": {"content": "你好"}}]}) + "\n\n",
    "data: " + json.dumps({"choices": [{"delta": {"content": ", 世界"}}]}) + "\n\n",
    "data: " + json.dumps({"choices": [{"delta": {"content": "!"}}]}) + "\n\n",
    "data: [DONE]\n\n",
]


class Handler(BaseHTTPRequestHandler):
    def do_POST(self):
        length = int(self.headers.get("Content-Length", 0))
        self.rfile.read(length)
        if self.server.auth_expected and self.headers.get("Authorization") != "Bearer test-key":
            self.send_response(401)
            self.end_headers()
            self.wfile.write(b'{"error": "bad key"}')
            return
        self.send_response(200)
        self.send_header("Content-Type", "text/event-stream")
        self.end_headers()
        for chunk in SSE_CHUNKS:
            self.wfile.write(chunk.encode())
            self.wfile.flush()

    def log_message(self, *args):
        pass


@pytest.fixture(scope="module")
def sse_server(tmp_path_factory):
    srv = HTTPServer(("127.0.0.1", 0), Handler)
    srv.auth_expected = False
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    yield srv
    srv.shutdown()


def make_provider(base_url, tmp_path, api_key=""):
    cfg = ConfigManager(path=str(tmp_path / "cfg.json"), defaults={})
    cfg.set("providers", {"local": {"base_url": base_url, "api_key": api_key, "model": "mx"}})
    cfg.set("active_provider", "local")
    return LLMProvider(cfg)


def test_stream_incremental(sse_server, tmp_path):
    """增量块按顺序 yield, 在 [DONE] 处停止。"""
    port = sse_server.server_port
    provider = make_provider(f"http://127.0.0.1:{port}/v1", tmp_path)
    chunks = list(provider.ask_stream("hi"))
    assert chunks == ["你好", ", 世界", "!"]


def test_stream_requires_key_when_remote(sse_server, tmp_path):
    """远程 base_url 无 key 时应拒绝(与 ask 同一套鉴权)。"""
    provider = make_provider("https://remote.example.com/v1", tmp_path)
    with pytest.raises(RuntimeError, match="auth:"):
        list(provider.ask_stream("hi"))


def test_stream_auth_error_mapped(sse_server, tmp_path):
    """上游 401 应抛 auth: 前缀错误。"""
    port = sse_server.server_port
    sse_server.auth_expected = True
    provider = make_provider(f"http://127.0.0.1:{port}/v1", tmp_path, api_key="wrong")
    with pytest.raises(RuntimeError, match="auth:"):
        list(provider.ask_stream("hi"))
    sse_server.auth_expected = False


def test_stream_network_error_mapped(tmp_path):
    """连不通的端口应抛 network: 前缀错误。"""
    cfg = ConfigManager(path=str(tmp_path / "cfg.json"), defaults={})
    cfg.set("providers", {"dead": {"base_url": "http://127.0.0.1:1/v1", "api_key": "x", "model": "m"}})
    cfg.set("active_provider", "dead")
    with pytest.raises(RuntimeError, match="network:"):
        list(LLMProvider(cfg).ask_stream("hi"))