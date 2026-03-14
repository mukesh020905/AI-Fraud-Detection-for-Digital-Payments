import pandas as pd
import requests
import time
import json
import random

API_URL = "http://localhost:8001/predict"
DATA_FILE = "creditcard.csv"

# Additional context for Behavioral AI
USERS = ["U1001", "U1002", "U1003", "U1004", "U1005"]
MERCHANTS = ["Amazon", "Flipkart", "Zomato", "Uber", "Apple Store", "Shell Gas"]
LOCATIONS = ["New York", "Mumbai", "London", "San Francisco", "Bangalore"]

def simulate_traffic():
    print(f"Loading {DATA_FILE} for simulation...")
    try:
        # Load a chunk of data, perhaps mostly normal with a few frauds
        # Load a manageable chunk of data (e.g., first 50,000 rows)
        df = pd.read_csv(DATA_FILE, nrows=50000)
        
        # To make simulation interesting, let's artificially increase fraud density slightly
        df_fraud = df[df['Class'] == 1].sample(frac=1) # Shuffle frauds
        df_normal = df[df['Class'] == 0].sample(n=len(df_fraud) * 10) # 10:1 ratio for sim
        
        sim_df = pd.concat([df_normal, df_fraud]).sample(frac=1).reset_index(drop=True)
        print(f"Simulation dataset ready with {len(sim_df)} transactions.")
        
        for index, row in sim_df.iterrows():
            # Randomly decide if it's a debit or credit (80% debit, 20% credit)
            is_credit = random.random() < 0.2
            tx_type = "credit" if is_credit else "debit"
            
            # Prepare payload matching Transaction schema
            payload = row.drop('Class').to_dict()
            payload['TransactionID'] = f"TXN-{int(time.time() * 1000)}-{index}"
            payload['transaction_type'] = tx_type
            
            # Behavioral Context
            user_id = random.choice(USERS)
            payload['user_id'] = user_id
            payload['merchant'] = random.choice(MERCHANTS)
            payload['location'] = random.choice(LOCATIONS)
            
            if tx_type == "credit":
                payload['sender_account'] = random.choice(["Unknown", "ACCT-4531", "ACCT-9921", "ACCT-1082"])
                payload['receiver_account'] = f"LOCAL-{user_id}"
                
                # Inject Credit Anomaly: Multiple micro deposits
                if random.random() < 0.05:
                    print(f"!!! Injecting MICRO-DEPOSIT anomaly for {user_id} !!!")
                    for i in range(4):
                        micro_payload = payload.copy()
                        micro_payload['TransactionID'] = f"{payload['TransactionID']}-M{i}"
                        micro_payload['Amount'] = random.uniform(5, 45)
                        try: requests.post(API_URL, json=micro_payload)
                        except: pass

                # Inject Fraud Ring: Circular Transfer (A -> B -> C -> A)
                if random.random() < 0.03:
                    print(f"!!! Injecting CIRCULAR TRANSFER pattern starting with {user_id} !!!")
                    # A -> B
                    target_b = "ACCT-" + str(random.randint(2000, 3000))
                    payload['receiver_account'] = target_b
                    try: requests.post(API_URL, json=payload)
                    except: pass
                    # B -> C
                    target_c = "ACCT-" + str(random.randint(3001, 4000))
                    p2 = payload.copy()
                    p2['sender_account'] = target_b
                    p2['receiver_account'] = target_c
                    p2['TransactionID'] = f"RING-B-{int(time.time()*1000)}"
                    try: requests.post(API_URL, json=p2)
                    except: pass
                    # C -> A
                    p3 = payload.copy()
                    p3['sender_account'] = target_c
                    p3['receiver_account'] = payload['sender_account']
                    p3['TransactionID'] = f"RING-C-{int(time.time()*1000)}"
                    try: requests.post(API_URL, json=p3)
                    except: pass

                # Inject Mule Network: Multiple accounts sending to one "hub"
                if random.random() < 0.03:
                    hub_acct = "HUB-" + str(random.randint(5000, 6000))
                    print(f"!!! Injecting MULE NETWORK surge towards hub {hub_acct} !!!")
                    for i in range(6):
                        mule_p = payload.copy()
                        mule_p['sender_account'] = f"MULE-{random.randint(7000, 8000)}"
                        mule_p['receiver_account'] = hub_acct
                        mule_p['TransactionID'] = f"MULE-{i}-{int(time.time()*1000)}"
                        try: requests.post(API_URL, json=mule_p)
                        except: pass
            else:
                payload['sender_account'] = f"LOCAL-{user_id}"
                payload['receiver_account'] = random.choice(MERCHANTS)

            # Occasionally inject behavioral anomaly (Huge amount)
            if random.random() < 0.05:
                payload['Amount'] = payload['Amount'] * 20
                print(f"!!! Injected intentional behavioral anomaly for {payload['user_id']} !!!")

            try:
                response = requests.post(API_URL, json=payload)
                if response.status_code == 200:
                    result = response.json()
                    status = f"[{result['RiskLevel']}]"
                    if result['BehavioralAlerts']:
                        status += f" ALERTS: {','.join(result['BehavioralAlerts'])}"
                    
                    print(f"[{tx_type.upper()}] {status} TXN: {result['TransactionID']} | Hybrid: {result['FinalRiskScore']:.4f}")
                else:
                    print(f"Error {response.status_code}: {response.text}")
            except requests.exceptions.ConnectionError:
                print("Failed to connect to API. Is it running?")
                time.sleep(5)
            
            # Simulate real-time delay (Speed increased 10x: 0.05 to 0.2 seconds)
            time.sleep(random.uniform(0.05, 0.2))
            
    except FileNotFoundError:
        print(f"Error: {DATA_FILE} not found.")

if __name__ == "__main__":
    simulate_traffic()
