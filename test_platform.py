import requests
import json
import time

API_BASE = "http://localhost:8000"

def test_webhook():
    print("Testing /webhook/payment...")
    payload = {
        "transaction_id": "WEB-123",
        "user_id": "U1005",
        "amount": 5000.0,
        "currency": "USD",
        "timestamp": time.time(),
        "location": "New York",
        "merchant": "Apple Store",
        "transaction_type": "debit"
    }
    resp = requests.post(f"{API_BASE}/webhook/payment", json=payload)
    print(f"Status: {resp.status_code}")
    if resp.status_code == 200:
        print(f"Result: {resp.json()['RiskLevel']} (Prob: {resp.json()['FraudProbability']:.2f})")

def test_email():
    print("\nTesting /transaction/email...")
    payload = {
        "subject": "Transaction Alert",
        "body": "You spent $250.00 at Amazon.",
        "sender_email": "user@example.com",
        "received_at": time.time()
    }
    resp = requests.post(f"{API_BASE}/transaction/email", json=payload)
    print(f"Status: {resp.status_code}")
    if resp.status_code == 200:
        print(f"Result: {resp.json()['RiskLevel']} (Amount parsed: {resp.json()['TransactionID']})")

def test_batch():
    print("\nTesting /transaction/batch...")
    payload = {
        "source": "PartnerBank",
        "transactions": [
            {
                "transaction_id": "BATCH-1",
                "user_id": "U999",
                "amount": 10.0,
                "currency": "USD",
                "timestamp": time.time(),
                "location": "London",
                "merchant": "Pub",
                "transaction_type": "debit"
            },
            {
                "transaction_id": "BATCH-2",
                "user_id": "U999",
                "amount": 9999.0,
                "currency": "USD",
                "timestamp": time.time(),
                "location": "Unknown",
                "merchant": "CryptoEx",
                "transaction_type": "debit"
            }
        ]
    }
    resp = requests.post(f"{API_BASE}/transaction/batch", json=payload)
    print(f"Status: {resp.status_code}")
    if resp.status_code == 200:
        print(f"Result: {resp.json()}")

if __name__ == "__main__":
    # Wait for API to be ready if needed
    test_webhook()
    test_email()
    test_batch()
