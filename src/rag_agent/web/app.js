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
  "manageSources",
  "sourceBulkToolbar",
  "selectAllSources",
  "selectedSourceCount",
  "deleteSelectedSources",
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
  "deleteDialogTitle",
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
  batchDeletionOutcome,
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
  prepare_context: "整理证据上下文",
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
  sourceRecords: new Map(),
  sourceSelectionMode: false,
  selectedSources: new Set(),
  sourceRefreshGeneration: 0,
  sourceStatusTimer: null,
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

function deletableSourceRecords() {
  return [...state.sourceRecords.values()].filter(
    (source) => source.documentId && source.deletable,
  );
}

function syncSourceSelectionControls() {
  const deletable = deletableSourceRecords();
  const deletableIds = new Set(deletable.map((source) => source.documentId));
  for (const documentId of state.selectedSources) {
    if (!deletableIds.has(documentId)) state.selectedSources.delete(documentId);
  }

  const selectedCount = state.selectedSources.size;
  const allSelected = deletable.length > 0 && selectedCount === deletable.length;
  refs.manageSources.disabled = deletable.length === 0 && !state.sourceSelectionMode;
  refs.manageSources.textContent = state.sourceSelectionMode ? "完成" : "管理";
  refs.manageSources.setAttribute("aria-pressed", String(state.sourceSelectionMode));
  refs.sourceBulkToolbar.hidden = !state.sourceSelectionMode;
  refs.selectAllSources.disabled = deletable.length === 0;
  refs.selectAllSources.textContent = allSelected ? "取消全选" : "全选";
  refs.selectAllSources.setAttribute("aria-pressed", String(allSelected));
  refs.selectedSourceCount.textContent = `已选 ${selectedCount}`;
  refs.deleteSelectedSources.disabled = selectedCount === 0;
  refs.deleteSelectedSources.textContent =
    selectedCount > 0 ? `删除所选 (${selectedCount})` : "删除所选";
}

