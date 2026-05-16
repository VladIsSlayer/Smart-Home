import abc
import random
import time
from typing import Any

from flask import Request


class SmartDevice(abc.ABC):
    def __init__(self, device_id: str, name: str):
        self.id: str = device_id
        self.name: str = name
        self.status: str = "offline"
        self.schedule: list = []
        print(f"[SmartDevice.__init__] created {self.name} ({self.id})")

    @abc.abstractmethod
    def connect(self) -> dict:
        pass

    def control(self, request: Request) -> dict:
        msg = f"{self.name}: control not implemented"
        print(f"[SmartDevice.control] {msg}")
        return {"ok": False, "message": msg}

    def executeCommand(self, command: str) -> str:
        self.status = f"executed: {command}"
        msg = f"{self.name}: command '{command}' executed"
        print(f"[SmartDevice.executeCommand] {msg}")
        return msg


class RobotVacuum(SmartDevice):
    def __init__(self, device_id: str, name: str):
        super().__init__(device_id, name)
        self.batteryLevel: int = 85
        self.dustContainerLevel: int = 20
        self.roomMapVersion: int = 1
        self.roomMap: list = ["hall", "kitchen", "bedroom"]
        self.cleaningState: str = "idle"

    def connect(self) -> dict:
        self.emulate()
        self.status = "online"
        payload = {
            "id": self.id,
            "status": self.status,
            "batteryLevel": self.batteryLevel,
            "cleaningState": self.cleaningState,
        }
        print(f"[RobotVacuum.connect] {payload}")
        return payload

    def emulate(self) -> None:
        self.batteryLevel = max(10, min(100, self.batteryLevel + random.randint(-2, 1)))
        self.dustContainerLevel = max(0, min(100, self.dustContainerLevel + random.randint(-1, 3)))

    def control(self, request: Request) -> dict:
        action = request.args.get("action", "start")
        mode = request.args.get("mode", "auto")
        if action == "start":
            self.cleaningState = "running"
            msg = self.startCleaning(mode, self.roomMap)
        elif action == "pause":
            self.cleaningState = "paused"
            msg = f"{self.name}: cleaning paused"
        elif action == "dock":
            self.cleaningState = "docked"
            msg = self.goToDock()
        else:
            msg = f"{self.name}: unknown action '{action}'"
            return {"ok": False, "message": msg, "cleaningState": self.cleaningState}
        print(f"[RobotVacuum.control] {msg}")
        return {"ok": True, "message": msg, "cleaningState": self.cleaningState, "mode": mode}

    def startCleaning(self, mode: str, roomMap: list) -> str:
        self.status = f"cleaning ({mode})"
        msg = f"{self.name}: cleaning started, mode={mode}, rooms={roomMap}"
        print(f"[RobotVacuum.startCleaning] {msg}")
        return msg

    def updateRoomMap(self, newRoomMap: list) -> str:
        self.roomMapVersion += 1
        self.roomMap = list(newRoomMap)
        msg = f"{self.name}: room map updated to v{self.roomMapVersion}"
        print(f"[RobotVacuum.updateRoomMap] {msg}")
        return msg

    def goToDock(self) -> str:
        self.status = "docked"
        msg = f"{self.name}: returned to dock"
        print(f"[RobotVacuum.goToDock] {msg}")
        return msg


class SmartCurtains(SmartDevice):
    DRIFT_INTERVAL_SEC = 120.0

    def __init__(self, device_id: str, name: str):
        super().__init__(device_id, name)
        self.positionPercent: int = 60
        self.mode: str = "manual"
        self._last_drift_at: float = time.monotonic()

    def connect(self) -> dict:
        self._maybe_drift()
        self.status = "online"
        payload = {"id": self.id, "positionPercent": self.positionPercent, "mode": self.mode}
        print(f"[SmartCurtains.connect] {payload}")
        return payload

    def _maybe_drift(self) -> None:
        """Редкое микродвижение (±1%) не чаще раза в 2 минуты — имитация ветра."""
        now = time.monotonic()
        if now - self._last_drift_at < self.DRIFT_INTERVAL_SEC:
            return
        self._last_drift_at = now
        shift = random.choice([-1, 0, 1])
        if shift == 0:
            return
        self.positionPercent = max(0, min(100, self.positionPercent + shift))
        print(f"[SmartCurtains._maybe_drift] position {self.positionPercent}%")

    def control(self, request: Request) -> dict:
        action = request.args.get("action", "set")
        if action == "open":
            percent = int(request.args.get("percent", 100))
            msg = self.open(percent)
        elif action == "close":
            msg = self.close()
        else:
            percent = int(request.args.get("percent", self.positionPercent))
            msg = self.open(percent)
        print(f"[SmartCurtains.control] {msg}")
        return {"ok": True, "message": msg, "positionPercent": self.positionPercent}

    def open(self, percent: int) -> str:
        self.positionPercent = max(0, min(100, percent))
        self._last_drift_at = time.monotonic()
        msg = f"{self.name}: opened to {self.positionPercent}%"
        print(f"[SmartCurtains.open] {msg}")
        return msg

    def close(self) -> str:
        self.positionPercent = 0
        self._last_drift_at = time.monotonic()
        msg = f"{self.name}: closed"
        print(f"[SmartCurtains.close] {msg}")
        return msg


