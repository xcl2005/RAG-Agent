const REQUIRED_IDS = [
  "statusBadge",
  "statusDetail",
  "statusDot",
  "fileInput",
  "uploadDropzone",
  "uploadLimits",
  "selectedFiles",
  "uploadButton",
  "jobStatus",
  "refreshSources",
  "sourceRegistry",
  "sourceCount",
  "sourceActionStatus",
  "apiKey",
  "toggleApiKey",
  "connectionSettings",
  "newThread",
  "conversation",
  "questionInput",
  "askButton",
  "includeTrace",
  "threadLabel",
  "answerTemplate",
  "sidebar",
  "sidebarToggle",
  "sidebarClose",
  "sidebarBackdrop",
  "inspector",
  "inspectorToggle",
  "inspectorClose",
  "evidencePanel",
  "runPanel",
  "evidenceInspector",
  "traceInspector",
  "deleteSourceDialog",
  "deleteSourceName",
  "deleteSourceMeta",
  "deleteSourceStatus",
  "cancelDeleteSource",
  "confirmDeleteSource",
];

if (!window.RagUiHelpers) {
  throw new Error("UI contract error: ui_helpers.js did not load");
}
const {
  basename,
  deletionOutcome,
  overlayInertState,
  sourceDisplayName,
} = window.RagUiHelpers;

const refs = Object.fromEntries(
  REQUIRED_IDS.map((id) => {
    const element = document.getElementById(id);
    if (!element) throw new Error(`UI contract error: #${id} is missing`);
    return [id, element];
  }),
);

const NODE_LABELS = {
  initialize: "初始化会话",
  plan_queries: "规划检索查询",
  retrieve: "执行混合检索",
  grade_evidence: "评估证据充分性",
  generate_answer: "生成有依据的回答",
  validate_citations: "校验引用编号",
  repair_citations: "修复引用格式",
  abstain: "证据不足，执行拒答",
  citation_failure: "引用失败，安全降级",
  finalize: "收口结果与追踪",
};

const SUPPORTED_SUFFIXES = new Set(["pdf", "docx", "md", "txt", "html", "htm"]);
const prefersReducedMotion = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
const sidebarOverlay = window.matchMedia("(max-width: 760px)");
const inspectorOverlay = window.matchMedia("(max-width: 1320px)");
const workspace = document.querySelector(".workspace");
if (!workspace) throw new Error("UI contract error: .workspace is missing");

const state = {
  threadId: localStorage.getItem("rag-thread-id"),
  files: [],
  request: null,
  uploadController: null,
  deletingSources: new Set(),
  pendingDelete: null,
  sourceRefreshGeneration: 0,
  uploadLimits: {
    maxFiles: 10,
    maxFileBytes: 20 * 1024 * 1024,
  },
  overlayOpeners: {
    sidebar: null,
    inspector: null,
  },
};

