// DOM Elements
const statusEl = document.getElementById('connection-status');
const totalTxEl = document.getElementById('total-tx');
const blockedTxEl = document.getElementById('blocked-tx');
const highRiskTxEl = document.getElementById('high-risk-tx');
const safeTxEl = document.getElementById('safe-tx');
const txBody = document.getElementById('tx-body');

const explanationCard = document.getElementById('explanation-card');
const behavioralCard = document.getElementById('behavioral-card');
const explanationText = document.getElementById('explanation-text');
const focusIdEl = document.getElementById('focus-id');
const userDetailsEl = document.getElementById('user-details');
const behavioralAlertsEl = document.getElementById('behavioral-alerts');
const hybridProgress = document.getElementById('hybrid-progress');
const hybridScoreText = document.getElementById('hybrid-score-text');

const creditCardEl = document.getElementById('credit-monitor-card');
const creditFocusIdEl = document.getElementById('credit-focus-id');
const creditAlertsListEl = document.getElementById('credit-alerts-list');
const creditDetailsEl = document.getElementById('credit-details');

const riskFilterEl = document.getElementById('risk-filter');
const pauseBtnEl = document.getElementById('pause-btn');

// Network Graph Variables
let simulation = null;
let svg = null;
let container = null;

// State
let stats = { total: 0, blocked: 0, high: 0, safe: 0 };
let distributionStats = { CRITICAL: 0, HIGH: 0, MEDIUM: 0, LOW: 0 };
let merchantRisks = new Map(); // merchant -> {count, totalRisk}
let regionalStats = new Map(); // location -> { count, totalRisk }
let timelineData = []; // {time, count}
let selectedTxId = null;
let txHistory = new Map(); // Store full data for selection drill-down
let shapChart = null;
let distChart = null;
let timelineChart = null;
let regionalChart = null;
let isFeedPaused = false;
let currentFilter = 'ALL';

// Event Listeners for new Controls
pauseBtnEl.addEventListener('click', () => {
    isFeedPaused = !isFeedPaused;
    if (isFeedPaused) {
        pauseBtnEl.textContent = '▶ Resume Feed';
        pauseBtnEl.classList.add('paused');
    } else {
        pauseBtnEl.textContent = '⏸ Pause Feed';
        pauseBtnEl.classList.remove('paused');
    }
});

riskFilterEl.addEventListener('change', (e) => {
    currentFilter = e.target.value;
    // Re-render the feed to apply the new filter to existing rows
    const allRows = txBody.querySelectorAll('tr');
    allRows.forEach(row => {
        // The classes are like 'row-SAFE', 'row-CRITICAL'
        const isCritical = row.classList.contains('row-CRITICAL');
        const isHigh = row.classList.contains('row-HIGH');
        
        let show = true;
        if (currentFilter === 'CRITICAL' && !isCritical) show = false;
        if (currentFilter === 'HIGH' && !(isCritical || isHigh)) show = false;
        
        row.style.display = show ? '' : 'none';
    });
});

