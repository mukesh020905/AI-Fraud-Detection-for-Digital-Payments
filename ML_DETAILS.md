# 🧠 Machine Learning Intelligence

This document details the data science and engineering effort behind the Fraud Risk Engine.

## 📊 Dataset: Credit Card Fraud (Kaggle)
The model is trained on the [Credit Card Fraud Detection](https://www.kaggle.com/datasets/mlg-ulb/creditcardfraud) dataset.
- **Observations:** ~284,807 transactions.
- **Base Imbalance:** Only 492 transactions are fraudulent (**0.172%**).
- **Features:** 28 PCA-transformed features (`V1`-`V28`), `Time`, and `Amount`.

## 🛠️ Feature Engineering Strategy
Standard features aren't enough for high-fidelity detection. We engineered four primary proxies for fraud behavior:

1.  **Log_Amount:** Financial amounts follow a power-law distribution. Log scaling stabilizes the variance of `Amount`.
2.  **Time Buckets:** Transitions are categorized into `morning`, `afternoon`, and `night`. Fraudulent activity often peaks during specific low-traffic windows.
3.  **Hourly Frequency:** Since we lack `UserID`, we use the density of transactions per hour as a proxy for network load. Anomalous spikes in frequency often correlate with bot attacks.
4.  **Is_High_Value:** A binary flag for transactions above the **95th percentile** of historic spending ($256.89 in this dataset).

## ⚖️ Handling Class Imbalance (SMOTE)
Training on a dataset where 99.8% of labels are "Safe" leads to a model that predicts "Safe" for everything. We solve this using **SMOTE (Synthetic Minority Over-sampling Technique)**.

- **Process:** Instead of just duplicating fraud cases, SMOTE creates synthetic "neighbors" in the feature space.
- **Impact:** Increases the model's sensitivity (Recall) to fraud without crippling precision.

## 🔍 Explainable AI (XAI) Implementation
We integrated **SHAP (SHapley Additive exPlanations)** to provide transparency for the Random Forest model.

### 🌲 SHAP TreeExplainer
Since we are using a Random Forest ensemble, we utilize the `shap.TreeExplainer`, which is optimized for tree-based models and provides fast, exact SHAP values.

### 🧮 Computation Logic
1. **Normalization**: Incoming data is scaled using the same `scaler.pkl` used in training.
2. **Value Calculation**: The explainer computes domestic SHAP values for the `Fraud` (class 1) prediction.
3. **Extraction**:
   - **TopRiskFactors**: The top 3 features with the highest *positive* contribution.
   - **FeatureImportance**: The raw contribution values for the top 5 absolute contributors.

### 📡 Data Flow
The computed SHAP values are included in the `/predict` JSON response and broadcast to the dashboard via WebSockets, enabling real-time visualization of "Why this transaction is suspicious."

## 🏆 Model Benchmarking
During development, we evaluated three architectures. The **Random Forest** was selected due to its superior F1-Score (balance of Precision and Recall).

| Metric | Logistic Regression | **Random Forest** | Gradient Boosting |
| :--- | :--- | :--- | :--- |
| **Precision** | 0.05 | **0.95** | 0.82 |
| **Recall** | 0.92 | **0.84** | 0.81 |
| **F1-Score** | 0.10 | **0.89** | 0.82 |
| **ROC-AUC** | 0.98 | **0.96** | 0.97 |

> [!IMPORTANT]
> While Logistic Regression has high Recall, its Precision is too low for a production system, as it would flag too many false positives. Random Forest provides the most stable production experience.

## 📦 Persistence & Serialization
The model pipeline is serialized into five distinct assets used by the API:
- `best_fraud_model.pkl`: The trained Random Forest classifier.
- `scaler.pkl`: StandardScaler fit on the training distribution.
- `scale_cols.pkl`: Explicit list of numerical columns to be scaled.
- `threshold.pkl`: The 95th percentile value for high-value flags.
- `freq_map.pkl`: Dictionary of hourly transaction densities.
