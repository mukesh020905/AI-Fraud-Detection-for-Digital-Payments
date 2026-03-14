# 🏁 Getting Started

Follow this guide to set up the Fraud Risk Engine, launch the dashboard, and begin simulating live transaction traffic.

## 📋 Prerequisites
- **Python 3.10 or higher**
- A modern web browser (Chrome, Firefox, or Edge)
- (Internal) The `creditcard.csv` dataset must be in the root directory.

## 🛠️ Installation

1. **Clone the project** (or navigate to the directory).
2. **Install core dependencies:**
   ```powershell
   pip install pandas numpy scikit-learn imbalanced-learn fastapi uvicorn requests joblib
   ```

## 🚀 Running the System

You will need **three terminal windows** to see the full real-time effect.

### 1. Launch the API (Terminal 1)
This starts the Risk Engine and loads the pre-trained model.
```powershell
uvicorn api:app
```
> [!NOTE]
> Ensure you see "Fraud Risk Engine loaded successfully" in the logs before proceeding.

### 2. Launch the Dashboard
Navigate to the `dashboard/` directory and open `index.html` in your browser.
- **Verification:** The top right corner should say **"● Live connected"** in green.

### 3. Start the Simulation (Terminal 2)
This script reads historical data and pipes it into the API.
```powershell
python simulate_stream.py
```
*(You will immediately see transactions appearing in the dashboard table and the risk chart).*

---

## 🔄 Updating & Retraining
If you modify the feature engineering logic in `fraud_detection_model.py` or provide a new dataset:

1.  **Retrain:**
    ```powershell
    python fraud_detection_model.py
    ```
2.  **Restart API:**
    Stop Terminal 1 (`Ctrl+C`) and run `uvicorn api:app` again to load the fresh `.pkl` weight files.

---

## 🧪 Testing Endpoints Manually
You can test the API without the simulator using `curl` or PowerShell:

```powershell
Invoke-RestMethod -Method Post -Uri "http://localhost:8000/predict" -ContentType "application/json" -Body '{"Time":10,"V1":-1.35,"V2":-0.07,"V3":2.53,"V4":1.37,"V5":-0.33,"V6":0.46,"V7":0.23,"V8":0.09,"V9":0.36,"V10":0.09,"V11":-0.55,"V12":-0.61,"V13":0.99,"V14":-0.31,"V15":1.46,"V16":-0.47,"V17":0.20,"V18":0.02,"V19":0.40,"V20":0.25,"V21":-0.01,"V22":0.27,"V23":-0.11,"V24":0.06,"V25":0.12,"V26":-0.18,"V27":0.13,"V28":-0.02,"Amount":149.62}'
```
