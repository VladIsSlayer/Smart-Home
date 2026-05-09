import abc
import random
import time
from typing import Any


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

    def executeCommand(self, command: str) -> str:
        self.status = f"executed: {command}"
        msg = f"{self.name}: command '{command}' executed"
        print(f"[SmartDevice.executeCommand] {msg}")
        return msg

    def saveSchedule(self, scheduleData: list) -> str:
        self.schedule = list(scheduleData)
        msg = f"{self.name}: schedule saved ({len(self.schedule)} items)"
        print(f"[SmartDevice.saveSchedule] {msg}")
        return msg

    def updateSchedule(self, scheduleData: list) -> str:
        self.schedule = list(scheduleData)
        msg = f"{self.name}: schedule updated ({len(self.schedule)} items)"
        print(f"[SmartDevice.updateSchedule] {msg}")
        return msg


class RobotVacuum(SmartDevice):
    def __init__(self, device_id: str, name: str):
        super().__init__(device_id, name)
        self.batteryLevel: int = 85
        self.dustContainerLevel: int = 20
        self.roomMapVersion: int = 1
        self.roomMap: list = ["hall", "kitchen", "bedroom"]

    def connect(self) -> dict:
        self.emulate()
        self.status = "online"
        payload = {"id": self.id, "status": self.status, "batteryLevel": self.batteryLevel}
        print(f"[RobotVacuum.connect] {payload}")
        return payload

    def emulate(self) -> None:
        self.batteryLevel = max(10, min(100, self.batteryLevel + random.randint(-2, 1)))
        self.dustContainerLevel = max(0, min(100, self.dustContainerLevel + random.randint(-1, 3)))

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
        self.positionPercent: int = 0
        self.mode: str = "manual"

    def connect(self) -> dict:
        self.status = "online"
        payload = {"id": self.id, "positionPercent": self.positionPercent, "mode": self.mode}
        print(f"[SmartCurtains.connect] {payload}")
        return payload

    def emulate(self) -> None:
        shift = random.randint(-5, 5)
        self.positionPercent = max(0, min(100, self.positionPercent + shift))

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
        # Медленное остывание: минус 1C каждые 10 секунд
        if elapsed >= 10.0:
            steps = int(elapsed // 10.0)
            self.currentWaterTemperature = max(24.0, self.currentWaterTemperature - float(steps))
            self._last_cool_down_at += steps * 10.0
        self.isBoiling = False

    def boil(self, targetTemp: int) -> str:
        self.targetTemperature = targetTemp
        self.currentWaterTemperature = float(targetTemp)
        self.isBoiling = True
        msg = f"{self.name}: boiled to {self.targetTemperature} C"
        print(f"[SmartKettle.boil] {msg}")
        self.isBoiling = False
        return msg

    def keepWarm(self, minutes: int) -> str:
        msg = f"{self.name}: keep warm for {minutes} minutes"
        print(f"[SmartKettle.keepWarm] {msg}")
        return msg

    def getCurrentWaterTemperature(self) -> float:
        print(f"[SmartKettle.getCurrentWaterTemperature] {self.currentWaterTemperature}")
        return self.currentWaterTemperature


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

    def setTargetTemperature(self, temp: float) -> str:
        self.targetTemperature = float(temp)
        msg = f"{self.name}: target temperature set to {self.targetTemperature} C"
        print(f"[TemperatureControl.setTargetTemperature] {msg}")
        return msg

    def getCurrentTemperature(self) -> float:
        print(f"[TemperatureControl.getCurrentTemperature] {self.temperature}")
        return self.temperature


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

    def setTargetHumidity(self, humidity: float) -> str:
        self.targetHumidity = float(humidity)
        msg = f"{self.name}: target humidity set to {self.targetHumidity} %"
        print(f"[HumidityControl.setTargetHumidity] {msg}")
        return msg

    def getCurrentHumidity(self) -> float:
        print(f"[HumidityControl.getCurrentHumidity] {self.humidity}")
        return self.humidity


class SmartLighting(SmartDevice):
    def __init__(self, device_id: str, name: str):
        super().__init__(device_id, name)
        self.brightness: int = 70
        self.colorTemperature: int = 3500

    def connect(self) -> dict:
        self.status = "online"
        payload = {
            "id": self.id,
            "brightness": self.brightness,
            "colorTemperature": self.colorTemperature,
        }
        print(f"[SmartLighting.connect] {payload}")
        return payload

    def emulate(self) -> None:
        self.brightness = max(10, min(100, self.brightness + random.randint(-4, 4)))
        self.colorTemperature = max(2400, min(5000, self.colorTemperature + random.randint(-120, 120)))

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

    def saveData(self, deviceId: str, payload: dict) -> None:
        self._deviceData.setdefault(deviceId, []).append(payload)
        print(f"[Database.saveData] {deviceId}: {payload}")

    def saveCommandLog(self, deviceId: str, command: str, result: str) -> None:
        entry = {"deviceId": deviceId, "command": command, "result": result}
        self._commandLog.append(entry)
        print(f"[Database.saveCommandLog] {entry}")

    def saveDeviceSchedule(self, deviceId: str, scheduleData: list) -> None:
        self.deviceScheduleList[deviceId] = list(scheduleData)
        print(f"[Database.saveDeviceSchedule] {deviceId}: {scheduleData}")

    def getDeviceHistory(self, deviceId: str) -> list:
        history = self._deviceData.get(deviceId, [])
        print(f"[Database.getDeviceHistory] {deviceId}: {len(history)} records")
        return history


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

    def dltDevice(self, deviceId: str) -> str:
        before = len(self.deviceList)
        self.deviceList = [d for d in self.deviceList if d.id != deviceId]
        after = len(self.deviceList)
        msg = "Device deleted" if after < before else "Device not found"
        print(f"[MainControlUnit.dltDevice] {deviceId}: {msg}")
        return msg

    def createCommand(self, deviceId: str, command: str) -> dict:
        payload = {"deviceId": deviceId, "command": command}
        self.command_queue.append(payload)
        print(f"[MainControlUnit.createCommand] {payload}")
        return payload

    def getData(self, deviceId: str) -> dict:
        device = next((d for d in self.deviceList if d.id == deviceId), None)
        if device is None:
            print(f"[MainControlUnit.getData] {deviceId}: not found")
            return {"error": "device not found"}
        data = device.connect()
        print(f"[MainControlUnit.getData] {deviceId}: {data}")
        return data

    def sentToDataBase(self, payload: dict) -> None:
        deviceId = str(payload.get("deviceId", "unknown"))
        self._database.saveData(deviceId, payload)
        print(f"[MainControlUnit.sentToDataBase] payload sent for {deviceId}")

    def dispatchCommand(self, deviceId: str, command: str) -> str:
        device = next((d for d in self.deviceList if d.id == deviceId), None)
        if device is None:
            result = "device not found"
            self._database.saveCommandLog(deviceId, command, result)
            print(f"[MainControlUnit.dispatchCommand] {deviceId}: {result}")
            return result
        result = device.executeCommand(command)
        self._database.saveCommandLog(deviceId, command, result)
        return result


class ChildUI:
    def __init__(self, mcu: MainControlUnit):
        self._mcu = mcu

    def showBasicStatus(self, data: dict) -> None:
        print(f"[ChildUI.showBasicStatus] {data}")

    def controlAllowedDevices(self) -> str:
        msg = "ChildUI: control of allowed devices enabled"
        print(f"[ChildUI.controlAllowedDevices] {msg}")
        return msg

    def sendCommand(self, deviceId: str, command: str) -> bool:
        result = self._mcu.dispatchCommand(deviceId, command)
        ok = "not found" not in result
        print(f"[ChildUI.sendCommand] device={deviceId}, ok={ok}")
        return ok


class ParentUI:
    def __init__(self, mcu: MainControlUnit):
        self._mcu = mcu

    def showFullStatus(self, data: dict) -> None:
        print(f"[ParentUI.showFullStatus] {data}")

    def configureAutomationRules(self) -> str:
        msg = "ParentUI: automation rules configured"
        print(f"[ParentUI.configureAutomationRules] {msg}")
        return msg

    def sendCommand(self, deviceId: str, command: str) -> bool:
        result = self._mcu.dispatchCommand(deviceId, command)
        ok = "not found" not in result
        print(f"[ParentUI.sendCommand] device={deviceId}, ok={ok}")
        return ok


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

    child_ui = ChildUI(mcu)
    parent_ui = ParentUI(mcu)

    return {
        "db": db,
        "mcu": mcu,
        "devices": devices,
        "child_ui": child_ui,
        "parent_ui": parent_ui,
    }