function escapeHtml(value) {
  return String(value ?? "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}

function extension(path) {
  const name = basename(path);
  return name.includes(".") ? name.split(".").pop().toLowerCase() : "file";
}

function sourceStatus(status) {
  return (
    {
      ready: "已就绪",
      failed: "索引失败",
      indexing: "索引中",
    }[status] || status || "未知状态"
  );
}

function formatBytes(value) {
  if (!Number.isFinite(value) || value <= 0) return "0 B";
  const units = ["B", "KB", "MB", "GB"];
  const index = Math.min(Math.floor(Math.log(value) / Math.log(1024)), units.length - 1);
  const amount = value / 1024 ** index;
  return `${amount >= 10 || index === 0 ? amount.toFixed(0) : amount.toFixed(1)} ${units[index]}`;
}

function scrollElement(element, block = "nearest") {
  element.scrollIntoView({
    behavior: prefersReducedMotion ? "auto" : "smooth",
    block,
  });
}

function headers(json = false) {
  const value = {};
  const apiKey = refs.apiKey.value.trim();
  if (apiKey) value["X-API-Key"] = apiKey;
  if (json) value["Content-Type"] = "application/json";
  return value;
}

async function responseBody(response) {
  const text = await response.text();
  if (!text) return {};
  try {
    return JSON.parse(text);
  } catch {
    return { detail: text.slice(0, 300) };
  }
}

function friendlyHttpError(status, detail, area = "request") {
  const fallback = typeof detail === "string" ? detail : `HTTP ${status}`;
  if (status === 401) {
    const error = new Error(
      "本地 API_ACCESS_KEY 无效或缺失。这里需要项目访问密钥，不是 GLM 模型 Key。",
    );
    error.code = "local_auth";
    return error;
  }
  if (status === 403 && (area === "upload" || area === "delete")) {
    return new Error(
      area === "delete"
        ? "服务端尚未启用删除，或当前 Key 没有删除权限。"
        : "服务端尚未启用上传，或当前 Key 没有上传权限。",
    );
  }
  if (status === 413) {
    return new Error(`上传限制：${fallback}`);
  }
  if (status === 415) return new Error("文件内容与扩展名不匹配，或类型不受支持。");
  if (status === 409) return new Error("同一批次中存在重复文件名。");
  if (status === 422) return new Error(fallback || "输入未通过服务端校验。");
  return new Error(fallback);
}

function revealApiKeySettings({ focus = false, openDrawer = false } = {}) {
  refs.connectionSettings.open = true;
  if (openDrawer && sidebarOverlay.matches) openSidebar();
  if (focus) window.requestAnimationFrame(() => refs.apiKey.focus());
}

function setThread(threadId, restored = false) {
  state.threadId = threadId;
  if (threadId) {
    localStorage.setItem("rag-thread-id", threadId);
    refs.threadLabel.textContent = `${restored ? "已恢复" : "线程"} · ${threadId.slice(0, 8)}`;
    refs.threadLabel.title = threadId;
  } else {
    localStorage.removeItem("rag-thread-id");
    refs.threadLabel.textContent = "新会话";
    refs.threadLabel.removeAttribute("title");
  }
}

function syncOverlayInert() {
  const inert = overlayInertState({
    sidebarMatches: sidebarOverlay.matches,
    inspectorMatches: inspectorOverlay.matches,
    sidebarOpen: document.body.classList.contains("sidebar-open"),
    inspectorOpen: document.body.classList.contains("inspector-open"),
  });
  workspace.inert = inert.workspace;
  refs.sidebar.inert = inert.sidebar;
  refs.inspector.inert = inert.inspector;
}

function restoreOverlayFocus(name) {
  const opener = state.overlayOpeners[name];
  state.overlayOpeners[name] = null;
  if (opener instanceof HTMLElement && opener.isConnected) opener.focus();
}

function openSidebar() {
  closeInspector(false);
  state.overlayOpeners.sidebar = document.activeElement;
  document.body.classList.add("sidebar-open");
  refs.sidebarToggle.setAttribute("aria-expanded", "true");
  syncOverlayInert();
  if (sidebarOverlay.matches) {
    window.requestAnimationFrame(() => refs.sidebarClose.focus());
  }
}

function closeSidebar(restoreFocus = true) {
  const wasOpen = document.body.classList.contains("sidebar-open");
  document.body.classList.remove("sidebar-open");
  refs.sidebarToggle.setAttribute("aria-expanded", "false");
  syncOverlayInert();
  if (wasOpen && restoreFocus) restoreOverlayFocus("sidebar");
}

function selectInspectorTab(name) {
  document.querySelectorAll("[data-inspector-tab]").forEach((button) => {
    const selected = button.dataset.inspectorTab === name;
    button.classList.toggle("active", selected);
    button.setAttribute("aria-selected", String(selected));
    button.tabIndex = selected ? 0 : -1;
  });
  refs.evidencePanel.hidden = name !== "evidence";
  refs.runPanel.hidden = name !== "run";
}

function openInspector(name = "evidence") {
  closeSidebar(false);
  if (!document.body.classList.contains("inspector-open")) {
    state.overlayOpeners.inspector = document.activeElement;
  }
  selectInspectorTab(name);
  document.body.classList.add("inspector-open");
  refs.inspectorToggle.setAttribute("aria-expanded", "true");
  syncOverlayInert();
  if (inspectorOverlay.matches) {
    window.requestAnimationFrame(() => refs.inspectorClose.focus());
  }
}

function closeInspector(restoreFocus = true) {
  const wasOpen = document.body.classList.contains("inspector-open");
  document.body.classList.remove("inspector-open");
  refs.inspectorToggle.setAttribute("aria-expanded", "false");
  syncOverlayInert();
  if (wasOpen && restoreFocus) restoreOverlayFocus("inspector");
}

async function checkHealth() {
  const badge = refs.statusBadge;
  try {
    const response = await fetch("/health/ready");
    const body = await responseBody(response);
    const dependencies = Object.entries(body.dependencies || {});
    const readyCount = dependencies.filter(([, value]) => value.ready).length;
    const summary =
      dependencies.length > 0
        ? `${readyCount}/${dependencies.length} dependencies ready`
        : body.status || "unknown";
    const isReady = response.ok && body.status === "ready";

    badge.textContent = isReady ? "就绪" : "降级";
    badge.className = `badge ${isReady ? "badge-ok" : "badge-warn"}`;
    refs.statusDot.className = `status-dot ${isReady ? "status-ready" : "status-degraded"}`;
    refs.statusDetail.textContent = summary;
    refs.statusDetail.title = dependencies
      .map(([name, value]) => `${name}: ${value.detail || value.ready}`)
      .join("\n");
  } catch (error) {
    badge.textContent = "离线";
    badge.className = "badge badge-error";
    refs.statusDot.className = "status-dot status-offline";
    refs.statusDetail.textContent = "backend unavailable";
    refs.statusDetail.title = error.message;
  }
}

async function loadCapabilities() {
  try {
    const response = await fetch("/api/v1/capabilities");
    const body = await responseBody(response);
    if (!response.ok) return;
    const maxFiles = Number(body.upload?.max_files || state.uploadLimits.maxFiles);
    const maxFileMb = Number(
      body.upload?.max_file_mb || state.uploadLimits.maxFileBytes / 1024 / 1024,
    );
    state.uploadLimits = {
      maxFiles,
      maxFileBytes: maxFileMb * 1024 * 1024,
    };
    refs.uploadLimits.textContent =
      `PDF · DOCX · MD · TXT · HTML · 最多 ${maxFiles} 个 / 单文件 ${maxFileMb} MB`;
  } catch {
    // Keep conservative defaults when the optional metadata endpoint is unavailable.
  }
}

async function refreshSources() {
  const generation = ++state.sourceRefreshGeneration;
  const container = refs.sourceRegistry;
  container.className = "source-registry muted";
  container.textContent = "正在读取资料库…";
  try {
    const response = await fetch("/api/v1/sources", { headers: headers() });
    const body = await responseBody(response);
    if (generation !== state.sourceRefreshGeneration) return;
    if (!response.ok) throw friendlyHttpError(response.status, body.detail);
    const sources = body.sources || [];
    refs.sourceCount.textContent = String(sources.length);
    container.className = "source-registry";
    container.innerHTML =
      sources.length === 0
        ? '<span class="muted">尚未建立索引</span>'
        : sources
            .map((source) => {
              const type = extension(source.source).slice(0, 4).toUpperCase();
              const displayName = sourceDisplayName(source);
              const documentId = String(source.document_id || "");
              const deleting = state.deletingSources.has(documentId);
              return `
                <article class="registry-item${deleting ? " is-deleting" : ""}" data-document-id="${escapeHtml(documentId)}">
                  <span class="file-type">${escapeHtml(type)}</span>
                  <div class="registry-copy">
                    <strong title="${escapeHtml(displayName)}">${escapeHtml(displayName)}</strong>
                    <span>${Number(source.chunk_count || 0)} 个分块 · ${escapeHtml(sourceStatus(source.status))}</span>
                  </div>
                  ${
                    documentId && source.deletable !== false
                      ? `<button
                           class="source-delete"
                           type="button"
                           data-delete-source="${escapeHtml(documentId)}"
                           data-display-name="${escapeHtml(displayName)}"
                           data-chunk-count="${Number(source.chunk_count || 0)}"
                           aria-label="删除 ${escapeHtml(displayName)}"
                           title="从知识库删除"
                           ${deleting ? "disabled" : ""}
                         >
                           <svg viewBox="0 0 24 24" aria-hidden="true">
                             <path d="M4 7h16M9 7V4h6v3m-8 0 1 13h8l1-13M10 11v5m4-5v5" />
                           </svg>
                         </button>`
                      : ""
                  }
                </article>`;
            })
            .join("");
  } catch (error) {
    if (generation !== state.sourceRefreshGeneration) return;
    if (error.code === "local_auth") revealApiKeySettings();
    refs.sourceCount.textContent = "—";
    container.className = "source-registry muted";
    container.textContent = error.message;
  }
}

function openDeleteDialog(button) {
  const documentId = button.dataset.deleteSource;
  const displayName = button.dataset.displayName || "该文档";
  if (!documentId || state.deletingSources.has(documentId)) return;
  state.pendingDelete = {
    documentId,
    displayName,
    chunkCount: Number(button.dataset.chunkCount || 0),
    opener: button,
  };
  refs.deleteSourceName.textContent = displayName;
  refs.deleteSourceMeta.textContent =
    `${state.pendingDelete.chunkCount} 个文本分块 · 受管上传文件`;
  refs.deleteSourceStatus.textContent = "";
  refs.cancelDeleteSource.disabled = false;
  refs.confirmDeleteSource.disabled = false;
  refs.confirmDeleteSource.textContent = "删除资料";
  refs.deleteSourceDialog.showModal();
  window.requestAnimationFrame(() => refs.cancelDeleteSource.focus());
}

function closeDeleteDialog() {
  if (!refs.deleteSourceDialog.open || state.pendingDelete?.deleting) return;
  refs.deleteSourceDialog.close();
}

function setSourceActionStatus({ tone = "neutral", assertive = false, message = "" }) {
  refs.sourceActionStatus.className =
    `source-action-status${tone === "neutral" ? "" : ` source-action-${tone}`}`;
  refs.sourceActionStatus.setAttribute("role", assertive ? "alert" : "status");
  refs.sourceActionStatus.setAttribute("aria-live", assertive ? "assertive" : "polite");
  refs.sourceActionStatus.textContent = message;
}

async function deletePendingSource() {
  const pending = state.pendingDelete;
  if (!pending || pending.deleting || state.deletingSources.has(pending.documentId)) return;
  pending.deleting = true;
  const { documentId, displayName, opener } = pending;

  state.deletingSources.add(documentId);
  opener.disabled = true;
  opener.closest(".registry-item")?.classList.add("is-deleting");
  refs.cancelDeleteSource.disabled = true;
  refs.confirmDeleteSource.disabled = true;
  refs.confirmDeleteSource.textContent = "正在删除…";
  refs.deleteSourceStatus.className = "dialog-status";
  refs.deleteSourceStatus.textContent = "正在清理文本索引、向量与上传文件…";
  setSourceActionStatus({ message: `正在删除 ${displayName}…` });

  try {
    const response = await fetch(`/api/v1/sources/${encodeURIComponent(documentId)}`, {
      method: "DELETE",
      headers: headers(),
    });
    const body = await responseBody(response);
    if (response.status === 404) {
      setSourceActionStatus(deletionOutcome(displayName, [], true));
      await refreshSources();
      refs.deleteSourceDialog.close();
      return;
    }
    if (!response.ok) throw friendlyHttpError(response.status, body.detail, "delete");

    const deferred = body.cleanup_deferred || [];
    setSourceActionStatus(deletionOutcome(displayName, deferred));
    await Promise.all([refreshSources(), checkHealth()]);
    refs.deleteSourceDialog.close();
  } catch (error) {
    if (error.code === "local_auth") {
      refs.deleteSourceDialog.close();
      revealApiKeySettings({ focus: true, openDrawer: true });
    }
    refs.deleteSourceStatus.className = "dialog-status dialog-error";
    refs.deleteSourceStatus.textContent = `删除失败：${error.message}`;
    setSourceActionStatus({
      tone: "error",
      assertive: true,
      message: `删除失败：${error.message}`,
    });
  } finally {
    state.deletingSources.delete(documentId);
    pending.deleting = false;
    if (opener.isConnected) {
      opener.disabled = false;
      opener.closest(".registry-item")?.classList.remove("is-deleting");
    }
    if (refs.deleteSourceDialog.open) {
      refs.cancelDeleteSource.disabled = false;
      refs.confirmDeleteSource.disabled = false;
      refs.confirmDeleteSource.textContent = "重新删除";
    }
  }
}

function setFiles(files, { preserveStatus = false } = {}) {
  const values = [...files];
  const unsupported = values.filter((file) => !SUPPORTED_SUFFIXES.has(extension(file.name)));
  const oversized = values.filter((file) => file.size > state.uploadLimits.maxFileBytes);
  if (values.length > state.uploadLimits.maxFiles) {
    refs.jobStatus.className = "job-status job-error";
    refs.jobStatus.textContent =
      `一次最多选择 ${state.uploadLimits.maxFiles} 个文件，当前为 ${values.length} 个。`;
    state.files = [];
    refs.fileInput.value = "";
  } else if (oversized.length) {
    refs.jobStatus.className = "job-status job-error";
    refs.jobStatus.textContent =
      `文件过大：${oversized.map((file) => file.name).join("、")}`;
    state.files = [];
    refs.fileInput.value = "";
  } else if (unsupported.length) {
    refs.jobStatus.className = "job-status job-error";
    refs.jobStatus.textContent = `不支持：${unsupported.map((file) => file.name).join("、")}`;
    state.files = [];
    refs.fileInput.value = "";
  } else {
    state.files = values;
    if (!preserveStatus) {
      refs.jobStatus.className = "job-status";
      refs.jobStatus.textContent = "";
    }
  }

  refs.selectedFiles.className = state.files.length ? "file-list" : "file-list muted";
  refs.selectedFiles.innerHTML =
    state.files.length === 0
      ? "尚未选择文件"
      : state.files
          .map(
            (file) => `
              <div class="selected-file">
                <span title="${escapeHtml(file.name)}">${escapeHtml(file.name)}</span>
                <span class="muted">${escapeHtml(formatBytes(file.size))}</span>
              </div>`,
          )
          .join("");
  refs.uploadButton.disabled = state.files.length === 0;
}

function clearFiles({ preserveStatus = false } = {}) {
  state.files = [];
  refs.fileInput.value = "";
  setFiles([], { preserveStatus });
}

function renderUser(question) {
  const article = document.createElement("article");
  article.className = "message user-message";
  article.textContent = question;
  refs.conversation.classList.add("has-messages");
  refs.conversation.append(article);
  scrollElement(article, "end");
}

function answerWithCitationButtons(answer, sources) {
  const validIds = new Set(sources.map((source) => source.id));
  return escapeHtml(answer).replace(/\[S(\d+)\]/g, (match, number) => {
    const id = `S${number}`;
    return validIds.has(id)
      ? `<button class="citation" type="button" data-source="${id}" aria-label="查看来源 ${id}">[${id}]</button>`
      : `<span class="citation">${match}</span>`;
  });
}

function evidenceLocation(source) {
  return [
    source.heading ? `章节 ${source.heading}` : "",
    source.page !== null && source.page !== undefined ? `第 ${source.page} 页` : "",
    source.chunk_index !== null && source.chunk_index !== undefined
      ? `chunk ${source.chunk_index}`
      : "",
  ]
    .filter(Boolean)
    .join(" · ");
}

function renderEvidenceInspector(sources, body = {}, selectedId = null) {
  if (!sources?.length) {
    refs.evidenceInspector.className = "inspector-empty";
    refs.evidenceInspector.innerHTML = `
      <span class="empty-glyph" aria-hidden="true">◫</span>
      <strong>${body.abstained ? "本次未采用证据" : "暂无证据"}</strong>
      <p>${body.abstained ? "证据门控没有放行低相关候选，因此不会暴露其路径或原文。" : "完成一次有依据的回答后，来源片段会显示在这里。"}</p>`;
    return;
  }

  refs.evidenceInspector.className = "";
  refs.evidenceInspector.innerHTML = `
    <div class="inspector-summary">
      <div class="summary-metric"><span>Sources</span><strong>${sources.length}</strong></div>
      <div class="summary-metric"><span>Score kind</span><strong>${escapeHtml(body.evidence?.score_kind || "ranked")}</strong></div>
    </div>
    <div class="evidence-list">
      ${sources
        .map(
          (source) => {
            const title = sourceDisplayName({
              display_name: source.title,
              source: source.source,
            });
            return `
            <article class="evidence-card" data-evidence-id="${escapeHtml(source.id)}" tabindex="-1">
              <div class="evidence-head">
                <span class="source-id">${escapeHtml(source.id)}</span>
                <strong class="source-title" title="${escapeHtml(title)}">${escapeHtml(title)}</strong>
                <span class="source-score">${Number(source.score || 0).toFixed(3)}</span>
              </div>
              <p class="source-location">${escapeHtml(evidenceLocation(source) || title)}</p>
              <p class="evidence-quote">${escapeHtml(source.quote)}</p>
            </article>`;
          },
        )
        .join("")}
    </div>`;

  if (selectedId) {
    const card = [...refs.evidenceInspector.querySelectorAll("[data-evidence-id]")].find(
      (item) => item.dataset.evidenceId === selectedId,
    );
    if (card) {
      card.classList.add("highlight");
      window.requestAnimationFrame(() => {
        if (!card.isConnected) return;
        card.focus({ preventScroll: true });
        scrollElement(card, "center");
      });
      window.setTimeout(() => card.classList.remove("highlight"), 1400);
    }
  }
}

function renderTraceInspector(events, body = {}, running = false) {
  const values = events || [];
  if (!values.length) {
    refs.traceInspector.className = "inspector-empty";
    refs.traceInspector.innerHTML = `
      <span class="empty-glyph" aria-hidden="true">⌁</span>
      <strong>工作流将在这里展开</strong>
      <p>提问后实时显示每个 Agent 节点的状态与耗时。</p>
      <ol class="workflow-preview" aria-label="工作流预览">
        <li>规划</li><li>检索</li><li>门控</li><li>生成</li><li>校验</li>
      </ol>`;
    return;
  }

  const totalLatency = values.reduce((sum, event) => sum + Number(event.latency_ms || 0), 0);
  refs.traceInspector.className = "";
  refs.traceInspector.innerHTML = `
    <div class="inspector-summary">
      <div class="summary-metric"><span>Nodes</span><strong>${values.length}</strong></div>
      <div class="summary-metric"><span>Node time</span><strong>${totalLatency.toFixed(1)} ms</strong></div>
      <div class="summary-metric"><span>Model calls</span><strong>${Number(body.usage?.model_calls || 0)}</strong></div>
      <div class="summary-metric"><span>Tokens</span><strong>${Number(body.usage?.input_tokens || 0)} in / ${Number(body.usage?.output_tokens || 0)} out</strong></div>
      <div class="summary-metric"><span>Trace</span><strong>${escapeHtml(String(body.trace_id || "running").slice(0, 8))}</strong></div>
    </div>
    <div class="trace-list">
      ${values
        .map((event, index) => {
          const isLatest = running && index === values.length - 1;
          const label = NODE_LABELS[event.node] || event.node || "workflow";
          return `
            <div class="trace-item">
              <span class="trace-dot ${isLatest ? "latest" : ""}">✓</span>
              <div class="trace-copy">
                <strong>${escapeHtml(label)}</strong>
                <span>${escapeHtml(event.node || "node")}</span>
              </div>
              <span class="trace-latency">${Number(event.latency_ms || 0).toFixed(1)} ms</span>
            </div>`;
        })
        .join("")}
    </div>`;
}

function renderAnswer(body) {
  const fragment = refs.answerTemplate.content.cloneNode(true);
  const article = fragment.querySelector("article");
  const statusBadge = fragment.querySelector(".answer-status");
  const isError = body.status === "error";
  const sources = body.sources || [];

  if (isError) {
    statusBadge.textContent = "请求失败";
    statusBadge.className = "answer-status badge badge-error";
    article.setAttribute("role", "alert");
  } else if (body.abstained) {
    statusBadge.textContent = "证据不足 · 已拒答";
    statusBadge.className = "answer-status badge badge-warn";
  } else {
    statusBadge.textContent = "引用已验证";
    statusBadge.className = "answer-status badge badge-ok";
  }

  fragment.querySelector(".answer-copy").innerHTML = answerWithCitationButtons(
    body.answer,
    sources,
  );

  const trace = body.trace || [];
  const nodeLatency = trace.reduce((sum, event) => sum + Number(event.latency_ms || 0), 0);
  fragment.querySelector(".answer-stats").innerHTML = [
    `置信度 ${(Number(body.confidence || 0) * 100).toFixed(0)}%`,
    `${sources.length} 条证据`,
    `${(nodeLatency / 1000).toFixed(1)} 秒`,
    `${Number(body.usage?.model_calls || 0)} 次模型调用`,
  ]
    .map((value) => `<span>${escapeHtml(value)}</span>`)
    .join("");

  const evidenceButton = fragment.querySelector(".evidence-button");
  evidenceButton.hidden = sources.length === 0;
  evidenceButton.addEventListener("click", () => {
    openInspector("evidence");
    renderEvidenceInspector(sources, body);
  });

  const runButton = fragment.querySelector(".run-details-button");
  runButton.hidden = trace.length === 0;
  runButton.addEventListener("click", () => {
    openInspector("run");
    renderTraceInspector(trace, body);
  });

  article.addEventListener("click", (event) => {
    const button = event.target.closest("[data-source]");
    if (!button) return;
    openInspector("evidence");
    renderEvidenceInspector(sources, body, button.dataset.source);
  });

  refs.conversation.append(fragment);
  renderEvidenceInspector(sources, body);
  if (trace.length) renderTraceInspector(trace, body);
  scrollElement(article, "start");
}

function renderLoading(requestId) {
  const article = document.createElement("article");
  article.className = "message assistant-message loading-message";
  article.dataset.requestId = requestId;
  article.setAttribute("role", "status");
  article.setAttribute("aria-live", "polite");
  article.innerHTML = `
    <header class="message-header">
      <div class="message-author">
        <span class="avatar" aria-hidden="true">AR</span>
        <div><strong>Adaptive RAG</strong><span>Workflow running</span></div>
      </div>
      <span class="badge badge-muted">运行中</span>
    </header>
    <div class="loading-copy">
      <span class="spinner" aria-hidden="true"></span>
      <span data-loading-copy>正在初始化有界工作流…</span>
    </div>`;
  refs.conversation.append(article);
  scrollElement(article, "end");
  return article;
}

function updateLoading(element, event) {
  const copy = element.querySelector("[data-loading-copy]");
  if (!copy) return;
  copy.textContent = NODE_LABELS[event.node] || event.node || "正在执行工作流…";
}

async function consumeSse(response, onEvent) {
  if (!response.body) throw new Error("浏览器没有提供可读响应流。");
  const reader = response.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";

  function consumeFrame(frame) {
    let event = "message";
    let id = "";
    const data = [];
    for (const line of frame.split("\n")) {
      if (line.startsWith("event:")) event = line.slice(6).trim();
      if (line.startsWith("id:")) id = line.slice(3).trim();
      if (line.startsWith("data:")) data.push(line.slice(5).trimStart());
    }
    if (!data.length) return;
    let parsed;
    try {
      parsed = JSON.parse(data.join("\n"));
    } catch {
      throw new Error("服务端返回了无法解析的 SSE 数据。");
    }
    onEvent({ event, id, data: parsed });
  }

  try {
    while (true) {
      const { done, value } = await reader.read();
      buffer += decoder.decode(value || new Uint8Array(), { stream: !done });
      buffer = buffer.replaceAll("\r\n", "\n");
      let boundary = buffer.indexOf("\n\n");
      while (boundary >= 0) {
        consumeFrame(buffer.slice(0, boundary));
        buffer = buffer.slice(boundary + 2);
        boundary = buffer.indexOf("\n\n");
      }
      if (done) break;
    }
    if (buffer.trim()) consumeFrame(buffer);
  } catch (error) {
    try {
      await reader.cancel(error);
    } catch {
      // The stream may already be closed or aborted; preserve the original error.
    }
    throw error;
  } finally {
    reader.releaseLock();
  }
}

function setRequestRunning(running) {
  refs.askButton.classList.toggle("is-running", running);
  refs.askButton.setAttribute("aria-label", running ? "停止当前请求" : "发送问题");
  refs.askButton.setAttribute("title", running ? "停止当前请求" : "发送问题");
  refs.askButton.innerHTML = running
    ? '<span>停止</span><span aria-hidden="true">■</span>'
    : '<span>发送</span><span aria-hidden="true">↗</span>';
  refs.questionInput.setAttribute("aria-busy", String(running));
}

function cancelActiveRequest() {
  if (!state.request) return;
  state.request.cancelledByUser = true;
  state.request.controller.abort();
  state.request.loading?.remove();
}

async function ask() {
  if (state.request) {
    cancelActiveRequest();
    return;
  }

  const question = refs.questionInput.value.trim();
  if (!question) return;
  refs.questionInput.value = "";
  resizeQuestionInput();
  renderUser(question);

  const requestId =
    window.crypto?.randomUUID?.() || `${Date.now()}-${Math.random().toString(16).slice(2)}`;
  const controller = new AbortController();
  const loading = renderLoading(requestId);
  const request = {
    id: requestId,
    controller,
    loading,
    events: [],
    cancelledByUser: false,
  };
  state.request = request;
  setRequestRunning(true);
  renderTraceInspector([], {}, true);

  try {
    const response = await fetch("/api/v1/chat/stream", {
      method: "POST",
      headers: headers(true),
      signal: controller.signal,
      body: JSON.stringify({
        question,
        thread_id: state.threadId,
        include_trace: refs.includeTrace.checked,
      }),
    });
    if (!response.ok) {
      const body = await responseBody(response);
      throw friendlyHttpError(response.status, body.detail);
    }

    let finalBody = null;
    let terminalEvent = null;
    await consumeSse(response, (message) => {
      if (state.request?.id !== requestId) return;
      if (terminalEvent) throw new Error("SSE 在终态之后又返回了额外事件。");

      if (message.event === "node") {
        request.events.push(message.data);
        updateLoading(loading, message.data);
        renderTraceInspector(request.events, { trace_id: message.id }, true);
        return;
      }
      if (message.event === "final") {
        terminalEvent = "final";
        finalBody = message.data;
        return;
      }
      if (message.event === "error") {
        terminalEvent = "error";
        throw new Error(
          message.data?.error?.message || "工作流在返回最终答案前意外终止。",
        );
      }
    });

    if (state.request?.id !== requestId) return;
    if (!finalBody) throw new Error("SSE 流结束，但没有返回最终答案。");

    setThread(finalBody.thread_id);
    loading.remove();
    renderAnswer(finalBody);
  } catch (error) {
    loading.remove();
    if (error.name !== "AbortError" && state.request?.id === requestId) {
      if (error.code === "local_auth") {
        revealApiKeySettings({ focus: true, openDrawer: true });
      }
      renderAnswer({
        status: "error",
        answer: `请求失败：${error.message}`,
        abstained: false,
        confidence: 0,
        sources: [],
        usage: {},
        evidence: {},
        trace: request.events,
        trace_id: "error",
      });
    }
  } finally {
    if (state.request?.id === requestId) {
      state.request = null;
      setRequestRunning(false);
      refs.questionInput.focus();
    }
  }
}

async function pollJob(jobId, signal) {
  const output = refs.jobStatus;
  for (let attempt = 0; attempt < 120; attempt += 1) {
    const response = await fetch(`/api/v1/jobs/${encodeURIComponent(jobId)}`, {
      headers: headers(),
      signal,
    });
    const body = await responseBody(response);
    if (!response.ok) throw friendlyHttpError(response.status, body.detail, "upload");

    output.className = "job-status";
    output.textContent =
      body.status === "queued"
        ? "任务已进入队列…"
        : body.status === "running"
          ? "正在解析、切片并建立索引…"
          : `任务状态：${body.status}`;

    if (body.status === "succeeded") {
      const result = body.result || {};
      const failed = Number(result.failed_files || 0);
      const errorSummary = (result.errors || [])
        .slice(0, 2)
        .map((item) => `${sourceDisplayName({ source: item.source })}：${item.error}`)
        .join("；");
      output.className = `job-status ${failed ? "job-error" : "job-success"}`;
      output.textContent = failed
        ? `部分完成：索引 ${Number(result.indexed_files || 0)}，跳过 ${Number(result.skipped_files || 0)}，失败 ${failed}。${errorSummary}`
        : `完成：${Number(result.indexed_files || 0)} 个文件，${Number(result.chunks || 0)} chunks`;
      clearFiles({ preserveStatus: true });
      await Promise.all([refreshSources(), checkHealth()]);
      return;
    }
    if (body.status === "failed") throw new Error(body.error || "索引任务失败。");
    await new Promise((resolve) => window.setTimeout(resolve, 1000));
  }
  throw new Error("任务等待超时，请稍后从资料库刷新状态。");
}

async function upload() {
  if (!state.files.length || state.uploadController) return;
  const controller = new AbortController();
  state.uploadController = controller;
  refs.uploadButton.disabled = true;
  refs.jobStatus.className = "job-status";
  refs.jobStatus.textContent = "正在上传文件…";

  try {
    const form = new FormData();
    state.files.forEach((file) => form.append("files", file));
    const response = await fetch("/api/v1/documents", {
      method: "POST",
      headers: headers(),
      signal: controller.signal,
      body: form,
    });
    const body = await responseBody(response);
    if (!response.ok) throw friendlyHttpError(response.status, body.detail, "upload");
    await pollJob(body.job_id, controller.signal);
  } catch (error) {
    if (error.name !== "AbortError") {
      refs.jobStatus.className = "job-status job-error";
      refs.jobStatus.textContent = error.message;
    }
  } finally {
    state.uploadController = null;
    refs.uploadButton.disabled = state.files.length === 0;
  }
}

function resizeQuestionInput() {
  refs.questionInput.style.height = "auto";
  refs.questionInput.style.height = `${Math.min(refs.questionInput.scrollHeight, 132)}px`;
}

function resetConversation() {
  cancelActiveRequest();
  closeInspector();
  setThread(null);
  refs.conversation.querySelectorAll(".message").forEach((message) => message.remove());
  refs.conversation.classList.remove("has-messages");
  renderEvidenceInspector([]);
  renderTraceInspector([]);
  refs.questionInput.value = "";
  resizeQuestionInput();
  refs.questionInput.focus();
}

function activeModalOverlay() {
  if (sidebarOverlay.matches && document.body.classList.contains("sidebar-open")) {
    return refs.sidebar;
  }
  if (inspectorOverlay.matches && document.body.classList.contains("inspector-open")) {
    return refs.inspector;
  }
  return null;
}

function trapOverlayFocus(event) {
  if (event.key !== "Tab") return;
  const overlay = activeModalOverlay();
  if (!overlay) return;
  const focusable = [
    ...overlay.querySelectorAll(
      'a[href], button:not([disabled]), input:not([disabled]), textarea:not([disabled]), [tabindex]:not([tabindex="-1"])',
    ),
  ].filter((element) => !element.hidden && element.getClientRects().length > 0);
  if (!focusable.length) return;

  const first = focusable[0];
  const last = focusable[focusable.length - 1];
  if (event.shiftKey && (document.activeElement === first || !overlay.contains(document.activeElement))) {
    event.preventDefault();
    last.focus();
  } else if (
    !event.shiftKey &&
    (document.activeElement === last || !overlay.contains(document.activeElement))
  ) {
    event.preventDefault();
    first.focus();
  }
}

refs.fileInput.addEventListener("change", (event) => setFiles(event.target.files));
refs.uploadButton.addEventListener("click", upload);

["dragenter", "dragover"].forEach((name) => {
  refs.uploadDropzone.addEventListener(name, (event) => {
    event.preventDefault();
    refs.uploadDropzone.classList.add("drag-active");
  });
});

["dragleave", "drop"].forEach((name) => {
  refs.uploadDropzone.addEventListener(name, (event) => {
    event.preventDefault();
    refs.uploadDropzone.classList.remove("drag-active");
  });
});

refs.uploadDropzone.addEventListener("drop", (event) => setFiles(event.dataTransfer.files));
refs.uploadDropzone.addEventListener("keydown", (event) => {
  if (event.key === "Enter" || event.key === " ") {
    event.preventDefault();
    refs.fileInput.click();
  }
});

refs.askButton.addEventListener("click", ask);
refs.questionInput.addEventListener("input", resizeQuestionInput);
refs.questionInput.addEventListener("keydown", (event) => {
  if (
    event.key === "Enter" &&
    !event.shiftKey &&
    !event.isComposing &&
    event.keyCode !== 229
  ) {
    event.preventDefault();
    ask();
  }
});

document.addEventListener("keydown", (event) => {
  if (refs.deleteSourceDialog.open) return;
  trapOverlayFocus(event);
  const target = event.target;
  const isEditable =
    target instanceof HTMLInputElement ||
    target instanceof HTMLTextAreaElement ||
    target.isContentEditable;
  if (event.key === "/" && !isEditable) {
    event.preventDefault();
    refs.questionInput.focus();
  }
  if (event.key === "Escape") {
    if (document.body.classList.contains("inspector-open")) {
      closeInspector();
    } else if (document.body.classList.contains("sidebar-open")) {
      closeSidebar();
    }
  }
});

document.querySelectorAll("[data-question]").forEach((button) => {
  button.addEventListener("click", () => {
    refs.questionInput.value = button.dataset.question;
    resizeQuestionInput();
    refs.questionInput.focus();
  });
});

const inspectorTabs = [...document.querySelectorAll("[data-inspector-tab]")];
inspectorTabs.forEach((button) => {
  button.addEventListener("click", () => selectInspectorTab(button.dataset.inspectorTab));
  button.addEventListener("keydown", (event) => {
    const currentIndex = inspectorTabs.indexOf(button);
    let nextIndex = null;
    if (event.key === "ArrowRight") nextIndex = (currentIndex + 1) % inspectorTabs.length;
    if (event.key === "ArrowLeft") {
      nextIndex = (currentIndex - 1 + inspectorTabs.length) % inspectorTabs.length;
    }
    if (event.key === "Home") nextIndex = 0;
    if (event.key === "End") nextIndex = inspectorTabs.length - 1;
    if (nextIndex === null) return;
    event.preventDefault();
    const nextTab = inspectorTabs[nextIndex];
    selectInspectorTab(nextTab.dataset.inspectorTab);
    nextTab.focus();
  });
});

refs.refreshSources.addEventListener("click", refreshSources);
refs.sourceRegistry.addEventListener("click", (event) => {
  const button = event.target.closest("[data-delete-source]");
  if (button) openDeleteDialog(button);
});
refs.cancelDeleteSource.addEventListener("click", closeDeleteDialog);
refs.confirmDeleteSource.addEventListener("click", deletePendingSource);
refs.deleteSourceDialog.addEventListener("cancel", (event) => {
  if (state.pendingDelete?.deleting) event.preventDefault();
});
refs.deleteSourceDialog.addEventListener("close", () => {
  const opener = state.pendingDelete?.opener;
  state.pendingDelete = null;
  if (opener instanceof HTMLElement && opener.isConnected) {
    opener.focus();
  } else {
    refs.refreshSources.focus();
  }
});
refs.newThread.addEventListener("click", resetConversation);
refs.sidebarToggle.addEventListener("click", openSidebar);
refs.sidebarClose.addEventListener("click", () => closeSidebar());
refs.sidebarBackdrop.addEventListener("click", () => {
  if (document.body.classList.contains("inspector-open")) closeInspector();
  if (document.body.classList.contains("sidebar-open")) closeSidebar();
});
refs.inspectorToggle.addEventListener("click", () => openInspector("evidence"));
refs.inspectorClose.addEventListener("click", () => closeInspector());

refs.apiKey.addEventListener("change", (event) => {
  sessionStorage.setItem("rag-api-key", event.target.value);
  refreshSources();
});

refs.toggleApiKey.addEventListener("click", () => {
  const showing = refs.apiKey.type === "text";
  refs.apiKey.type = showing ? "password" : "text";
  refs.toggleApiKey.textContent = showing ? "显示" : "隐藏";
  refs.toggleApiKey.setAttribute("aria-label", showing ? "显示 API Key" : "隐藏 API Key");
});

refs.apiKey.value = sessionStorage.getItem("rag-api-key") || "";
sidebarOverlay.addEventListener("change", syncOverlayInert);
inspectorOverlay.addEventListener("change", syncOverlayInert);
setThread(state.threadId, Boolean(state.threadId));
setRequestRunning(false);
resizeQuestionInput();
syncOverlayInert();
checkHealth();
loadCapabilities();
refreshSources();
