"""Self-contained, offline HTML reports built only from recorded evidence."""
from __future__ import annotations

import json
from importlib.resources import files
from pathlib import Path

from .evidence import verify_bundle


def write_report(bundles: list[dict], path: str | Path) -> None:
    for evidence in bundles:
        verify_bundle(evidence)
    data = json.dumps(bundles, ensure_ascii=True, allow_nan=False).replace("<", "\\u003c").replace(">", "\\u003e").replace("&", "\\u0026")
    template = files("breachtwin").joinpath("assets/report.html").read_text(encoding="utf-8")
    text = template.replace("__BREACHTWIN_DATA__", data)
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(text, encoding="utf-8")
