# Slide 1: Title Slide
**Title:** Fintech Fraud Intelligence Platform
**Subtitle:** Real-Time AI Fraud Detection for Digital Payments
**Visual Suggestion:** A sleek, dark-themed background resembling the dashboard UI, featuring nodes connecting, representing digital payments and network security.

---

# Slide 2: The Problem
**Title:** The Challenge of Modern Digital Fraud
**Key Points:**
- **Speed:** Fraud happens in milliseconds; traditional batch-processing is too slow.
- **Complexity:** Fraudsters form organized rings, breaking transactions into micro-deposits or circular transfers to evade simple rules.
- **Black Box AI:** Standard ML models block transactions but don't explain *why* to human analysts.
**Visual Suggestion:** A graphic showing a fast-moving data stream with a "fraudulent" red packet slipping through traditional filters.

---

# Slide 3: Our Solution Architecture
**Title:** Multi-Layered Intelligence Pipeline
**Key Points:**
- **Transaction Stream:** Real-time ingestion via Webhooks, APIs, and batch processing.
- **Feature Engineering:** Instantly transforming raw data (time-bucketing, frequency mapping, dataset normalization).
- **ML Classifier:** Highly-optimized Random Forest model trained on the Kaggle Credit Card Fraud dataset.
- **Hybrid Scoring:** Combining ML probability with real-time behavioral and network graph analytics.
**Visual Suggestion:** A flowchart mirroring the `ARCHITECTURE.md` file:
`Data Source -> Normalization -> (ML + Behavioral + Graph) -> Hybrid Risk Score -> Dashboard`

---

# Slide 4: The Machine Learning Core
**Title:** Predictive Accuracy & Handling Imbalance
**Key Points:**
- **Dataset:** Kaggle Credit Card Fraud Dataset (highly anomalous/imbalanced data).
- **Techniques Used:** 
  - **SMOTE (Synthetic Minority Over-sampling Technique)** to train the model effectively on rare fraud events.
  - Scale engineering and logarithmic transformations for extreme transaction amounts.
- **Engine:** Sub-100ms inference time using optimized Python/Joblib.
**Visual Suggestion:** Two bar charts side-by-side or a confusion matrix showing how SMOTE balanced the fraud vs. normal transaction data.

---

# Slide 5: Key Innovation 1 - Explainable AI (XAI)
**Title:** Solving the "Black Box" Problem 
**Key Points:**
- Powered by **SHAP (SHapley Additive exPlanations)**.
- Every transaction block gets dissected to reveal the exact features that triggered the alert.
- Example: Analysts instantly see if fraud was flagged due to "Unusual Location," "Velocity Spike," or a specific engineered feature (e.g., V14 anomaly).
**Visual Suggestion:** A screenshot of the dashboard's "ML Risk Analysis" section showing the horizontal bar charts ranking risk factors.

---

# Slide 6: Key Innovation 2 - Behavioral & Graph Analytics
**Title:** Catching the Fraud Network, Not Just the Node
**Key Points:**
- **Behavioral Profiling:** Tracks user velocity, geolocation footprints, and spending habits over time. Catches Account Takeovers (ATO).
- **Graph Topology:** Analyzes the relationship between senders and receivers.
- **Detection Capabilities:** Successfully identifies Mule Accounts, Fan-out disbursements, and Circular Transfer rings in real-time.
**Visual Suggestion:** A screenshot or illustration of the glowing D3.js "Network Topology" map from your dashboard.

---

# Slide 7: The UI/UX Experience
**Title:** Premium Real-Time Analyst Dashboard
**Key Points:**
- Dark-mode, high-contrast interface designed for prolonged analyst monitoring.
- **Live WebSocket Data:** Stats, tables, and graphs update without page reloads.
- **Actionable Insights:** Interactive charts (Risk Distribution, Activity Timelines) and prioritized High-Risk Merchant lists.
**Visual Suggestion:** A high-quality, full-screen screenshot of the main Dashboard UI (pulse chart, live feed, stats).

---

# Slide 8: Impact & Scalability
**Title:** Built for the Enterprise
**Key Points:**
- **Scalable Backend:** FastAPI handles concurrent asynchronous requests with minimal overhead.
- **Persistent Intelligence:** SQLite database silently tracks user histories and graph edges across sessions.
- **Real-World Application:** Ready to deploy for payment processors, banks, and e-commerce platforms to automatically freeze transactions or alert human analysts.
**Visual Suggestion:** Icons representing scalability (cloud servers), speed (lightning bolt), and security (shield).

---

# Slide 9: Conclusion & Q&A
**Title:** Securing the Future of Digital Payments
**Key Points:**
- Recap: Fast, explainable, network-aware fraud intelligence.
- Thank You.
- Open for Questions.
**Visual Suggestion:** Your logo or project name bolded in the center, with your name/team name below.
