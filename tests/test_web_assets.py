import re
from html.parser import HTMLParser
from importlib.resources import files


class _IdCollector(HTMLParser):
    """Collect DOM ids without adding a browser-only test dependency."""

    def __init__(self) -> None:
        super().__init__()
        self.ids: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        del tag
        for name, value in attrs:
            if name == "id" and value:
                self.ids.append(value)


def _web_asset(name: str) -> str:
    return files("rag_agent").joinpath("web", name).read_text(encoding="utf-8")


def test_web_shell_preserves_the_javascript_dom_contract():
    html = _web_asset("index.html")
    script = _web_asset("app.js")
    parser = _IdCollector()
    parser.feed(html)

    required_block = re.search(r"const REQUIRED_IDS = \[(.*?)\];", script, re.DOTALL)
    assert required_block is not None
    required_ids = set(re.findall(r'"([A-Za-z][A-Za-z0-9]*)"', required_block.group(1)))
    assert required_ids <= set(parser.ids)
    assert len(parser.ids) == len(set(parser.ids))
    assert '<html lang="zh-CN">' in html
    assert 'role="log"' in html
    assert 'aria-live="polite"' in html


def test_web_client_keeps_streaming_upload_and_accessibility_guards():
    html = _web_asset("index.html")
    script = _web_asset("app.js")
    stylesheet = _web_asset("styles.css")

    assert 'src="/static/ui_helpers.js' in html
    assert 'fetch("/api/v1/chat/stream"' in script
    assert 'fetch("/api/v1/documents"' in script
    assert 'fetch("/api/v1/capabilities"' in script
    assert 'method: "DELETE"' in script
    assert "deleteSourceDialog" in script
    assert "sourceActionStatus" in script
    assert "overlayInertState" in script
    assert "event.isComposing" in script
    assert "AbortController" in script
    assert "escapeHtml" in script
    assert "prefers-reduced-motion" in stylesheet
    assert ":focus-visible" in stylesheet


def test_web_shell_uses_the_bright_evidence_studio_theme():
    html = _web_asset("index.html")
    stylesheet = _web_asset("styles.css")

    assert '<meta name="theme-color" content="#f6f8fc" />' in html
    assert 'aria-describedby="composerHint"' in html
    assert 'aria-labelledby="evidenceTab"' in html
    assert "color-scheme: light" in stylesheet
    assert "color-scheme: dark" not in stylesheet
    assert "100dvh" in stylesheet
    assert "@media (forced-colors: active)" in stylesheet
