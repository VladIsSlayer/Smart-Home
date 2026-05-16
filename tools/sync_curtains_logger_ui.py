#!/usr/bin/env python3
"""Синхронизация SmartCurtains, Logger и UI из LR9 в LR4–LR8."""

from __future__ import annotations

import re
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LR9 = ROOT / "LR9"
SRC_THINGS = (LR9 / "things.py").read_text(encoding="utf-8")


def extract(text: str, start: str, end: str) -> str:
    i = text.index(start)
    j = text.index(end, i)
    return text[i:j]


def merge_things(path: Path) -> None:
    text = path.read_text(encoding="utf-8")
    curtains = extract(SRC_THINGS, "class SmartCurtains", "class SmartKettle")
    if "class Logger:" in text:
        logger = extract(SRC_THINGS, "class Logger:", "class Database:")
        text = text[: text.index("class SmartCurtains")] + curtains + text[text.index("class SmartKettle") :]
        text = text[: text.index("class Logger:")] + logger + text[text.index("class Database:") :]
    else:
        text = text[: text.index("class SmartCurtains")] + curtains + text[text.index("class SmartKettle") :]
    if "CURTAIN_ACTION_PATTERN" not in text.split("class SmartDevice")[0]:
        if "import re\n" not in text:
            text = text.replace("import random\n", "import random\nimport re\n", 1)
        text = text.replace(
            "from flask import Request\n\n\nclass SmartDevice",
            'from flask import Request\n\nCURTAIN_ACTION_PATTERN = re.compile(r"^(open|close|set|save)$", re.IGNORECASE)\n\n\nclass SmartDevice',
            1,
        )
    path.write_text(text, encoding="utf-8")


def patch_script(path: Path, lab: int) -> None:
    src = (LR9 / "server" / "script.js").read_text(encoding="utf-8")
    dst = path.read_text(encoding="utf-8")
    for fn in ("renderAnalysis", "refreshAnalysisPanel", "connectSmartCurtains"):
        block = extract(src, f"function {fn}", "function ")
        if fn == "connectSmartCurtains":
            block = extract(src, "function connectSmartCurtains", "function connectSmartKettle")
        old = extract(dst, f"function {fn}", "function " if fn != "connectSmartCurtains" else "function connectSmartKettle")
        if fn == "connectSmartCurtains":
            old = extract(dst, "function connectSmartCurtains", "function connectSmartKettle")
        dst = dst.replace(old, block)
    # curtain buttons
    dst = re.sub(
        r'bind\("adminCurtainsOpenBtn".*?bind\("adminLightsOnBtn"',
        extract(src, 'bind("adminCurtainsOpenBtn"', 'bind("adminLightsOnBtn"'),
        dst,
        count=1,
        flags=re.DOTALL,
    )
    # dom ready tail
    if "refreshAnalysisPanel" not in dst and lab >= 8:
        dst = dst.replace(
            "connectAllThings();",
            "connectAllThings();\n    refreshAnalysisPanel();",
            1,
        )
        if "setInterval(refreshAnalysisPanel" not in dst:
            dst = dst.replace(
                "setInterval(connectAllThings, 5000);",
                "setInterval(connectAllThings, 5000);\n    setInterval(refreshAnalysisPanel, 5000);",
                1,
            )
    if lab == 9 and "setInterval(loadTemperatureChart" not in dst:
        dst = dst.replace(
            "setInterval(refreshAnalysisPanel, 5000);",
            "setInterval(refreshAnalysisPanel, 5000);\n    if (document.getElementById(\"temperatureChart\")) {\n        setInterval(loadTemperatureChart, 10000);\n    }",
            1,
        )
    path.write_text(dst, encoding="utf-8")


def patch_admin_curtains(path: Path) -> None:
    src = (LR9 / "server" / "admin.html").read_text(encoding="utf-8")
    dst = path.read_text(encoding="utf-8")
    start = '<h2 class="section-title">Умные шторы'
    end = '<h2 class="section-title">Умные лампы'
    s = src[src.index(start) : src.index(end)]
    d0 = dst.index(start)
    d1 = dst.index(end)
    path.write_text(dst[:d0] + s + dst[d1:], encoding="utf-8")


def main() -> None:
    for n in range(4, 10):
        lab = ROOT / f"LR{n}"
        print(f"LR{n}...")
        merge_things(lab / "things.py")
        patch_script(lab / "server" / "script.js", n)
        patch_admin_curtains(lab / "server" / "admin.html")
        if n >= 7:
            app = (lab / "app.py").read_text(encoding="utf-8")
            if "payload[\"analysis\"]" not in app and "connect_smart_curtains" in app:
                app = app.replace(
                    "    return jsonify(curtains.connect())",
                    "    payload = curtains.connect()\n    payload[\"analysis\"] = _analysis_payload()\n    return jsonify(payload)",
                    1,
                )
                (lab / "app.py").write_text(app, encoding="utf-8")
    print("Done.")


if __name__ == "__main__":
    main()
