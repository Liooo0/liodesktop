# LioDesktop 计划书 v3.0 — AI 资讯雷达桌面应用

> 2026-08-16 · 方向变更:v2.1(装修/配音工具箱)→ v3.0(AI 行业资讯雷达)
> 定位:个人 AI 行业资讯雷达桌面应用——自动追踪最新 AI 模型/开源项目/社区动态,自动核验真伪(官方源+跑分+显存需求+争议标注)
> 架构复用:v2.1 的 Host 架构/生命周期/里程碑全部保留,仅更换 Adapter 内容
> 学习体系总纲见同目录 LEARNING_ROADMAP.md(五层能力模型+七阶段栈,已定稿)

## 0. 核心认知(纠正后)

**deepseek-harness-desktop ≠ 网页套壳。** 它是:Electron Host(单实例/Profile/启动管理/托盘)+ 上游 Harness Runtime(Agent/模型/工具/Web UI),通过 loopback HTTP/WebSocket 连接,桌面能力以官方插件机制组合。

**LioDesktop 的学习目标随之升级**:
- 短期(现在):用 Python+pywebview 快速做出可用产品(评审结论不变)
- 长期:补全 Host 思维——Service Manager、生命周期、Adapter/插件化、Streaming
- **两条腿走路**:产品线(Python 快落地)+ 学习线(P 系列阶梯)

## 1. 架构

```text
┌─────────────────────────────────────────────┐
│              LioDesktop UI                  │
│  HTML/CSS/JS + pywebview(v1)               │
│  资讯雷达 │ AI问答 │ 模型情报 │ 设置 │ 状态  │
└──────────────────┬──────────────────────────┘
                   │
            Local App Core
            (Flask/Waitress, 127.0.0.1, 动态端口)
                   │
      ┌────────────┼────────────┐
      ↓            ↓            ↓
 GitHubRadar    HF/ModelRadar  DeepSeekAdapter
 Adapter        Adapter        (AI问答/核验分析)
      ↓            ↓            ↓
 GitHub API    HuggingFace    DeepSeek API
 (trending/    (新模型/跑分/   (LLM 总结/核验)
 新repo/搜索)   权重发布)
```

**v1 原则:Flask 是统一入口,Adapter 是插件化的雏形(接口冻结,未来可演进为动态插件加载)。**

## 2. 应用生命周期

```text
启动: Launcher → 读配置 → 选端口 → 启内核 → /health 轮询 → pywebview 加载
使用: 窗口(隐藏) / 托盘(显示/退出) / 服务状态灯
退出: 托盘退出 → 停 Flask → 清理子进程 → 结束
```
关窗(×)= 隐藏;**≠ 退出**。Flask 提供 `GET /health`(壳判断就绪用)。

## 3. 目录与数据分层

```text
程序资源(打包进 .app,只读): Resources/{ui, prompts, default_kb}
用户数据(升级不覆盖): ~/.liodesktop/{config.json(600), knowledge, audio, cache, logs}
```
API Key 首次启动引导设置,存 config.json,不进打包文件。

## 4. 服务状态管理 + 错误分层

- ServiceStatus: online/offline/starting/error/unknown,三服务独立,互不拖垮
- UI 状态灯:DeepSeek ● / 装修顾问 ● / GPT-SoVITS ○
- 错误分层:网络/认证/限流/服务/本地,禁止笼统"请求失败"

## 5. 里程碑(与学习路线 P 系列合并)

| 里程碑 | 内容 | 对应学习项目 |
|---|---|---|
| **M0** 工程骨架 | Launcher/Service Manager/Config/Logger/Health | **P3 Local Service Manager**(subprocess 启停/状态机) |
| **M1** Desktop Shell | Flask/Waitress 内核 + pywebview 壳 + UI 骨架 | **P4 Mini Desktop** |
| **M2** 三 Adapter | DeepSeek/RenovBot/GPTSoVITS + 错误分层 + SQLite 历史 | P2 Streaming(JS/WebSocket/SSE)+ SQLite |
| **M3** Desktop UX | 托盘/状态中心/设置/Markdown/音频 | P2 前端能力(HTML/CSS/JS/DOM/Fetch) |
| **M4** Distribution | .spec + 标准 bundle + arm64 + 干净 Mac | 打包发布层 |
| **M5**(学习线,不阻塞产品) | **Mini DSH Desktop**:Electron+TS,Electron→Python Runtime,health/lifecycle/tray | **P5(核心学习项目)** |
| **P6** 长期演进 | LioDesktop 插件化(plugins/ 目录动态加载)+ Keychain + 自动更新 | 插件系统/Extension Architecture |

## 6. 技术栈学习路线(分层,项目驱动,不是课程)

```text
Python(核心,已有) → API/RAG/LLM/SQLite/WebSocket/subprocess/生命周期
HTML/CSS/JS(必补) → 聊天/流式/Markdown/设置/状态灯(自己能写)
Node.js/TypeScript(必补) → npm/child_process/fs/WebSocket/Electron 基础
Electron(P5 专门练) → Main/Renderer/IPC/Loopback/Subprocess/Lifecycle
进程管理(重点) → ServiceManager: start/stop/restart/health/wait_ready/kill_tree
Git 进阶 → branch/merge/submodule/workspace/monorepo/CI/Actions
打包发布 → PyInstaller/Electron Builder/.app/签名/Gatekeeper
插件系统(长期) → Plugin/Service/Slot 组合,而非 if-page 分支
```

**学习顺序不贪多:随 LioDesktop 里程碑推进,学到哪用到哪;P5(Electron)单独安排,不阻塞产品线。**

## 7. 边界与取舍

| 决策 | 结论 |
|---|---|
| v1 壳 | pywebview(Python 快落地);Electron 留给 P5 学习项目 |
| GPT-SoVITS | 不打包,检测调用;内置 Launcher 二期 |
| Web 服务器 | 开发 Flask,正式 Waitress |
| 打包 | 标准 bundle,不用 --onefile,arm64 首发 |
| SQLite | M2 加入(聊天/咨询/TTS 历史持久化) |
| 插件系统 | v1=Adapter(雏形),真正动态插件=M5/P6 |
| 作品集叙事 | 卖点=桌面 Host 架构+Service Manager+Adapter,不是三个功能 |

## 8. 最终验收标准

干净 Mac 双击 .app → 无终端无浏览器 → 状态灯 → 三页可用(含历史记录)→ 断网/停服务有明确错误 → 托盘退出干净 → 升级不丢数据。

## 9. 成本

全免费;DeepSeek API 每月几元;签名(¥688/年)接单后再说。
