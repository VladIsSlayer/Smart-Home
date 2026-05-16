#!/usr/bin/env python3
"""Синхронизация исправлений устройств и UI из LR4 в LR3 и LR5-LR9."""

from pathlib import Path
import shutil

ROOT = Path(__file__).resolve().parents[1]
LR4 = ROOT / "LR4"
TARGETS = [ROOT / "LR3"] + [ROOT / f"LR{n}" for n in range(5, 10)]


def patch_things(path: Path) -> None:
    text = path.read_text(encoding="utf-8")
    original = text

    # SmartCurtains: медленный дрейф
    old_curtains_block = """class SmartCurtains(SmartDevice):
    def __init__(self, device_id: str, name: str):
        super().__init__(device_id, name)
        self.positionPercent: int = 60
        self.mode: str = "manual"

    def connect(self) -> dict:
        self.emulate()
        self.status = "online"
"""
    new_curtains_block = """class SmartCurtains(SmartDevice):
    DRIFT_INTERVAL_SEC = 120.0

    def __init__(self, device_id: str, name: str):
        super().__init__(device_id, name)
        self.positionPercent: int = 60
        self.mode: str = "manual"
        self._last_drift_at: float = time.monotonic()

    def connect(self) -> dict:
        self._maybe_drift()
        self.status = "online"
"""
    if old_curtains_block in text and "DRIFT_INTERVAL_SEC" not in text:
        text = text.replace(old_curtains_block, new_curtains_block)

    if "def _maybe_drift(self)" not in text and "class SmartCurtains" in text:
        text = text.replace(
            '        print(f"[SmartCurtains.connect] {payload}")\n        return payload\n\n    def emulate(self)',
            '        print(f"[SmartCurtains.connect] {payload}")\n        return payload\n\n    def _maybe_drift(self) -> None:\n        now = time.monotonic()\n        if now - self._last_drift_at < self.DRIFT_INTERVAL_SEC:\n            return\n        self._last_drift_at = now\n        shift = random.choice([-1, 0, 1])\n        if shift == 0:\n            return\n        self.positionPercent = max(0, min(100, self.positionPercent + shift))\n\n    def emulate(self)',
        )

    # Удалить агрессивный emulate штор
    text = text.replace(
        "    def emulate(self) -> None:\n        shift = random.randint(-3, 3)\n        self.positionPercent = max(0, min(100, self.positionPercent + shift))\n",
        "",
    )
    text = text.replace(
        "    def emulate(self) -> None:\n        shift = random.randint(-5, 5)\n        self.positionPercent = max(0, min(100, self.positionPercent + shift))\n",
        "",
    )

    if "self._last_drift_at = time.monotonic()" not in text.split("def open(self")[0]:
        text = text.replace(
            "    def open(self, percent: int) -> str:\n        self.positionPercent = max(0, min(100, percent))\n",
            "    def open(self, percent: int) -> str:\n        self.positionPercent = max(0, min(100, percent))\n        self._last_drift_at = time.monotonic()\n",
            1,
        )
        text = text.replace(
            "    def close(self) -> str:\n        self.positionPercent = 0\n",
            "    def close(self) -> str:\n        self.positionPercent = 0\n        self._last_drift_at = time.monotonic()\n",
            1,
        )

    # Temperature emulate -> к цели
    text = text.replace(
        """    def emulate(self) -> None:
        now = time.monotonic()
        if now - self._last_emulate_at >= 15.0:
            self.temperature = round(max(16.0, min(30.0, self.temperature + random.choice([-0.1, 0.1]))), 1)
            self._last_emulate_at = now
""",
        """    def emulate(self) -> None:
        now = time.monotonic()
        if now - self._last_emulate_at < 20.0:
            return
        self._last_emulate_at = now
        if self.temperature < self.targetTemperature:
            self.temperature = round(min(self.targetTemperature, self.temperature + 0.2), 1)
        elif self.temperature > self.targetTemperature:
            self.temperature = round(max(self.targetTemperature, self.temperature - 0.2), 1)
""",
    )

    text = text.replace(
        """    def emulate(self) -> None:
        now = time.monotonic()
        if now - self._last_emulate_at >= 15.0:
            self.humidity = round(max(25.0, min(70.0, self.humidity + random.choice([-0.3, 0.3]))), 1)
            self._last_emulate_at = now
""",
        """    def emulate(self) -> None:
        now = time.monotonic()
        if now - self._last_emulate_at < 20.0:
            return
        self._last_emulate_at = now
        if self.humidity < self.targetHumidity:
            self.humidity = round(min(self.targetHumidity, self.humidity + 0.5), 1)
        elif self.humidity > self.targetHumidity:
            self.humidity = round(max(self.targetHumidity, self.humidity - 0.5), 1)
""",
    )

    # SmartLighting rgb + без дрейфа
    if "self.rgb_r" not in text:
        text = text.replace(
            "        self.colorTemperature: int = 3500\n        self.isOn: bool = True",
            "        self.colorTemperature: int = 3500\n        self.rgb_r: int = 255\n        self.rgb_g: int = 180\n        self.rgb_b: int = 90\n        self.isOn: bool = True",
            1,
        )

    text = text.replace(
        """    def connect(self) -> dict:
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
""",
        """    def connect(self) -> dict:
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
""",
    )

    # LR3 lighting connect without emulate call
    text = text.replace(
        """    def connect(self) -> dict:
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
""",
        """    def connect(self) -> dict:
        self.status = "online"
        payload = {
            "id": self.id,
            "brightness": self.brightness,
            "colorTemperature": self.colorTemperature,
            "rgb_r": self.rgb_r,
            "rgb_g": self.rgb_g,
            "rgb_b": self.rgb_b,
            "isOn": True,
        }
        print(f"[SmartLighting.connect] {payload}")
        return payload
""",
    )

    if text != original:
        path.write_text(text, encoding="utf-8")
        print(f"Patched things: {path.name}")


