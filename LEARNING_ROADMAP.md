# Lio AI 应用工程能力模型 — 学习路线(最终版)

> 2026-08-16 定稿 · 目标:AI Application → Agent → Harness → Desktop Host → AI Platform 完整栈
> 原则:能拆解 + 能做缩小版,不是自己造 DSH

## 0. 总原则(防走偏)

1. **目标 = 看到 DSH Desktop 能拆出 Host/Runtime/Plugin/Web Client/Process Lifecycle/Release Pipeline,并做缩小版**
2. **不要把最终形态理解成所有东西都必须自己实现**
3. **第一版功能少,但代码结构留扩展接口**(现在功能很少,架构允许未来扩展)
4. **学习跟着项目走,不做课程式学习**

## 1. 五层能力模型

| 层 | 内容 | 优先级 |
|---|---|---|
| ① 语言层 | Python(核心)+ TypeScript(Electron/Node 能读能改) | 进行中 |
| ② Runtime 层 | Process Lifecycle / Service Manager / Health / Port / Crash Recovery / **Generation / Profile** / kill_tree / graceful shutdown | **最值得补** |
| ③ 架构层 | App → **Host + Plugin**(Runtime/Service/Plugin/Profile Manager + UI + 能力插件) | 长期 |
| ④ 产品层 | **Profile / Workspace / Session / Context**(工作模式:摄影/求职/装修/开发,各自模型+Prompt+知识库+历史) | 新增 |
| ⑤ 平台层 | 插件市场/远程/同步/账号/观测(DSH 也在画饼) | **坚决不做,只看** |

## 2. 七阶段学习栈

```text
阶段1 Python      FastAPI / asyncio / subprocess / SQLite / LLM API      ← 已有基础,继续
阶段2 Web         HTML / CSS / JS / Fetch / SSE / WebSocket              ← 必补(自己写UI)
阶段3 Node/TS     npm/pnpm / Node / TS / fs / child_process / Electron  ← 必补(P5)
阶段4 Runtime     Service Manager / Lifecycle / Health / Port / Crash   ← 核心(P3/M0)
阶段5 AI架构      LLM / RAG / Tool Calling / MCP / Agent / Session / Plugin
阶段6 Desktop     Tray / Window / Native API / Packaging / Signing / Auto Update / CI
阶段7 Platform    Marketplace / Remote / Sync / Permission / Observability   ← 先不学
```

## 3. 四方向补充(最终版新增)

- **Runtime Engineering**:ServiceManager 接口 start/stop/restart/status/health/wait_ready/kill_tree/recover/switch_profile;学习 DSH 的 generation 语义(切换 profile = dispose 当前 generation 重建,不跨代复用 service/window/subprocess 句柄)
- **Profile/Workspace**:把"功能页"升级为"工作环境"——每个 Profile 有自己的模型/Prompt/知识库/API/历史 Session;DSH 有 last-known-good / pending target 生命周期概念可借鉴
- **Plugin Architecture**:能力通过 Plugin/Service/Slot 组合而非 if-page 分支;LioDesktop v1 的 Adapter = 雏形
- **Observability**:日志/状态/健康检查进 UI(状态灯),先做日志+状态,不做上报

## 4. 项目序列(最终版)

```text
P1 ✅ Python Local API      renov_bot(Flask+知识库)         已完成
P2     Streaming AI App     JS + SSE/WebSocket 聊天流式      并入 LioDesktop M2
P3     Local Service Mgr    subprocess 启停/状态机            = LioDesktop M0
P4     Mini Desktop         pywebview 包壳                    = LioDesktop M1
P5     Mini DSH Desktop     Electron+TS → Python Runtime     = LioDesktop M5(拿offer后)
P6     LioDesktop 插件化    Host+Plugin+Profile              长期演进
```

## 5. LioDesktop v1 边界(降复杂度,留接口)

**做**:Python Core(Service Manager/API/Config)+ Web UI + pywebview + 3 Adapters(DeepSeek/RenovBot/GPTSoVITS)
**留接口不做**:插件市场/账号/云同步/手机端/自动更新/多 Profile/复杂 IPC——但在代码结构上预留(Adapter 接口、ServiceManager 抽象、config 分层)

## 6. 与现有学习记录的关系

- 本文件 = 学习体系总纲;~/python-learning/learning-record.md = 逐日学习记录
- LioDesktop PLAN.md = 工程任务书(按本路线执行)
- 路线已收敛,**不再新增路线文档**;下一步永远是"做下一个里程碑"
