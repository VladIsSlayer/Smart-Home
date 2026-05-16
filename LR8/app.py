from flask import Flask, jsonify, render_template, request

import things

app = Flask(__name__, template_folder="server", static_folder="server", static_url_path="")

system = things.build_system()
devices = system["devices"]
automation = system["automation"]
logger = system["logger"]

robot, curtains, kettle, temperature, humidity, lighting = devices


def _run_automation() -> list[str]:
    return automation.run_after_sensor_update()


def _analysis_payload() -> dict:
    return {
        "avg_temperature": logger.get_average_temperature(),
        "max_temperature": logger.get_max_temperature(),
        "avg_humidity": logger.get_average_humidity(),
        "max_humidity": logger.get_max_humidity(),
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


@app.route("/connect_robot_vacuum")
def connect_robot_vacuum():
    return jsonify(robot.connect())


@app.route("/connect_smart_curtains")
def connect_smart_curtains():
    payload = curtains.connect()
    auto = _run_automation()
    if auto:
        payload["automation"] = auto
    payload["analysis"] = _analysis_payload()
    return jsonify(payload)


@app.route("/connect_smart_kettle")
def connect_smart_kettle():
    return jsonify(kettle.connect())


@app.route("/connect_temperature_control")
def connect_temperature_control():
    payload = temperature.connect()
    logger.insert_temperature(temperature.temperature)
    auto = _run_automation()
    if auto:
        payload["automation"] = auto
    payload["analysis"] = _analysis_payload()
    return jsonify(payload)


@app.route("/connect_humidity_control")
def connect_humidity_control():
    payload = humidity.connect()
    logger.insert_humidity(humidity.humidity)
    auto = _run_automation()
    if auto:
        payload["automation"] = auto
    payload["analysis"] = _analysis_payload()
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


@app.route("/api/analysis")
def api_analysis():
    return jsonify({"ok": True, "analysis": _analysis_payload()})


if __name__ == "__main__":
    app.run(debug=True)
