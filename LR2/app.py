from flask import Flask, jsonify, render_template, request

import things

app = Flask(__name__, template_folder="server", static_folder="server", static_url_path="")

system = things.build_system()
db = system["db"]
mcu = system["mcu"]
devices = system["devices"]
child_ui = system["child_ui"]
parent_ui = system["parent_ui"]

robot = devices[0]
curtains = devices[1]
kettle = devices[2]
temperature = devices[3]
humidity = devices[4]
lighting = devices[5]

runtime_state = {
    "kettle_on": False,
    "vacuum_state": "Ожидает запуска",
    "map_name": "",
    "lights_on": True,
    "light_rgb": {"r": 255, "g": 180, "b": 90},
    "scene_last_saved": "",
}


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


def _make_status() -> dict:
    if runtime_state["kettle_on"]:
        kettle.currentWaterTemperature = min(float(kettle.targetTemperature), kettle.currentWaterTemperature + 2.0)
        if kettle.currentWaterTemperature >= float(kettle.targetTemperature):
            runtime_state["kettle_on"] = False
            kettle.isBoiling = False
    else:
        kettle.currentWaterTemperature = max(24.0, kettle.currentWaterTemperature - 1.0)

    return {
        "kettle": {
            "is_on": runtime_state["kettle_on"],
            "state_text": "Включен" if runtime_state["kettle_on"] else "Выключен",
            "current_temp": kettle.currentWaterTemperature,
            "target_temp": kettle.targetTemperature,
        },
        "vacuum": {
            "state": runtime_state["vacuum_state"],
            "battery": robot.batteryLevel,
            "map_name": runtime_state["map_name"] or "не загружена",
        },
        "curtains": {"position_percent": curtains.positionPercent},
        "lights": {
            "brightness": lighting.brightness,
            "color_temp": lighting.colorTemperature,
            "rgb": runtime_state["light_rgb"],
            "is_on": runtime_state["lights_on"],
            "state_text": "Включены" if runtime_state["lights_on"] else "Выключены",
        },
        "climate": {
            "temperature": temperature.temperature,
            "target_temperature": temperature.targetTemperature,
            "humidity": humidity.humidity,
            "target_humidity": humidity.targetHumidity,
        },
        "devices": [d.name for d in mcu.deviceList],
        "scene_last_saved": runtime_state["scene_last_saved"],
    }


@app.route("/api/status")
def api_status():
    return jsonify(_make_status())


@app.route("/api")
@app.route("/api/")
def api_root():
    return jsonify({"ok": True, "message": "LR2 API is running", "status": _make_status()})


@app.route("/api/kettle/on", methods=["POST"])
def api_kettle_on():
    payload = request.get_json(silent=True) or {}
    target = int(payload.get("target_temp", kettle.targetTemperature))
    kettle.targetTemperature = max(40, min(100, target))
    kettle.isBoiling = True
    runtime_state["kettle_on"] = True
    msg = kettle.executeCommand(f"boil:{kettle.targetTemperature}")
    db.saveCommandLog(kettle.id, "kettle_on", msg)
    return jsonify({"ok": True, "message": f"Чайник включен, цель {kettle.targetTemperature} C"})


@app.route("/api/kettle/off", methods=["POST"])
def api_kettle_off():
    kettle.isBoiling = False
    runtime_state["kettle_on"] = False
    msg = kettle.executeCommand("off")
    db.saveCommandLog(kettle.id, "kettle_off", msg)
    return jsonify({"ok": True, "message": "Чайник выключен"})


@app.route("/api/kettle/target", methods=["POST"])
def api_kettle_target():
    payload = request.get_json(silent=True) or {}
    target = int(payload.get("target_temp", kettle.targetTemperature))
    kettle.targetTemperature = max(40, min(100, target))
    msg = f"Целевая температура чайника сохранена: {kettle.targetTemperature} C"
    return jsonify({"ok": True, "message": msg, "target_temp": kettle.targetTemperature})


@app.route("/api/curtains/open", methods=["POST"])
def api_curtains_open():
    payload = request.get_json(silent=True) or {}
    percent = int(payload.get("percent", 100))
    result = curtains.open(percent)
    return jsonify({"ok": True, "message": result, "position": curtains.positionPercent})


