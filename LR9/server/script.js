function clamp(value, min, max) {
    const number = Number(value);
    if (Number.isNaN(number)) return min;
    return Math.max(min, Math.min(max, number));
}

let localEditLockUntil = 0;
const dirtyInputs = new Set();

function markLocalEditing() {
    localEditLockUntil = Date.now() + 8000;
}

function shouldUpdateInput(input) {
    return Boolean(input) && document.activeElement !== input && Date.now() > localEditLockUntil && !dirtyInputs.has(input.id);
}

function markInputDirty(event) {
    const input = event.target;
    if (!(input instanceof HTMLElement) || !input.id) return;
    dirtyInputs.add(input.id);
    markLocalEditing();
}

function showMessage(text, isError = false) {
    const adminMsg = document.getElementById("adminActionMessage");
    const userMsg = document.getElementById("userActionMessage");
    const target = adminMsg || userMsg;
    if (!target) return;
    target.textContent = text;
    target.style.color = isError ? "#b92020" : "";
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

function ajaxGet(url, onSuccess, onError) {
    fetch(url)
        .then((response) => response.json())
        .then(onSuccess)
        .catch((error) => {
            const msg = `Ошибка запроса ${url}: ${error.message}`;
            if (onError) onError(msg);
            else showMessage(msg, true);
        });
}

function buildQuery(params) {
    const query = new URLSearchParams();
    Object.entries(params).forEach(([key, value]) => {
        if (value !== undefined && value !== null && value !== "") query.set(key, String(value));
    });
    const text = query.toString();
    return text ? `?${text}` : "";
}

function controlGet(path, params, onSuccess) {
    ajaxGet(`${path}${buildQuery(params)}`, (data) => {
        if (data.message) showMessage(data.message, !data.ok);
        if (onSuccess) onSuccess(data);
        markLocalEditing();
        connectAllThings();
    });
}

function applyLightingRgb(r, g, b, prefix = "") {
    const ids = prefix
        ? [`${prefix}LampR`, `${prefix}LampG`, `${prefix}LampB`]
        : ["lampR", "lampG", "lampB"];
    const map = { [ids[0]]: r, [ids[1]]: g, [ids[2]]: b };
    ids.forEach((id) => {
        const el = document.getElementById(id);
        if (!el || !shouldUpdateInput(el)) return;
        el.value = String(map[id]);
        el.dispatchEvent(new Event("input"));
    });
}

// --- Мониторинг ---

function connectRobotVacuum() {
    ajaxGet("/connect_robot_vacuum", (data) => {
        const stateText =
            data.cleaningState === "running" ? "Уборка" : data.cleaningState === "docked" ? "На базе" : "На связи";
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

function showAutomation(actions) {
    if (!actions || !actions.length) return;
    showMessage(`Автоматика: ${actions.join("; ")}`);
}

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

let temperatureChartInstance = null;

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
                    pointRadius: 3,
                }],
            },
            options: {
                responsive: true,
                plugins: { legend: { display: true } },
                scales: {
                    y: { beginAtZero: false, title: { display: true, text: "C" } },
                    x: { ticks: { maxRotation: 45, minRotation: 0 } },
                },
            },
        });
    });
}

function connectSmartCurtains() {
    ajaxGet("/connect_smart_curtains", (data) => {
        if (data.automation) showAutomation(data.automation);
        const adminSlider = document.getElementById("curtainLevel");
        if (shouldUpdateInput(adminSlider)) adminSlider.value = String(data.positionPercent);
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
        const tempRounded = Math.round(data.currentWaterTemperature);
        if (adminTemp) adminTemp.value = String(tempRounded);
        if (userTemp) userTemp.textContent = String(tempRounded);
        const boiling = Boolean(data.isBoiling);
        if (adminState) adminState.textContent = boiling ? "Кипячение" : "Ожидание";
        if (userState) userState.textContent = boiling ? "Кипячение" : "Ожидание";
        if (adminIndicator) adminIndicator.classList.toggle("on", boiling);
        if (userIndicator) userIndicator.classList.toggle("on", boiling);
        const kettleTarget = document.getElementById("kettleTemp");
        if (shouldUpdateInput(kettleTarget)) kettleTarget.value = String(data.targetTemperature);
    });
}

