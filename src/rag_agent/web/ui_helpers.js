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

  function deletionOutcome(displayName, cleanupDeferred = [], missing = false) {
    const label = String(displayName || "该资料");
    if (missing) {
      return {
        tone: "success",
        assertive: false,
        message: `${label} 已不在资料库中`,
      };
    }
    const deferred = Array.isArray(cleanupDeferred) ? cleanupDeferred : [];
    if (deferred.length) {
      return {
        tone: "warning",
        assertive: true,
        message: `已从知识库删除 ${label}；${deferred.join("、")} 清理未完成，请检查服务日志。`,
      };
    }
    return {
      tone: "success",
      assertive: false,
      message: `已删除 ${label}`,
    };
  }

  return {
    basename,
    deletionOutcome,
    overlayInertState,
    sourceDisplayName,
  };
});
