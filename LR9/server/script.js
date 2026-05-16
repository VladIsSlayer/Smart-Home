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
    ["indexDateTime", "adminDateTime", "userDateTime"].forEach((id) => {
        const el = document.getElementById(id);
        if (el) el.textContent = now;
    });
}

function handleConnectResponse(data) {
    if (data && data.ok === false && data.message) {
        showMessage(data.message, true);
    }
}

function ajaxGet(url, onSuccess, onError) {
    fetch(url)
        .then(async (response) => {
            const data = await response.json().catch(() => ({}));
            if (!response.ok) {
                const msg = data.message || `HTTP ${response.status} для ${url}`;
                throw new Error(msg);
            }
            return data;
        })
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

function controlGet(path, params, onSuccess, refreshMode = "all") {
    ajaxGet(`${path}${buildQuery(params)}`, (data) => {
        if (data.message) showMessage(data.message, !data.ok);
        if (onSuccess) onSuccess(data);
        markLocalEditing();
        if (refreshMode === "all") connectAllThings();
        else if (refreshMode === "lighting") {
            if (data.brightness !== undefined) updateLightingFromData(data);
            else connectSmartLighting();
        }
    });
}

function debounce(fn, delayMs) {
    let timerId = null;
    return (...args) => {
        clearTimeout(timerId);
        timerId = setTimeout(() => fn(...args), delayMs);
    };
}

function apiPost(path, body, onSuccess) {
    fetch(path, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body),
    })
        .then((response) => response.json())
        .then((data) => {
            if (data.message) showMessage(data.message, !data.ok);
            if (onSuccess) onSuccess(data);
        })
        .catch((error) => showMessage(`Ошибка запроса ${path}: ${error.message}`, true));
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
        handleConnectResponse(data);
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
    const list = document.getElementById("analysisStats");
    if (!list || !analysis) return;
    const fmt = (v) => (v === null || v === undefined ? "—" : String(v));
    const hasData =
        analysis.avg_temperature !== null &&
        analysis.avg_temperature !== undefined;
    list.innerHTML = `
        <li>Средняя температура: ${fmt(analysis.avg_temperature)} C</li>
        <li>Максимальная температура: ${fmt(analysis.max_temperature)} C</li>
        <li>Средняя влажность: ${fmt(analysis.avg_humidity)} %</li>
        <li>Максимальная влажность: ${fmt(analysis.max_humidity)} %</li>
        ${hasData ? "" : "<li class=\"device-meta\">Подождите 15–30 с: идёт накопление данных с датчиков…</li>"}
    `;
}

function refreshAnalysisPanel() {
    if (!document.getElementById("analysisStats")) return;
    ajaxGet("/api/analysis", (data) => {
        if (data.analysis) renderAnalysis(data.analysis);
    });
}

let temperatureChartInstance = null;

function temperatureChartYScale(values) {
    if (!values.length) {
        return { min: 15, max: 30 };
    }
    const minVal = Math.min(...values);
    const maxVal = Math.max(...values);
    const spread = Math.max(maxVal - minVal, 1);
    const pad = Math.max(0.5, spread * 0.15);
    return {
        min: Math.floor((minVal - pad) * 10) / 10,
        max: Math.ceil((maxVal + pad) * 10) / 10,
    };
}

function applyTemperatureChartData(chartPayload) {
    const chart = chartPayload || { labels: [], values: [] };
    const values = (chart.values || []).map((v) => Number(v));
    const yScale = temperatureChartYScale(values);

    if (!temperatureChartInstance) {
        return false;
    }

    temperatureChartInstance.data.labels = chart.labels || [];
    temperatureChartInstance.data.datasets[0].data = values;
    temperatureChartInstance.options.scales.y.min = yScale.min;
    temperatureChartInstance.options.scales.y.max = yScale.max;
    temperatureChartInstance.update();
    return true;
}

