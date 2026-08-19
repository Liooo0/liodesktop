// LioDesktop UI 逻辑: 状态灯/雷达/问答/设置
const $ = s => document.querySelector(s);

// 侧边栏切换
document.querySelectorAll(".nav-btn").forEach(btn => {
  btn.addEventListener("click", () => {
    document.querySelectorAll(".nav-btn").forEach(b => b.classList.remove("active"));
    document.querySelectorAll(".page").forEach(p => p.classList.remove("active"));
    btn.classList.add("active");
    $("#page-" + btn.dataset.page).classList.add("active");
    if (btn.dataset.page === "radar" && !window._radarLoaded) loadNewModels();
    if (btn.dataset.page === "models" && !window._modelsLoaded) { window._modelsLoaded = true; loadModels(); loadVerifyHistory(); }
  });
});

// 状态灯
async function refreshStatus() {
  try {
    const r = await fetch("/status");
    const d = await r.json();
    for (const [name, st] of Object.entries(d)) {
      const dot = $("#dot-" + name);
      if (dot) { dot.className = "dot " + (st.status || "unknown"); }
    }
    $("#dot-core").className = "dot online";
  } catch (e) { $("#dot-core").className = "dot error"; }
}
setInterval(refreshStatus, 15000); refreshStatus();

// 资讯雷达
function renderRepos(items) {
  const box = $("#radar-list");
  if (!items.length) { box.innerHTML = '<div class="empty">没有结果</div>'; return; }
  box.innerHTML = items.map(it => `
    <div class="card">
      <h4><a href="${it.url}" target="_blank">${it.name}</a></h4>
      <div class="desc">${it.desc || "—"}</div>
      <div class="meta">
        <span class="stars">★ ${it.stars}</span>
        <span>${it.lang || ""}</span>
        <span>创建 ${it.created}</span>
        <span>更新 ${it.pushed}</span>
      </div>
    </div>`).join("");
}
async function loadNewModels() {
  window._radarLoaded = true;
  $("#radar-list").innerHTML = '<div class="loading">扫描近7天新项目…</div>';
  try {
    const r = await fetch("/api/radar?days=7");
    const d = await r.json();
    renderRepos(d.ok ? d.items : []);
    if (!d.ok) $("#radar-list").innerHTML = `<div class="empty">出错: ${d.error}</div>`;
  } catch (e) { $("#radar-list").innerHTML = '<div class="empty">网络错误</div>'; }
}
$("#radar-new").addEventListener("click", loadNewModels);
$("#radar-search").addEventListener("click", async () => {
  const q = $("#radar-q").value.trim();
  if (!q) return;
  $("#radar-list").innerHTML = '<div class="loading">搜索中…</div>';
  try {
    const r = await fetch("/api/radar?q=" + encodeURIComponent(q));
    const d = await r.json();
    renderRepos(d.ok ? d.items : []);
    if (!d.ok) $("#radar-list").innerHTML = `<div class="empty">出错: ${d.error}</div>`;
  } catch (e) { $("#radar-list").innerHTML = '<div class="empty">网络错误</div>'; }
});
$("#radar-q").addEventListener("keydown", e => { if (e.key === "Enter") $("#radar-search").click(); });

