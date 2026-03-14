# 🏗️ System Architecture

This document provides a technical blueprint of the Fraud Risk Engine & Dashboard, detailing how components interact to provide real-time fraud detection.

## 🔄 High-Level Data Flow

**Core Solution Architecture Pipeline:**
`Transaction stream` ➜ `Feature engineering` ➜ `ML classifier` ➜ `Fraud scoring`

Building on this core pipeline, the system operates as a hybrid reactive pipeline. Data flows from sensors/simulators through parallel intelligence paths (ML + Behavioral) before being explained by SHAP and broadcast to the dashboard.

```mermaid
graph TD
    A[simulate_stream.py / Bank Webhook] -- JSON Payload --> B[api.py: FastAPI Engine]
    B -- Feature Analysis --> C{Random Forest Model}
    B -- Behavioral Analysis --> F[UserProfiler Engine]
    B -- Network Analysis --> N[NetworkAnalyzer Graph]
    C -- ML Probability --> G[Hybrid Scorer]
    F -- Anomaly Score --> G
    N -- Network Risk --> G
    G -- Final Risk Score --> H[SHAP Explainer]
    H -- Top Factors --> B
    B -- WebSocket Broadcast /ws --> D[dashboard/index.html]
    D -- Live Update --> E[D3.js Graph / Chart.js / Alerts / XAI Panel]
```

## 🏗️ Component Breakdown

### 1. Hybrid Intelligence Engine (`api.py`)
The central nervous system of the platform. It handles:
- **Normalization Layer**: Centralized mapper for Webhooks, Emails, and Streams.
- **ML Pathway**: Real-time inference using Random Forest + SHAP for feature-level explanations.
- **Behavioral Pathway**: Advanced `UserProfiler` with persistence (SQLite), tracking velocity, geography, and spending baselines.
- **Network Pathway**: `NetworkAnalyzer` builds persistent graph edges to detect cycles (rings) and mule hub surges.
- **Persistence Layer**: `DatabaseManager` ensures that user reputation and network relationships survive system restarts.
- **Real-Time Sink**: High-performance WebSocket management for zero-refresh UI updates.

### 2. Dashboard Analytics (`dashboard/`)
The frontend is a reactive surveillance suite:
- **Topology Monitor**: D3.js powered graph showing the live transaction network and high-risk clusters.
- **Risk Distribution**: Real-time pie-chart view of system-wide risk levels.
- **Activity Timeline**: Visualizes transaction volume surges and volatility.
- **XAI & Behavioral Panels**: Deep-dive sections showing AI reasoning and behavioral violation alerts.

### 3. Simulation & Ingestion Tools
- **`simulate_stream.py`**: High-fidelity transaction generator that mimics real-user behaviors and injects intentional anomalies.
- **Multi-Source Ready**: API supports direct ingestion from payment gateways (`/webhook/payment`) and email alerts (`/transaction/email`).

## 🛠️ Tech Stack Rationale

| Layer | Technology | Rationale |
| :--- | :--- | :--- |
| **Backend** | FastAPI | High performance, async I/O, and automated documentation. |
| **ML Model** | Random Forest | Effective for tabular data and supported by SHAP's fast `TreeExplainer`. |
| **Explainability** | SHAP | Gold standard for feature importance and prediction transparency. |
| **Behavioral** | In-Memory | High-speed profiling for low-latency scoring. |

## 📡 Sequence Diagram

```mermaid
sequenceDiagram
    participant S as Source (Webhook/Sim)
    participant A as API Engine
    participant M as ML & SHAP
    participant B as Behavior Engine
    participant D as Dashboard
    
    A->>D: WebSocket Connection Established
    loop For Each Transaction
        S->>A: POST /predict (Payload + Context)
        par Parallel Execution
            A->>M: Compute ML Prob & SHAP Values
            A->>B: Compute Behavioral Anomaly %
            A->>N: Compute Graph Network Risk
        end
        A->>A: Weighted Hybrid Score (50/30/20)
        A->>D: Real-time Broadcast (All Indicators)
        D->>D: Update Stats & Render Charts
    end
```