function connectTemperatureControl() {
    ajaxGet("/connect_temperature_control", (data) => {
        if (data.automation) showAutomation(data.automation);
        if (data.analysis) renderAnalysis(data.analysis);
        const currentEl = document.getElementById("adminClimateCurrentTemp");
        const targetDisplay = document.getElementById("adminClimateTargetTempDisplay");
        const targetInput = document.getElementById("homeTargetTemp");
        if (currentEl) currentEl.textContent = String(data.temperature);
        if (targetDisplay) targetDisplay.textContent = String(data.targetTemperature);
        if (shouldUpdateInput(targetInput)) targetInput.value = String(data.targetTemperature);

        const userCurrent = document.getElementById("userCurrentTemperature");
        const userTarget = document.getElementById("userTargetTemperature");
        if (userCurrent) userCurrent.textContent = String(data.temperature);
        if (userTarget) userTarget.textContent = String(data.targetTemperature);
        updateAdminClimateSummary(data.temperature, data.targetTemperature, null, null);
    });
}

function connectHumidityControl() {
    ajaxGet("/connect_humidity_control", (data) => {
        if (data.automation) showAutomation(data.automation);
        if (data.analysis) renderAnalysis(data.analysis);
        const currentEl = document.getElementById("adminClimateCurrentHumidity");
        const targetDisplay = document.getElementById("adminClimateTargetHumidityDisplay");
        const targetInput = document.getElementById("homeTargetHumidity");
        if (currentEl) currentEl.textContent = String(data.humidity);
        if (targetDisplay) targetDisplay.textContent = String(data.targetHumidity);
        if (shouldUpdateInput(targetInput)) targetInput.value = String(data.targetHumidity);

        const userCurrent = document.getElementById("userCurrentHumidity");
        const userTarget = document.getElementById("userTargetHumidity");
        if (userCurrent) userCurrent.textContent = String(data.humidity);
        if (userTarget) userTarget.textContent = String(data.targetHumidity);
        updateAdminClimateSummary(null, null, data.humidity, data.targetHumidity);
    });
}

function connectSmartLighting() {
    ajaxGet("/connect_smart_lighting", (data) => {
        const lightPower = document.getElementById("lightPower");
        const lightLevel = document.getElementById("lightLevel");
        if (shouldUpdateInput(lightPower)) lightPower.value = String(data.brightness);
        if (shouldUpdateInput(lightLevel)) lightLevel.value = String(data.brightness);

        const r = data.rgb_r ?? 255;
        const g = data.rgb_g ?? 180;
        const b = data.rgb_b ?? 90;
        applyLightingRgb(r, g, b, "");
        applyLightingRgb(r, g, b, "user");

        const adminSummary = document.getElementById("adminSummaryLights");
        const userSummary = document.getElementById("userSummaryLights");
        if (adminSummary) {
            adminSummary.textContent = `Лампы: ${data.brightness} %, RGB(${r}, ${g}, ${b})`;
        }
        if (userSummary) {
            userSummary.textContent = `Лампы: яркость ${data.brightness} %, RGB(${r}, ${g}, ${b})`;
        }
    });
}

