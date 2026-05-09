function clamp(value, min, max) {
    const number = Number(value);
    if (Number.isNaN(number)) {
        return min;
    }
    return Math.max(min, Math.min(max, number));
}

function showError(text) {
    const adminMsg = document.getElementById("adminActionMessage");
    const userMsg = document.getElementById("userActionMessage");
    const target = adminMsg || userMsg;
    if (!target) return;
    target.textContent = text;
    target.style.color = "#b92020";
}

function setupSummaryToggles() {
    document.querySelectorAll("[data-toggle-target]").forEach((button) => {
        button.addEventListener("click", () => {
            const target = document.getElementById(button.getAttribute("data-toggle-target"));
            if (!target) return;
            const hidden = target.classList.toggle("is-hidden");
            button.textContent = hidden ? "Показать сводку" : "Скрыть сводку";
        });
    });
}

function setupThemeToggle() {
    const key = "smartHomeTheme";
    const applyTheme = (theme) => {
        document.body.classList.toggle("dark-theme", theme === "dark");
        document.querySelectorAll("[data-style-toggle]").forEach((toggle) => {
            toggle.textContent = theme === "dark" ? "Светлый стиль" : "Ночной стиль";
        });
    };
    applyTheme(localStorage.getItem(key) || "light");
    document.querySelectorAll("[data-style-toggle]").forEach((button) => {
        button.addEventListener("click", () => {
            const next = document.body.classList.contains("dark-theme") ? "light" : "dark";
            localStorage.setItem(key, next);
            applyTheme(next);
        });
    });
}

function updateDateTimeLocal() {
    const now = new Date().toLocaleString("ru-RU");
    ["adminDateTime", "userDateTime"].forEach((id) => {
        const el = document.getElementById(id);
        if (el) el.textContent = now;
    });
}

function ajaxGet(url, onSuccess) {
    fetch(url)
        .then((response) => response.json())
        .then(onSuccess)
        .catch((error) => showError(`Ошибка запроса ${url}: ${error.message}`));
}

function connectRobotVacuum() {
    ajaxGet("/connect_robot_vacuum", (data) => {
        const stateText = data.status === "online" ? "На связи" : data.status;
        const adminState = document.getElementById("adminVacuumState");
        const userState = document.getElementById("userVacuumState");
        if (adminState) adminState.textContent = `${stateText}, заряд ${data.batteryLevel}%`;
        if (userState) userState.textContent = `${stateText}, заряд ${data.batteryLevel}%`;
        const adminSummary = document.getElementById("adminSummaryVacuum");
        const userSummary = document.getElementById("userSummaryVacuum");
        if (adminSummary) adminSummary.textContent = `Пылесос: заряд ${data.batteryLevel}%`;
        if (userSummary) userSummary.textContent = `Робот-пылесос: заряд ${data.batteryLevel}%`;
    });
}

function connectSmartCurtains() {
    ajaxGet("/connect_smart_curtains", (data) => {
        const adminSlider = document.getElementById("curtainLevel");
        if (adminSlider) adminSlider.value = String(data.positionPercent);
        const adminSummary = document.getElementById("adminSummaryCurtains");
        const userSummary = document.getElementById("userSummaryCurtains");
        if (adminSummary) adminSummary.textContent = `Шторы: открыты на ${data.positionPercent} %`;
        if (userSummary) userSummary.textContent = `Шторы: открыты на ${data.positionPercent} %`;
    });
}

function connectSmartKettle() {
    ajaxGet("/connect_smart_kettle", (data) => {
        const adminTemp = document.getElementById("adminKettleCurrentTemp");
        const userTemp = document.getElementById("userKettleCurrentTemp");
        const adminState = document.getElementById("adminKettleStateText");
        const userState = document.getElementById("userKettleStateText");
        const adminIndicator = document.getElementById("adminKettleIndicator");
        const userIndicator = document.getElementById("userKettleIndicator");
        if (adminTemp) adminTemp.value = String(Math.round(data.currentWaterTemperature));
        if (userTemp) userTemp.textContent = String(Math.round(data.currentWaterTemperature));
        if (adminState) adminState.textContent = data.isBoiling ? "Кипячение" : "Ожидание";
        if (userState) userState.textContent = data.isBoiling ? "Кипячение" : "Ожидание";
        if (adminIndicator) adminIndicator.classList.toggle("on", Boolean(data.isBoiling));
        if (userIndicator) userIndicator.classList.toggle("on", Boolean(data.isBoiling));
        const adminSummary = document.getElementById("adminSummaryKettle");
        const userSummary = document.getElementById("userSummaryKettle");
        const tempRounded = Math.round(data.currentWaterTemperature);
        if (adminSummary) adminSummary.textContent = `Чайник: ${tempRounded} C`;
        if (userSummary) userSummary.textContent = `Чайник: ${tempRounded} C`;
    });
}