function renderSourceRegistry() {
  const container = refs.sourceRegistry;
  const sources = [...state.sourceRecords.values()];
  refs.sourceCount.textContent = String(sources.length);
  container.className =
    `source-registry${state.sourceSelectionMode ? " is-selecting" : ""}`;
  container.innerHTML =
    sources.length === 0
      ? '<span class="muted">尚未建立索引</span>'
      : sources
          .map((source) => {
            const type = extension(source.source || source.displayName).slice(0, 4).toUpperCase();
            const deleting = state.deletingSources.has(source.documentId);
            const selected = state.selectedSources.has(source.documentId);
            const selector = source.deletable
              ? `<label class="source-selector" title="选择 ${escapeHtml(source.displayName)}">
                   <input
                     type="checkbox"
                     data-select-source="${escapeHtml(source.documentId)}"
                     aria-label="选择 ${escapeHtml(source.displayName)}"
                     ${selected ? "checked" : ""}
                     ${deleting ? "disabled" : ""}
                   />
                   <span class="source-select-mark" aria-hidden="true">✓</span>
                 </label>`
              : '<span class="source-selector-placeholder" aria-hidden="true"></span>';
            return `
              <article
                class="registry-item${deleting ? " is-deleting" : ""}${selected ? " is-selected" : ""}"
                data-document-id="${escapeHtml(source.documentId)}"
              >
                ${selector}
                <span class="file-type">${escapeHtml(type)}</span>
                <div class="registry-copy">
                  <strong title="${escapeHtml(source.displayName)}">${escapeHtml(source.displayName)}</strong>
                  <span>${source.chunkCount} 个分块 · ${escapeHtml(sourceStatus(source.status))}</span>
                </div>
                ${
                  source.deletable
                    ? `<button
                         class="source-delete"
                         type="button"
                         data-delete-source="${escapeHtml(source.documentId)}"
                         data-display-name="${escapeHtml(source.displayName)}"
                         data-chunk-count="${source.chunkCount}"
                         aria-label="删除 ${escapeHtml(source.displayName)}"
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
  syncSourceSelectionControls();
}

function setSourceSelectionMode(active, { focusManage = false } = {}) {
  if (active && deletableSourceRecords().length === 0) return;
  state.sourceSelectionMode = Boolean(active);
  if (!state.sourceSelectionMode) state.selectedSources.clear();
  renderSourceRegistry();
  if (focusManage) refs.manageSources.focus();
}

function toggleAllSources() {
  const ids = deletableSourceRecords().map((source) => source.documentId);
  const allSelected = ids.length > 0 && ids.every((documentId) =>
    state.selectedSources.has(documentId),
  );
  state.selectedSources = new Set(allSelected ? [] : ids);
  renderSourceRegistry();
  refs.selectAllSources.focus();
}

async function refreshSources() {
  const generation = ++state.sourceRefreshGeneration;
  const container = refs.sourceRegistry;
  container.className =
    `source-registry muted${state.sourceSelectionMode ? " is-selecting" : ""}`;
  container.textContent = "正在读取资料库…";
  try {
    const response = await fetch("/api/v1/sources", { headers: headers() });
    const body = await responseBody(response);
    if (generation !== state.sourceRefreshGeneration) return;
    if (!response.ok) throw friendlyHttpError(response.status, body.detail);
    const sources = Array.isArray(body.sources) ? body.sources : [];
    state.sourceRecords = new Map(
      sources.map((source) => {
        const documentId = String(source.document_id || "");
        return [
          documentId,
          {
            ...source,
            documentId,
            displayName: sourceDisplayName(source),
            chunkCount: Number(source.chunk_count || 0),
            deletable: Boolean(documentId && source.deletable !== false),
          },
        ];
      }),
    );
    if (state.sourceRecords.size === 0) {
      state.sourceSelectionMode = false;
      state.selectedSources.clear();
    }
    renderSourceRegistry();
  } catch (error) {
    if (generation !== state.sourceRefreshGeneration) return;
    if (error.code === "local_auth") revealApiKeySettings();
    refs.sourceCount.textContent = "—";
    container.className =
      `source-registry muted${state.sourceSelectionMode ? " is-selecting" : ""}`;
    container.textContent = error.message;
    syncSourceSelectionControls();
  }
}

function openDeleteDialogForItems(items, opener, { batch = false } = {}) {
  const pendingItems = items.filter(
    (item) => item.documentId && !state.deletingSources.has(item.documentId),
  );
  if (pendingItems.length === 0) return;
  state.pendingDelete = {
    items: pendingItems,
    opener,
    batch,
    deleting: false,
  };
  const itemCount = pendingItems.length;
  const totalChunks = pendingItems.reduce((total, item) => total + item.chunkCount, 0);
  refs.deleteDialogTitle.textContent =
    itemCount === 1 ? "删除这份资料？" : `删除所选 ${itemCount} 份资料？`;
  refs.deleteSourceName.textContent =
    itemCount === 1 ? `“${pendingItems[0].displayName}”` : `所选 ${itemCount} 份资料`;
  refs.deleteSourceMeta.textContent =
    `${itemCount} 份资料 · ${totalChunks} 个文本分块 · 受管上传文件`;
  refs.deleteSourceStatus.className = "dialog-status";
  refs.deleteSourceStatus.textContent = "";
  refs.cancelDeleteSource.disabled = false;
  refs.confirmDeleteSource.disabled = false;
  refs.confirmDeleteSource.textContent =
    itemCount === 1 ? "删除资料" : `删除 ${itemCount} 份资料`;
  refs.deleteSourceDialog.showModal();
  window.requestAnimationFrame(() => refs.cancelDeleteSource.focus());
}

function openDeleteDialog(button) {
  const documentId = button.dataset.deleteSource;
  const displayName = button.dataset.displayName || "该文档";
  if (!documentId || state.deletingSources.has(documentId)) return;
  openDeleteDialogForItems(
    [{
      documentId,
      displayName,
      chunkCount: Number(button.dataset.chunkCount || 0),
    }],
    button,
  );
}

function openBatchDeleteDialog() {
  const items = [...state.selectedSources]
    .map((documentId) => state.sourceRecords.get(documentId))
    .filter(Boolean);
  openDeleteDialogForItems(items, refs.deleteSelectedSources, { batch: true });
}

function closeDeleteDialog() {
  if (!refs.deleteSourceDialog.open || state.pendingDelete?.deleting) return;
  refs.deleteSourceDialog.close();
}

function setSourceActionStatus({
  tone = "neutral",
  assertive = false,
  message = "",
  clearAfterMs = 0,
}) {
  if (state.sourceStatusTimer) {
    window.clearTimeout(state.sourceStatusTimer);
    state.sourceStatusTimer = null;
  }
  refs.sourceActionStatus.className =
    `source-action-status${tone === "neutral" ? "" : ` source-action-${tone}`}`;
  refs.sourceActionStatus.setAttribute("role", assertive ? "alert" : "status");
  refs.sourceActionStatus.setAttribute("aria-live", assertive ? "assertive" : "polite");
  refs.sourceActionStatus.textContent = message;
  if (message && clearAfterMs > 0) {
    state.sourceStatusTimer = window.setTimeout(() => {
      refs.sourceActionStatus.textContent = "";
      refs.sourceActionStatus.className = "source-action-status";
      state.sourceStatusTimer = null;
    }, clearAfterMs);
  }
}

async function requestSourceDeletion(item) {
  const response = await fetch(`/api/v1/sources/${encodeURIComponent(item.documentId)}`, {
    method: "DELETE",
    headers: headers(),
  });
  const body = await responseBody(response);
  if (response.status === 404) return { missing: true, cleanupDeferred: [] };
  if (!response.ok) throw friendlyHttpError(response.status, body.detail, "delete");
  return {
    missing: false,
    cleanupDeferred: Array.isArray(body.cleanup_deferred) ? body.cleanup_deferred : [],
  };
}

async function deletePendingSource() {
  const pending = state.pendingDelete;
  if (!pending || pending.deleting || pending.items.length === 0) return;
  pending.deleting = true;
  const { items, opener } = pending;

  for (const item of items) state.deletingSources.add(item.documentId);
  if (opener instanceof HTMLButtonElement) opener.disabled = true;
  renderSourceRegistry();
  refs.cancelDeleteSource.disabled = true;
  refs.confirmDeleteSource.disabled = true;
  refs.confirmDeleteSource.textContent = "正在删除…";
  refs.deleteSourceStatus.className = "dialog-status";
  setSourceActionStatus({ message: `正在删除 0 / ${items.length}…` });

  let deletedCount = 0;
  let missingCount = 0;
  const cleanupDeferred = [];
  const failures = [];
  let authError = null;

  for (let index = 0; index < items.length; index += 1) {
    const item = items[index];
    const progress = `正在删除 ${index + 1} / ${items.length}…`;
    refs.deleteSourceStatus.textContent = `${progress} 正在清理索引与上传文件。`;
    setSourceActionStatus({ message: progress });
    try {
      const result = await requestSourceDeletion(item);
      if (result.missing) {
        missingCount += 1;
      } else {
        deletedCount += 1;
        cleanupDeferred.push(...result.cleanupDeferred);
      }
    } catch (error) {
      failures.push({ item, error });
      if (error.code === "local_auth") {
        authError = error;
        for (const unattempted of items.slice(index + 1)) {
          failures.push({ item: unattempted, error });
        }
        break;
      }
    }
  }

  const failedIds = new Set(failures.map(({ item }) => item.documentId));
  for (const item of items) {
    state.deletingSources.delete(item.documentId);
    if (!failedIds.has(item.documentId)) state.selectedSources.delete(item.documentId);
  }
  if (pending.batch) {
    state.sourceSelectionMode = failures.length > 0;
    state.selectedSources = new Set(failures.map(({ item }) => item.documentId));
  }

  if (deletedCount + missingCount > 0) {
    await refreshSources();
    if (deletedCount > 0) await checkHealth();
  } else {
    renderSourceRegistry();
  }

  const outcome =
    failures.length === 0 && items.length === 1
      ? deletionOutcome(items[0].displayName, cleanupDeferred, missingCount === 1)
      : batchDeletionOutcome({
          deletedCount,
          missingCount,
          failedCount: failures.length,
          cleanupDeferred,
        });
  setSourceActionStatus(outcome);
  pending.deleting = false;
  if (refs.deleteSourceDialog.open) refs.deleteSourceDialog.close();

  if (authError) {
    revealApiKeySettings({ focus: true, openDrawer: true });
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
        <li>检索</li><li>门控</li><li>整理</li><li>生成</li><li>校验</li>
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
                ${event.node === "prepare_context" ? `<span>${Number(event.selected_count || 0)} 个片段 · ${Number(event.document_count || 0)} 份资料 · 去重 ${Number(event.duplicate_count || 0)} 个<br>${Number(event.context_chars || 0)} / ${Number(event.budget_chars || 0)} 字符${event.context_truncated ? " · 已裁剪" : ""}${event.selection_fallback ? " · 强证据优先回退" : ""}</span>` : ""}
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
  const failureKind = String(body.failure_kind || "");
  const sources = body.sources || [];

  if (failureKind === "generation_failure") {
    statusBadge.textContent = "模型生成失败";
    statusBadge.className = "answer-status badge badge-error";
    article.setAttribute("role", "alert");
  } else if (failureKind === "citation_failure") {
    statusBadge.textContent = "引用校验失败";
    statusBadge.className = "answer-status badge badge-error";
    article.setAttribute("role", "alert");
  } else if (isError) {
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
    } else if (state.sourceSelectionMode) {
      setSourceSelectionMode(false, { focusManage: true });
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
refs.manageSources.addEventListener("click", () => {
  setSourceSelectionMode(!state.sourceSelectionMode, { focusManage: true });
});
refs.selectAllSources.addEventListener("click", toggleAllSources);
refs.deleteSelectedSources.addEventListener("click", openBatchDeleteDialog);
refs.sourceRegistry.addEventListener("click", (event) => {
  const button = event.target.closest("[data-delete-source]");
  if (button) openDeleteDialog(button);
});
refs.sourceRegistry.addEventListener("change", (event) => {
  const checkbox = event.target.closest("[data-select-source]");
  if (!(checkbox instanceof HTMLInputElement)) return;
  const documentId = checkbox.dataset.selectSource;
  if (!documentId || !state.sourceRecords.has(documentId)) return;
  if (checkbox.checked) {
    state.selectedSources.add(documentId);
  } else {
    state.selectedSources.delete(documentId);
  }
  checkbox.closest(".registry-item")?.classList.toggle("is-selected", checkbox.checked);
  syncSourceSelectionControls();
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
