import abc
import json
import random
import re
import sys
import time
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any

from flask import Request

if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass


def _safe_print(msg: str) -> None:
    try:
        print(msg)
    except UnicodeEncodeError:
        print(msg.encode("ascii", errors="replace").decode("ascii"))

try:
    import pymongo

    PYMONGO_AVAILABLE = True
except ImportError:
    pymongo = None
    PYMONGO_AVAILABLE = False

VACUUM_MODE_PATTERN = re.compile(r"^(eco|auto|turbo)$", re.IGNORECASE)
CURTAIN_ACTION_PATTERN = re.compile(r"^(open|close|set|save)$", re.IGNORECASE)


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
        _safe_print(f"[SmartDevice.__init__] created {self.name} ({self.id})")

    @abc.abstractmethod
    def connect(self) -> dict:
        pass

    def control(self, request: Request) -> dict:
        msg = f"{self.name}: control not implemented"
        _safe_print(f"[SmartDevice.control] {msg}")
        return {"ok": False, "message": msg}

    def executeCommand(self, command: str) -> str:
        self.status = f"executed: {command}"
        msg = f"{self.name}: command '{command}' executed"
        _safe_print(f"[SmartDevice.executeCommand] {msg}")
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
            "dustContainerLevel": self.dustContainerLevel,
        }
        _safe_print(f"[RobotVacuum.connect] {payload}")
        return payload

    def emulate(self) -> None:
        if self.cleaningState == "running":
            self.batteryLevel = max(5, self.batteryLevel - random.randint(1, 3))
            self.dustContainerLevel = max(0, min(100, self.dustContainerLevel + random.randint(1, 3)))
        elif self.cleaningState == "docked":
            self.batteryLevel = min(100, self.batteryLevel + random.randint(2, 5))
            self.dustContainerLevel = max(0, self.dustContainerLevel - random.randint(0, 1))

    def control(self, request: Request) -> dict:
        action = request.args.get("action", "start")
        mode = request.args.get("mode", "auto")
        if action == "start" and not VACUUM_MODE_PATTERN.match(mode):
            msg = f"Недопустимый режим уборки '{mode}'. Допустимо: eco, auto, turbo"
            _safe_print(f"[RobotVacuum.control] {msg}")
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
        _safe_print(f"[RobotVacuum.control] {msg}")
        return {"ok": True, "message": msg, "cleaningState": self.cleaningState, "mode": mode}

    def startCleaning(self, mode: str, roomMap: list) -> str:
        self.status = f"cleaning ({mode})"
        msg = f"{self.name}: cleaning started, mode={mode}, rooms={roomMap}"
        _safe_print(f"[RobotVacuum.startCleaning] {msg}")
        return msg

    def updateRoomMap(self, newRoomMap: list) -> str:
        self.roomMapVersion += 1
        self.roomMap = list(newRoomMap)
        msg = f"{self.name}: room map updated to v{self.roomMapVersion}"
        _safe_print(f"[RobotVacuum.updateRoomMap] {msg}")
        return msg

    def goToDock(self) -> str:
        self.status = "docked"
        msg = f"{self.name}: returned to dock"
        _safe_print(f"[RobotVacuum.goToDock] {msg}")
        return msg