@app.route("/api/curtains/close", methods=["POST"])
def api_curtains_close():
    result = curtains.close()
    return jsonify({"ok": True, "message": result, "position": curtains.positionPercent})


@app.route("/api/curtains/set", methods=["POST"])
def api_curtains_set():
    payload = request.get_json(silent=True) or {}
    percent = int(payload.get("percent", curtains.positionPercent))
    percent = max(0, min(100, percent))
    result = curtains.open(percent)
    return jsonify({"ok": True, "message": f"Положение штор сохранено: {percent}%", "position": curtains.positionPercent, "result": result})


@app.route("/api/lights/apply", methods=["POST"])
def api_lights_apply():
    payload = request.get_json(silent=True) or {}
    brightness = int(payload.get("brightness", lighting.brightness))
    r = int(payload.get("r", runtime_state["light_rgb"]["r"]))
    g = int(payload.get("g", runtime_state["light_rgb"]["g"]))
    b = int(payload.get("b", runtime_state["light_rgb"]["b"]))
    lighting.setBrightness(brightness)
    runtime_state["light_rgb"] = {
        "r": max(0, min(255, r)),
        "g": max(0, min(255, g)),
        "b": max(0, min(255, b)),
    }
    avg = int((runtime_state["light_rgb"]["r"] + runtime_state["light_rgb"]["g"] + runtime_state["light_rgb"]["b"]) / 3)
    lighting.setColorTemperature(2000 + int((avg / 255) * 4500))
    return jsonify({"ok": True, "message": "Настройки ламп применены", "lights": _make_status()["lights"]})


@app.route("/api/lights/on", methods=["POST"])
def api_lights_on():
    runtime_state["lights_on"] = True
    if lighting.brightness == 0:
        lighting.setBrightness(70)
    return jsonify({"ok": True, "message": "Лампы включены", "lights": _make_status()["lights"]})


@app.route("/api/lights/off", methods=["POST"])
def api_lights_off():
    runtime_state["lights_on"] = False
    lighting.setBrightness(0)
    return jsonify({"ok": True, "message": "Лампы выключены", "lights": _make_status()["lights"]})


@app.route("/api/vacuum/start", methods=["POST"])
def api_vacuum_start():
    runtime_state["vacuum_state"] = "Запущен"
    result = robot.startCleaning("auto", robot.roomMap)
    return jsonify({"ok": True, "message": result, "state": runtime_state["vacuum_state"]})


@app.route("/api/vacuum/pause", methods=["POST"])
def api_vacuum_pause():
    runtime_state["vacuum_state"] = "Ожидает запуска"
    return jsonify({"ok": True, "message": "Уборка приостановлена", "state": runtime_state["vacuum_state"]})


@app.route("/api/vacuum/dock", methods=["POST"])
def api_vacuum_dock():
    runtime_state["vacuum_state"] = "Ожидает запуска"
    result = robot.goToDock()
    return jsonify({"ok": True, "message": result, "state": runtime_state["vacuum_state"]})


@app.route("/api/map/upload", methods=["POST"])
def api_map_upload():
    payload = request.get_json(silent=True) or {}
    map_name = str(payload.get("map_name", "")).strip()
    if not map_name:
        return jsonify({"ok": False, "message": "Имя карты не передано"}), 400
    runtime_state["map_name"] = map_name
    robot.updateRoomMap(["hall", "kitchen", "bedroom"])
    return jsonify({"ok": True, "message": f"Карта '{map_name}' загружена", "map_name": map_name})


@app.route("/api/map/view")
def api_map_view():
    map_name = runtime_state["map_name"]
    if not map_name:
        return jsonify({"ok": False, "message": "Карта дома еще не загружена"}), 404
    return jsonify({"ok": True, "message": f"Открыта карта: {map_name}", "map_name": map_name})


@app.route("/api/devices")
def api_devices():
    return jsonify({"ok": True, "devices": [d.name for d in mcu.deviceList]})


@app.route("/api/devices/add", methods=["POST"])
def api_devices_add():
    payload = request.get_json(silent=True) or {}
    name = str(payload.get("name", "")).strip()
    if not name:
        return jsonify({"ok": False, "message": "Пустое имя устройства"}), 400
    device_id = f"custom-{len(mcu.deviceList) + 1}"
    new_device = things.SmartLighting(device_id, name)
    mcu.addDevice(new_device)
    return jsonify({"ok": True, "message": f"Устройство '{name}' добавлено", "devices": [d.name for d in mcu.deviceList]})


