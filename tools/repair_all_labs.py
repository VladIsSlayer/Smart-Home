#!/usr/bin/env python3
"""Восстановление LR4–LR9: things.py, app.py, script.js по эталону LR9."""

from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LR9_THINGS = (ROOT / "LR9" / "things.py").read_text(encoding="utf-8")  # includes _safe_print
LR9_SCRIPT = (ROOT / "LR9" / "server" / "script.js").read_text(encoding="utf-8")

BUILD_SYSTEMS = {
    4: '''
def build_system() -> dict[str, Any]:
    db = Database("SmartHomeDB")
    mcu = MainControlUnit(db)
    devices: list[SmartDevice] = [
        RobotVacuum("vacuum-1", "RobotVacuum"),
        SmartCurtains("curtains-1", "SmartCurtains"),
        SmartKettle("kettle-1", "SmartKettle"),
        TemperatureControl("temp-1", "TemperatureControl"),
        HumidityControl("humidity-1", "HumidityControl"),
        SmartLighting("light-1", "SmartLighting"),
    ]
    for device in devices:
        mcu.addDevice(device)
    scene_manager = SceneManager("data")
    return {
        "db": db,
        "mcu": mcu,
        "devices": devices,
        "child_ui": ChildUI(mcu),
        "parent_ui": ParentUI(mcu),
        "scene_manager": scene_manager,
    }
''',
    5: None,  # same as 4
    6: '''
def build_system() -> dict[str, Any]:
    db = Database("SmartHomeDB")
    mcu = MainControlUnit(db)
    devices: list[SmartDevice] = [
        RobotVacuum("vacuum-1", "RobotVacuum"),
        SmartCurtains("curtains-1", "SmartCurtains"),
        SmartKettle("kettle-1", "SmartKettle"),
        TemperatureControl("temp-1", "TemperatureControl"),
        HumidityControl("humidity-1", "HumidityControl"),
        SmartLighting("light-1", "SmartLighting"),
    ]
    for device in devices:
        mcu.addDevice(device)
    automation = HomeAutomation(
        temperature=devices[3],
        humidity=devices[4],
        lighting=devices[5],
        curtains=devices[1],
    )
    scene_manager = SceneManager("data")
    return {
        "db": db,
        "mcu": mcu,
        "devices": devices,
        "child_ui": ChildUI(mcu),
        "parent_ui": ParentUI(mcu),
        "automation": automation,
        "scene_manager": scene_manager,
    }
''',
}

BUILD_SYSTEMS[5] = BUILD_SYSTEMS[4]

# LR7-9 use full build from LR9 (default)


def patch_things(lab: int) -> None:
    text = LR9_THINGS
    if lab in BUILD_SYSTEMS:
        text = text[: text.index("def build_system()")] + BUILD_SYSTEMS[lab].strip() + "\n"
    (ROOT / f"LR{lab}" / "things.py").write_text(text, encoding="utf-8")


ANALYSIS_TILE_RE = re.compile(
    r'\s*<article class="tile tile-wide">.*?id="temperatureChart".*?</article>',
    re.DOTALL,
)
CHART_BLOCK_RE = re.compile(
    r"\s*<h3>График температуры</h3>\s*<canvas id=\"temperatureChart\"[^>]*></canvas>",
    re.DOTALL,
)
CHART_JS_SCRIPT_RE = re.compile(
    r'\s*<script src="https://cdn\.jsdelivr\.net/npm/chart\.js[^"]*"></script>\s*',
    re.DOTALL,
)


def patch_admin_html(lab: int) -> None:
    text = (ROOT / "LR9" / "server" / "admin.html").read_text(encoding="utf-8")
    if lab < 7:
        text = ANALYSIS_TILE_RE.sub("", text)
    elif lab < 9:
        text = CHART_BLOCK_RE.sub("", text)
        text = CHART_JS_SCRIPT_RE.sub("\n", text)
        text = text.replace(
            "<h2 class=\"section-title\">Анализ и визуализация 📈</h2>",
            "<h2 class=\"section-title\">Анализ данных 📊</h2>",
        )
    for other in ("index.html", "user.html"):
        src = ROOT / "LR9" / "server" / other
        dst = ROOT / f"LR{lab}" / "server" / other
        body = src.read_text(encoding="utf-8").replace("?v=11", f"?v={lab}")
        dst.write_text(body, encoding="utf-8")
    text = text.replace("?v=11", f"?v={lab}")
    (ROOT / f"LR{lab}" / "server" / "admin.html").write_text(text, encoding="utf-8")


INIT_ANALYSIS_BLOCK = """    if (document.getElementById("analysisStats")) {
        refreshAnalysisPanel();
        setInterval(refreshAnalysisPanel, 5000);
    }
"""
INIT_CHART_BLOCK = """    if (document.getElementById("temperatureChart")) {
        loadTemperatureChart();
        setInterval(loadTemperatureChart, 5000);
    }
"""


