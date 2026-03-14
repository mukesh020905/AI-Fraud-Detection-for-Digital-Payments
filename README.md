# 🛡️ Fraud Risk Engine & Real-Time Dashboard

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
# 🛡️ Fintech Fraud Intelligence Platform

An advanced, AI-powered financial fraud intelligence system capable of monitoring digital payment transactions in real time across multiple sources. This platform detects both individual fraud events and coordinated fraud networks using a multi-layered intelligence pipeline.

## 🌟 Key Features
- **Multi-Source Ingestion**: Unified endpoints for simulated streams, bank webhooks, email alerts, and batch processing.
- **Hybrid Risk Scoring**: 50% ML (Random Forest) + 30% Behavioral Analytics + 20% Graph Network Risk.
- **Behavioral Intelligence**: Real-time profiling of user velocity, geographic patterns, and spending anomalies.
- **Graph-Based Network Detection**: Identifies circular transfers, mule networks, and suspicious transaction clusters.
- **Explainable AI (XAI)**: SHAP-powered decomposition of ML decisions into human-readable risk factors.
- **Persistent Intelligence**: Historical data storage in SQLite for continuous profiling across sessions.
- **Real-Time Visualization**: High-performance dashboard with topology maps, risk distribution charts, and activity timelines.

## 🏗️ Multi-Layer Detection Pipeline
1. **Normalization Layer**: Maps heterogenous sources (Webhook, Email, Stream) to a common schema.
2. **Intelligence Layer**: Parallel analysis via ML Core, Behavioral Profile Engine, and Network Graph Analyzer.
3. **Scoring Layer**: Weighted fusion of all risk indicators into a final "Hybrid Risk Index".
4. **Explanation Layer**: Generates SHAP values to explain the top drivers behind the risk.
5. **Action Layer**: Instant broadcast to monitoring suites via low-latency WebSockets.

### Key Features
*   **⚡ Real-Time Inference:** FastAPI backend performing sub-100ms scoring.
*   **🧠 Beyond simple debit fraud detection, this engine now features a **dual-model strategy** capable of identifying suspicious incoming funds (credit fraud) and outgoing payments (debit fraud) in real-time.
*   **🏦 Bank Webhook Ingestion:** Production-ready `POST /webhook/payment` endpoint for real-world transaction streaming.
*   **🔍 Explainable AI (XAI):** Integrated **SHAP** to provide transparent, human-readable reasons for every fraud alert.
*   **📊 Live Dashboard:** Modern UI with risk highlighting, real-time feature importance charts, and behavioral monitor alerts.

- `threshold.pkl`: The 95th percentile value for high-value flags.
- `freq_map.pkl`: Dictionary of hourly transaction densities.

## 🔍 Explainable AI (XAI) with SHAP
The Fraud Risk Engine uses **SHAP (SHapley Additive exPlanations)** to solve the "Black Box" problem in machine learning.

- **How it works**: For every transaction, the system calculates the exact contribution of each feature (e.g., `Amount`, `V14`, `Hour`) to the final fraud probability.
- **Top Risk Factors**: The backend identifies features with the highest positive SHAP values—those most responsible for pushing a transaction into the "High Risk" category.
- **Visual Transparency**: The dashboard renders a real-time horizontal bar chart, allowing analysts to see exactly which indicators (like "Unusual location" or "High transaction amount") triggered the alert.

---

## 📂 Documentation Modules
Explore the technical depth of the system through these dedicated guides:

1.  **[Architecture Blueprint](ARCHITECTURE.md):** Deep dive into system design and data flow.
2.  **[Machine Learning Details](ML_DETAILS.md):** Feature engineering, SMOTE strategy, and model benchmarks.
3.  **[API Reference](API_GUIDE.md):** Schema definitions for `/predict`, **Bank Webhooks**, and WebSocket broadcasts.
4.  **[Getting Started](GETTING_STARTED.md):** Frictionless setup, deployment, and retraining guide.

---

## 🛠️ Quick Start (Local)

1. **Install Dependencies:**
   ```bash
   pip install fastapi uvicorn pandas scikit-learn imbalanced-learn joblib
   ```

2. **Launch the Engine:**
   ```bash
   uvicorn api:app
   ```

3. **Start Simulation:**
   ```mermaid
graph TD
    A[simulate_stream.py] -- HTTP POST /predict --> B[api.py: FastAPI Engine]
    B -- Feature Analysis --> C{Random Forest Model}
    B -- Behavioral Analysis --> F[UserProfiler Engine]
    C -- ML Probability --> G[Hybrid Scorer]
    F -- Anomaly Score --> G
    G -- Final Risk Score --> B
    B -- WebSocket Broadcast /ws --> D[dashboard/index.html]
    D -- Live Update --> E[Chart.js / Stats / Table / Behavioral Monitor]
```

4. **View Dashboard:**
   Open `dashboard/index.html` in your browser.

---