@app.route("/api/devices/remove", methods=["POST"])
def api_devices_remove():
    payload = request.get_json(silent=True) or {}
    index = int(payload.get("index", -1))
    if index < 0 or index >= len(mcu.deviceList):
        return jsonify({"ok": False, "message": "Некорректный индекс"}), 400
    name = mcu.deviceList[index].name
    del mcu.deviceList[index]
    return jsonify({"ok": True, "message": f"Устройство '{name}' удалено", "devices": [d.name for d in mcu.deviceList]})


@app.route("/api/climate/apply", methods=["POST"])
def api_climate_apply():
    payload = request.get_json(silent=True) or {}
    t = float(payload.get("target_temperature", temperature.targetTemperature))
    h = float(payload.get("target_humidity", humidity.targetHumidity))
    msg_t = temperature.setTargetTemperature(t)
    msg_h = humidity.setTargetHumidity(h)
    return jsonify({"ok": True, "message": f"{msg_t}; {msg_h}", "climate": _make_status()["climate"]})


@app.route("/api/scene/save", methods=["POST"])
def api_scene_save():
    payload = request.get_json(silent=True) or {}
    name = str(payload.get("name", "")).strip() or "Без названия"
    scene_dt = f"{payload.get('date', '')} {payload.get('time', '')}".strip()
    runtime_state["scene_last_saved"] = f"{name} ({scene_dt})"
    return jsonify({"ok": True, "message": f"Сценарий '{name}' сохранен", "scene": runtime_state["scene_last_saved"]})


@app.route("/demo")
def demo():
    print("\n===== LR2 DEMO START =====")

    robot = devices[0]
    curtains = devices[1]
    kettle = devices[2]
    temperature = devices[3]
    humidity = devices[4]
    lighting = devices[5]

    results = {
        "connect": [device.connect() for device in devices],
        "robot": [
            robot.startCleaning("eco", ["hall", "kitchen"]),
            robot.updateRoomMap(["hall", "kitchen", "bedroom", "bathroom"]),
            robot.goToDock(),
        ],
        "curtains": [curtains.open(65), curtains.close()],
        "kettle": [kettle.boil(95), kettle.keepWarm(15), kettle.getCurrentWaterTemperature()],
        "temperature": [temperature.setTargetTemperature(23.5), temperature.getCurrentTemperature()],
        "humidity": [humidity.setTargetHumidity(48.0), humidity.getCurrentHumidity()],
        "lighting": [lighting.setBrightness(80), lighting.setColorTemperature(4200)],
        "schedules": [
            kettle.saveSchedule(["07:00 boil 90C"]),
            lighting.updateSchedule(["20:00 brightness 40%"]),
        ],
    }

    cmd1 = mcu.createCommand("kettle-1", "boil:95")
    cmd2 = mcu.createCommand("light-1", "setBrightness:80")
    res1 = mcu.dispatchCommand("kettle-1", "boil:95")
    res2 = mcu.dispatchCommand("light-1", "setBrightness:80")
    data_temp = mcu.getData("temp-1")
    mcu.sentToDataBase({"deviceId": "temp-1", "value": data_temp})
    db.saveDeviceSchedule("kettle-1", ["07:00 boil 90C"])
    history = db.getDeviceHistory("temp-1")

    child_ok = child_ui.sendCommand("curtains-1", "open:50")
    child_ui.controlAllowedDevices()
    child_ui.showBasicStatus(mcu.getData("curtains-1"))

    parent_ok = parent_ui.sendCommand("light-1", "setColorTemperature:4000")
    parent_ui.configureAutomationRules()
    parent_ui.showFullStatus(mcu.getData("light-1"))

    report = {
        "results": results,
        "mcu": {
            "created_commands": [cmd1, cmd2],
            "dispatch_results": [res1, res2],
            "queue_size": len(mcu.command_queue),
        },
        "database": {"history_temp_count": len(history)},
        "ui": {"child_send_ok": child_ok, "parent_send_ok": parent_ok},
    }

    print("===== LR2 DEMO END =====\n")
    return jsonify(report)


if __name__ == "__main__":
    app.run(debug=True)
