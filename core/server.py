"""LioDesktop 内核: Flask 统一入口(health/status/radar/chat/config)

错误统一经 errors.to_error_response 转换: 对外只暴露 code/message,
真实异常进日志,不泄漏内部细节。
"""
import json
import os
import sys
import urllib.request

from flask import Flask, Response, jsonify, request, send_from_directory, stream_with_context

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from adapters.github_radar import GitHubRadar
from adapters.llm import LLMProvider
from adapters.model_radar import ModelRadar
from core.config import ConfigManager
from core.db import db_add, db_query
from core.errors import (
    AppError,
    AuthError,
    NetworkError,
    ProviderError,
    RateLimitError,
    ValidationError,
    to_error_response,
)
from core.logger import get_logger
from core.service_manager import ServiceManager

log = get_logger("server")
app = Flask(__name__, static_folder=None)

config = ConfigManager()
sm = ServiceManager()
github = GitHubRadar()
models = ModelRadar()
llm = LLMProvider(config)

# 注册服务(状态灯探测)
sm.register("github", check=github.health)
sm.register("models", check=models.health)
sm.register("llm", check=llm.health)

UI_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "ui")


def _map_error(e):
    """把适配层异常(RuntimeError 前缀 / AppError)映射为统一错误响应。"""
    if isinstance(e, AppError):
        return to_error_response(e)
    msg = str(e)
    if msg.startswith("auth:"):
        return to_error_response(AuthError(msg[5:].strip()))
    if msg.startswith("limit:"):
        return to_error_response(RateLimitError(msg[6:].strip()))
    if msg.startswith("network:"):
        return to_error_response(NetworkError(msg[8:].strip()))
    if msg.startswith("service:"):
        return to_error_response(ProviderError(msg[8:].strip()))
    log.exception("unhandled error")
    return to_error_response(e)

@app.route("/health")
def health():
    return jsonify({"ok": True, "app": "liodesktop", "version": "0.1.0"})

@app.route("/status")
def status():
    return jsonify(sm.probe_all())

@app.route("/api/radar")
def radar():
    q = request.args.get("q", "")
    try:
        days = int(request.args.get("days", "7"))
    except ValueError:
        return to_error_response(ValidationError("days 必须是数字"))
    try:
        if q:
            items = github.search_repos(q)
        else:
            items = github.new_models(days)
        return jsonify({"ok": True, "items": items})
    except Exception as e:
        body, status = _map_error(e)
        return jsonify(body), status

@app.route("/api/chat", methods=["POST"])
def chat():
    q = (request.json or {}).get("q", "").strip()
    if not q:
        return jsonify({"ok": False, "code": "VALIDATION_ERROR", "message": "请输入问题"}), 400
    try:
        answer = llm.ask(q)
        db_add("chat", q, answer)
        return jsonify({"ok": True, "answer": answer})
    except Exception as e:
        body, status = _map_error(e)
        return jsonify(body), status

