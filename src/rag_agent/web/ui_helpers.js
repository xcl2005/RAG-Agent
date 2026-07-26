(function exposeUiHelpers(root, factory) {
  const helpers = factory();
  if (typeof module === "object" && module.exports) {
    module.exports = helpers;
  } else {
    root.RagUiHelpers = helpers;
  }
})(typeof globalThis === "undefined" ? this : globalThis, function createUiHelpers() {
  "use strict";

  const UPLOAD_STORED_NAME_RE = /^[0-9a-f]{12}-(.+)$/i;

  function basename(path) {
    return String(path || "").split(/[\\/]/).pop() || "unknown";
  }

  function sourceDisplayName(source) {
    // A server-provided display_name is authoritative. Only legacy responses
    // without that field need the physical upload-prefix fallback.
    const explicit = String(source?.display_name || "").trim();
    if (explicit) return explicit;
    const fallback = basename(source?.source);
    return fallback.match(UPLOAD_STORED_NAME_RE)?.[1] || fallback;
  }

  function overlayInertState({
    sidebarMatches,
    inspectorMatches,
    sidebarOpen,
    inspectorOpen,
  }) {
    const sidebarIsModal = Boolean(sidebarMatches && sidebarOpen);
    const inspectorIsModal = Boolean(inspectorMatches && inspectorOpen);
    return {
      workspace: sidebarIsModal || inspectorIsModal,
      sidebar: inspectorIsModal || Boolean(sidebarMatches && !sidebarOpen),
      inspector: sidebarIsModal || Boolean(inspectorMatches && !inspectorOpen),
    };
  }

  function batchDeletionOutcome({
    deletedCount = 0,
    missingCount = 0,
    failedCount = 0,
    cleanupDeferred = [],
  } = {}) {
    const deleted = Math.max(0, Number(deletedCount) || 0);
    const missing = Math.max(0, Number(missingCount) || 0);
    const failed = Math.max(0, Number(failedCount) || 0);
    const deferred = [
      ...new Set(Array.isArray(cleanupDeferred) ? cleanupDeferred.filter(Boolean) : []),
    ];

    if (failed > 0) {
      const completed = deleted + missing;
      return {
        tone: "error",
        assertive: true,
        message:
          `${failed} 份资料删除失败，失败项已保持选中，可重新尝试。` +
          (completed > 0 ? `其余 ${completed} 份已处理。` : ""),
      };
    }
    if (deferred.length > 0) {
      return {
        tone: "warning",
        assertive: true,
        message: `资料已从知识库移除，但 ${deferred.length} 个后台清理步骤未完成，请检查服务日志。`,
      };
    }
    if (deleted === 0 && missing > 0) {
      return {
        tone: "success",
        assertive: false,
        message: missing === 1 ? "资料已不在资料库中" : "所选资料已不在资料库中",
        clearAfterMs: 2800,
      };
    }
    const completed = deleted + missing;
    return {
      tone: "success",
      assertive: false,
      message: completed > 1 ? `已删除 ${completed} 份资料` : "资料已删除",
      clearAfterMs: 2800,
    };
  }

  function deletionOutcome(displayName, cleanupDeferred = [], missing = false) {
    // The filename belongs in the confirmation dialog, not in a persistent
    // sidebar status. This keeps the library quiet after a successful action.
    void displayName;
    return batchDeletionOutcome({
      deletedCount: missing ? 0 : 1,
      missingCount: missing ? 1 : 0,
      cleanupDeferred,
    });
  }

  return {
    basename,
    batchDeletionOutcome,
    deletionOutcome,
    overlayInertState,
    sourceDisplayName,
  };
});
