let alertHistory = [];
let totalAlerts = 0;
let recentRisks = [];

function initNotifications() {
    console.log("[Command Center] Initializing Intelligence HUD...");
    updateStatusUI(false);
    
    // Check if we are using localhost or a specific IP
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    let host = window.location.hostname;
    
    // In many local environments, hostname is empty when opened as a file
    if (!host || host === "" || host === "localhost") {
        host = "127.0.0.1"; // Default to 127.0.0.1 which uvicorn is explicitly bound to
    }
    
    const port = "8001";
    const wsUrl = `${protocol}//${host}:${port}/ws`;

    console.log("[Command Center] Attempting connection to sensor stream:", wsUrl);
    const ws = new WebSocket(wsUrl);

    ws.onopen = () => {
        console.log("[Command Center] Sensor stream LINK ESTABLISHED.");
        updateStatusUI(true);
    };

    ws.onmessage = (event) => {
        try {
            console.log("[Command Center] Packet received:", event.data.substring(0, 100) + "...");
            const data = JSON.parse(event.data);
            processIntelligence(data);
        } catch (e) {
            console.warn("[Command Center] Malformed packet ignored.", e);
        }
    };

    ws.onclose = () => {
        console.error("[Command Center] Sensor Link LOST. Re-engaging in 5s...");
        updateStatusUI(false);
        setTimeout(initNotifications, 5000);
    };

    ws.onerror = (err) => {
        console.error("[Command Center] Sensor Bus ERROR.", err);
    };
}

function updateStatusUI(connected) {
    const el = document.getElementById('sensor-status');
    if (!el) return;
    
    if (connected) {
        el.innerText = "Linked";
        el.className = "ws-status-badge connected";
    } else {
        el.innerText = "Searching...";
        el.className = "ws-status-badge disconnected";
    }
}

function processIntelligence(data) {
    const riskLevel = data.RiskLevel ? data.RiskLevel.toUpperCase() : "LOW";
    const isUnknown = (data.Sender && data.Sender.toLowerCase() === "unknown") || 
                      (data.Receiver && data.Receiver.toLowerCase() === "unknown");

    // Tracking for Threat Level calculation
    recentRisks.push(riskLevel);
    if (recentRisks.length > 20) recentRisks.shift();
    updateThreatLevelHUD();

    // Filtering for active alerts (CRITICAL, HIGH, UNKNOWN)
    if (riskLevel === "CRITICAL" || riskLevel === "HIGH" || isUnknown) {
        let type = riskLevel.toLowerCase();
        let title = "Risk Alert Detected";
        let message = `Surveillance detected suspicious ${data.Type || 'TX'} for ${data.Sender}.`;

        if (isUnknown) {
            type = "unknown";
            title = "Unknown Identity Alert";
            message = `Transaction involving unverified account detected: ${data.Sender} ➔ ${data.Receiver}.`;
        } else if (riskLevel === "CRITICAL") {
            title = "CRITICAL FRAUD BREACH";
        }

        triggerAlert(title, message, type, data);
    } 
    // Show MEDIUM risks in intelligence feed for awareness, but NO toasts
    else if (riskLevel === "MEDIUM") {
        addToIntelLog("ELEVATED ACTIVITY", `Potential anomaly detected for ${data.Sender}. Observation required.`, "medium", data);
    }
}

function triggerAlert(title, message, type, rawData) {
    addToIntelLog(title, message, type, rawData);
    showToast(title, message, type);
}

function addToIntelLog(title, message, type, rawData) {
    const timestamp = new Date().toLocaleTimeString('en-US', { hour12: false });
    totalAlerts++;
    
    const alertEntry = { title, message, type, time: timestamp, data: rawData };
    alertHistory.unshift(alertEntry);
    if (alertHistory.length > 100) alertHistory.pop();

    updateHUDStats();
    updateIntelFeed();
}

function updateHUDStats() {
    const badge = document.getElementById('intel-alert-count');
    if (badge) badge.innerText = totalAlerts;
}

function updateThreatLevelHUD() {
    const el = document.getElementById('hud-threat-level');
    if (!el) return;

    const criticalCount = recentRisks.filter(r => r === "CRITICAL").length;
    const highCount = recentRisks.filter(r => r === "HIGH").length;

    if (criticalCount > 2) {
        el.innerText = "CRITICAL";
        el.style.color = "#ef4444";
        el.className = "pulse-warn";
    } else if (highCount > 3 || criticalCount > 0) {
        el.innerText = "ELEVATED";
        el.style.color = "#f59e0b";
        el.className = "";
    } else {
        el.innerText = "LOW";
        el.style.color = "#10b981";
        el.className = "";
    }
}

function updateIntelFeed() {
    const feed = document.getElementById('intel-feed');
    if (!feed) return;

    feed.innerHTML = alertHistory.map(alert => `
        <div class="intel-entry ${alert.type}">
            <div class="intel-time"><i class="far fa-clock"></i> ${alert.time}</div>
            <div class="intel-label" style="color: ${getAlertColor(alert.type)}">${alert.title}</div>
            <div class="intel-content">${alert.message}</div>
            <div style="font-size: 0.65rem; color: #475569; margin-top: 5px; font-family: monospace;">
                TX_ID: ${alert.data.TransactionID || 'N/A'} | AMT: $${alert.data.Amount}
            </div>
        </div>
    `).join('');
}

function showToast(title, message, type) {
    const container = document.getElementById('notification-container');
    if (!container) return;

    const toast = document.createElement('div');
    toast.className = `toast ${type}`;
    
    const icon = type === 'critical' ? '<i class="fas fa-triangle-exclamation"></i>' : 
                 (type === 'high' ? '<i class="fas fa-bolt"></i>' : '<i class="fas fa-user-secret"></i>');

    toast.innerHTML = `
        <div class="toast-icon">${icon}</div>
        <div class="toast-content">
            <div class="toast-title">${title}</div>
            <div class="toast-msg">${message}</div>
        </div>
        <div class="toast-close" onclick="this.parentElement.remove()">×</div>
    `;

    container.appendChild(toast);

    setTimeout(() => {
        toast.classList.add('fade-out');
        setTimeout(() => toast.remove(), 400);
    }, 10000);
}

function getAlertColor(type) {
    if (type === 'critical') return '#ef4444';
    if (type === 'high') return '#f59e0b';
    if (type === 'medium') return '#94a3b8';
    return '#3b82f6';
}

document.addEventListener('DOMContentLoaded', initNotifications);