// Markdown 轻量渲染(顺序: 代码块→行内→粗斜体→标题→列表→链接)
function escapeHtml(s) {
  return s.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
}
function mdRender(text) {
  let h = escapeHtml(text);
  h = h.replace(/```(\w*)\n([\s\S]*?)```/g, '<pre><code>$2</code></pre>');
  h = h.replace(/`([^`]+)`/g, "<code>$1</code>");
  h = h.replace(/\*\*(.+?)\*\*/g, "<b>$1</b>");
  h = h.replace(/^### (.+)$/gm, "<h4>$1</h4>");
  h = h.replace(/^## (.+)$/gm, "<h3>$1</h3>");
  h = h.replace(/^- (.+)$/gm, "• $1");
  h = h.replace(/\[([^\]]+)\]\(([^)]+)\)/g, '<a href="$2" target="_blank">$1</a>');
  h = h.replace(/\n/g, "<br>");
  return h;
}

// 聊天(带历史 + Markdown)
function addMsg(who, text, time) {
  const m = document.createElement("div");
  m.className = "msg " + who;
  m.innerHTML = mdRender(text);
  if (time) {
    const t = document.createElement("div");
    t.className = "msg-time"; t.textContent = time;
    m.appendChild(t);
  }
  $("#chat-box").appendChild(m);
  $("#chat-box").scrollTop = 99999;
  return m;
}
async function loadChatHistory() {
  try {
    const r = await fetch("/api/history?kind=chat&limit=20");
    const d = await r.json();
    if (!d.ok || !d.items.length) return;
    const items = d.items.reverse();
    $("#chat-box").innerHTML = '<div class="msg-time" style="text-align:center">— 历史记录 —</div>';
    items.forEach(it => { addMsg("user", it.query, it.time); addMsg("bot", it.result, ""); });
  } catch (e) {}
}
loadChatHistory();
async function sendChat() {
  const q = $("#chat-input").value.trim();
  if (!q) return;
  addMsg("user", q);
  const wait = addMsg("bot", "思考中…");
  $("#chat-input").value = "";
  try {
    const r = await fetch("/api/chat", { method: "POST",
      headers: { "Content-Type": "application/json" }, body: JSON.stringify({ q }) });
    const d = await r.json();
    wait.textContent = d.ok ? d.answer : "⚠ " + d.error;
    if (!d.ok) wait.className = "msg bot err";
  } catch (e) { wait.textContent = "⚠ 网络错误"; wait.className = "msg bot err"; }
}
$("#chat-send").addEventListener("click", sendChat);
$("#chat-input").addEventListener("keydown", e => { if (e.key === "Enter") sendChat(); });

// 模型情报: 核验台
function renderReport(d) {
  const box = $("#verify-result");
  if (!d.ok) { box.innerHTML = `<div class="empty">出错: ${d.error}</div>`; return; }
  if (!d.report) { box.innerHTML = `<div class="empty">${d.evidence[0] || "无结果"}</div>`; return; }
  // Markdown 渲染
  box.innerHTML = `<div class="verify-report">
    <div class="verify-models">识别模型: ${d.models.join(" / ") || "无"}</div>
    <div class="report">${mdRender(d.report)}</div>
    <div class="evidence">证据:<br>${escapeHtml(d.evidence.join("\n")).replace(/\n/g, "<br>")}</div>
  </div>`;
}
async function doVerify() {
  const t = $("#verify-text").value.trim();
  if (!t) return;
  $("#verify-result").innerHTML = '<div class="loading">收集证据 + LLM 核验中(约 10-30 秒)…</div>';
  try {
    const r = await fetch("/api/verify", { method: "POST",
      headers: { "Content-Type": "application/json" }, body: JSON.stringify({ text: t }) });
    renderReport(await r.json());
  } catch (e) { $("#verify-result").innerHTML = '<div class="empty">网络错误</div>'; }
}
$("#verify-btn").addEventListener("click", doVerify);
$("#verify-text").addEventListener("keydown", e => { if (e.key === "Enter") doVerify(); });

async function loadModels() {
  $("#models-list").innerHTML = '<div class="loading">加载中…</div>';
  try {
    const r = await fetch("/api/models");
    const d = await r.json();
    if (!d.ok) { $("#models-list").innerHTML = `<div class="empty">出错: ${d.error}</div>`; return; }
    $("#models-list").innerHTML = d.items.map(it => `
      <div class="card">
        <h4><a href="${it.url}" target="_blank">${it.id}</a></h4>
        <div class="meta">
          <span class="stars">♥ ${it.likes}</span>
          <span>↓ ${it.downloads}</span>
          <span>${it.size || ""}</span>
          <span>${it.pipeline || ""}</span>
          <span>更新 ${it.modified}</span>
        </div>
      </div>`).join("") || '<div class="empty">无</div>';
  } catch (e) { $("#models-list").innerHTML = '<div class="empty">网络错误</div>'; }
}
$("#models-refresh").addEventListener("click", loadModels);

async function loadVerifyHistory() {
  try {
    const r = await fetch("/api/history?kind=verify&limit=8");
    const d = await r.json();
    if (!d.ok || !d.items.length) { $("#verify-history").innerHTML = '<div class="empty">暂无记录</div>'; return; }
    $("#verify-history").innerHTML = d.items.map((it, i) => `
      <div class="card hist" data-i="${i}">
        <h4>${it.query.slice(0, 60)}</h4>
        <div class="meta"><span>${it.time}</span></div>
        <div class="hist-report" style="display:none">${escapeHtml(it.result).slice(0, 800)}</div>
      </div>`).join("");
    document.querySelectorAll(".hist").forEach(el => el.addEventListener("click", () => {
      const rp = el.querySelector(".hist-report");
      rp.style.display = rp.style.display === "none" ? "block" : "none";
    }));
  } catch (e) {}
}
function escapeHtml(s) {
  return s.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/\n/g, "<br>");
}

// 设置: 供应商管理
const PRESETS = {
  deepseek:  { label: "DeepSeek",    base: "https://api.deepseek.com",                          model: "deepseek-v4-flash" },
  qwen:      { label: "阿里百炼Qwen", base: "https://dashscope.aliyuncs.com/compatible-mode/v1", model: "qwen-plus" },
  openai:    { label: "OpenAI",      base: "https://api.openai.com/v1",                         model: "gpt-4o-mini" },
  kimi:      { label: "Kimi",        base: "https://api.moonshot.cn/v1",                        model: "moonshot-v1-8k" },
  glm:       { label: "智谱GLM",     base: "https://open.bigmodel.cn/api/paas/v4",              model: "glm-4-flash" },
  ollama:    { label: "Ollama本地",  base: "http://127.0.0.1:11434/v1",                         model: "qwen2.5:7b" },
  openrouter: { label: "OpenRouter", base: "https://openrouter.ai/api/v1",                      model: "openai/gpt-4o-mini" },
};
$("#preset-apply").addEventListener("click", () => {
  const p = PRESETS[$("#preset-select").value];
  if (!p) return;
  $("#p-name").value = $("#preset-select").value;
  $("#p-base").value = p.base;
  $("#p-model").value = p.model;
  $("#p-key").value = "";
});

async function loadProviders() {
  try {
    const r = await fetch("/api/providers");
    const d = await r.json();
    if (!d.ok) return;
    $("#provider-list").innerHTML = d.providers.map(pv => `
      <div class="card provider-item">
        <div>
          <div class="pname">${pv.name} ${pv.name === d.active ? '<span class="active-badge">当前</span>' : ""}</div>
          <div class="pmeta">${pv.base_url} · ${pv.model} · ${pv.has_key ? "已配Key" : "无Key"}</div>
        </div>
        ${pv.name !== d.active ? `<button class="mini" data-act="${pv.name}">设为当前</button>` : ""}
      </div>`).join("") || '<div class="empty">还没配置任何供应商</div>';
    document.querySelectorAll("[data-act]").forEach(b => b.addEventListener("click", async () => {
      await fetch("/api/providers", { method: "POST", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ set_active: b.dataset.act }) });
      loadProviders(); refreshStatus();
    }));
  } catch (e) {}
}
$("#p-test").addEventListener("click", async () => {
  $("#p-hint").textContent = "测试中…";
  const r = await fetch("/api/providers/test", { method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ base_url: $("#p-base").value, api_key: $("#p-key").value,
                           model: $("#p-model").value }) });
  const d = await r.json();
  $("#p-hint").textContent = d.ok ? "✓ 连接成功" : "✗ " + d.error;
});
$("#p-save").addEventListener("click", async () => {
  const r = await fetch("/api/providers", { method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ name: $("#p-name").value.trim(), base_url: $("#p-base").value.trim(),
                           api_key: $("#p-key").value.trim(), model: $("#p-model").value.trim(),
                           make_active: true }) });
  const d = await r.json();
  $("#p-hint").textContent = d.ok ? "已保存并设为当前 ✓" : "✗ " + d.error;
  if (d.ok) { loadProviders(); refreshStatus(); }
});
loadProviders();
