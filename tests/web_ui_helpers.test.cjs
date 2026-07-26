const assert = require("node:assert/strict");
const test = require("node:test");

const {
  batchDeletionOutcome,
  deletionOutcome,
  overlayInertState,
  sourceDisplayName,
} = require("../src/rag_agent/web/ui_helpers.js");

test("explicit display names never lose a valid hash-like prefix", () => {
  assert.equal(
    sourceDisplayName({
      display_name: "abcdef123456-report.md",
      source: "0123456789ab-abcdef123456-report.md",
    }),
    "abcdef123456-report.md",
  );
});

test("legacy physical upload names still receive a readable fallback", () => {
  assert.equal(
    sourceDisplayName({ source: "C:\\uploads\\0123456789ab-project-report.pdf" }),
    "project-report.pdf",
  );
  assert.equal(sourceDisplayName({ source: "/knowledge/plain-name.md" }), "plain-name.md");
});

test("closed mobile overlays are inert and an open overlay isolates the workspace", () => {
  assert.deepEqual(
    overlayInertState({
      sidebarMatches: true,
      inspectorMatches: true,
      sidebarOpen: false,
      inspectorOpen: false,
    }),
    { workspace: false, sidebar: true, inspector: true },
  );
  assert.deepEqual(
    overlayInertState({
      sidebarMatches: true,
      inspectorMatches: true,
      sidebarOpen: true,
      inspectorOpen: false,
    }),
    { workspace: true, sidebar: false, inspector: true },
  );
});

test("deferred cleanup is an assertive persistent warning", () => {
  assert.deepEqual(deletionOutcome("report.pdf", ["向量"]), {
    tone: "warning",
    assertive: true,
    message: "资料已从知识库移除，但 1 个后台清理步骤未完成，请检查服务日志。",
  });
});

test("successful deletion feedback is generic and self-clearing", () => {
  const outcome = deletionOutcome("sensitive-filename.pdf");
  assert.deepEqual(outcome, {
    tone: "success",
    assertive: false,
    message: "资料已删除",
    clearAfterMs: 2800,
  });
  assert.equal(outcome.message.includes("sensitive-filename.pdf"), false);
});

test("batch failures remain actionable without listing document names", () => {
  assert.deepEqual(
    batchDeletionOutcome({
      deletedCount: 2,
      failedCount: 1,
    }),
    {
      tone: "error",
      assertive: true,
      message: "1 份资料删除失败，失败项已保持选中，可重新尝试。其余 2 份已处理。",
    },
  );
});

test("batch deletion reports a compact count and self-clears", () => {
  assert.deepEqual(batchDeletionOutcome({ deletedCount: 3 }), {
    tone: "success",
    assertive: false,
    message: "已删除 3 份资料",
    clearAfterMs: 2800,
  });
});