def patch_script(lab: int) -> None:
    text = LR9_SCRIPT.replace("?v=11", f"?v={lab}")
    if lab < 7:
        text = re.sub(
            r"\nfunction renderAnalysis\(analysis\) \{.*?\n\}\n",
            "\n",
            text,
            count=1,
            flags=re.DOTALL,
        )
        text = re.sub(
            r"\nfunction refreshAnalysisPanel\(\) \{.*?\n\}\n",
            "\n",
            text,
            count=1,
            flags=re.DOTALL,
        )
        text = text.replace("        if (data.analysis) renderAnalysis(data.analysis);\n", "")
        text = text.replace(INIT_ANALYSIS_BLOCK, "")
        text = text.replace(INIT_CHART_BLOCK, "")
    if lab < 9:
        text = re.sub(
            r"\nlet temperatureChartInstance = null;.*?^function connectSmartCurtains",
            "\nfunction connectSmartCurtains",
            text,
            count=1,
            flags=re.MULTILINE | re.DOTALL,
        )
        text = text.replace(INIT_CHART_BLOCK, "")
    (ROOT / f"LR{lab}" / "server" / "script.js").write_text(text, encoding="utf-8")


def write_app(lab: int) -> None:
    common_head = '''import sys

from flask import Flask, jsonify, render_template, request

if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

import things

app = Flask(__name__, template_folder="server", static_folder="server", static_url_path="")

system = things.build_system()
devices = system["devices"]
scene_manager = system["scene_manager"]
'''
    if lab >= 6:
        common_head += "automation = system[\"automation\"]\n"
    if lab >= 7:
        common_head += "logger = system[\"logger\"]\n"
    common_head += """
robot, curtains, kettle, temperature, humidity, lighting = devices
"""
    if lab >= 7:
        common_head += "\nlogger.bootstrap_initial(temperature.temperature, humidity.humidity)\n"
    if lab >= 6:
        common_head += """
def _run_automation() -> list[str]:
    return automation.run_after_sensor_update()

"""
    if lab >= 7:
        common_head += """
def _analysis_payload() -> dict:
    return {
        "avg_temperature": logger.get_average_temperature(),
        "max_temperature": logger.get_max_temperature(),
        "avg_humidity": logger.get_average_humidity(),
        "max_humidity": logger.get_max_humidity(),
    }

"""

    routes = '''
@app.route("/")
def home():
    return render_template("index.html")


@app.route("/index.html")
def index_html():
    return render_template("index.html")


@app.route("/admin.html")
def admin_html():
    return render_template("admin.html")


@app.route("/user.html")
def user_html():
    return render_template("user.html")


@app.route("/connect_robot_vacuum")
def connect_robot_vacuum():
    return jsonify(robot.connect(request))


@app.route("/connect_smart_curtains")
def connect_smart_curtains():
    payload = curtains.connect(request)
'''
    if lab >= 6:
        routes += """    auto = _run_automation()
    if auto:
        payload["automation"] = auto
"""
    if lab >= 7:
        routes += '    payload["analysis"] = _analysis_payload()\n'
    routes += """    return jsonify(payload)


@app.route("/connect_smart_kettle")
def connect_smart_kettle():
    return jsonify(kettle.connect(request))


@app.route("/connect_temperature_control")
def connect_temperature_control():
    payload = temperature.connect(request)
"""
    if lab >= 7:
        routes += "    logger.insert_temperature(temperature.temperature)\n"
    if lab >= 6:
        routes += """    auto = _run_automation()
    if auto:
        payload["automation"] = auto
"""
    if lab >= 7:
        routes += '    payload["analysis"] = _analysis_payload()\n'
    routes += """    return jsonify(payload)


@app.route("/connect_humidity_control")
def connect_humidity_control():
    payload = humidity.connect(request)
"""
    if lab >= 7:
        routes += "    logger.insert_humidity(humidity.humidity)\n"
    if lab >= 6:
        routes += """    auto = _run_automation()
    if auto:
        payload["automation"] = auto
"""
    if lab >= 7:
        routes += '    payload["analysis"] = _analysis_payload()\n'
    routes += """    return jsonify(payload)


@app.route("/connect_smart_lighting")
def connect_smart_lighting():
    return jsonify(lighting.connect(request))


@app.route("/control_robot_vacuum")
def control_robot_vacuum():
    return jsonify(robot.control(request))


@app.route("/control_smart_curtains")
def control_smart_curtains():
    return jsonify(curtains.control(request))


@app.route("/control_smart_kettle")
def control_smart_kettle():
    return jsonify(kettle.control(request))


@app.route("/control_temperature_control")
def control_temperature_control():
    return jsonify(temperature.control(request))


@app.route("/control_humidity_control")
def control_humidity_control():
    return jsonify(humidity.control(request))


@app.route("/control_smart_lighting")
def control_smart_lighting():
    return jsonify(lighting.control(request))

"""

    extra = ""
    if lab >= 7:
        extra += '''

@app.route("/api/analysis")
def api_analysis():
    return jsonify({"ok": True, "analysis": _analysis_payload()})

'''
    if lab >= 9:
        extra += '''
@app.route("/api/chart/temperature")
def api_chart_temperature():
    chart = logger.get_temperature_chart_data(limit=30)
    return jsonify({"ok": True, "chart": chart})

'''

    scenes = '''
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

    footer = '''
if __name__ == "__main__":
    app.run(debug=True)
'''
    if lab == 9:
        footer = '''
if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000, debug=True, use_reloader=False, threaded=True)
'''
    (ROOT / f"LR{lab}" / "app.py").write_text(
        common_head + routes + extra + scenes + footer, encoding="utf-8"
    )


def main() -> None:
    for lab in range(4, 10):
        print(f"Repair LR{lab}...")
        patch_things(lab)
        patch_script(lab)
        patch_admin_html(lab)
        write_app(lab)
    print("Done.")


if __name__ == "__main__":
    main()