def copy_server_files(target: Path, version: str) -> None:
    for name in ("script.js", "admin.html"):
        src = LR4 / "server" / name
        dst = target / "server" / name
        if not dst.parent.exists():
            continue
        if target.name in ("LR8", "LR9") and name == "admin.html":
            # только климат-секция в admin — копируем script полностью
            if name == "admin.html":
                patch_admin_climate(dst)
                continue
        shutil.copy2(src, dst)
        print(f"Copied {name} -> {target.name}")

    script = target / "server" / "script.js"
    if script.exists() and target.name in ("LR8", "LR9"):
        merge_lr89_script(script)

    html = target / "server" / "admin.html"
    if html.exists():
        text = html.read_text(encoding="utf-8")
        if "script.js?v=" in text:
            text = text.replace('script.js?v=2', f'script.js?v={version}')
            text = text.replace('script.js?v=4', f'script.js?v={version}')
            text = text.replace('script.js?v=9', f'script.js?v={version}')
            html.write_text(text, encoding="utf-8")


def patch_admin_climate(admin_path: Path) -> None:
    text = admin_path.read_text(encoding="utf-8")
    if "homeTargetTemp" in text:
        return
    text = text.replace(
        '<label for="homeTemp">Температура в доме (C):</label>\n                        <input id="homeTemp"',
        '<p class="device-meta">\n                            Текущая температура: <strong id="adminClimateCurrentTemp">22.0</strong> C\n                            &nbsp;|&nbsp; цель: <strong id="adminClimateTargetTempDisplay">24.0</strong> C\n                        </p>\n                        <label for="homeTargetTemp">Задать целевую температуру (C):</label>\n                        <input id="homeTargetTemp"',
    )
    text = text.replace(
        '<label for="homeHumidity">Влажность в доме (%):</label>\n                        <input id="homeHumidity"',
        '<p class="device-meta">\n                            Текущая влажность: <strong id="adminClimateCurrentHumidity">45.0</strong> %\n                            &nbsp;|&nbsp; цель: <strong id="adminClimateTargetHumidityDisplay">50.0</strong> %\n                        </p>\n                        <label for="homeTargetHumidity">Задать целевую влажность (%):</label>\n                        <input id="homeTargetHumidity"',
    )
    text = text.replace("Сохранить температуру и влажность", "Применить цели климата")
    admin_path.write_text(text, encoding="utf-8")
    print(f"Patched admin climate: {admin_path.parent.parent.name}")