function loadTemperatureChart() {
    const canvas = document.getElementById("temperatureChart");
    if (!canvas || typeof Chart === "undefined") return;
    ajaxGet("/api/chart/temperature", (payload) => {
        const chart = payload.chart || { labels: [], values: [] };
        if (applyTemperatureChartData(chart)) {
            return;
        }
        const ctx = canvas.getContext("2d");
        const values = (chart.values || []).map((v) => Number(v));
        const yScale = temperatureChartYScale(values);
        const gradient = ctx.createLinearGradient(0, 0, 0, canvas.height || 180);
        gradient.addColorStop(0, "rgba(47, 111, 237, 0.45)");
        gradient.addColorStop(1, "rgba(47, 111, 237, 0.02)");
        temperatureChartInstance = new Chart(ctx, {
            type: "line",
            data: {
                labels: chart.labels,
                datasets: [{
                    label: "Температура, °C",
                    data: values,
                    borderColor: "#2f6fed",
                    backgroundColor: gradient,
                    borderWidth: 2.5,
                    fill: true,
                    tension: 0.4,
                    pointRadius: values.length <= 3 ? 5 : 4,
                    pointHoverRadius: 6,
                    pointBackgroundColor: "#ffffff",
                    pointBorderColor: "#2f6fed",
                    pointBorderWidth: 2,
                }],
            },
            options: {
                responsive: true,
                maintainAspectRatio: true,
                animation: { duration: 600 },
                plugins: {
                    legend: { display: true, labels: { font: { size: 13 } } },
                    tooltip: { mode: "index", intersect: false },
                },
                interaction: { mode: "nearest", axis: "x", intersect: false },
                scales: {
                    y: {
                        min: yScale.min,
                        max: yScale.max,
                        grid: { color: "rgba(120, 130, 150, 0.2)" },
                        title: { display: true, text: "°C", font: { weight: "600" } },
                    },
                    x: {
                        grid: { display: false },
                        ticks: { maxRotation: 40, minRotation: 0, maxTicksLimit: 8 },
                    },
                },
            },
        });
    });
}

function connectSmartCurtains() {
    ajaxGet("/connect_smart_curtains", (data) => {
        handleConnectResponse(data);
        if (data.automation) showAutomation(data.automation);
        if (data.analysis) renderAnalysis(data.analysis);
        const pos = data.positionPercent ?? 0;
        const target = data.targetPosition ?? pos;
        const adminPos = document.getElementById("adminCurtainsPosition");
        const adminTarget = document.getElementById("adminCurtainsTarget");
        const adminTargetWrap = document.getElementById("adminCurtainsTargetWrap");
        if (adminPos) adminPos.textContent = String(pos);
        if (adminTarget) adminTarget.textContent = String(target);
        if (adminTargetWrap) adminTargetWrap.classList.toggle("is-hidden", pos === target);
        const savedOpen = document.getElementById("adminCurtainsSavedOpen");
        if (savedOpen && data.savedOpenPercent !== undefined) {
            savedOpen.textContent = String(data.savedOpenPercent);
        }
        const adminSlider = document.getElementById("curtainLevel");
        if (shouldUpdateInput(adminSlider)) adminSlider.value = String(pos);
        const adminSummary = document.getElementById("adminSummaryCurtains");
        const userSummary = document.getElementById("userSummaryCurtains");
        const posText = pos === target ? `${pos} %` : `${pos} % -> ${target} %`;
        if (adminSummary) adminSummary.textContent = `Шторы: ${posText}`;
        if (userSummary) userSummary.textContent = `Шторы: ${posText}`;
    });
}

