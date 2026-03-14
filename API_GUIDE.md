# 📡 API Reference Guide

The Fraud Risk Engine exposes a high-performance REST API for inference and a WebSocket for real-time broadcasting.

## 🟢 Base URL
```text
http://localhost:8000
```

---

## 🛣️ Endpoints

### 1. Predict Risk
Performs real-time scoring of a financial transaction.

**Request:** `POST /predict`

**Payload Schema:**
| Field | Type | Description |
| :--- | :--- | :--- |
| `Time` | `float` | Seconds elapsed since the first transaction in the dataset. |
| `Amount` | `float` | Transaction value in USD. |
| `V1...V28` | `float` | PCA-transformed features from the source system. |
| `TransactionID` | `string` | (Optional) Unique reference ID. Defaults to "Unknown". |

**Example Request:**
```json
{
  "Time": 45.0,
  "Amount": 125.50,
  "V1": -1.359807,
  "V2": -0.072781,
  ...
  "V28": 0.013456,
  "TransactionID": "TXN-12345"
}
```

**Response Schema (`RiskScore`):**
```json
{
  "TransactionID": "TXN-12345",
  "IsFraud": 0,
  "FraudProbability": 0.12,
  "RiskLevel": "LOW"
}
```

---

### 2. Bank Webhook Ingestion
The primary endpoint for integrating with real-world payment gateways or bank notification systems.

**Request:** `POST /webhook/payment`

**Payload Schema (`BankTransaction`):**
| Field | Type | Description |
| :--- | :--- | :--- |
| `transaction_id` | `string` | Unique ID from the banking provider. |
| `user_id` | `string` | Internal or external customer identifier. |
| `amount` | `float` | Transaction value. |
| `currency` | `string` | ISO currency code (e.g., "USD"). |
| `timestamp` | `float` | Unix timestamp of the event. |
| `location` | `string` | Literal city/region name. |
| `merchant` | `string` | Name of the vendor. |

**Example Request:**
```json
{
  "transaction_id": "TXN12345",
  "user_id": "U1001",
  "amount": 2500,
  "currency": "USD",
  "timestamp": 1730000000,
  "location": "New York",
  "merchant": "Amazon"
}
```

**Functionality:**
- Automatically maps `timestamp` to model `Time`.
- Sets PCA features (`V1`-`V28`) to `0.0` (Neutral position).
- Broadcasts result to the dashboard instantly.

---

### 3. Live Broadcast (WebSockets)
Subscribes to all incoming transaction scores. Useful for dashboards and logging sinks.

**Request:** `WS /ws`

**Message Format:**
The API broadcasts a JSON string for every successful prediction.
```json
{
  "TransactionID": "TXN-12456",
  "Amount": 1250.00,
  "Time": 46.2,
  "IsFraud": 1,
  "FraudProbability": 0.98,
  "RiskLevel": "CRITICAL"
}
```

---

## ⚠️ Internal Risk Scaling
The `RiskLevel` field returned by the API is derived from the raw `FraudProbability` using the following logic:

| Risk Level | Probability Range | Action Recommendation |
| :--- | :--- | :--- |
| **SAFE/LOW** | 0.0 - 0.2 | Auto-approve. |
| **MEDIUM** | 0.2 - 0.5 | Flag for secondary review. |
| **HIGH** | 0.5 - 0.8 | Temporary hold / MFA required. |
| **CRITICAL** | 0.8 - 1.0 | Immediate block. |

---

## 🛠️ Errors
| Status Code | Meaning | Solution |
| :--- | :--- | :--- |
| `400` | Bad Request | Ensure all `V1`-`V28` fields are present. |
| `500` | Model Not Loaded | Ensure `uvicorn api:app` was run in a folder containing `.pkl` files. |
