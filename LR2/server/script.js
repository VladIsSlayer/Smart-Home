function clamp(value, min, max) {
    const number = Number(value);
    if (Number.isNaN(number)) {
        return min;
    }
    return Math.max(min, Math.min(max, number));
}

async function api(path, options = {}) {
    const response = await fetch(path, {
        headers: { "Content-Type": "application/json" },
        ...options,
    });
    const raw = await response.text();
    let data = null;
    try {
        data = raw ? JSON.parse(raw) : {};
    } catch (_error) {
        const shortBody = raw.slice(0, 120).replace(/\s+/g, " ");
        throw new Error(`Сервер вернул не JSON (HTTP ${response.status}): ${shortBody}`);
    }
    if (!response.ok) {
        throw new Error(data.message || `HTTP ${response.status}`);
    }
    return data;
}

function showMessage(text, isError = false) {
    const adminMsg = document.getElementById("adminActionMessage");
    const userMsg = document.getElementById("userActionMessage");
    const target = adminMsg || userMsg;
    if (!target) return;
    target.textContent = text;
    target.style.color = isError ? "#b92020" : "";
}

let localEditLockUntil = 0;
const dirtyInputs = new Set();

function markLocalEditing() {
    localEditLockUntil = Date.now() + 5000;
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

function clearDirty(...ids) {
    ids.forEach((id) => dirtyInputs.delete(id));
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
    [rInput, gInput, bInput].forEach((i) => i.addEventListener("input", update));
    update();
}

function applyTheme(theme) {
    document.body.classList.toggle("dark-theme", theme === "dark");
    document.querySelectorAll("[data-style-toggle]").forEach((toggle) => {
        toggle.textContent = theme === "dark" ? "Светлый стиль" : "Ночной стиль";
    });
}

function setupThemeToggle() {
    const key = "smartHomeTheme";
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

function renderStatus(status) {
    const kettleTempAdmin = document.getElementById("adminKettleCurrentTemp");
    const kettleTargetAdmin = document.getElementById("kettleTemp");
    const kettleTempUser = document.getElementById("userKettleCurrentTemp");
    const kettleStateAdmin = document.getElementById("adminKettleStateText");
    const kettleStateUser = document.getElementById("userKettleStateText");
    const kettleIndicatorAdmin = document.getElementById("adminKettleIndicator");
    const kettleIndicatorUser = document.getElementById("userKettleIndicator");

    if (kettleTempAdmin) kettleTempAdmin.value = Math.round(status.kettle.current_temp);
    if (shouldUpdateInput(kettleTargetAdmin)) kettleTargetAdmin.value = status.kettle.target_temp;
    if (kettleTempUser) kettleTempUser.textContent = String(Math.round(status.kettle.current_temp));
    if (kettleStateAdmin) kettleStateAdmin.textContent = status.kettle.state_text;
    if (kettleStateUser) kettleStateUser.textContent = status.kettle.state_text;
    if (kettleIndicatorAdmin) kettleIndicatorAdmin.classList.toggle("on", status.kettle.is_on);
    if (kettleIndicatorUser) kettleIndicatorUser.classList.toggle("on", status.kettle.is_on);

    const vacuumAdmin = document.getElementById("adminVacuumState");
    const vacuumUser = document.getElementById("userVacuumState");
    if (vacuumAdmin) vacuumAdmin.textContent = status.vacuum.state;
    if (vacuumUser) vacuumUser.textContent = status.vacuum.state;

    const mapAdmin = document.getElementById("adminMapStatus");
    const mapUser = document.getElementById("userMapStatus");
    if (mapAdmin) mapAdmin.textContent = status.vacuum.map_name;
    if (mapUser) mapUser.textContent = status.vacuum.map_name;

    const curtainLevel = document.getElementById("curtainLevel");
    if (shouldUpdateInput(curtainLevel)) curtainLevel.value = String(status.curtains.position_percent);

    const lightPower = document.getElementById("lightPower");
    const lightLevel = document.getElementById("lightLevel");
    if (shouldUpdateInput(lightPower)) lightPower.value = String(status.lights.brightness);
    if (shouldUpdateInput(lightLevel)) lightLevel.value = String(status.lights.brightness);

    const lampR = document.getElementById("lampR");
    const lampG = document.getElementById("lampG");
    const lampB = document.getElementById("lampB");
    if (lampR && lampG && lampB) {
        const canUpdateRgb = shouldUpdateInput(lampR) && shouldUpdateInput(lampG) && shouldUpdateInput(lampB);
        if (canUpdateRgb) {
            lampR.value = String(status.lights.rgb.r);
            lampG.value = String(status.lights.rgb.g);
            lampB.value = String(status.lights.rgb.b);
            lampR.dispatchEvent(new Event("input"));
        }
    }

    const userLampR = document.getElementById("userLampR");
    const userLampG = document.getElementById("userLampG");
    const userLampB = document.getElementById("userLampB");
    if (userLampR && userLampG && userLampB) {
        const canUpdateUserRgb =
            shouldUpdateInput(userLampR) && shouldUpdateInput(userLampG) && shouldUpdateInput(userLampB);
        if (canUpdateUserRgb) {
            userLampR.value = String(status.lights.rgb.r);
            userLampG.value = String(status.lights.rgb.g);
            userLampB.value = String(status.lights.rgb.b);
            userLampR.dispatchEvent(new Event("input"));
        }
    }

    const userList = document.getElementById("userDeviceList");
    const adminList = document.getElementById("adminDeviceList");
    const removeSelect = document.getElementById("removeDeviceSelect");
    const listHtml = status.devices.map((d) => `<li>${d}</li>`).join("");
    if (userList) userList.innerHTML = listHtml;
    if (adminList) adminList.innerHTML = listHtml;
    if (removeSelect) {
        removeSelect.innerHTML = status.devices.map((d, i) => `<option value="${i}">${d}</option>`).join("");
    }
}

async function refreshStatus() {
    try {
        const data = await api("/api/status");
        renderStatus(data);
    } catch (error) {
        showMessage(`Ошибка статуса: ${error.message}`, true);
    }
}

function bindButton(id, handler) {
    const btn = document.getElementById(id);
    if (!btn) return;
    btn.addEventListener("click", async () => {
        try {
            await handler();
        } catch (error) {
            showMessage(error.message || "Неизвестная ошибка", true);
        }
    });
}

function setupActions() {
    bindButton("adminKettleOnBtn", async () => {
        const target = document.getElementById("kettleTemp");
        const data = await api("/api/kettle/on", {
            method: "POST",
            body: JSON.stringify({ target_temp: target ? Number(target.value) : 90 }),
        });
        clearDirty("kettleTemp");
        showMessage(data.message);
        refreshStatus();
    });
    bindButton("adminKettleOffBtn", async () => {
        const data = await api("/api/kettle/off", { method: "POST", body: "{}" });
        showMessage(data.message);
        refreshStatus();
    });
    bindButton("adminKettleTargetSaveBtn", async () => {
        const target = document.getElementById("kettleTemp");
        const data = await api("/api/kettle/target", {
            method: "POST",
            body: JSON.stringify({ target_temp: target ? Number(target.value) : 90 }),
        });
        clearDirty("kettleTemp");
        showMessage(data.message);
        refreshStatus();
    });
    bindButton("userKettleOnBtn", async () => {
        const data = await api("/api/kettle/on", { method: "POST", body: "{}" });
        showMessage(data.message);
        refreshStatus();
    });
    bindButton("userKettleOffBtn", async () => {
        const data = await api("/api/kettle/off", { method: "POST", body: "{}" });
        showMessage(data.message);
        refreshStatus();
    });

    bindButton("adminCurtainsOpenBtn", async () => {
        const level = document.getElementById("curtainLevel");
        const data = await api("/api/curtains/open", {
            method: "POST",
            body: JSON.stringify({ percent: level ? Number(level.value) : 100 }),
        });
        clearDirty("curtainLevel");
        showMessage(data.message);
        refreshStatus();
    });
    bindButton("adminCurtainsCloseBtn", async () => {
        const data = await api("/api/curtains/close", { method: "POST", body: "{}" });
        clearDirty("curtainLevel");
        showMessage(data.message);
        refreshStatus();
    });
    bindButton("adminCurtainsSaveBtn", async () => {
        const level = document.getElementById("curtainLevel");
        const data = await api("/api/curtains/set", {
            method: "POST",
            body: JSON.stringify({ percent: level ? Number(level.value) : 0 }),
        });
        clearDirty("curtainLevel");
        showMessage(data.message);
        refreshStatus();
    });
    bindButton("userCurtainsOpenBtn", async () => {
        const data = await api("/api/curtains/open", { method: "POST", body: JSON.stringify({ percent: 100 }) });
        showMessage(data.message);
        refreshStatus();
    });
    bindButton("userCurtainsCloseBtn", async () => {
        const data = await api("/api/curtains/close", { method: "POST", body: "{}" });
        showMessage(data.message);
        refreshStatus();
    });

    bindButton("adminLightsApplyBtn", async () => {
        const brightness = Number(document.getElementById("lightPower")?.value || 70);
        const r = Number(document.getElementById("lampR")?.value || 255);
        const g = Number(document.getElementById("lampG")?.value || 180);
        const b = Number(document.getElementById("lampB")?.value || 90);
        const data = await api("/api/lights/apply", {
            method: "POST",
            body: JSON.stringify({ brightness, r, g, b }),
        });
        showMessage(data.message);
        refreshStatus();
    });
    bindButton("adminLightsOnBtn", async () => {
        const data = await api("/api/lights/on", { method: "POST", body: "{}" });
        showMessage(data.message);
        refreshStatus();
    });
    bindButton("adminLightsOffBtn", async () => {
        const data = await api("/api/lights/off", { method: "POST", body: "{}" });
        showMessage(data.message);
        refreshStatus();
    });
    bindButton("userLightsApplyBtn", async () => {
        const brightness = Number(document.getElementById("lightLevel")?.value || 70);
        const r = Number(document.getElementById("userLampR")?.value || 255);
        const g = Number(document.getElementById("userLampG")?.value || 180);
        const b = Number(document.getElementById("userLampB")?.value || 90);
        const data = await api("/api/lights/apply", {
            method: "POST",
            body: JSON.stringify({ brightness, r, g, b }),
        });
        showMessage(data.message);
        refreshStatus();
    });

    bindButton("adminVacuumStartBtn", async () => {
        const data = await api("/api/vacuum/start", { method: "POST", body: "{}" });
        showMessage(data.message);
        refreshStatus();
    });
    bindButton("adminVacuumPauseBtn", async () => {
        const data = await api("/api/vacuum/pause", { method: "POST", body: "{}" });
        showMessage(data.message);
        refreshStatus();
    });
    bindButton("adminVacuumDockBtn", async () => {
        const data = await api("/api/vacuum/dock", { method: "POST", body: "{}" });
        showMessage(data.message);
        refreshStatus();
    });
    bindButton("userVacuumStartBtn", async () => {
        const data = await api("/api/vacuum/start", { method: "POST", body: "{}" });
        showMessage(data.message);
        refreshStatus();
    });
    bindButton("userVacuumPauseBtn", async () => {
        const data = await api("/api/vacuum/pause", { method: "POST", body: "{}" });
        showMessage(data.message);
        refreshStatus();
    });
    bindButton("userVacuumDockBtn", async () => {
        const data = await api("/api/vacuum/dock", { method: "POST", body: "{}" });
        showMessage(data.message);
        refreshStatus();
    });

    bindButton("uploadMapBtn", async () => {
        const fileInput = document.getElementById("mapFileInput");
        const file = fileInput && fileInput.files ? fileInput.files[0] : null;
        if (!file) {
            showMessage("Выберите файл карты", true);
            return;
        }
        const data = await api("/api/map/upload", {
            method: "POST",
            body: JSON.stringify({ map_name: file.name }),
        });
        showMessage(data.message);
        refreshStatus();
    });
    const viewMap = async () => {
        try {
            const data = await api("/api/map/view");
            showMessage(data.message);
        } catch (error) {
            showMessage(error.message, true);
        }
    };
    bindButton("viewMapBtn", viewMap);
    bindButton("viewMapBtnUser", viewMap);

    bindButton("addDeviceBtn", async () => {
        const input = document.getElementById("newDeviceName");
        const name = input ? input.value.trim() : "";
        if (!name) {
            showMessage("Введите имя устройства", true);
            return;
        }
        const data = await api("/api/devices/add", {
            method: "POST",
            body: JSON.stringify({ name }),
        });
        if (input) input.value = "";
        showMessage(data.message);
        refreshStatus();
    });
    bindButton("removeDeviceBtn", async () => {
        const select = document.getElementById("removeDeviceSelect");
        const index = select ? Number(select.value) : -1;
        const data = await api("/api/devices/remove", {
            method: "POST",
            body: JSON.stringify({ index }),
        });
        showMessage(data.message);
        refreshStatus();
    });

    bindButton("adminClimateApplyBtn", async () => {
        const t = Number(document.getElementById("homeTemp")?.value || 24);
        const h = Number(document.getElementById("homeHumidity")?.value || 50);
        const data = await api("/api/climate/apply", {
            method: "POST",
            body: JSON.stringify({ target_temperature: t, target_humidity: h }),
        });
        showMessage(data.message);
        refreshStatus();
    });

    bindButton("adminSceneSaveBtn", async () => {
        const name = document.getElementById("sceneName")?.value || "";
        const date = document.getElementById("sceneDate")?.value || "";
        const time = document.getElementById("sceneTime")?.value || "";
        const data = await api("/api/scene/save", {
            method: "POST",
            body: JSON.stringify({ name, date, time }),
        });
        showMessage(data.message);
        refreshStatus();
    });
}

document.addEventListener("DOMContentLoaded", () => {
    setupThemeToggle();
    setupSummaryToggles();
    setupRgbPreview("lampR", "lampG", "lampB", "lampColorPreview", "lampColorValue");
    setupRgbPreview("userLampR", "userLampG", "userLampB", "userLampColorPreview", "userLampColorValue");
    setInterval(updateDateTimeLocal, 1000);
    updateDateTimeLocal();
    setupActions();
    document
        .querySelectorAll(
            "#kettleTemp, #curtainLevel, #lightPower, #lightLevel, #lampR, #lampG, #lampB, #userLampR, #userLampG, #userLampB, #homeTemp, #homeHumidity"
        )
        .forEach((input) => input.addEventListener("input", markInputDirty));
    refreshStatus();
    setInterval(refreshStatus, 3000);
});