function connectSmartKettle() {
    ajaxGet("/connect_smart_kettle", (data) => {
        handleConnectResponse(data);
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
        handleConnectResponse(data);
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
        handleConnectResponse(data);
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

function updateLightingFromData(data) {
    const lightPower = document.getElementById("lightPower");
    const lightLevel = document.getElementById("lightLevel");
    if (shouldUpdateInput(lightPower)) lightPower.value = String(data.brightness);
    if (shouldUpdateInput(lightLevel)) lightLevel.value = String(data.brightness);

    const r = data.rgb_r ?? 255;
    const g = data.rgb_g ?? 180;
    const b = data.rgb_b ?? 90;
    applyLightingRgb(r, g, b, "");
    applyLightingRgb(r, g, b, "user");

    const isOn = Boolean(data.isOn);
    const adminIndicator = document.getElementById("adminLightsIndicator");
    const adminState = document.getElementById("adminLightsStateText");
    if (adminIndicator) adminIndicator.classList.toggle("on", isOn);
    if (adminState) adminState.textContent = isOn ? "Включены" : "Выключены";

    const adminSummary = document.getElementById("adminSummaryLights");
    const userSummary = document.getElementById("userSummaryLights");
    const stateLabel = isOn ? "вкл." : "выкл.";
    if (adminSummary) {
        adminSummary.textContent = `Лампы: ${stateLabel}, ${data.brightness} %, RGB(${r}, ${g}, ${b})`;
    }
    if (userSummary) {
        userSummary.textContent = `Лампы: ${stateLabel}, ${data.brightness} %, RGB(${r}, ${g}, ${b})`;
    }
}

function connectSmartLighting() {
    ajaxGet("/connect_smart_lighting", (data) => {
        handleConnectResponse(data);
        updateLightingFromData(data);
    });
}

function applyLightingBrightness(sliderId) {
    const isAdmin = sliderId === "lightPower";
    const brightness = document.getElementById(sliderId)?.value ?? 70;
    const r = document.getElementById(isAdmin ? "lampR" : "userLampR")?.value ?? 255;
    const g = document.getElementById(isAdmin ? "lampG" : "userLampG")?.value ?? 180;
    const b = document.getElementById(isAdmin ? "lampB" : "userLampB")?.value ?? 90;
    controlGet(
        "/control_smart_lighting",
        { action: "apply", brightness, r, g, b },
        (data) => updateLightingFromData(data),
        "none"
    );
}

const debouncedAdminBrightness = debounce(() => applyLightingBrightness("lightPower"), 200);
const debouncedUserBrightness = debounce(() => applyLightingBrightness("lightLevel"), 200);

function setupLightingBrightnessLive() {
    const lightPower = document.getElementById("lightPower");
    if (lightPower) {
        lightPower.addEventListener("input", (event) => {
            markInputDirty(event);
            debouncedAdminBrightness();
        });
    }
    const lightLevel = document.getElementById("lightLevel");
    if (lightLevel) {
        lightLevel.addEventListener("input", (event) => {
            markInputDirty(event);
            debouncedUserBrightness();
        });
    }
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
        controlGet("/control_smart_curtains", { action: "open" });
    });
    bind("userCurtainsOpenBtn", () => controlGet("/control_smart_curtains", { action: "open" }));
    bind("adminCurtainsCloseBtn", () => controlGet("/control_smart_curtains", { action: "close" }));
    bind("userCurtainsCloseBtn", () => controlGet("/control_smart_curtains", { action: "close" }));
    bind("adminCurtainsSaveBtn", () => {
        const level = document.getElementById("curtainLevel");
        controlGet("/control_smart_curtains", { action: "save", percent: level ? level.value : 60 });
    });

    bind("adminLightsOnBtn", () => controlGet("/control_smart_lighting", { action: "on" }));
    bind("adminLightsOffBtn", () => controlGet("/control_smart_lighting", { action: "off" }));
    bind("adminLightsBrightnessBtn", () => applyLightingBrightness("lightPower"));
    bind("userLightsBrightnessBtn", () => applyLightingBrightness("lightLevel"));
    bind("adminLightsApplyBtn", () => {
        const brightness = document.getElementById("lightPower")?.value || 70;
        const r = document.getElementById("lampR")?.value || 255;
        const g = document.getElementById("lampG")?.value || 180;
        const b = document.getElementById("lampB")?.value || 90;
        controlGet(
            "/control_smart_lighting",
            { action: "apply", brightness, r, g, b },
            (data) => updateLightingFromData(data),
            "lighting"
        );
    });
    bind("userLightsApplyBtn", () => {
        const brightness = document.getElementById("lightLevel")?.value || 70;
        const r = document.getElementById("userLampR")?.value || 255;
        const g = document.getElementById("userLampG")?.value || 180;
        const b = document.getElementById("userLampB")?.value || 90;
        controlGet(
            "/control_smart_lighting",
            { action: "apply", brightness, r, g, b },
            (data) => updateLightingFromData(data),
            "lighting"
        );
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

function collectSceneActionsFromForm() {
    const actions = {};
    if (document.getElementById("sceneChkLighting")?.checked) {
        actions.lighting = {
            on: Number(document.getElementById("lightPower")?.value || 0) > 0,
            brightness: Number(document.getElementById("lightPower")?.value || 70),
            r: Number(document.getElementById("lampR")?.value || 255),
            g: Number(document.getElementById("lampG")?.value || 180),
            b: Number(document.getElementById("lampB")?.value || 90),
        };
    }
    if (document.getElementById("sceneChkCurtains")?.checked) {
        actions.curtains = { percent: Number(document.getElementById("curtainLevel")?.value || 60) };
    }
    if (document.getElementById("sceneChkKettle")?.checked) {
        actions.kettle = {
            action: "target",
            target_temp: Number(document.getElementById("kettleTemp")?.value || 90),
        };
    }
    if (document.getElementById("sceneChkClimateT")?.checked) {
        actions.temperature = { target: Number(document.getElementById("homeTargetTemp")?.value || 24) };
    }
    if (document.getElementById("sceneChkClimateH")?.checked) {
        actions.humidity = { target: Number(document.getElementById("homeTargetHumidity")?.value || 50) };
    }
    if (document.getElementById("sceneChkVacuum")?.checked) {
        actions.vacuum = { action: "start", mode: "auto" };
    }
    return actions;
}

function resetSceneForm() {
    const idEl = document.getElementById("sceneEditId");
    if (idEl) idEl.value = "";
    const nameEl = document.getElementById("sceneName");
    if (nameEl) nameEl.value = "";
    ["sceneDate", "sceneTime"].forEach((id) => {
        const el = document.getElementById(id);
        if (el) el.value = "";
    });
}

function fillSceneForm(scene) {
    const idEl = document.getElementById("sceneEditId");
    if (idEl) idEl.value = scene.id || "";
    const nameEl = document.getElementById("sceneName");
    if (nameEl) nameEl.value = scene.name || "";
    const dateEl = document.getElementById("sceneDate");
    if (dateEl) dateEl.value = scene.date || "";
    const timeEl = document.getElementById("sceneTime");
    if (timeEl) timeEl.value = scene.time || "";
    const actions = scene.actions || {};
    const setChk = (id, on) => {
        const el = document.getElementById(id);
        if (el) el.checked = Boolean(on);
    };
    setChk("sceneChkLighting", actions.lighting);
    setChk("sceneChkCurtains", actions.curtains);
    setChk("sceneChkKettle", actions.kettle);
    setChk("sceneChkClimateT", actions.temperature);
    setChk("sceneChkClimateH", actions.humidity);
    setChk("sceneChkVacuum", actions.vacuum);
}

function renderScenesList(scenes) {
    const list = document.getElementById("scenesList");
    if (!list) return;
    if (!scenes || !scenes.length) {
        list.innerHTML = "<li>Нет сценариев</li>";
        return;
    }
    list.innerHTML = scenes
        .map((scene) => {
            const when = [scene.date, scene.time].filter(Boolean).join(" ");
            const badge = scene.builtin ? "встроенный" : "пользовательский";
            const schedule = when ? ` · ${when}` : "";
            return `<li data-scene-id="${scene.id}">
                <div class="scene-meta">
                    <span class="scene-title">${scene.name}</span>
                    <span> (${badge}${schedule})</span>
                </div>
                <button type="button" class="btn btn-scene-apply" data-id="${scene.id}">Применить</button>
                <button type="button" class="btn btn-scene-edit" data-id="${scene.id}">Изменить</button>
                ${scene.builtin ? "" : `<button type="button" class="btn btn-scene-delete" data-id="${scene.id}">Удалить</button>`}
            </li>`;
        })
        .join("");

    list.querySelectorAll(".btn-scene-apply").forEach((btn) => {
        btn.addEventListener("click", () => {
            apiPost("/api/scenes/apply", { id: btn.getAttribute("data-id") }, () => connectAllThings());
        });
    });
    list.querySelectorAll(".btn-scene-edit").forEach((btn) => {
        btn.addEventListener("click", () => {
            const scene = scenes.find((s) => s.id === btn.getAttribute("data-id"));
            if (scene) fillSceneForm(scene);
        });
    });
    list.querySelectorAll(".btn-scene-delete").forEach((btn) => {
        btn.addEventListener("click", () => {
            apiPost("/api/scenes/delete", { id: btn.getAttribute("data-id") }, () => loadScenes());
        });
    });
}

function loadScenes() {
    ajaxGet("/api/scenes", (data) => renderScenesList(data.scenes || []));
}

function setupSceneActions() {
    const saveBtn = document.getElementById("adminSceneSaveBtn");
    if (saveBtn) {
        saveBtn.addEventListener("click", () => {
            const actions = collectSceneActionsFromForm();
            if (!Object.keys(actions).length) {
                showMessage("Отметьте хотя бы один блок для сценария", true);
                return;
            }
            apiPost("/api/scenes/save", {
                id: document.getElementById("sceneEditId")?.value || "",
                name: document.getElementById("sceneName")?.value || "Новый сценарий",
                date: document.getElementById("sceneDate")?.value || "",
                time: document.getElementById("sceneTime")?.value || "",
                actions,
            }, () => {
                resetSceneForm();
                loadScenes();
                connectAllThings();
            });
        });
    }
    const resetBtn = document.getElementById("adminSceneResetBtn");
    if (resetBtn) resetBtn.addEventListener("click", resetSceneForm);
}

function initDevicePage() {
    setupRgbPreview("lampR", "lampG", "lampB", "lampColorPreview", "lampColorValue");
    setupRgbPreview("userLampR", "userLampG", "userLampB", "userLampColorPreview", "userLampColorValue");
    setupLightingBrightnessLive();
    setupControlActions();
    setupSceneActions();
    connectAllThings();
    setInterval(connectAllThings, 5000);
    if (document.getElementById("scenesList")) loadScenes();
    if (document.getElementById("analysisStats")) {
        refreshAnalysisPanel();
        setInterval(refreshAnalysisPanel, 5000);
    }
    if (document.getElementById("temperatureChart")) {
        loadTemperatureChart();
        setInterval(loadTemperatureChart, 5000);
    }
    document
        .querySelectorAll(
            "#kettleTemp, #curtainLevel, #lightPower, #lightLevel, #lampR, #lampG, #lampB, #userLampR, #userLampG, #userLampB, #homeTargetTemp, #homeTargetHumidity"
        )
        .forEach((input) => input.addEventListener("input", markInputDirty));
}

document.addEventListener("DOMContentLoaded", () => {
    setupThemeToggle();
    setupSummaryToggles();
    updateDateTimeLocal();
    setInterval(updateDateTimeLocal, 1000);
    if (document.getElementById("kettleTemp") || document.getElementById("curtainLevel")) {
        initDevicePage();
    }
});
