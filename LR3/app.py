from flask import Flask, jsonify, render_template

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


if __name__ == "__main__":
    app.run(debug=True)
