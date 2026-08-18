# LioDesktop — AI 资讯雷达桌面应用

> 不用开浏览器,双击即用的 AI 行业资讯雷达:自动追踪新模型/新项目,贴一条传闻自动核验真伪。
> 架构:Python Core(Flask/Waitress)+ pywebview 壳 + HTML UI + 多供应商 LLM(OpenAI 兼容)

## 功能

- **资讯雷达**:GitHub 搜新项目/新仓库(近 7 天新项目一键拉取)
- **模型情报**:HuggingFace 新模型列表 + **消息核验台**(贴传闻→自动查 HF/GitHub 证据→LLM 出真伪报告)
- **AI 问答**:通用对话,支持切换供应商;**流式输出(SSE)**,边生成边渲染
- **多供应商**:DeepSeek / 阿里百炼 Qwen / OpenAI / Kimi / GLM / Ollama / OpenRouter / 自定义(测试连接+一键切换)
- **桌面体验**:系统托盘、关窗隐藏、窗口状态记忆、SQLite 历史、Markdown 渲染

## 开发运行

```bash
python3 -m venv .venv
env -u PYTHONPATH .venv/bin/pip install -i https://pypi.tuna.tsinghua.edu.cn/simple flask waitress pywebview pyobjc
env -u PYTHONPATH .venv/bin/python app.py
```

## 打包分发

```bash
env -u PYTHONPATH .venv/bin/pyinstaller --noconfirm --clean LioDesktop.spec
# 产出 dist/LioDesktop.app(标准 bundle,~16MB)
```

## 数据位置

- 配置/Key: `~/.liodesktop/config.json`(600 权限)
- 历史记录: `~/.liodesktop/liodesktop.db`
- 日志: `~/.liodesktop/logs/app.log`

## 里程碑

M0 工程骨架 ✅ → M1 Desktop Shell ✅ → M2 雷达+核验+SQLite ✅ → M3 桌面体验 ✅ → M4 打包分发 ✅ → M5 流式输出(SSE)✅

## 架构速览

```
pywebview UI ──fetch──→ Flask/Waitress(Core)
                          ├── /api/chat/stream  SSE 逐块推送(stream_with_context, 每块落 UI)
                          ├── /api/radar|models|verify  适配器层(GitHub/HF/LLM)
                          ├── /api/providers  多供应商配置(Key 只回传掩码)
                          └── ServiceManager  状态灯探测 + 错误分级(AppError 六分类 / code+message)
```

- 问答链路:UI → POST /api/chat/stream → LLMProvider.ask_stream() 逐块 yield → `data: {delta}` 事件 → UI 增量 mdRender → `[DONE]` 落库 SQLite
- 错误统一:适配层抛 `auth:/limit:/network:/service:` 前缀,`_map_error` 转标准 `{code, message}`;SSE 中途出错走 `event: error` 不破坏流
- 测试:`tests/` 25 用例(配置/错误/服务/流式解析/SSE 协议端到端,假上游不发真实请求)

## 后续演进(学习路线)

- M5:Electron 版 Mini DSH Desktop(Host 架构学习项目)
- 插件化(Plugin Manager)、多 Profile(工作环境)
- 自动更新、Keychain 存 Key