function connectTemperatureControl() {
    ajaxGet("/connect_temperature_control", (data) => {
        const homeTemp = document.getElementById("homeTemp");
        if (homeTemp) homeTemp.value = String(data.temperature);
        const userCurrent = document.getElementById("userCurrentTemperature");
        const userTarget = document.getElementById("userTargetTemperature");
        if (userCurrent) userCurrent.textContent = String(data.temperature);
        if (userTarget) userTarget.textContent = String(data.targetTemperature);
        const userSummary = document.getElementById("userSummaryTemperature");
        if (userSummary) userSummary.textContent = `Температура: ${data.temperature} C (цель ${data.targetTemperature} C)`;
        updateAdminClimateSummary();
    });
}

function connectHumidityControl() {
    ajaxGet("/connect_humidity_control", (data) => {
        const homeHumidity = document.getElementById("homeHumidity");
        if (homeHumidity) homeHumidity.value = String(data.humidity);
        const userCurrent = document.getElementById("userCurrentHumidity");
        const userTarget = document.getElementById("userTargetHumidity");
        if (userCurrent) userCurrent.textContent = String(data.humidity);
        if (userTarget) userTarget.textContent = String(data.targetHumidity);
        const userSummary = document.getElementById("userSummaryHumidity");
        if (userSummary) userSummary.textContent = `Влажность: ${data.humidity} % (цель ${data.targetHumidity} %)`;
        updateAdminClimateSummary();
    });
}

function connectSmartLighting() {
    ajaxGet("/connect_smart_lighting", (data) => {
        const lightPower = document.getElementById("lightPower");
        const lightLevel = document.getElementById("lightLevel");
        if (lightPower) lightPower.value = String(data.brightness);
        if (lightLevel) lightLevel.value = String(data.brightness);

        const lampR = document.getElementById("lampR");
        const lampG = document.getElementById("lampG");
        const lampB = document.getElementById("lampB");
        const userLampR = document.getElementById("userLampR");
        const userLampG = document.getElementById("userLampG");
        const userLampB = document.getElementById("userLampB");

        const avg = clamp(Math.round((data.colorTemperature - 2000) / 18), 0, 255);
        const r = 255;
        const g = clamp(avg, 80, 220);
        const b = clamp(255 - avg, 60, 200);

        if (lampR && lampG && lampB) {
            lampR.value = String(r);
            lampG.value = String(g);
            lampB.value = String(b);
            lampR.dispatchEvent(new Event("input"));
        }
        if (userLampR && userLampG && userLampB) {
            userLampR.value = String(r);
            userLampG.value = String(g);
            userLampB.value = String(b);
            userLampR.dispatchEvent(new Event("input"));
        }
        const adminSummary = document.getElementById("adminSummaryLights");
        const userSummary = document.getElementById("userSummaryLights");
        if (adminSummary) adminSummary.textContent = `Лампы: ${data.brightness} % яркости, ${data.colorTemperature} K`;
        if (userSummary) userSummary.textContent = `Лампы: яркость ${data.brightness} %, ${data.colorTemperature} K`;
    });
}

function updateAdminClimateSummary() {
    const t = document.getElementById("homeTemp");
    const h = document.getElementById("homeHumidity");
    const adminSummary = document.getElementById("adminSummaryClimate");
    if (!t || !h || !adminSummary) return;
    adminSummary.textContent = `Климат: ${t.value} C / ${h.value} % влажности`;
}

function setupRgbPreview(rId, gId, bId, previewId, valueId) {
    const rInput = document.getElementById(rId);
    const gInput = document.getElementById(gId);
    const bInput = document.getElementById(bId);
    const preview = document.getElementById(previewId);
    const valueLabel = document.getElementById(valueId);
    if (!rInput || !gInput || !bInput || !preview || !valueLabel) return;

    const update = () => {
        const r = clamp(rInput.value, 0, 255);
        const g = clamp(gInput.value, 0, 255);
        const b = clamp(bInput.value, 0, 255);
        rInput.value = r;
        gInput.value = g;
        bInput.value = b;
        preview.style.background = `rgb(${r}, ${g}, ${b})`;
        valueLabel.textContent = `RGB(${r}, ${g}, ${b})`;
    };
    [rInput, gInput, bInput].forEach((input) => input.addEventListener("input", update));
    update();
}

function connectAllThings() {
    connectRobotVacuum();
    connectSmartCurtains();
    connectSmartKettle();
    connectTemperatureControl();
    connectHumidityControl();
    connectSmartLighting();
}

document.addEventListener("DOMContentLoaded", () => {
    setupThemeToggle();
    setupSummaryToggles();
    setupRgbPreview("lampR", "lampG", "lampB", "lampColorPreview", "lampColorValue");
    setupRgbPreview("userLampR", "userLampG", "userLampB", "userLampColorPreview", "userLampColorValue");
    updateDateTimeLocal();
    setInterval(updateDateTimeLocal, 1000);
    connectAllThings();
    setInterval(connectAllThings, 10000);
});
