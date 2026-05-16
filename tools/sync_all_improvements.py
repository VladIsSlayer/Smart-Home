#!/usr/bin/env python3
"""Синхронизация доработок устройств, UI и сценариев из LR9 в LR4-LR8."""

from __future__ import annotations

import re
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LR9 = ROOT / "LR9"
TARGETS = [ROOT / f"LR{n}" for n in range(4, 10)]

SCENE_API = '''

@app.route("/api/scenes", methods=["GET"])
def api_scenes_list():
    return jsonify({"ok": True, "scenes": scene_manager.list_scenes()})


@app.route("/api/scenes/save", methods=["POST"])
def api_scenes_save():
    payload = request.get_json(silent=True) or {}
    scene = scene_manager.save_scene(payload)
    return jsonify({"ok": True, "message": f"Сценарий «{scene['name']}» сохранён", "scene": scene})


@app.route("/api/scenes/apply", methods=["POST"])
def api_scenes_apply():
    payload = request.get_json(silent=True) or {}
    scene_id = str(payload.get("id", "")).strip()
    if not scene_id:
        return jsonify({"ok": False, "message": "Не указан id сценария"})
    messages = scene_manager.apply_scene(scene_id, robot, curtains, kettle, temperature, humidity, lighting)
    if messages and messages[0].startswith("Сценарий '"):
        return jsonify({"ok": False, "message": messages[0]})
    scene = scene_manager.get_scene(scene_id)
    return jsonify({
        "ok": True,
        "message": f"Сценарий «{scene['name'] if scene else scene_id}» применён",
        "details": messages,
    })


@app.route("/api/scenes/delete", methods=["POST"])
def api_scenes_delete():
    payload = request.get_json(silent=True) or {}
    scene_id = str(payload.get("id", "")).strip()
    if scene_manager.delete_scene(scene_id):
        return jsonify({"ok": True, "message": "Сценарий удалён"})
    return jsonify({"ok": False, "message": "Нельзя удалить встроенный или неизвестный сценарий"})
'''


def extract_block(text: str, start_marker: str, end_marker: str) -> str:
    start = text.index(start_marker)
    end = text.index(end_marker, start)
    return text[start:end]


def merge_things(target: Path, lr9_text: str, target_text: str) -> str:
    device_block = extract_block(lr9_text, "class RobotVacuum", "class SceneManager:")
    scene_block = extract_block(lr9_text, "class SceneManager:", "class Database:")
    tail = target_text[target_text.index("class Database:") :]
    head = target_text[: target_text.index("class RobotVacuum")]
    if "import uuid" not in head:
        head = head.replace("import time\n", "import time\nimport uuid\n")
    merged = head + device_block + scene_block + tail
    # build_system: ensure scene_manager
    if "scene_manager = SceneManager" not in merged:
        merged = re.sub(
            r"(    for device in devices:\n        mcu\.addDevice\(device\)\n)",
            r"\1\n    scene_manager = SceneManager(\"data\")\n",
            merged,
            count=1,
        )
        if '"scene_manager": scene_manager' not in merged:
            merged = re.sub(
                r"(\n    return \{[^\}]+)(\n    \})",
                lambda m: (
                    m.group(1).rstrip()
                    + (",\n        \"scene_manager\": scene_manager" if "scene_manager" not in m.group(1) else "")
                    + m.group(2)
                ),
                merged,
                count=1,
                flags=re.DOTALL,
            )
    return merged


def patch_app_py(path: Path) -> None:
    text = path.read_text(encoding="utf-8")
    if "scene_manager = system" in text:
        pass
    elif 'logger = system["logger"]' in text:
        text = text.replace(
            'logger = system["logger"]',
            'logger = system["logger"]\nscene_manager = system["scene_manager"]',
            1,
        )
    elif "devices = system" in text and "scene_manager" not in text:
        text = text.replace(
            "devices = system[\"devices\"]",
            'devices = system["devices"]\nscene_manager = system["scene_manager"]',
            1,
        )
    if "/api/scenes" not in text:
        anchor = "if __name__"
        if "@app.route(\"/api/chart/temperature\")" in text:
            text = text.replace("\n\nif __name__", SCENE_API + "\n\nif __name__", 1)
        elif "@app.route(\"/api/analysis\")" in text:
            text = text.replace("\n\nif __name__", SCENE_API + "\n\nif __name__", 1)
        else:
            text = text.replace("\n\nif __name__", SCENE_API + "\n\nif __name__", 1)
    path.write_text(text, encoding="utf-8")


