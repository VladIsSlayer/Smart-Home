import sys

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
automation = system["automation"]

robot, curtains, kettle, temperature, humidity, lighting = devices

def _run_automation() -> list[str]:
    return automation.run_after_sensor_update()


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
    return jsonify(robot.connect())


@app.route("/connect_smart_curtains")
def connect_smart_curtains():
    payload = curtains.connect()
    auto = _run_automation()
    if auto:
        payload["automation"] = auto
    return jsonify(payload)


@app.route("/connect_smart_kettle")
def connect_smart_kettle():
    return jsonify(kettle.connect())


@app.route("/connect_temperature_control")
def connect_temperature_control():
    payload = temperature.connect()
    auto = _run_automation()
    if auto:
        payload["automation"] = auto
    return jsonify(payload)


@app.route("/connect_humidity_control")
def connect_humidity_control():
    payload = humidity.connect()
    auto = _run_automation()
    if auto:
        payload["automation"] = auto
    return jsonify(payload)


@app.route("/connect_smart_lighting")
def connect_smart_lighting():
    return jsonify(lighting.connect())


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


if __name__ == "__main__":
    app.run(debug=True)