class SmartKettle(SmartDevice):
    def __init__(self, device_id: str, name: str):
        super().__init__(device_id, name)
        self.waterLevelMl: int = 1200
        self.targetTemperature: int = 90
        self.currentWaterTemperature: float = 50.0
        self.isBoiling: bool = False
        self._last_cool_down_at: float = time.monotonic()

    def connect(self) -> dict:
        self.emulate()
        self.status = "online"
        payload = {
            "id": self.id,
            "waterLevelMl": self.waterLevelMl,
            "targetTemperature": self.targetTemperature,
            "currentWaterTemperature": self.currentWaterTemperature,
            "isBoiling": self.isBoiling,
        }
        print(f"[SmartKettle.connect] {payload}")
        return payload

    def emulate(self) -> None:
        self.waterLevelMl = max(0, min(1700, self.waterLevelMl + random.randint(-30, 10)))
        now = time.monotonic()
        elapsed = now - self._last_cool_down_at
        if elapsed >= 10.0:
            steps = int(elapsed // 10.0)
            self.currentWaterTemperature = max(24.0, self.currentWaterTemperature - float(steps))
            self._last_cool_down_at += steps * 10.0
        if not self.isBoiling:
            pass

    def control(self, request: Request) -> dict:
        action = request.args.get("action", "target")
        if action == "on":
            target = int(request.args.get("target_temp", self.targetTemperature))
            msg = self.boil(target)
            return {
                "ok": True,
                "message": msg,
                "isBoiling": self.isBoiling,
                "targetTemperature": self.targetTemperature,
                "currentWaterTemperature": self.currentWaterTemperature,
            }
        if action == "off":
            self.isBoiling = False
            msg = f"{self.name}: turned off"
            print(f"[SmartKettle.control] {msg}")
            return {"ok": True, "message": msg, "isBoiling": False, "currentWaterTemperature": self.currentWaterTemperature}
        target = int(request.args.get("target_temp", self.targetTemperature))
        self.targetTemperature = max(40, min(100, target))
        msg = f"{self.name}: target temperature saved {self.targetTemperature} C"
        print(f"[SmartKettle.control] {msg}")
        return {"ok": True, "message": msg, "targetTemperature": self.targetTemperature}

    def boil(self, targetTemp: int) -> str:
        self.targetTemperature = max(40, min(100, targetTemp))
        self.currentWaterTemperature = float(self.targetTemperature)
        self.isBoiling = True
        msg = f"{self.name}: boiled to {self.targetTemperature} C"
        print(f"[SmartKettle.boil] {msg}")
        self.isBoiling = False
        return msg


class TemperatureControl(SmartDevice):
    def __init__(self, device_id: str, name: str):
        super().__init__(device_id, name)
        self.temperature: float = 22.0
        self.targetTemperature: float = 24.0
        self._last_emulate_at: float = time.monotonic()

    def connect(self) -> dict:
        self.emulate()
        self.status = "online"
        payload = {"id": self.id, "temperature": self.temperature, "targetTemperature": self.targetTemperature}
        print(f"[TemperatureControl.connect] {payload}")
        return payload

    def emulate(self) -> None:
        now = time.monotonic()
        if now - self._last_emulate_at < 20.0:
            return
        self._last_emulate_at = now
        if self.temperature < self.targetTemperature:
            self.temperature = round(min(self.targetTemperature, self.temperature + 0.2), 1)
        elif self.temperature > self.targetTemperature:
            self.temperature = round(max(self.targetTemperature, self.temperature - 0.2), 1)

    def control(self, request: Request) -> dict:
        target = float(request.args.get("target_temperature", self.targetTemperature))
        msg = self.setTargetTemperature(target)
        print(f"[TemperatureControl.control] {msg}")
        return {
            "ok": True,
            "message": msg,
            "temperature": self.temperature,
            "targetTemperature": self.targetTemperature,
        }

    def setTargetTemperature(self, temp: float) -> str:
        self.targetTemperature = round(max(16.0, min(30.0, float(temp))), 1)
        msg = f"{self.name}: target temperature set to {self.targetTemperature} C"
        print(f"[TemperatureControl.setTargetTemperature] {msg}")
        return msg


class HumidityControl(SmartDevice):
    def __init__(self, device_id: str, name: str):
        super().__init__(device_id, name)
        self.humidity: float = 45.0
        self.targetHumidity: float = 50.0
        self._last_emulate_at: float = time.monotonic()

    def connect(self) -> dict:
        self.emulate()
        self.status = "online"
        payload = {"id": self.id, "humidity": self.humidity, "targetHumidity": self.targetHumidity}
        print(f"[HumidityControl.connect] {payload}")
        return payload

    def emulate(self) -> None:
        now = time.monotonic()
        if now - self._last_emulate_at < 20.0:
            return
        self._last_emulate_at = now
        if self.humidity < self.targetHumidity:
            self.humidity = round(min(self.targetHumidity, self.humidity + 0.5), 1)
        elif self.humidity > self.targetHumidity:
            self.humidity = round(max(self.targetHumidity, self.humidity - 0.5), 1)

    def control(self, request: Request) -> dict:
        target = float(request.args.get("target_humidity", self.targetHumidity))
        msg = self.setTargetHumidity(target)
        print(f"[HumidityControl.control] {msg}")
        return {
            "ok": True,
            "message": msg,
            "humidity": self.humidity,
            "targetHumidity": self.targetHumidity,
        }

    def setTargetHumidity(self, humidity: float) -> str:
        self.targetHumidity = round(max(25.0, min(70.0, float(humidity))), 1)
        msg = f"{self.name}: target humidity set to {self.targetHumidity} %"
        print(f"[HumidityControl.setTargetHumidity] {msg}")
        return msg


class SmartLighting(SmartDevice):
    def __init__(self, device_id: str, name: str):
        super().__init__(device_id, name)
        self.brightness: int = 70
        self.colorTemperature: int = 3500
        self.rgb_r: int = 255
        self.rgb_g: int = 180
        self.rgb_b: int = 90
        self.isOn: bool = True

    def connect(self) -> dict:
        self.status = "online"
        payload = {
            "id": self.id,
            "brightness": self.brightness,
            "colorTemperature": self.colorTemperature,
            "rgb_r": self.rgb_r,
            "rgb_g": self.rgb_g,
            "rgb_b": self.rgb_b,
            "isOn": self.isOn,
        }
        print(f"[SmartLighting.connect] {payload}")
        return payload

    def control(self, request: Request) -> dict:
        action = request.args.get("action", "apply")
        if action == "on":
            self.isOn = True
            if self.brightness == 0:
                self.brightness = 70
            msg = f"{self.name}: turned on"
        elif action == "off":
            self.isOn = False
            self.brightness = 0
            msg = f"{self.name}: turned off"
        else:
            brightness = int(request.args.get("brightness", self.brightness))
            self.rgb_r = max(0, min(255, int(request.args.get("r", self.rgb_r))))
            self.rgb_g = max(0, min(255, int(request.args.get("g", self.rgb_g))))
            self.rgb_b = max(0, min(255, int(request.args.get("b", self.rgb_b))))
            self.setBrightness(brightness)
            avg = int((self.rgb_r + self.rgb_g + self.rgb_b) / 3)
            self.colorTemperature = max(2000, min(6500, 2000 + int((avg / 255) * 4500)))
            self.isOn = self.brightness > 0
            msg = f"{self.name}: settings applied"
        print(f"[SmartLighting.control] {msg}")
        return {
            "ok": True,
            "message": msg,
            "brightness": self.brightness,
            "colorTemperature": self.colorTemperature,
            "rgb_r": self.rgb_r,
            "rgb_g": self.rgb_g,
            "rgb_b": self.rgb_b,
            "isOn": self.isOn,
        }

    def setBrightness(self, value: int) -> str:
        self.brightness = max(0, min(100, value))
        msg = f"{self.name}: brightness set to {self.brightness}%"
        print(f"[SmartLighting.setBrightness] {msg}")
        return msg

    def setColorTemperature(self, value: int) -> str:
        self.colorTemperature = max(2000, min(6500, value))
        msg = f"{self.name}: color temperature set to {self.colorTemperature}K"
        print(f"[SmartLighting.setColorTemperature] {msg}")
        return msg


class Database:
    def __init__(self, name: str):
        self.name: str = name
        self.deviceScheduleList: dict[str, list] = {}
        self._deviceData: dict[str, list] = {}
        self._commandLog: list[dict[str, str]] = []
        print(f"[Database.__init__] db '{self.name}' initialized")

    def saveCommandLog(self, deviceId: str, command: str, result: str) -> None:
        entry = {"deviceId": deviceId, "command": command, "result": result}
        self._commandLog.append(entry)
        print(f"[Database.saveCommandLog] {entry}")


class MainControlUnit:
    def __init__(self, database: Database):
        self.deviceList: list[SmartDevice] = []
        self.command_queue: list[dict] = []
        self._database = database
        print("[MainControlUnit.__init__] main control unit created")

    def addDevice(self, device: SmartDevice) -> str:
        self.deviceList.append(device)
        msg = f"Device '{device.name}' added"
        print(f"[MainControlUnit.addDevice] {msg}")
        return msg


class ChildUI:
    def __init__(self, mcu: MainControlUnit):
        self._mcu = mcu


class ParentUI:
    def __init__(self, mcu: MainControlUnit):
        self._mcu = mcu


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

    return {
        "db": db,
        "mcu": mcu,
        "devices": devices,
        "child_ui": ChildUI(mcu),
        "parent_ui": ParentUI(mcu),
    }
