function clamp(value, min, max) {
    const number = Number(value);
    if (Number.isNaN(number)) {
        return min;
    }
    return Math.max(min, Math.min(max, number));
}

function setupSummaryToggles() {
    const buttons = document.querySelectorAll("[data-toggle-target]");
    buttons.forEach((button) => {
        button.addEventListener("click", () => {
            const targetId = button.getAttribute("data-toggle-target");
            const target = document.getElementById(targetId);
            if (!target) {
                return;
            }
            const hidden = target.classList.toggle("is-hidden");
            button.textContent = hidden ? "Показать сводку" : "Скрыть сводку";
        });
    });
}

function setupRgbPreview(rId, gId, bId, previewId, valueId) {
    const rInput = document.getElementById(rId);
    const gInput = document.getElementById(gId);
    const bInput = document.getElementById(bId);
    const preview = document.getElementById(previewId);
    const valueLabel = document.getElementById(valueId);

    if (!rInput || !gInput || !bInput || !preview || !valueLabel) {
        return;
    }

    const update = () => {
        const r = clamp(rInput.value, 0, 255);
        const g = clamp(gInput.value, 0, 255);
        const b = clamp(bInput.value, 0, 255);
        rInput.value = r;
        gInput.value = g;
        bInput.value = b;
        const color = `rgb(${r}, ${g}, ${b})`;
        preview.style.background = color;
        valueLabel.textContent = `RGB(${r}, ${g}, ${b})`;
    };

    [rInput, gInput, bInput].forEach((input) => {
        input.addEventListener("input", update);
        input.addEventListener("change", update);
    });

    update();
}

function setupDateTime() {
    const targets = ["adminDateTime", "userDateTime"]
        .map((id) => document.getElementById(id))
        .filter(Boolean);

    if (!targets.length) {
        return;
    }

    const update = () => {
        const now = new Date();
        const formatted = now.toLocaleString("ru-RU");
        targets.forEach((target) => {
            target.textContent = formatted;
        });
    };

    update();
    setInterval(update, 1000);
}

function setupKettleTemperature() {
    const inputTarget = document.getElementById("adminKettleCurrentTemp");
    const textTarget = document.getElementById("userKettleCurrentTemp");
    const adminStateText = document.getElementById("adminKettleStateText");
    const userStateText = document.getElementById("userKettleStateText");
    const adminIndicator = document.getElementById("adminKettleIndicator");
    const userIndicator = document.getElementById("userKettleIndicator");
    const adminTargetInput = document.getElementById("kettleTemp");
    const kettleButtons = document.querySelectorAll("[data-kettle-action]");

    if (!inputTarget && !textTarget && !kettleButtons.length) {
        return;
    }

    let currentTemp = 24;
    let isOn = false;

    const renderState = () => {
        const stateText = isOn ? "Включен" : "Выключен";
        if (adminStateText) {
            adminStateText.textContent = stateText;
        }
        if (userStateText) {
            userStateText.textContent = stateText;
        }
        if (adminIndicator) {
            adminIndicator.classList.toggle("on", isOn);
        }
        if (userIndicator) {
            userIndicator.classList.toggle("on", isOn);
        }
    };

    kettleButtons.forEach((button) => {
        button.addEventListener("click", () => {
            const action = button.getAttribute("data-kettle-action");
            if (action === "on") {
                isOn = true;
            } else if (action === "off") {
                isOn = false;
            }
            renderState();
        });
    });

    const update = () => {
        const targetTemp = adminTargetInput ? clamp(adminTargetInput.value, 40, 100) : 100;
        if (isOn) {
            currentTemp = Math.min(targetTemp, currentTemp + 2);
            if (currentTemp >= targetTemp) {
                isOn = false;
                renderState();
            }
        } else {
            currentTemp = Math.max(24, currentTemp - 1);
        }

        if (inputTarget) {
            inputTarget.value = String(currentTemp);
        }
        if (textTarget) {
            textTarget.textContent = String(currentTemp);
        }
    };

    renderState();
    update();
    setInterval(update, 1000);
}

function setupVacuumStateButtons() {
    const buttons = document.querySelectorAll("[data-vacuum-state-target]");
    buttons.forEach((button) => {
        button.addEventListener("click", () => {
            const targetId = button.getAttribute("data-vacuum-state-target");
            const nextState = button.getAttribute("data-vacuum-state");
            const target = document.getElementById(targetId);
            if (!target || !nextState) {
                return;
            }
            target.textContent = nextState;
        });
    });
}

const DEVICES_KEY = "smartHomeDevices";
const THEME_KEY = "smartHomeTheme";
const ROBOT_MAP_KEY = "smartHomeRobotMap";

function getDefaultDevices() {
    return [
        "Робот-пылесос",
        "Умные шторы",
        "Умный чайник",
        "Климат-контроль",
        "Умная лампа 1",
        "Умная лампа 2",
        "Умная лампа 3",
        "Умная лампа 4",
    ];
}