// Risk Pulse Chart (Mini)
let riskChart = null;
try {
    const ctxRisk = document.getElementById('riskChart').getContext('2d');
    if (typeof Chart !== 'undefined') {
        riskChart = new Chart(ctxRisk, {
            type: 'line',
            data: {
                labels: Array(20).fill(''),
                datasets: [{
                    data: Array(20).fill(0),
                    borderColor: '#3b82f6',
                    borderWidth: 2,
                    pointRadius: 0,
                    fill: true,
                    backgroundColor: 'rgba(59, 130, 246, 0.1)',
                    tension: 0.4
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: { legend: { display: false } },
                scales: { 
                    x: { display: false }, 
                    y: { display: false, min: 0, max: 100 } 
                },
                animation: { duration: 0 }
            }
        });
    } else {
        console.warn("Chart.js not loaded. Skipping pulse chart.");
    }
} catch (e) {
    console.error("Error initializing Risk Pulse Chart:", e);
}

function updateStats(txData) {
    stats.total++;
    const level = txData.RiskLevel || 'LOW';
    distributionStats[level] = (distributionStats[level] || 0) + 1;

    if (txData.RiskLevel === 'CRITICAL') stats.blocked++;
    else if (txData.RiskLevel === 'HIGH' || txData.RiskLevel === 'MEDIUM') stats.high++;
    else stats.safe++;
    
    totalTxEl.textContent = stats.total.toLocaleString();
    blockedTxEl.textContent = stats.blocked.toLocaleString();
    highRiskTxEl.textContent = stats.high.toLocaleString();
    safeTxEl.textContent = stats.safe.toLocaleString();

    // Update Merchant Ranking
    const merchant = txData.merchant || 'Unknown';
    const current = merchantRisks.get(merchant) || { count: 0, totalRisk: 0 };
    current.count++;
    current.totalRisk += txData.FinalRiskScore;
    merchantRisks.set(merchant, current);

    // Update Regional Stats
    const loc = txData.location || 'Unknown';
    if (loc !== 'Unknown') {
        const currentLoc = regionalStats.get(loc) || { count: 0, totalRisk: 0 };
        currentLoc.count++;
        currentLoc.totalRisk += txData.FinalRiskScore;
        regionalStats.set(loc, currentLoc);
    }
}

function updateAnalyticsCharts() {
    updateDistributionChart();
    updateTimelineChart();
    renderMerchantRanking();
    updateRegionalChart();
}

function updatePulseChart(prob) {
    if (!riskChart) return;
    riskChart.data.datasets[0].data.push(prob * 100);
    riskChart.data.datasets[0].data.shift();
    riskChart.update('none'); 
}

function appendToFeed(txData) {
    const row = document.createElement('tr');
    row.id = `row-${txData.TransactionID}`;
    row.className = `new-row row-${txData.RiskLevel}`;
    
    // Check filter before attaching to DOM
    let show = true;
    if (currentFilter === 'CRITICAL' && txData.RiskLevel !== 'CRITICAL') show = false;
    if (currentFilter === 'HIGH' && (txData.RiskLevel !== 'CRITICAL' && txData.RiskLevel !== 'HIGH')) show = false;
    
    if (!show) {
        row.style.display = 'none';
    }
    
    const prob = (txData.FraudProbability * 100).toFixed(1);
    const timeStr = new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' });
    const amountStr = new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD' }).format(txData.Amount);
    const txType = txData.Type || 'DEBIT';
    const typeClass = txType === 'CREDIT' ? 'badge-credit' : 'badge-debit';
    const counterparty = txType === 'CREDIT' ? (txData.Sender || 'Unknown') : (txData.merchant || 'Global Network');
    
    row.innerHTML = `
        <td>${timeStr}</td>
        <td style="font-family: monospace; font-size: 0.75rem;">${txData.TransactionID}</td>
        <td><span class="status-badge ${typeClass}">${txType}</span></td>
        <td>${counterparty}</td>
        <td style="font-weight: 700;">${amountStr}</td>
        <td>${prob}%</td>
        <td><span class="status-badge status-${txData.RiskLevel}">${txData.RiskLevel}</span></td>
    `;
    
    row.addEventListener('click', () => selectTransaction(txData.TransactionID));
    
    txBody.prepend(row);
    if (txBody.children.length > 50) txBody.removeChild(txBody.lastChild);
}

function selectTransaction(txId) {
    // UI selection
    const oldRow = document.querySelector('tr.selected');
    if (oldRow) oldRow.classList.remove('selected');
    
    const newRow = document.getElementById(`row-${txId}`);
    if (newRow) newRow.classList.add('selected');
    
    selectedTxId = txId;
    const data = txHistory.get(txId);
    if (data) renderAnalysis(data);
}

function renderAnalysis(data) {
    const txType = data.Type || 'DEBIT';
    
    if (txType === 'CREDIT') {
        // Show Credit Panel, Hide Debit Panels
        explanationCard.style.display = 'none';
        behavioralCard.style.display = 'none';
        creditCardEl.style.display = 'block';
        
        creditFocusIdEl.textContent = data.TransactionID;
        
        // Render Credit Alerts
        const alerts = data.BehavioralAlerts || [];
        creditAlertsListEl.innerHTML = '';
        if (alerts.length === 0) {
            creditAlertsListEl.innerHTML = '<span class="status-badge status-SAFE">Legitimate Inbound</span>';
        } else {
            alerts.forEach(a => {
                const b = document.createElement('div');
                b.className = 'behavior-alert-badge';
                b.style.marginBottom = '0.5rem';
                b.textContent = `🚨 ${a.replace(/_/g, ' ')}`;
                creditAlertsListEl.appendChild(b);
            });
        }
        
        // Render Credit Details
        creditDetailsEl.innerHTML = `
            <div class="detail-item">
                <label>Sender Account</label>
                <span>${data.Sender || 'Unknown'}</span>
            </div>
            <div class="detail-item">
                <label>Receiver (Local)</label>
                <span>${data.Receiver || 'Unknown'}</span>
            </div>
            <div class="detail-item">
                <label>Hybrid Credit Risk</label>
                <span class="risk-text-${data.RiskLevel}">${(data.FinalRiskScore * 100).toFixed(1)}%</span>
            </div>
            <div class="detail-item">
                <label>Status</label>
                <span class="status-badge status-${data.RiskLevel}">${data.RiskLevel}</span>
            </div>
            <div class="detail-item" style="grid-column: span 2; border-top: 1px solid rgba(255,255,255,0.1); padding-top: 10px; margin-top: 10px;">
                <label>Network Connectivity Risk</label>
                <div class="progress-bar">
                    <div class="progress-fill" style="width: ${(data.NetworkScore || 0) * 100}%; background: ${(data.NetworkScore || 0) > 0.4 ? '#ef4444' : '#3498db'};"></div>
                </div>
                <span>${((data.NetworkScore || 0) * 100).toFixed(0)}% Cluster Alignment</span>
            </div>
        `;
        
    } else {
        // Show Debit Panels, Hide Credit Panel
        explanationCard.style.display = 'block';
        behavioralCard.style.display = 'block';
        creditCardEl.style.display = 'none';
        
        focusIdEl.textContent = data.TransactionID;
        
        // 1. ML Explanation
        const prob = (data.FraudProbability * 100).toFixed(1);
        const factors = data.TopRiskFactors.map(f => `<li>• ${f}</li>`).join('');
        
        explanationText.innerHTML = `
            <p>This transaction was flagged with a <strong>${prob}%</strong> ML probability.</p>
            <p><strong>Primary Drivers:</strong></p>
            <ul>${factors}</ul>
        `;
        
        renderShapChart(data.FeatureImportance);
        
        // 2. Behavioral Profile
        const alerts = data.BehavioralAlerts || [];
        behavioralAlertsEl.innerHTML = '';
        
        if (alerts.length === 0) {
            behavioralAlertsEl.innerHTML = '<span class="status-badge status-SAFE">Baseline Consistent</span>';
        } else {
            alerts.forEach(a => {
                const b = document.createElement('span');
                b.className = 'behavior-alert-badge';
                b.textContent = `⚠️ ${a.replace(/_/g, ' ')}`;
                behavioralAlertsEl.appendChild(b);
            });
        }
        
        const profile = data.UserProfileSummary;
        if (profile) {
            userDetailsEl.innerHTML = `
                <div class="detail-item">
                    <label>Avg Spending</label>
                    <span>$${profile.avg_amount}</span>
                </div>
                <div class="detail-item">
                    <label>Total History</label>
                    <span>${profile.total_txs} txs</span>
                </div>
                <div class="detail-item">
                    <label>Market Scope</label>
                    <span>${profile.unique_merchants} Merch</span>
                </div>
                <div class="detail-item">
                    <label>Geo Footprint</label>
                    <span>${profile.unique_locations} Loc</span>
                </div>
            `;
        }
        
        const hybridScore = (data.FinalRiskScore * 100).toFixed(1);
        hybridProgress.style.width = `${hybridScore}%`;
        hybridScoreText.textContent = `${hybridScore}%`;
    }
}

function renderShapChart(importance) {
    if (typeof Chart === 'undefined') return;
    const ctxShap = document.getElementById('shapChart').getContext('2d');
    const labels = Object.keys(importance);
    const data = Object.values(importance);
    
    try {
        if (shapChart) {
            shapChart.data.labels = labels;
            shapChart.data.datasets[0].data = data;
            shapChart.data.datasets[0].backgroundColor = data.map(v => v > 0 ? 'rgba(239, 68, 68, 0.6)' : 'rgba(59, 130, 246, 0.6)');
            shapChart.data.datasets[0].borderColor = data.map(v => v > 0 ? '#ef4444' : '#3b82f6');
            shapChart.update();
            return;
        }
        
        shapChart = new Chart(ctxShap, {
            type: 'bar',
            data: {
                labels: labels,
                datasets: [{
                    data: data,
                    backgroundColor: data.map(v => v > 0 ? 'rgba(239, 68, 68, 0.6)' : 'rgba(59, 130, 246, 0.6)'),
                    borderColor: data.map(v => v > 0 ? '#ef4444' : '#3b82f6'),
                    borderWidth: 1,
                    borderRadius: 4
                }]
            },
            options: {
                indexAxis: 'y',
                responsive: true,
                maintainAspectRatio: false,
                plugins: { legend: { display: false } },
                scales: {
                    x: { grid: { color: 'rgba(255, 255, 255, 0.05)' }, ticks: { color: '#64748b', font: { size: 10 } } },
                    y: { grid: { display: false }, ticks: { color: '#f8fafc', font: { size: 11 } } }
                }
            }
        });
    } catch (e) {
        console.error("Error rendering SHAP chart:", e);
    }
}

function initAnalyticsCharts() {
    if (typeof Chart === 'undefined') {
        console.warn("Chart.js not loaded. Analytics charts will be unavailable.");
        return;
    }
    
    try {
        // Distribution Chart (Pie)
        const ctxDist = document.getElementById('distributionChart').getContext('2d');
        distChart = new Chart(ctxDist, {
            type: 'doughnut',
            data: {
                labels: ['Low', 'Medium', 'High', 'Critical'],
                datasets: [{
                    data: [0, 0, 0, 0],
                    backgroundColor: ['#10b981', '#f59e0b', '#f97316', '#ef4444'],
                    borderWidth: 0,
                    hoverOffset: 4
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: { legend: { position: 'right', labels: { color: '#94a3b8', font: { size: 10 }, usePointStyle: true } } },
                cutout: '70%'
            }
        });

        // Timeline Chart (Bar)
        const ctxTime = document.getElementById('timelineChart').getContext('2d');
        timelineChart = new Chart(ctxTime, {
            type: 'bar',
            data: {
                labels: Array(15).fill(''),
                datasets: [{
                    label: 'Transactions',
                    data: Array(15).fill(0),
                    backgroundColor: 'rgba(59, 130, 246, 0.5)',
                    borderRadius: 4
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: { legend: { display: false } },
                scales: {
                    x: { display: false },
                    y: { grid: { color: 'rgba(255, 255, 255, 0.05)' }, ticks: { color: '#64748b', font: { size: 10 } } }
                }
            }
        });

        // Regional Chart (Horizontal Bar)
        const ctxRegion = document.getElementById('regionalChart').getContext('2d');
        regionalChart = new Chart(ctxRegion, {
            type: 'bar',
            data: {
                labels: [],
                datasets: [{
                    data: [],
                    backgroundColor: 'rgba(16, 185, 129, 0.6)',
                    borderColor: '#10b981',
                    borderWidth: 1,
                    borderRadius: 4
                }]
            },
            options: {
                indexAxis: 'y',
                responsive: true,
                maintainAspectRatio: false,
                plugins: { legend: { display: false } },
                scales: {
                    x: { grid: { color: 'rgba(255, 255, 255, 0.05)' }, ticks: { color: '#64748b', font: { size: 10 } } },
                    y: { grid: { display: false }, ticks: { color: '#f8fafc', font: { size: 11 } } }
                }
            }
        });
    } catch (e) {
        console.error("Error initializing analytics charts:", e);
    }
}

function updateDistributionChart() {
    if (!distChart || typeof Chart === 'undefined') return;
    try {
        distChart.data.datasets[0].data = [
            distributionStats.LOW,
            distributionStats.MEDIUM,
            distributionStats.HIGH,
            distributionStats.CRITICAL
        ];
        distChart.update('none');
    } catch (e) {
        console.error("Error updating Distribution Chart:", e);
    }
}

function updateTimelineChart() {
    if (!timelineChart || typeof Chart === 'undefined') return;
    try {
        // Simple windowed timeline (buckets of 5 seconds or just per tx for demo)
        timelineData.push(1);
        if (timelineData.length > 15) timelineData.shift();
        timelineChart.data.datasets[0].data = timelineData;
        timelineChart.update('none');
    } catch (e) {
        console.error("Error updating Timeline Chart:", e);
    }
}

function renderMerchantRanking() {
    const list = document.getElementById('merchant-ranking');
    const sorted = [...merchantRisks.entries()]
        .sort((a, b) => (b[1].totalRisk / b[1].count) - (a[1].totalRisk / a[1].count))
        .slice(0, 5);

    list.innerHTML = sorted.map(([name, data]) => {
        const avgRisk = (data.totalRisk / data.count).toFixed(2);
        const level = avgRisk > 0.7 ? 'CRITICAL' : (avgRisk > 0.4 ? 'HIGH' : 'SAFE');
        return `
            <div class="merchant-item">
                <span>${name} <small>(${data.count} tx)</small></span>
                <span class="risk-score risk-text-${level}">${(avgRisk * 100).toFixed(0)}%</span>
            </div>
        `;
    }).join('') || '<p class="placeholder-text">Scanning merchants...</p>';
}

function updateRegionalChart() {
    if (!regionalChart || typeof Chart === 'undefined') return;
    
    try {
        // Get top 5 locations by activity
        const sorted = [...regionalStats.entries()]
            .sort((a, b) => b[1].count - a[1].count)
            .slice(0, 5);
            
        const labels = sorted.map(item => item[0]);
        const data = sorted.map(item => item[1].count);
        
        // Color based on average risk in that region
        const bgColors = sorted.map(item => {
            const avgRisk = item[1].totalRisk / item[1].count;
            if (avgRisk > 0.5) return 'rgba(239, 68, 68, 0.6)'; // Critical/High
            if (avgRisk > 0.2) return 'rgba(245, 158, 11, 0.6)'; // Medium
            return 'rgba(16, 185, 129, 0.6)'; // Low
        });
        
        const borderColors = sorted.map(item => {
            const avgRisk = item[1].totalRisk / item[1].count;
            if (avgRisk > 0.5) return '#ef4444';
            if (avgRisk > 0.2) return '#f59e0b';
            return '#10b981';
        });

        regionalChart.data.labels = labels;
        regionalChart.data.datasets[0].data = data;
        regionalChart.data.datasets[0].backgroundColor = bgColors;
        regionalChart.data.datasets[0].borderColor = borderColors;
        regionalChart.update('none');
    } catch (e) {
        console.error("Error updating Regional Chart:", e);
    }
}

// --- D3.js Graph Functions ---
function initNetworkGraph() {
    if (typeof d3 === 'undefined') {
        console.warn("D3.js not loaded. Network topology will be unavailable.");
        return;
    }
    
    try {
        const svgEl = document.getElementById('network-graph');
        const width = svgEl.clientWidth || 600;
        const height = svgEl.clientHeight || 350;

        svg = d3.select("#network-graph")
            .attr("viewBox", [0, 0, width, height]);

        svg.selectAll("*").remove(); // Clear
        container = svg.append("g");

        // Zoom behavior
        svg.call(d3.zoom().on("zoom", (event) => {
            container.attr("transform", event.transform);
        }));

        simulation = d3.forceSimulation()
            .force("link", d3.forceLink().id(d => d.id).distance(60))
            .force("charge", d3.forceManyBody().strength(-150))
            .force("center", d3.forceCenter(width / 2, height / 2));

        // Global listeners set once to avoid memory leaks
        simulation.on("tick", () => {
            container.selectAll(".link")
                .attr("x1", d => d.source.x)
                .attr("y1", d => d.source.y)
                .attr("x2", d => d.source.x === d.target.x ? d.target.x + 1 : d.target.x) // prevent NaN
                .attr("y2", d => d.target.y);

            container.selectAll(".node")
                .attr("cx", d => d.x)
                .attr("cy", d => d.y);
        });
    } catch (e) {
        console.error("Error initializing Network Graph:", e);
    }
}

function updateNetworkGraph(graphData) {
    if (!simulation || !container || typeof d3 === 'undefined') return;

    try {
        // Use a simpler differential update or throttle
        const nodes = graphData.nodes;
        const links = graphData.links;

        // Update Links
        const link = container.selectAll(".link")
            .data(links, d => {
                // D3 mutates source/target into objects. We must ensure we use IDs for the key.
                const s = typeof d.source === 'object' ? d.source.id : d.source;
                const r = typeof d.target === 'object' ? d.target.id : d.target;
                return `${s}-${r}`;
            })
            .join("line")
            .attr("class", "link");

        // Update Nodes
        const node = container.selectAll(".node")
            .data(nodes, d => d.id)
            .join("circle")
            .attr("class", d => `node ${d.type} ${d.is_suspicious ? 'suspicious' : ''}`)
            .attr("r", d => d.type === 'account' ? 8 : 6)
            .attr("fill", d => {
                if (d.is_suspicious) return "#ef4444";
                return d.type === 'account' ? "#3b82f6" : "#10b981";
            });

        node.select("title").remove(); // Prevent double titles
        node.append("title").text(d => d.id);

        // Only restart if nodes/links changed significantly
        simulation.nodes(nodes);
        simulation.force("link").links(links);
        simulation.alpha(0.3).restart(); // Lower alpha for smoother updates
    } catch (e) {
        console.error("Error updating Network Graph:", e);
    }
}

function connect() {
    let host = window.location.hostname;
    let port = "8001"; // Target 8001 for the API logic
    
    // Fallback for local files or missing host
    if (!host || host === "" || host === "127.0.0.1") host = "localhost";

    // If the dashboard IS served from port 8000 (e.g. /static/index.html), 
    // then 'window.location.port' will be 8000, which is correct.
    // If it's served from 5500 (Live Server), we MUST override to 8000.
    if (window.location.port && window.location.port === "8001") {
        port = "8001";
    }

    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const wsUrl = `${protocol}//${host}:${port}/ws`;
    
    console.log("Connecting to Fraud Engine WebSocket:", wsUrl);
    const ws = new WebSocket(wsUrl);
    
    ws.onopen = () => {
        console.log("WebSocket Connected");
        statusEl.textContent = 'SYSTEM LIVE';
        statusEl.classList.add('connected');
    };
    
    ws.onmessage = (event) => {
        console.log("WS Data Received Row Count:", event.data.length);
        
        // Ignore plain text handshakes or ping/pong noise
        if (typeof event.data !== 'string' || !event.data.trim().startsWith('{')) {
            if (event.data !== 'connected') console.log("WS Meta Info:", event.data);
            return;
        }

        try {
            const data = JSON.parse(event.data);
            console.log("Parsed Transaction:", data.TransactionID, "Risk:", data.RiskLevel);
            
            // Critical check: Ensure IDs exist
            if (!data.TransactionID) {
                console.warn("Received data without TransactionID:", data);
                return;
            }

            // Always update background stats and memory even if paused
            txHistory.set(data.TransactionID, data);
            updateStats(data);
            
            if (isFeedPaused) return; // Stop UI updates if paused
            
            updatePulseChart(data.FraudProbability || 0);
            appendToFeed(data);
            updateAnalyticsCharts();
            
            // Auto-focus logic: Focus the very FIRST item, then only focus CRITICAL ones
            if (!selectedTxId) {
                selectTransaction(data.TransactionID);
            } else if (data.RiskLevel === 'CRITICAL') {
                selectTransaction(data.TransactionID);
            }

            // Update Graph
            if (data.GraphData) {
                updateNetworkGraph(data.GraphData);
            }
        } catch(e) {
            console.error("Dashboard Processing Error:", e);
            console.debug("Raw data causing error:", event.data);
        }
    };
    
    ws.onerror = (err) => {
        console.error("WS Error", err);
        statusEl.textContent = 'WS CONNECTION ERROR';
        statusEl.classList.remove('connected');
    };
    
    ws.onclose = () => {
        statusEl.textContent = 'ENGINE OFFLINE - RECONNECTING';
        statusEl.classList.remove('connected');
        setTimeout(connect, 3000);
    };
}

// CSV Upload logic removed as part of feature decommissioning.

window.addEventListener('DOMContentLoaded', () => {
    initNetworkGraph();
    initAnalyticsCharts();
    connect();
});