class SmartCurtains(SmartDevice):
    DRIFT_INTERVAL_SEC = 120.0
    MOVE_INTERVAL_SEC = 1.5
    MOVE_STEP = 40

    def __init__(self, device_id: str, name: str):
        super().__init__(device_id, name)
        self.positionPercent: int = 60
        self._target_position: int = 60
        self.savedOpenPercent: int = 60
        self.mode: str = "manual"
        self._last_drift_at: float = time.monotonic()
        self._last_move_at: float = time.monotonic()

    def connect(self) -> dict:
        self._advance_position()
        if self.positionPercent == self._target_position:
            self._maybe_drift()
        self.status = "online"
        payload = {
            "id": self.id,
            "positionPercent": self.positionPercent,
            "targetPosition": self._target_position,
            "savedOpenPercent": self.savedOpenPercent,
            "mode": self.mode,
        }
        _safe_print(f"[SmartCurtains.connect] {payload}")
        return payload

    def _advance_position(self) -> None:
        now = time.monotonic()
        elapsed = now - self._last_move_at
        if elapsed < self.MOVE_INTERVAL_SEC:
            return
        steps = max(1, int(elapsed // self.MOVE_INTERVAL_SEC))
        self._last_move_at += steps * self.MOVE_INTERVAL_SEC
        for _ in range(steps):
            if self.positionPercent < self._target_position:
                self.positionPercent = min(self._target_position, self.positionPercent + self.MOVE_STEP)
            elif self.positionPercent > self._target_position:
                self.positionPercent = max(self._target_position, self.positionPercent - self.MOVE_STEP)
            else:
                break

    def _maybe_drift(self) -> None:
        now = time.monotonic()
        if now - self._last_drift_at < self.DRIFT_INTERVAL_SEC:
            return
        self._last_drift_at = now
        shift = random.choice([-1, 0, 1])
        if shift == 0:
            return
        self.positionPercent = max(0, min(100, self.positionPercent + shift))
        self._target_position = self.positionPercent

    def set_target_position(self, percent: int) -> None:
        self._target_position = max(0, min(100, percent))
        self._last_drift_at = time.monotonic()

    def _fast_advance(self, steps: int = 4) -> None:
        """Быстрый сдвиг при нажатии кнопок (не ждать следующего опроса)."""
        for _ in range(steps):
            if self.positionPercent == self._target_position:
                break
            if self.positionPercent < self._target_position:
                self.positionPercent = min(self._target_position, self.positionPercent + self.MOVE_STEP)
            else:
                self.positionPercent = max(self._target_position, self.positionPercent - self.MOVE_STEP)
        self._last_move_at = time.monotonic()

    def _control_payload(self, msg: str, ok: bool = True) -> dict:
        return {
            "ok": ok,
            "message": msg,
            "positionPercent": self.positionPercent,
            "targetPosition": self._target_position,
            "savedOpenPercent": self.savedOpenPercent,
        }

    def control(self, request: Request) -> dict:
        action = request.args.get("action", "set")
        if not CURTAIN_ACTION_PATTERN.match(action):
            msg = f"Недопустимое действие штор '{action}'. Допустимо: open, close, set, save"
            _safe_print(f"[SmartCurtains.control] {msg}")
            return self._control_payload(msg, ok=False)
        if action == "save":
            percent, err = _parse_int(
                request.args.get("percent", str(self.savedOpenPercent)), "percent", 0, 100
            )
            if err:
                return self._control_payload(err, ok=False)
            self.savedOpenPercent = percent
            msg = f"{self.name}: сохранено открытие для кнопки «Открыть» — {self.savedOpenPercent}%"
            _safe_print(f"[SmartCurtains.control] {msg}")
            return self._control_payload(msg)
        if action == "open":
            raw_percent = request.args.get("percent", "").strip()
            if raw_percent:
                percent, err = _parse_int(raw_percent, "percent", 0, 100)
                if err:
                    return self._control_payload(err, ok=False)
            else:
                percent = self.savedOpenPercent
            msg = self.open(percent)
        elif action == "close":
            msg = self.close()
        else:
            percent, err = _parse_int(request.args.get("percent", str(self.positionPercent)), "percent", 0, 100)
            if err:
                return self._control_payload(err, ok=False)
            msg = self.open(percent)
        self._fast_advance()
        _safe_print(f"[SmartCurtains.control] {msg}")
        return self._control_payload(msg)

    def open(self, percent: int) -> str:
        self.set_target_position(percent)
        msg = f"{self.name}: moving toward {self._target_position}% (now {self.positionPercent}%)"
        _safe_print(f"[SmartCurtains.open] {msg}")
        return msg

    def close(self) -> str:
        self.set_target_position(0)
        msg = f"{self.name}: closing (now {self.positionPercent}%)"
        _safe_print(f"[SmartCurtains.close] {msg}")
        return msg


class SmartKettle(SmartDevice):
    HEAT_INTERVAL_SEC = 5.0
    HEAT_STEP_C = 4.0

    def __init__(self, device_id: str, name: str):
        super().__init__(device_id, name)
        self.waterLevelMl: int = 1200
        self.targetTemperature: int = 90
        self.currentWaterTemperature: float = 50.0
        self.isBoiling: bool = False
        self._last_thermal_at: float = time.monotonic()

    def connect(self) -> dict:
        self.emulate()
        self.status = "online"
        payload = {
            "id": self.id,
            "waterLevelMl": self.waterLevelMl,
            "targetTemperature": self.targetTemperature,
            "currentWaterTemperature": round(self.currentWaterTemperature, 1),
            "isBoiling": self.isBoiling,
        }
        _safe_print(f"[SmartKettle.connect] {payload}")
        return payload

    def emulate(self) -> None:
        self.waterLevelMl = max(0, min(1700, self.waterLevelMl + random.randint(-30, 10)))
        now = time.monotonic()
        elapsed = now - self._last_thermal_at
        if elapsed < self.HEAT_INTERVAL_SEC:
            return
        steps = int(elapsed // self.HEAT_INTERVAL_SEC)
        self._last_thermal_at += steps * self.HEAT_INTERVAL_SEC
        for _ in range(steps):
            if self.isBoiling:
                if self.currentWaterTemperature >= self.targetTemperature:
                    self.currentWaterTemperature = float(self.targetTemperature)
                    self.isBoiling = False
                    break
                self.currentWaterTemperature = min(
                    float(self.targetTemperature),
                    self.currentWaterTemperature + self.HEAT_STEP_C,
                )
            else:
                self.currentWaterTemperature = max(24.0, self.currentWaterTemperature - 0.5)

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
            _safe_print(f"[SmartKettle.control] {msg}")
            return {"ok": True, "message": msg, "isBoiling": False, "currentWaterTemperature": self.currentWaterTemperature}
        target, err = _parse_int(request.args.get("target_temp", str(self.targetTemperature)), "target_temp", 40, 100)
        if err:
            return {"ok": False, "message": err, "targetTemperature": self.targetTemperature}
        self.targetTemperature = target
        msg = f"{self.name}: target temperature saved {self.targetTemperature} C"
        _safe_print(f"[SmartKettle.control] {msg}")
        return {"ok": True, "message": msg, "targetTemperature": self.targetTemperature}

    def boil(self, targetTemp: int) -> str:
        self.targetTemperature = max(40, min(100, targetTemp))
        self.isBoiling = True
        msg = f"{self.name}: heating to {self.targetTemperature} C (now {self.currentWaterTemperature:.1f} C)"
        _safe_print(f"[SmartKettle.boil] {msg}")
        return msg


class TemperatureControl(SmartDevice):
    EMULATE_INTERVAL_SEC = 5.0
    TEMP_STEP = 1.2
    def __init__(self, device_id: str, name: str):
        super().__init__(device_id, name)
        self.temperature: float = 22.0
        self.targetTemperature: float = 24.0
        self._last_emulate_at: float = time.monotonic()

    def connect(self) -> dict:
        self.emulate()
        self.status = "online"
        payload = {"id": self.id, "temperature": self.temperature, "targetTemperature": self.targetTemperature}
        _safe_print(f"[TemperatureControl.connect] {payload}")
        return payload

    def emulate(self) -> None:
        now = time.monotonic()
        elapsed = now - self._last_emulate_at
        if elapsed < self.EMULATE_INTERVAL_SEC:
            return
        steps = int(elapsed // self.EMULATE_INTERVAL_SEC)
        self._last_emulate_at += steps * self.EMULATE_INTERVAL_SEC
        for _ in range(steps):
            if self.temperature < self.targetTemperature:
                self.temperature = round(min(self.targetTemperature, self.temperature + self.TEMP_STEP), 1)
            elif self.temperature > self.targetTemperature:
                self.temperature = round(max(self.targetTemperature, self.temperature - self.TEMP_STEP), 1)

    def control(self, request: Request) -> dict:
        target, err = _parse_float(request.args.get("target_temperature", str(self.targetTemperature)), "target_temperature")
        if err:
            return {"ok": False, "message": err, "targetTemperature": self.targetTemperature}
        msg = self.setTargetTemperature(target)
        _safe_print(f"[TemperatureControl.control] {msg}")
        return {
            "ok": True,
            "message": msg,
            "temperature": self.temperature,
            "targetTemperature": self.targetTemperature,
        }

    def setTargetTemperature(self, temp: float) -> str:
        self.targetTemperature = round(max(16.0, min(30.0, float(temp))), 1)
        msg = f"{self.name}: target temperature set to {self.targetTemperature} C"
        _safe_print(f"[TemperatureControl.setTargetTemperature] {msg}")
        return msg


class HumidityControl(SmartDevice):
    EMULATE_INTERVAL_SEC = 5.0
    HUMIDITY_STEP = 2.5
    def __init__(self, device_id: str, name: str):
        super().__init__(device_id, name)
        self.humidity: float = 45.0
        self.targetHumidity: float = 50.0
        self._last_emulate_at: float = time.monotonic()

    def connect(self) -> dict:
        self.emulate()
        self.status = "online"
        payload = {"id": self.id, "humidity": self.humidity, "targetHumidity": self.targetHumidity}
        _safe_print(f"[HumidityControl.connect] {payload}")
        return payload

    def emulate(self) -> None:
        now = time.monotonic()
        elapsed = now - self._last_emulate_at
        if elapsed < self.EMULATE_INTERVAL_SEC:
            return
        steps = int(elapsed // self.EMULATE_INTERVAL_SEC)
        self._last_emulate_at += steps * self.EMULATE_INTERVAL_SEC
        for _ in range(steps):
            if self.humidity < self.targetHumidity:
                self.humidity = round(min(self.targetHumidity, self.humidity + self.HUMIDITY_STEP), 1)
            elif self.humidity > self.targetHumidity:
                self.humidity = round(max(self.targetHumidity, self.humidity - self.HUMIDITY_STEP), 1)

    def control(self, request: Request) -> dict:
        target, err = _parse_float(request.args.get("target_humidity", str(self.targetHumidity)), "target_humidity")
        if err:
            return {"ok": False, "message": err, "targetHumidity": self.targetHumidity}
        if target < 25 or target > 70:
            msg = f"Влажность должна быть 25..70 %, получено {target}"
            return {"ok": False, "message": msg, "targetHumidity": self.targetHumidity}
        msg = self.setTargetHumidity(target)
        _safe_print(f"[HumidityControl.control] {msg}")
        return {
            "ok": True,
            "message": msg,
            "humidity": self.humidity,
            "targetHumidity": self.targetHumidity,
        }

    def setTargetHumidity(self, humidity: float) -> str:
        self.targetHumidity = round(max(25.0, min(70.0, float(humidity))), 1)
        msg = f"{self.name}: target humidity set to {self.targetHumidity} %"
        _safe_print(f"[HumidityControl.setTargetHumidity] {msg}")
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
        _safe_print(f"[SmartLighting.connect] {payload}")
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
            brightness, err_b = _parse_int(request.args.get("brightness", str(self.brightness)), "brightness", 0, 100)
            r, err_r = _parse_int(request.args.get("r", str(self.rgb_r)), "r", 0, 255)
            g, err_g = _parse_int(request.args.get("g", str(self.rgb_g)), "g", 0, 255)
            b, err_b2 = _parse_int(request.args.get("b", str(self.rgb_b)), "b", 0, 255)
            if err_b:
                return {"ok": False, "message": err_b, "brightness": self.brightness}
            if err_r:
                return {"ok": False, "message": err_r, "brightness": self.brightness}
            if err_g:
                return {"ok": False, "message": err_g, "brightness": self.brightness}
            if err_b2:
                return {"ok": False, "message": err_b2, "brightness": self.brightness}
            self.rgb_r, self.rgb_g, self.rgb_b = r, g, b
            self.setBrightness(brightness)
            avg = int((self.rgb_r + self.rgb_g + self.rgb_b) / 3)
            self.colorTemperature = max(2000, min(6500, 2000 + int((avg / 255) * 4500)))
            self.isOn = self.brightness > 0
            msg = f"{self.name}: settings applied"
        _safe_print(f"[SmartLighting.control] {msg}")
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
        _safe_print(f"[SmartLighting.setBrightness] {msg}")
        return msg

    def setColorTemperature(self, value: int) -> str:
        self.colorTemperature = max(2000, min(6500, value))
        msg = f"{self.name}: color temperature set to {self.colorTemperature}K"
        _safe_print(f"[SmartLighting.setColorTemperature] {msg}")
        return msg


class HomeAutomation:
    """Автоматическое управление по данным датчиков (связь из ЛР1: климат -> шторы и освещение)."""

    def __init__(
        self,
        temperature: "TemperatureControl",
        humidity: "HumidityControl",
        lighting: "SmartLighting",
        curtains: "SmartCurtains",
    ):
        self._temperature = temperature
        self._humidity = humidity
        self._lighting = lighting
        self._curtains = curtains
        self.last_actions: list[str] = []
        _safe_print("[HomeAutomation.__init__] automation module ready")

    def run_after_sensor_update(self) -> list[str]:
        actions: list[str] = []
        t = self._temperature.temperature
        t_target = self._temperature.targetTemperature
        h = self._humidity.humidity
        h_target = self._humidity.targetHumidity

        if t < t_target - 0.5:
            if self._lighting.brightness < 85:
                self._lighting.setBrightness(min(100, self._lighting.brightness + 15))
                self._lighting.isOn = True
                actions.append(f"Авто: яркость ламп повышена до {self._lighting.brightness}% (холодно)")
            if self._curtains._target_position > 15:
                new_pos = max(0, self._curtains._target_position - 25)
                self._curtains.open(new_pos)
                actions.append(f"Авто: шторы движутся к {new_pos}% (сохранение тепла)")
        self.last_actions = actions
        for action in actions:
            _safe_print(f"[HomeAutomation.run_after_sensor_update] {action}")
        return actions


class Logger:
    """Долгосрочное хранение данных (MongoDB или JSON-файл при недоступности сервера)."""

    LOG_INTERVAL_SEC = 5.0

    def __init__(self, db_name: str, fallback_dir: str = "data"):
        self.db_name = db_name
        self._last_temperature: float | None = None
        self._last_humidity: float | None = None
        self._last_temp_log_at: float = 0.0
        self._last_hum_log_at: float = 0.0
        self._mongo_ok = False
        self._client = None
        self._db = None
        base = Path(__file__).resolve().parent
        self._fallback_path = base / fallback_dir / f"{db_name}.json"
        self._fallback_path.parent.mkdir(parents=True, exist_ok=True)
        if not self._fallback_path.exists():
            self._fallback_path.write_text("{}", encoding="utf-8")

        if PYMONGO_AVAILABLE:
            try:
                self._client = pymongo.MongoClient("mongodb://localhost:27017/", serverSelectionTimeoutMS=800)
                self._client.admin.command("ping")
                self._db = self._client[db_name]
                self._mongo_ok = True
                _safe_print(f"[Logger] MongoDB connected: {db_name}")
            except Exception as exc:
                _safe_print(f"[Logger] MongoDB unavailable ({exc}), using JSON fallback")

    def _load_fallback(self) -> dict:
        try:
            return json.loads(self._fallback_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            return {}

    def _save_fallback(self, data: dict) -> None:
        self._fallback_path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")

    def _insert(self, collection: str, document: dict) -> None:
        if self._mongo_ok and self._db is not None:
            self._db[collection].insert_one(document)
            return
        store = self._load_fallback()
        store.setdefault(collection, []).append(document)
        self._save_fallback(store)

    def _should_log(self, value: float, last_value: float | None, last_log_at: float) -> bool:
        now = time.monotonic()
        if last_value is None:
            return True
        if abs(value - last_value) >= 0.05:
            return True
        return (now - last_log_at) >= self.LOG_INTERVAL_SEC

    def insert_temperature(self, value: float) -> str:
        value = round(float(value), 1)
        if not self._should_log(value, self._last_temperature, self._last_temp_log_at):
            return "temperature unchanged"
        self._last_temperature = value
        self._last_temp_log_at = time.monotonic()
        doc = {"timeStamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"), "temperature": value}
        self._insert("Temperature", doc)
        _safe_print(f"[Logger.insert_temperature] {doc}")
        return "temperature saved"

    def insert_humidity(self, value: float) -> str:
        value = round(float(value), 1)
        if not self._should_log(value, self._last_humidity, self._last_hum_log_at):
            return "humidity unchanged"
        self._last_humidity = value
        self._last_hum_log_at = time.monotonic()
        doc = {"timeStamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"), "humidity": value}
        self._insert("Humidity", doc)
        _safe_print(f"[Logger.insert_humidity] {doc}")
        return "humidity saved"

    def _read_collection(self, collection: str, field: str) -> list[float]:
        values: list[float] = []
        if self._mongo_ok and self._db is not None:
            for row in self._db[collection].find({}, {field: 1, "_id": 0}):
                if field in row:
                    values.append(float(row[field]))
            return values
        store = self._load_fallback()
        for row in store.get(collection, []):
            if field in row:
                values.append(float(row[field]))
        return values

    def get_average_temperature(self) -> float | None:
        values = self._read_collection("Temperature", "temperature")
        if not values:
            return None
        return round(sum(values) / len(values), 2)

    def get_max_temperature(self) -> float | None:
        values = self._read_collection("Temperature", "temperature")
        return round(max(values), 2) if values else None

    def get_average_humidity(self) -> float | None:
        values = self._read_collection("Humidity", "humidity")
        if not values:
            return None
        return round(sum(values) / len(values), 2)

    def get_max_humidity(self) -> float | None:
        values = self._read_collection("Humidity", "humidity")
        return round(max(values), 2) if values else None

    def get_temperature_chart_data(self, limit: int = 30) -> dict:
        labels: list[str] = []
        data: list[float] = []
        rows: list[dict] = []
        if self._mongo_ok and self._db is not None:
            rows = list(self._db["Temperature"].find({}, {"timeStamp": 1, "temperature": 1, "_id": 0}).sort("_id", -1).limit(limit))
            rows.reverse()
        else:
            store = self._load_fallback()
            rows = store.get("Temperature", [])[-limit:]
        for row in rows:
            labels.append(str(row.get("timeStamp", "")))
            data.append(float(row.get("temperature", 0)))
        return {"labels": labels, "values": data}


class SceneManager:
    """Хранение и применение сценариев умного дома."""

    DEFAULT_SCENES: list[dict[str, Any]] = [
        {
            "id": "warm-evening",
            "name": "Теплый вечер",
            "date": "",
            "time": "20:00",
            "builtin": True,
            "actions": {
                "lighting": {"on": True, "brightness": 45, "r": 255, "g": 160, "b": 80},
                "curtains": {"percent": 25},
                "kettle": {"action": "target", "target_temp": 75},
                "temperature": {"target": 23.0},
                "humidity": {"target": 48.0},
            },
        },
        {
            "id": "morning",
            "name": "Утро",
            "date": "",
            "time": "07:30",
            "builtin": True,
            "actions": {
                "lighting": {"on": True, "brightness": 90, "r": 255, "g": 220, "b": 180},
                "curtains": {"percent": 100},
                "temperature": {"target": 22.0},
                "humidity": {"target": 50.0},
            },
        },
        {
            "id": "away",
            "name": "Экономия",
            "date": "",
            "time": "",
            "builtin": True,
            "actions": {
                "lighting": {"on": False, "brightness": 0, "r": 200, "g": 200, "b": 200},
                "curtains": {"percent": 0},
                "temperature": {"target": 20.0},
                "humidity": {"target": 45.0},
                "kettle": {"action": "off"},
            },
        },
        {
            "id": "cleaning",
            "name": "Уборка",
            "date": "",
            "time": "10:00",
            "builtin": True,
            "actions": {
                "vacuum": {"action": "start", "mode": "auto"},
                "curtains": {"percent": 80},
                "lighting": {"on": True, "brightness": 60, "r": 255, "g": 255, "b": 255},
            },
        },
    ]

    def __init__(self, data_dir: str = "data"):
        base = Path(__file__).resolve().parent
        self._path = base / data_dir / "scenes.json"
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._scenes: dict[str, dict[str, Any]] = {}
        self._load()
        _safe_print(f"[SceneManager] loaded {len(self._scenes)} scenes")

    def _load(self) -> None:
        if self._path.exists():
            try:
                raw = json.loads(self._path.read_text(encoding="utf-8"))
                for scene in raw.get("scenes", []):
                    if scene.get("id"):
                        self._scenes[scene["id"]] = scene
            except (json.JSONDecodeError, OSError):
                self._scenes = {}
        if not self._scenes:
            for scene in self.DEFAULT_SCENES:
                self._scenes[scene["id"]] = dict(scene)
            self._save()

    def _save(self) -> None:
        payload = {"scenes": list(self._scenes.values())}
        self._path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    def list_scenes(self) -> list[dict[str, Any]]:
        return sorted(self._scenes.values(), key=lambda s: (not s.get("builtin"), s.get("name", "")))

    def get_scene(self, scene_id: str) -> dict[str, Any] | None:
        return self._scenes.get(scene_id)

    def save_scene(self, payload: dict[str, Any]) -> dict[str, Any]:
        scene_id = str(payload.get("id") or "").strip() or str(uuid.uuid4())[:8]
        actions = payload.get("actions") or {}
        scene = {
            "id": scene_id,
            "name": str(payload.get("name", "Без названия")).strip() or "Без названия",
            "date": str(payload.get("date", "")),
            "time": str(payload.get("time", "")),
            "builtin": bool(self._scenes.get(scene_id, {}).get("builtin", False)),
            "actions": actions,
        }
        if not scene["builtin"]:
            scene["builtin"] = False
        self._scenes[scene_id] = scene
        self._save()
        _safe_print(f"[SceneManager.save_scene] {scene['name']} ({scene_id})")
        return scene

    def delete_scene(self, scene_id: str) -> bool:
        scene = self._scenes.get(scene_id)
        if not scene:
            return False
        if scene.get("builtin"):
            return False
        del self._scenes[scene_id]
        self._save()
        _safe_print(f"[SceneManager.delete_scene] {scene_id}")
        return True

    def apply_scene(
        self,
        scene_id: str,
        robot: RobotVacuum,
        curtains: SmartCurtains,
        kettle: SmartKettle,
        temperature: TemperatureControl,
        humidity: HumidityControl,
        lighting: SmartLighting,
    ) -> list[str]:
        scene = self._scenes.get(scene_id)
        if not scene:
            return [f"Сценарий '{scene_id}' не найден"]
        actions = scene.get("actions", {})
        messages: list[str] = []

        if "lighting" in actions:
            cfg = actions["lighting"]
            if cfg.get("on") is False:
                lighting.isOn = False
                lighting.brightness = 0
                messages.append("Лампы выключены")
            else:
                lighting.isOn = True
                lighting.setBrightness(int(cfg.get("brightness", lighting.brightness)))
                lighting.rgb_r = int(cfg.get("r", lighting.rgb_r))
                lighting.rgb_g = int(cfg.get("g", lighting.rgb_g))
                lighting.rgb_b = int(cfg.get("b", lighting.rgb_b))
                messages.append(f"Лампы: {lighting.brightness}%, RGB({lighting.rgb_r},{lighting.rgb_g},{lighting.rgb_b})")

        if "curtains" in actions:
            percent = int(actions["curtains"].get("percent", curtains.positionPercent))
            curtains.open(percent)
            messages.append(f"Шторы: цель {percent}%")

        if "kettle" in actions:
            cfg = actions["kettle"]
            if cfg.get("action") == "off":
                kettle.isBoiling = False
                messages.append("Чайник выключен")
            elif cfg.get("action") == "on":
                kettle.boil(int(cfg.get("target_temp", kettle.targetTemperature)))
                messages.append(f"Чайник: нагрев до {kettle.targetTemperature} C")
            else:
                kettle.targetTemperature = int(cfg.get("target_temp", kettle.targetTemperature))
                messages.append(f"Чайник: цель {kettle.targetTemperature} C")

        if "temperature" in actions:
            target = float(actions["temperature"].get("target", temperature.targetTemperature))
            temperature.setTargetTemperature(target)
            messages.append(f"Климат: цель T {temperature.targetTemperature} C")

        if "humidity" in actions:
            target = float(actions["humidity"].get("target", humidity.targetHumidity))
            humidity.setTargetHumidity(target)
            messages.append(f"Климат: цель влажности {humidity.targetHumidity} %")

        if "vacuum" in actions:
            cfg = actions["vacuum"]
            action = cfg.get("action", "start")
            mode = cfg.get("mode", "auto")
            if action == "start" and VACUUM_MODE_PATTERN.match(str(mode)):
                robot.cleaningState = "running"
                robot.startCleaning(str(mode), robot.roomMap)
                messages.append(f"Пылесос: уборка ({mode})")
            elif action == "dock":
                robot.cleaningState = "docked"
                robot.goToDock()
                messages.append("Пылесос: на базе")
            elif action == "pause":
                robot.cleaningState = "paused"
                messages.append("Пылесос: пауза")

        summary = f"Сценарий «{scene['name']}»: " + "; ".join(messages)
        _safe_print(f"[SceneManager.apply_scene] {summary}")
        return messages


class Database:
    def __init__(self, name: str):
        self.name: str = name
        self.deviceScheduleList: dict[str, list] = {}
        self._deviceData: dict[str, list] = {}
        self._commandLog: list[dict[str, str]] = []
        _safe_print(f"[Database.__init__] db '{self.name}' initialized")

    def saveCommandLog(self, deviceId: str, command: str, result: str) -> None:
        entry = {"deviceId": deviceId, "command": command, "result": result}
        self._commandLog.append(entry)
        _safe_print(f"[Database.saveCommandLog] {entry}")


class MainControlUnit:
    def __init__(self, database: Database):
        self.deviceList: list[SmartDevice] = []
        self.command_queue: list[dict] = []
        self._database = database
        _safe_print("[MainControlUnit.__init__] main control unit created")

    def addDevice(self, device: SmartDevice) -> str:
        self.deviceList.append(device)
        msg = f"Device '{device.name}' added"
        _safe_print(f"[MainControlUnit.addDevice] {msg}")
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
    scene_manager = SceneManager("data")
    return {
        "db": db,
        "mcu": mcu,
        "devices": devices,
        "child_ui": ChildUI(mcu),
        "parent_ui": ParentUI(mcu),
        "scene_manager": scene_manager,
    }
