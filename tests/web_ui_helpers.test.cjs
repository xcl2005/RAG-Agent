const assert = require("node:assert/strict");
const test = require("node:test");

const {
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
    message: "已从知识库删除 report.pdf；向量 清理未完成，请检查服务日志。",
  });
  assert.equal(deletionOutcome("report.pdf").tone, "success");
});