@app.route("/api/chat/stream", methods=["POST"])
def chat_stream():
    """流式问答(SSE): 边生成边推给 UI。

    事件协议:
      data: {"delta": "..."}   增量文本
      data: [DONE]             结束(完整答案此时落库)
      event: error             出错时(负载同 to_error_response: code/message)
    """
    q = (request.json or {}).get("q", "").strip()
    if not q:
        return jsonify({"ok": False, "code": "VALIDATION_ERROR", "message": "请输入问题"}), 400

    def gen():
        chunks = []
        try:
            for delta in llm.ask_stream(q):
                chunks.append(delta)
                yield f"data: {json.dumps({'delta': delta}, ensure_ascii=False)}\n\n"
            answer = "".join(chunks).strip()
            if answer:
                db_add("chat", q, answer)
            yield "data: [DONE]\n\n"
        except Exception as e:
            body, _ = _map_error(e)
            yield f"event: error\ndata: {json.dumps(body, ensure_ascii=False)}\n\n"

    return Response(stream_with_context(gen()), mimetype="text/event-stream",
                    headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"})

@app.route("/api/models")
def api_models():
    try:
        items = models.recent_models()
        return jsonify({"ok": True, "items": items})
    except Exception as e:
        body, status = _map_error(e)
        return jsonify(body), status

@app.route("/api/verify", methods=["POST"])
def verify():
    text = (request.json or {}).get("text", "").strip()
    if not text:
        return jsonify({"ok": False, "code": "VALIDATION_ERROR", "message": "请输入要核验的内容"}), 400
    try:
        result = models.verify(text, github, llm)
        db_add("verify", text, json.dumps(result, ensure_ascii=False)[:2000])
        return jsonify(result)
    except Exception as e:
        body, status = _map_error(e)
        return jsonify(body), status

@app.route("/api/providers", methods=["GET", "POST"])
def providers():
    if request.method == "GET":
        return jsonify({"ok": True, "active": config.get("active_provider", ""),
                        "providers": llm.list_providers()})
    body = request.json or {}
    if body.get("set_active"):
        llm.set_active(body["set_active"])
        return jsonify({"ok": True})
    name = body.get("name", "")
    if not name:
        return jsonify({"ok": False, "error": "name required"}), 400
    llm.upsert(name, body.get("base_url", ""), body.get("api_key", ""), body.get("model", ""))
    if body.get("make_active"):
        llm.set_active(name)
    return jsonify({"ok": True})

@app.route("/api/providers/test", methods=["POST"])
def providers_test():
    """测试连接: 用临时配置发一个最小请求"""
    body = request.json or {}
    base_url = body.get("base_url", "")
    api_key = body.get("api_key", "")
    model = body.get("model", "")
    if not (base_url and model):
        return jsonify({"ok": False, "error": "base_url/model 必填"}), 400
    import json as _json
    payload = _json.dumps({
        "model": model,
        "messages": [{"role": "user", "content": "ping"}],
        "max_tokens": 5,
    }).encode()
    headers = {"Content-Type": "application/json"}
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"
    req = urllib.request.Request(base_url.rstrip("/") + "/chat/completions",
                                 data=payload, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            _json.loads(r.read())
        return jsonify({"ok": True, "message": "连接成功 ✓"})
    except urllib.error.HTTPError as e:
        return jsonify({"ok": False, "error": f"HTTP {e.code}: {e.read().decode()[:150]}"})
    except urllib.error.URLError as e:
        return jsonify({"ok": False, "error": f"网络错误: {e.reason}"})

@app.route("/api/history")
def history():
    kind = request.args.get("kind", "verify")
    rows = db_query(kind, limit=min(int(request.args.get("limit", "10")), 50))
    return jsonify({"ok": True, "items": rows})

@app.route("/api/config", methods=["GET", "POST"])
def cfg():
    if request.method == "GET":
        # 不回传完整 key,只给掩码
        key = config.get("deepseek", {}).get("api_key", "")
        masked = (key[:4] + "..." + key[-4:]) if len(key) > 8 else ""
        return jsonify({"deepseek_configured": bool(key), "key_masked": masked,
                        "theme": config.get("theme")})
    body = request.json or {}
    if "api_key" in body and body["api_key"]:
        cfg_d = config.get("deepseek", {})
        cfg_d["api_key"] = body["api_key"].strip()
        config.set("deepseek", cfg_d)
    if "theme" in body:
        config.set("theme", body["theme"])
    config.set("first_run", False)
    return jsonify({"ok": True})

@app.route("/")
def index():
    return send_from_directory(UI_DIR, "index.html")

@app.route("/<path:name>")
def static_files(name):
    return send_from_directory(UI_DIR, name)

def run(port=0):
    """启动内核;port=0 动态分配,返回实际端口"""
    import socket
    if port == 0:
        s = socket.socket()
        s.bind(("127.0.0.1", 0))
        port = s.getsockname()[1]
        s.close()
    log.info(f"内核启动 127.0.0.1:{port}")
    from waitress import serve
    serve(app, host="127.0.0.1", port=port, threads=8)
    return port

if __name__ == "__main__":
    run()
