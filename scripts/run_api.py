"""PyCharm-friendly API entry point.

PyCharm may use ``scripts/`` as the working directory when a file is launched
directly. Resolve the repository root before importing application settings so
Pydantic can find the project's ``.env`` and relative storage paths.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path


def _include_localhost_in_no_proxy() -> None:
    """Keep local Qdrant traffic away from machine-level HTTP proxies."""

    for variable in ("NO_PROXY", "no_proxy"):
        entries = [item.strip() for item in os.environ.get(variable, "").split(",") if item.strip()]
        for host in ("localhost", "127.0.0.1"):
            if host not in entries:
                entries.append(host)
        os.environ[variable] = ",".join(entries)


def main() -> None:
    """Run the same installed API entry point used by ``rag-agent-api``."""

    project_root = Path(__file__).resolve().parents[1]
    os.chdir(project_root)
    sys.path.insert(0, str(project_root / "src"))
    _include_localhost_in_no_proxy()

    # Import after fixing cwd/sys.path: Settings is created at module import and
    # intentionally reads .env relative to the repository root.
    from rag_agent.api.main import run

    run()


if __name__ == "__main__":
    main()
