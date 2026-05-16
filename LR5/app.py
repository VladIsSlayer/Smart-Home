from flask import Flask, jsonify, render_template, request

import things

app = Flask(__name__, template_folder="server", static_folder="server", static_url_path="")

system = things.build_system()
devices = system["devices"]

robot, curtains, kettle, temperature, humidity, lighting = devices


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


# --- Мониторинг (ЛР3, без изменений) ---


@app.route("/connect_robot_vacuum")
def connect_robot_vacuum():
    return jsonify(robot.connect())


@app.route("/connect_smart_curtains")
def connect_smart_curtains():
    return jsonify(curtains.connect())


@app.route("/connect_smart_kettle")
def connect_smart_kettle():
    return jsonify(kettle.connect())


@app.route("/connect_temperature_control")
def connect_temperature_control():
    return jsonify(temperature.connect())


@app.route("/connect_humidity_control")
def connect_humidity_control():
    return jsonify(humidity.connect())


@app.route("/connect_smart_lighting")
def connect_smart_lighting():
    return jsonify(lighting.connect())


# --- Управляющие команды (ЛР4) ---


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


if __name__ == "__main__":
    app.run(debug=True)