def patch_admin_html(path: Path) -> None:
    src = (LR9 / "server" / "admin.html").read_text(encoding="utf-8")
    dst = path.read_text(encoding="utf-8")
    for block_name, start, end in [
        ("curtains", "<h2 class=\"section-title\">Умные шторы", "</article>\n\n                <article class=\"tile\">\n                    <h2 class=\"section-title\">Умные лампы"),
        ("lights_header", "<h2 class=\"section-title\">Умные лампы", "<label for=\"lightPower\">"),
        ("scenes", "<h2 class=\"section-title\">Сценарии", "</article>\n            </motion>\n        </section>"),
    ]:
        if block_name == "scenes":
            end = "</article>\n            </div>\n        </section>"
        try:
            s_chunk = src[src.index(start) : src.index(end, src.index(start)) + len(end)]
            d_start = dst.index(start)
            d_end = dst.index(end, d_start) + len(end)
            dst = dst[:d_start] + s_chunk + dst[d_end:]
        except ValueError:
            print(f"  skip admin block {block_name} in {path.parent.parent.name}")
    path.write_text(dst, encoding="utf-8")


def copy_script_from_lr9(target: Path, lab: int) -> None:
    src_path = LR9 / "server" / "script.js"
    dst_path = target / "server" / "script.js"
    text = src_path.read_text(encoding="utf-8")
    if lab < 9:
        text = re.sub(r"\?v=9", f"?v={lab}", text)
        # remove chart-specific if not in lab
        if lab < 9:
            text = re.sub(
                r"let temperatureChartInstance = null;.*?^function connectSmartCurtains",
                "function connectSmartCurtains",
                text,
                count=1,
                flags=re.MULTILINE | re.DOTALL,
            )
            text = text.replace("        if (data.analysis) renderAnalysis(data.analysis);\n", "")
            text = text.replace("    loadTemperatureChart();\n", "")
            text = text.replace("    setInterval(loadTemperatureChart, 15000);\n", "")
        if lab < 8:
            text = re.sub(r"function renderAnalysis.*?^let temperatureChartInstance", "let temperatureChartInstance", text, count=1, flags=re.MULTILINE | re.DOTALL)
            text = text.replace("let temperatureChartInstance = null;\n\n", "")
        if lab < 6:
            text = text.replace("        if (data.automation) showAutomation(data.automation);\n", "")
            text = text.replace("function showAutomation(actions) {\n    if (!actions || !actions.length) return;\n    showMessage(`Автоматика: ${actions.join(\"; \")}`);\n}\n\n", "")
    dst_path.write_text(text, encoding="utf-8")


def main() -> None:
    lr9_things = (LR9 / "things.py").read_text(encoding="utf-8")
    style_css = (LR9 / "server" / "style.css").read_text(encoding="utf-8")
    for n in range(4, 10):
        path = ROOT / f"LR{n}" / "server" / "style.css"
        existing = path.read_text(encoding="utf-8")
        if ".scenes-list" not in existing:
            path.write_text(existing + "\n" + style_css[style_css.index(".scenes-list") :], encoding="utf-8")

    for target in TARGETS:
        lab = int(target.name.replace("LR", ""))
        print(f"=== {target.name} ===")
        things_path = target / "things.py"
        merged = merge_things(things_path, lr9_things, things_path.read_text(encoding="utf-8"))
        things_path.write_text(merged, encoding="utf-8")
        patch_app_py(target / "app.py")
        patch_admin_html(target / "server" / "admin.html")
        copy_script_from_lr9(target, lab)
        print(f"  updated {target.name}")

    print("Done.")


if __name__ == "__main__":
    main()
