"""Deterministic guardrails around the probabilistic model.

Prompt instructions alone are not a security boundary. These checks therefore
run in application code: input normalization, retrieved-content risk tagging,
and citation validation are all deterministic and unit-testable.
"""

from __future__ import annotations

import re
import unicodedata
from dataclasses import asdict, dataclass

CONTROL_CHAR_RE = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]")
CITATION_RE = re.compile(r"\[S(\d+)\]")

# These patterns are signals, not proof of an attack. We tag the chunk and tell
# the model to treat it as data; we do not silently delete legitimate security
# documentation that happens to discuss prompt injection.
INJECTION_SIGNALS: tuple[tuple[str, re.Pattern[str]], ...] = (
    ("ignore_instructions", re.compile(r"ignore\s+(all\s+)?previous\s+instructions", re.I)),
    ("system_prompt_request", re.compile(r"(reveal|print|show).{0,20}system\s+prompt", re.I)),
    ("role_override", re.compile(r"\b(system|assistant)\s*:\s*", re.I)),
    ("tool_coercion", re.compile(r"(call|invoke|execute).{0,20}(tool|function|shell)", re.I)),
    ("zh_ignore_instructions", re.compile(r"忽略.{0,12}(之前|以上|原有).{0,12}(指令|要求|规则)")),
    ("zh_prompt_request", re.compile(r"(输出|泄露|显示).{0,12}(系统提示词|系统指令|密钥)")),
)


@dataclass(slots=True)
class CitationReport:
    """Result of checking the generated answer against available source IDs."""

    valid: bool
    cited_ids: list[str]
    invalid_ids: list[str]
    reason: str

    def to_dict(self) -> dict:
        return asdict(self)


def sanitize_question(question: str, max_chars: int) -> str:
    """Normalize user input while preserving meaningful punctuation."""

    normalized = unicodedata.normalize("NFKC", question)
    normalized = CONTROL_CHAR_RE.sub("", normalized).strip()
    if not normalized:
        raise ValueError("question cannot be empty")
    if len(normalized) > max_chars:
        raise ValueError(f"question exceeds the {max_chars}-character limit")
    return normalized


def detect_prompt_injection(text: str) -> list[str]:
    """Return explainable risk tags for untrusted retrieved text."""

    return [name for name, pattern in INJECTION_SIGNALS if pattern.search(text)]


def validate_citations(answer: str, source_count: int, *, abstained: bool = False) -> CitationReport:
    """Check that an evidence-based answer cites only sources that exist.

    A refusal/abstention does not need a citation. A substantive answer must cite
    at least one source, and every cited identifier must map to the context that
    was actually supplied to the model.
    """

    numbers = [int(value) for value in CITATION_RE.findall(answer)]
    cited = list(dict.fromkeys(f"S{number}" for number in numbers))
    invalid = [f"S{number}" for number in numbers if number < 1 or number > source_count]
    invalid = list(dict.fromkeys(invalid))

    if invalid:
        return CitationReport(False, cited, invalid, "answer cites a source that was not provided")
    if not abstained and source_count == 0:
        return CitationReport(False, cited, [], "substantive answer has no evidence source")
    if not abstained and source_count > 0 and not cited:
        return CitationReport(False, [], [], "answer contains no source citation")
    return CitationReport(True, cited, [], "citations map to the supplied evidence")