def merge_lr89_script(script_path: Path) -> None:
    """Добавить в LR8/LR9 функции анализа/графика из существующего script если есть."""
    lr4 = (LR4 / "server" / "script.js").read_text(encoding="utf-8")
    current = script_path.read_text(encoding="utf-8")
    for block in ("function renderAnalysis", "function loadTemperatureChart", "let temperatureChartInstance"):
        if block in lr4 and block not in current:
            # append missing blocks from backup - skip, LR9 should already have them
            pass
    # LR9: ensure loadTemperatureChart exists - copy from LR4 base was overwritten; re-read LR9 if needed
    if script_path.parent.parent.name == "LR9" and "loadTemperatureChart" not in current:
        extra = """

let temperatureChartInstance = null;

function renderAnalysis(analysis) {
    if (!analysis) return;
    const list = document.getElementById("analysisStats");
    if (!list) return;
    const fmt = (v) => (v === null || v === undefined ? "—" : String(v));
    list.innerHTML = `
        <li>Средняя температура: ${fmt(analysis.avg_temperature)} C</li>
        <li>Максимальная температура: ${fmt(analysis.max_temperature)} C</li>
        <li>Средняя влажность: ${fmt(analysis.avg_humidity)} %</li>
        <li>Максимальная влажность: ${fmt(analysis.max_humidity)} %</li>
    `;
}

function loadTemperatureChart() {
    const canvas = document.getElementById("temperatureChart");
    if (!canvas || typeof Chart === "undefined") return;
    ajaxGet("/api/chart/temperature", (payload) => {
        const chart = payload.chart || { labels: [], values: [] };
        if (temperatureChartInstance) {
            temperatureChartInstance.data.labels = chart.labels;
            temperatureChartInstance.data.datasets[0].data = chart.values;
            temperatureChartInstance.update();
            return;
        }
        temperatureChartInstance = new Chart(canvas, {
            type: "line",
            data: {
                labels: chart.labels,
                datasets: [{
                    label: "Температура, C",
                    data: chart.values,
                    borderColor: "#2f6fed",
                    backgroundColor: "rgba(47, 111, 237, 0.15)",
                    fill: true,
                    tension: 0.35,
                }],
            },
            options: { responsive: true },
        });
    });
}
"""
        if "DOMContentLoaded" in current:
            current = current.replace(
                "    connectAllThings();\n    setInterval(connectAllThings, 10000);",
                "    connectAllThings();\n    loadTemperatureChart();\n    setInterval(connectAllThings, 10000);\n    setInterval(loadTemperatureChart, 15000);",
            )
            current = current.replace(
                "function connectTemperatureControl()",
                extra + "\nfunction showAutomation(actions) {\n    if (!actions || !actions.length) return;\n    showMessage(`Автоматика: ${actions.join('; ')}`);\n}\n\nfunction connectTemperatureControl()",
            )
            current = current.replace(
                "        if (data.automation) showAutomation(data.automation);\n        const homeTemp",
                "        if (data.automation) showAutomation(data.automation);\n        if (data.analysis) renderAnalysis(data.analysis);\n        const homeTemp",
            )
        script_path.write_text(current, encoding="utf-8")


def main() -> None:
    for target in TARGETS:
        things = target / "things.py"
        if things.exists():
            patch_things(things)
        ver = target.name.replace("LR", "")
        copy_server_files(target, ver)


if __name__ == "__main__":
    main()
