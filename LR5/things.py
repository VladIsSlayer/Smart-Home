import abc
import random
import re
import time
from typing import Any

from flask import Request

VACUUM_MODE_PATTERN = re.compile(r"^(eco|auto|turbo)$", re.IGNORECASE)
CURTAIN_ACTION_PATTERN = re.compile(r"^(open|close|set)$", re.IGNORECASE)


def _parse_float(raw: str, field: str) -> tuple[float | None, str | None]:
    try:
        return float(raw), None
    except (TypeError, ValueError):
        return None, f"Поле '{field}' должно быть числом, получено: {raw!r}"


def _parse_int(raw: str, field: str, low: int, high: int) -> tuple[int | None, str | None]:
    try:
        value = int(float(raw))
    except (TypeError, ValueError):
        return None, f"Поле '{field}' должно быть целым числом, получено: {raw!r}"
    if value < low or value > high:
        return None, f"Поле '{field}' должно быть в диапазоне {low}..{high}"
    return value, None


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
        if action == "start" and not VACUUM_MODE_PATTERN.match(mode):
            msg = f"Недопустимый режим уборки '{mode}'. Допустимо: eco, auto, turbo"
            print(f"[RobotVacuum.control] {msg}")
            return {"ok": False, "message": msg, "cleaningState": self.cleaningState}
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
    def __init__(self, device_id: str, name: str):
        super().__init__(device_id, name)
        self.positionPercent: int = 60
        self.mode: str = "manual"

    def connect(self) -> dict:
        self.emulate()
        self.status = "online"
        payload = {"id": self.id, "positionPercent": self.positionPercent, "mode": self.mode}
        print(f"[SmartCurtains.connect] {payload}")
        return payload

    def emulate(self) -> None:
        shift = random.randint(-3, 3)
        self.positionPercent = max(0, min(100, self.positionPercent + shift))

    def control(self, request: Request) -> dict:
        action = request.args.get("action", "set")
        if not CURTAIN_ACTION_PATTERN.match(action):
            msg = f"Недопустимое действие штор '{action}'. Допустимо: open, close, set"
            print(f"[SmartCurtains.control] {msg}")
            return {"ok": False, "message": msg, "positionPercent": self.positionPercent}
        if action == "open":
            percent, err = _parse_int(request.args.get("percent", "100"), "percent", 0, 100)
            if err:
                return {"ok": False, "message": err, "positionPercent": self.positionPercent}
            msg = self.open(percent)
        elif action == "close":
            msg = self.close()
        else:
            percent, err = _parse_int(request.args.get("percent", str(self.positionPercent)), "percent", 0, 100)
            if err:
                return {"ok": False, "message": err, "positionPercent": self.positionPercent}
            msg = self.open(percent)
        print(f"[SmartCurtains.control] {msg}")
        return {"ok": True, "message": msg, "positionPercent": self.positionPercent}

    def open(self, percent: int) -> str:
        self.positionPercent = max(0, min(100, percent))
        msg = f"{self.name}: opened to {self.positionPercent}%"
        print(f"[SmartCurtains.open] {msg}")
        return msg

    def close(self) -> str:
        self.positionPercent = 0
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
            target, err = _parse_int(request.args.get("target_temp", str(self.targetTemperature)), "target_temp", 40, 100)
            if err:
                return {"ok": False, "message": err, "isBoiling": self.isBoiling}
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
        target, err = _parse_int(request.args.get("target_temp", str(self.targetTemperature)), "target_temp", 40, 100)
        if err:
            return {"ok": False, "message": err, "targetTemperature": self.targetTemperature}
        self.targetTemperature = target
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
        if now - self._last_emulate_at >= 15.0:
            self.temperature = round(max(16.0, min(30.0, self.temperature + random.choice([-0.1, 0.1]))), 1)
            self._last_emulate_at = now

    def control(self, request: Request) -> dict:
        target, err = _parse_float(request.args.get("target_temperature", str(self.targetTemperature)), "target_temperature")
        if err:
            return {"ok": False, "message": err, "targetTemperature": self.targetTemperature}
        msg = self.setTargetTemperature(target)
        print(f"[TemperatureControl.control] {msg}")
        return {"ok": True, "message": msg, "targetTemperature": self.targetTemperature}

    def setTargetTemperature(self, temp: float) -> str:
        self.targetTemperature = float(temp)
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
        if now - self._last_emulate_at >= 15.0:
            self.humidity = round(max(25.0, min(70.0, self.humidity + random.choice([-0.3, 0.3]))), 1)
            self._last_emulate_at = now

    def control(self, request: Request) -> dict:
        target, err = _parse_float(request.args.get("target_humidity", str(self.targetHumidity)), "target_humidity")
        if err:
            return {"ok": False, "message": err, "targetHumidity": self.targetHumidity}
        if target < 25 or target > 70:
            msg = f"Влажность должна быть 25..70 %, получено {target}"
            return {"ok": False, "message": msg, "targetHumidity": self.targetHumidity}
        msg = self.setTargetHumidity(target)
        print(f"[HumidityControl.control] {msg}")
        return {"ok": True, "message": msg, "targetHumidity": self.targetHumidity}

    def setTargetHumidity(self, humidity: float) -> str:
        self.targetHumidity = float(humidity)
        msg = f"{self.name}: target humidity set to {self.targetHumidity} %"
        print(f"[HumidityControl.setTargetHumidity] {msg}")
        return msg


class SmartLighting(SmartDevice):
    def __init__(self, device_id: str, name: str):
        super().__init__(device_id, name)
        self.brightness: int = 70
        self.colorTemperature: int = 3500
        self.isOn: bool = True

    def connect(self) -> dict:
        self.emulate()
        self.status = "online"
        payload = {
            "id": self.id,
            "brightness": self.brightness,
            "colorTemperature": self.colorTemperature,
            "isOn": self.isOn,
        }
        print(f"[SmartLighting.connect] {payload}")
        return payload

    def emulate(self) -> None:
        if self.isOn:
            self.brightness = max(10, min(100, self.brightness + random.randint(-4, 4)))
            self.colorTemperature = max(2400, min(5000, self.colorTemperature + random.randint(-120, 120)))

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
            brightness, err_b = _parse_int(request.args.get("brightness", str(self.brightness)), "brightness", 0, 100)
            color_temp, err_c = _parse_int(
                request.args.get("color_temperature", str(self.colorTemperature)), "color_temperature", 2000, 6500
            )
            if err_b:
                return {"ok": False, "message": err_b, "brightness": self.brightness}
            if err_c:
                return {"ok": False, "message": err_c, "colorTemperature": self.colorTemperature}
            self.setBrightness(brightness)
            self.setColorTemperature(color_temp)
            self.isOn = self.brightness > 0
            msg = f"{self.name}: settings applied"
        print(f"[SmartLighting.control] {msg}")
        return {
            "ok": True,
            "message": msg,
            "brightness": self.brightness,
            "colorTemperature": self.colorTemperature,
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