function getDevices() {
    const raw = localStorage.getItem(DEVICES_KEY);
    if (!raw) {
        const defaults = getDefaultDevices();
        localStorage.setItem(DEVICES_KEY, JSON.stringify(defaults));
        return defaults;
    }
    try {
        const parsed = JSON.parse(raw);
        if (Array.isArray(parsed) && parsed.length) {
            return parsed;
        }
    } catch (_error) {
        // ignore parsing issues and restore defaults
    }
    const defaults = getDefaultDevices();
    localStorage.setItem(DEVICES_KEY, JSON.stringify(defaults));
    return defaults;
}

function setDevices(devices) {
    localStorage.setItem(DEVICES_KEY, JSON.stringify(devices));
}

function renderDevices() {
    const devices = getDevices();
    const userList = document.getElementById("userDeviceList");
    const adminList = document.getElementById("adminDeviceList");
    const removeSelect = document.getElementById("removeDeviceSelect");

    const listHtml = devices.map((device) => `<li>${device}</li>`).join("");
    if (userList) {
        userList.innerHTML = listHtml;
    }
    if (adminList) {
        adminList.innerHTML = listHtml;
    }
    if (removeSelect) {
        removeSelect.innerHTML = devices
            .map((device, index) => `<option value="${index}">${device}</option>`)
            .join("");
    }
}

function setupDeviceManager() {
    const addBtn = document.getElementById("addDeviceBtn");
    const removeBtn = document.getElementById("removeDeviceBtn");
    const newDeviceInput = document.getElementById("newDeviceName");
    const removeSelect = document.getElementById("removeDeviceSelect");

    renderDevices();

    if (!addBtn || !removeBtn || !newDeviceInput || !removeSelect) {
        return;
    }

    addBtn.addEventListener("click", () => {
        const name = newDeviceInput.value.trim();
        if (!name) {
            return;
        }
        const devices = getDevices();
        devices.push(name);
        setDevices(devices);
        newDeviceInput.value = "";
        renderDevices();
    });

    removeBtn.addEventListener("click", () => {
        const index = Number(removeSelect.value);
        const devices = getDevices();
        if (Number.isNaN(index) || index < 0 || index >= devices.length) {
            return;
        }
        devices.splice(index, 1);
        setDevices(devices);
        renderDevices();
    });
}

function applyTheme(theme) {
    document.body.classList.toggle("dark-theme", theme === "dark");
    const toggles = document.querySelectorAll("[data-style-toggle]");
    toggles.forEach((toggle) => {
        toggle.textContent = theme === "dark" ? "Светлый стиль" : "Ночной стиль";
    });
}

function setupThemeToggle() {
    const savedTheme = localStorage.getItem(THEME_KEY) || "light";
    applyTheme(savedTheme);

    const toggles = document.querySelectorAll("[data-style-toggle]");
    toggles.forEach((button) => {
        button.addEventListener("click", () => {
            const isDark = document.body.classList.contains("dark-theme");
            const nextTheme = isDark ? "light" : "dark";
            localStorage.setItem(THEME_KEY, nextTheme);
            applyTheme(nextTheme);
        });
    });
}

function setMapStatusText(fileName) {
    const text = fileName || "не загружена";
    const admin = document.getElementById("adminMapStatus");
    const user = document.getElementById("userMapStatus");
    if (admin) {
        admin.textContent = text;
    }
    if (user) {
        user.textContent = text;
    }
}

function setupRobotMapControls() {
    const fileInput = document.getElementById("mapFileInput");
    const uploadBtn = document.getElementById("uploadMapBtn");
    const viewBtnAdmin = document.getElementById("viewMapBtn");
    const viewBtnUser = document.getElementById("viewMapBtnUser");

    setMapStatusText(localStorage.getItem(ROBOT_MAP_KEY));

    if (uploadBtn && fileInput) {
        uploadBtn.addEventListener("click", () => {
            const file = fileInput.files && fileInput.files[0];
            if (!file) {
                return;
            }
            localStorage.setItem(ROBOT_MAP_KEY, file.name);
            setMapStatusText(file.name);
        });
    }

    const viewHandler = () => {
        const map = localStorage.getItem(ROBOT_MAP_KEY);
        if (!map) {
            alert("Карта дома еще не загружена.");
            return;
        }
        alert(`Открыта карта дома: ${map}`);
    };

    if (viewBtnAdmin) {
        viewBtnAdmin.addEventListener("click", viewHandler);
    }
    if (viewBtnUser) {
        viewBtnUser.addEventListener("click", viewHandler);
    }
}

document.addEventListener("DOMContentLoaded", () => {
    setupThemeToggle();
    setupSummaryToggles();
    setupRgbPreview("lampR", "lampG", "lampB", "lampColorPreview", "lampColorValue");
    setupRgbPreview("userLampR", "userLampG", "userLampB", "userLampColorPreview", "userLampColorValue");
    setupDateTime();
    setupKettleTemperature();
    setupVacuumStateButtons();
    setupDeviceManager();
    setupRobotMapControls();
});
