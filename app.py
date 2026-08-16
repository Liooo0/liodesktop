"""LioDesktop 壳入口: Launcher + pywebview 窗口
启动编排: 起内核(waitress) → /health 轮询 → 开窗口
生命周期: 关窗=隐藏;托盘退出=停内核
"""
import os, sys, threading, time, urllib.request

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from core.logger import get_logger
from core.config import ConfigManager
from core.server import run as run_server

log = get_logger("launcher")
config = ConfigManager()
PORT = 0
READY = threading.Event()

def start_kernel():
    """线程里起内核,记录实际端口"""
    global PORT
    PORT = run_server(PORT)  # run_server 内部动态选端口,但这里拿不到返回值(serve阻塞)
    # 改为: 预选端口再启动
    READY.set()

def pick_port():
    import socket
    s = socket.socket(); s.bind(("127.0.0.1", 0))
    port = s.getsockname()[1]; s.close()
    return port

def wait_health(port, timeout=20):
    for _ in range(timeout * 5):
        try:
            with urllib.request.urlopen(f"http://127.0.0.1:{port}/health", timeout=2) as r:
                if r.status == 200:
                    return True
        except Exception:
            time.sleep(0.2)
    return False

def main():
    global PORT
    PORT = pick_port()
    log.info(f"启动编排: 端口 {PORT}")
    t = threading.Thread(target=run_server, args=(PORT,), daemon=True)
    t.start()
    if not wait_health(PORT):
        log.error("内核 health 检查失败")
        sys.exit(1)
    log.info("内核就绪,打开窗口")
    import webview
    # 窗口状态记忆(位置/大小恢复)
    ws = config.get("window", {}) or {}
    w = webview.create_window("LioDesktop · AI 资讯雷达",
                              f"http://127.0.0.1:{PORT}",
                              width=ws.get("width", 1080), height=ws.get("height", 720),
                              x=ws.get("x"), y=ws.get("y"),
                              min_size=(860, 600))

    # 关窗=隐藏 + 记忆窗口状态(托盘退出才真退出)
    def on_closing():
        try:
            config.set("window", {"x": w.x, "y": w.y, "width": w.width, "height": w.height})
        except Exception:
            pass
        w.hide()
        return False

    w.events.closing += on_closing

    def setup_tray():
        # NSStatusItem 必须在主线程创建(AppHelper.callAfter 调度)
        from PyObjCTools import AppHelper
        from core.tray import TrayHandler
        handler = TrayHandler.alloc().init()
        AppHelper.callAfter(handler.setup,
                            lambda: w.show(), lambda: os._exit(0))

    webview.start(func=setup_tray)

if __name__ == "__main__":
    main()