function updateAdminClimateSummary(currentT, targetT, currentH, targetH) {
    const adminSummary = document.getElementById("adminSummaryClimate");
    if (!adminSummary) return;
    const tCur = currentT ?? document.getElementById("adminClimateCurrentTemp")?.textContent ?? "—";
    const tTar = targetT ?? document.getElementById("adminClimateTargetTempDisplay")?.textContent ?? "—";
    const hCur = currentH ?? document.getElementById("adminClimateCurrentHumidity")?.textContent ?? "—";
    const hTar = targetH ?? document.getElementById("adminClimateTargetHumidityDisplay")?.textContent ?? "—";
    adminSummary.textContent = `Климат: ${tCur} C (цель ${tTar} C) / ${hCur} % (цель ${hTar} %)`;
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

// --- Управляющие команды ---

function setupControlActions() {
    const bind = (id, handler) => {
        const btn = document.getElementById(id);
        if (btn) btn.addEventListener("click", handler);
    };

    bind("adminKettleOnBtn", () => {
        const target = document.getElementById("kettleTemp");
        controlGet("/control_smart_kettle", { action: "on", target_temp: target ? target.value : 90 });
    });
    bind("userKettleOnBtn", () => controlGet("/control_smart_kettle", { action: "on", target_temp: 90 }));
    bind("adminKettleOffBtn", () => controlGet("/control_smart_kettle", { action: "off" }));
    bind("userKettleOffBtn", () => controlGet("/control_smart_kettle", { action: "off" }));
    bind("adminKettleTargetSaveBtn", () => {
        const target = document.getElementById("kettleTemp");
        controlGet("/control_smart_kettle", { action: "target", target_temp: target ? target.value : 90 });
    });

    bind("adminCurtainsOpenBtn", () => {
        controlGet("/control_smart_curtains", { action: "open", percent: 100 });
    });
    bind("userCurtainsOpenBtn", () => controlGet("/control_smart_curtains", { action: "open", percent: 100 }));
    bind("adminCurtainsCloseBtn", () => controlGet("/control_smart_curtains", { action: "close" }));
    bind("userCurtainsCloseBtn", () => controlGet("/control_smart_curtains", { action: "close" }));
    bind("adminCurtainsSaveBtn", () => {
        const level = document.getElementById("curtainLevel");
        controlGet("/control_smart_curtains", { action: "set", percent: level ? level.value : 0 });
    });

    bind("adminLightsOnBtn", () => controlGet("/control_smart_lighting", { action: "on" }));
    bind("adminLightsOffBtn", () => controlGet("/control_smart_lighting", { action: "off" }));
    bind("adminLightsApplyBtn", () => {
        const brightness = document.getElementById("lightPower")?.value || 70;
        const r = document.getElementById("lampR")?.value || 255;
        const g = document.getElementById("lampG")?.value || 180;
        const b = document.getElementById("lampB")?.value || 90;
        controlGet("/control_smart_lighting", { action: "apply", brightness, r, g, b });
    });
    bind("userLightsApplyBtn", () => {
        const brightness = document.getElementById("lightLevel")?.value || 70;
        const r = document.getElementById("userLampR")?.value || 255;
        const g = document.getElementById("userLampG")?.value || 180;
        const b = document.getElementById("userLampB")?.value || 90;
        controlGet("/control_smart_lighting", { action: "apply", brightness, r, g, b });
    });

    bind("adminVacuumStartBtn", () => controlGet("/control_robot_vacuum", { action: "start", mode: "auto" }));
    bind("userVacuumStartBtn", () => controlGet("/control_robot_vacuum", { action: "start", mode: "eco" }));
    bind("adminVacuumPauseBtn", () => controlGet("/control_robot_vacuum", { action: "pause" }));
    bind("userVacuumPauseBtn", () => controlGet("/control_robot_vacuum", { action: "pause" }));
    bind("adminVacuumDockBtn", () => controlGet("/control_robot_vacuum", { action: "dock" }));
    bind("userVacuumDockBtn", () => controlGet("/control_robot_vacuum", { action: "dock" }));

    bind("adminClimateApplyBtn", () => {
        const t = document.getElementById("homeTargetTemp")?.value || 24;
        const h = document.getElementById("homeTargetHumidity")?.value || 50;
        controlGet("/control_temperature_control", { target_temperature: t });
        controlGet("/control_humidity_control", { target_humidity: h });
    });
}

document.addEventListener("DOMContentLoaded", () => {
    setupThemeToggle();
    setupSummaryToggles();
    setupRgbPreview("lampR", "lampG", "lampB", "lampColorPreview", "lampColorValue");
    setupRgbPreview("userLampR", "userLampG", "userLampB", "userLampColorPreview", "userLampColorValue");
    updateDateTimeLocal();
    setInterval(updateDateTimeLocal, 1000);
    setupControlActions();
    connectAllThings();
    loadTemperatureChart();
    setInterval(connectAllThings, 10000);
    setInterval(loadTemperatureChart, 15000);

    document
        .querySelectorAll(
            "#kettleTemp, #curtainLevel, #lightPower, #lightLevel, #lampR, #lampG, #lampB, #userLampR, #userLampG, #userLampB, #homeTargetTemp, #homeTargetHumidity"
        )
        .forEach((input) => input.addEventListener("input", markInputDirty));
});
