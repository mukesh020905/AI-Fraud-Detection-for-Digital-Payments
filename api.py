import os
import json
import asyncio
import time
import sqlite3
import traceback
import pandas as pd
import numpy as np
import joblib
import shap
from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect, UploadFile, File
from fastapi.encoders import jsonable_encoder
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, RedirectResponse
import math
import numpy as np

def sanitize_for_json(obj):
    """Recursively replace NaN and Infinity with None to ensure valid JSON."""
    if isinstance(obj, float) or isinstance(obj, np.floating):
        if np.isnan(obj) or np.isinf(obj):
            return None
        return float(obj)
    elif isinstance(obj, np.integer):
        return int(obj)
    elif isinstance(obj, np.ndarray):
        return sanitize_for_json(obj.tolist())
    elif isinstance(obj, dict):
        return {k: sanitize_for_json(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [sanitize_for_json(v) for v in obj]
    return obj
from pydantic import BaseModel
from typing import List, Dict, Optional, Set
from collections import defaultdict, deque

app = FastAPI(title="Fraud Risk Engine API")

# Allow all CORS for the dashboard
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global variables for model and metadata
model = None
scaler = None
scale_cols = None
threshold = None
freq_map = None

# Static hosting removed from here (moved to bottom)

# Input Data Schema
class Transaction(BaseModel):
    Time: float
    V1: float
    V2: float
    V3: float
    V4: float
    V5: float
    V6: float
    V7: float
    V8: float
    V9: float
    V10: float
    V11: float
    V12: float
    V13: float
    V14: float
    V15: float
    V16: float
    V17: float
    V18: float
    V19: float
    V20: float
    V21: float
    V22: float
    V23: float
    V24: float
    V25: float
    V26: float
    V27: float
    V28: float
    Amount: float
    TransactionID: str = "Unknown"
    transaction_type: str = "debit" # Must be "debit" or "credit"
    sender_account: Optional[str] = "Unknown"
    receiver_account: Optional[str] = "Unknown"
    user_id: str = "DefaultUser"
    merchant: str = "Unknown"
    location: str = "Unknown"


# Bank Webhook Schema
class BankTransaction(BaseModel):
    transaction_id: str
    user_id: str
    amount: float
    currency: str
    timestamp: float
    location: str
    merchant: str
    transaction_type: str = "debit" # "debit" or "credit"
    sender_account: Optional[str] = "Unknown"
    receiver_account: Optional[str] = "Unknown"

# Email Transaction Schema
class EmailTransaction(BaseModel):
    subject: str
    body: str
    sender_email: str
    received_at: float

# Batch Transaction Schema
class BatchTransaction(BaseModel):
    source: str
    transactions: List[BankTransaction]


# Output Schema
class RiskScore(BaseModel):
    TransactionID: str
    IsFraud: int
    FraudProbability: float
    RiskLevel: str
    TopRiskFactors: List[str] = []
    FeatureImportance: Dict[str, float] = {}
    BehavioralProbability: float = 0.0
    BehavioralAlerts: List[str] = []
    FinalRiskScore: float = 0.0
    UserProfileSummary: Optional[Dict] = None

# Active websocket connections
class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        self.active_connections.remove(websocket)

    async def broadcast(self, message_obj):
        if not self.active_connections:
            return
        
        # Sanitize data for JSON (handle NaN/Inf)
        sanitized_data = sanitize_for_json(message_obj)
        message_str = json.dumps(jsonable_encoder(sanitized_data))
        
        print(f"Broadcasting to {len(self.active_connections)} clients...")
        for connection in self.active_connections:
            try:
                await connection.send_text(message_str)
            except Exception as e:
                print(f"Broadcast Error: {e}")

manager = ConnectionManager()

# Database Manager for Forensics and Persistence
class DatabaseManager:
    def __init__(self, db_path="transactions.db"):
        self.db_path = db_path
        self._init_db()

    def _init_db(self):
        with sqlite3.connect(self.db_path) as conn:
            # Transactions table
            conn.execute("""
                CREATE TABLE IF NOT EXISTS transactions (
                    id TEXT PRIMARY KEY,
                    user_id TEXT,
                    time REAL,
                    amount REAL,
                    type TEXT,
                    sender TEXT,
                    receiver TEXT,
                    risk_score REAL,
                    risk_level TEXT,
                    is_fraud INTEGER,
                    ml_prob REAL,
                    behavioral_prob REAL,
                    alerts TEXT,
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            """)
            # User Profiles table
            conn.execute("""
                CREATE TABLE IF NOT EXISTS user_profiles (
                    user_id TEXT PRIMARY KEY,
                    profile_json TEXT,
                    last_updated DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            """)
            # Network Edges table
            conn.execute("""
                CREATE TABLE IF NOT EXISTS network_edges (
                    sender TEXT,
                    receiver TEXT,
                    weight INTEGER,
                    last_seen DATETIME DEFAULT CURRENT_TIMESTAMP,
                    PRIMARY KEY (sender, receiver)
                )
            """)

    def save_transaction(self, tx_data: Dict):
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute("""
                    INSERT OR REPLACE INTO transactions (
                        id, user_id, time, amount, type, sender, receiver, 
                        risk_score, risk_level, is_fraud, ml_prob, behavioral_prob, alerts
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    tx_data["TransactionID"],
                    tx_data.get("user_id", "DefaultUser"),
                    tx_data["Time"],
                    tx_data["Amount"],
                    tx_data["Type"],
                    tx_data["Sender"],
                    tx_data["Receiver"],
                    tx_data["FinalRiskScore"],
                    tx_data["RiskLevel"],
                    tx_data["IsFraud"],
                    tx_data["FraudProbability"],
                    tx_data["BehavioralProbability"],
                    ",".join(tx_data["BehavioralAlerts"])
                ))
                conn.commit() # Explicit commit
        except Exception as e:
            print(f"DB Error (save_transaction): {e}")

    def save_profile(self, user_id: str, profile_data: Dict):
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute("""
                    INSERT OR REPLACE INTO user_profiles (user_id, profile_json, last_updated)
                    VALUES (?, ?, CURRENT_TIMESTAMP)
                """, (user_id, json.dumps(profile_data)))
        except Exception as e:
            print(f"DB Error (save_profile): {e}")

    def load_profiles(self) -> Dict[str, Dict]:
        profiles = {}
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.execute("SELECT user_id, profile_json FROM user_profiles")
                for row in cursor:
                    profiles[row[0]] = json.loads(row[1])
                    # Re-hydrate sets from lists
                    p = profiles[row[0]]
                    p["usual_hours"] = set(p.get("usual_hours", []))
                    p["merchants"] = set(p.get("merchants", []))
                    p["locations"] = set(p.get("locations", []))
        except Exception as e:
            print(f"DB Error (load_profiles): {e}")
        return profiles

    def save_edge(self, sender: str, receiver: str, weight: int):
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute("""
                    INSERT OR REPLACE INTO network_edges (sender, receiver, weight, last_seen)
                    VALUES (?, ?, ?, CURRENT_TIMESTAMP)
                """, (sender, receiver, weight))
        except Exception as e:
            print(f"DB Error (save_edge): {e}")

    def load_network(self) -> List[tuple]:
        edges = []
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.execute("SELECT sender, receiver, weight FROM network_edges")
                edges = cursor.fetchall()
        except Exception as e:
            print(f"DB Error (load_network): {e}")
        return edges

db_manager = DatabaseManager()

# Behavioral Profiling Engine
class UserProfiler:
    def __init__(self, db=None):
        self.db = db
        self.profiles = self.db.load_profiles() if self.db else {}

    def get_profile(self, user_id: str):
        if user_id not in self.profiles:
            # Initialize default profile
            self.profiles[user_id] = {
                "avg_amount": 0.0,
                "tx_count": 0,
                "usual_hours": set(),
                "merchants": set(),
                "locations": set(),
                "recent_timestamps": [], 
                "credit_history": [], # [(amount, timestamp)]
                "sender_reputation": {}, # sender_account -> tx_count
                "last_credit_time": 0.0,
                "geo_footprint": {} # location -> count
            }
        return self.profiles[user_id]

    def update_profile(self, user_id: str, amount: float, hour: int, merchant: str, location: str, tx_type: str = "debit", sender: str = "Unknown"):
        p = self.get_profile(user_id)
        current_time = time.time()
        
        if tx_type == "credit":
            p["credit_history"].append((amount, current_time))
            if len(p["credit_history"]) > 50: p["credit_history"].pop(0)
            p["last_credit_time"] = current_time
            p["sender_reputation"][sender] = p["sender_reputation"].get(sender, 0) + 1
        else:
            p["recent_timestamps"].append(current_time)
            # Keep only timestamps from last 10 minutes
            p["recent_timestamps"] = [ts for ts in p["recent_timestamps"] if current_time - ts < 600]
        
        # Moving average
        p["avg_amount"] = (p["avg_amount"] * p["tx_count"] + amount) / (p["tx_count"] + 1)
        p["tx_count"] += 1
        p["usual_hours"].add(hour)
        p["merchants"].add(merchant)
        p["locations"].add(location)
        p["geo_footprint"][location] = p["geo_footprint"].get(location, 0) + 1

        # Persistence: save update to DB (async/background ideally, but here we trigger via predict)
        if self.db:
            # Convert sets to lists for JSON
            db_p = p.copy()
            db_p["usual_hours"] = list(p["usual_hours"])
            db_p["merchants"] = list(p["merchants"])
            db_p["locations"] = list(p["locations"])
            asyncio.create_task(asyncio.to_thread(self.db.save_profile, user_id, db_p))

    def compute_anomaly_score(self, user_id: str, amount: float, hour: int, merchant: str, location: str) -> Dict:
        p = self.get_profile(user_id)
        current_time = time.time()
        
        if p["tx_count"] < 3: # Need some history
            return {"score": 0.0, "alerts": []}

        alerts = []
        score = 0.0

        # 1. Amount Deviation
        if p["avg_amount"] > 0:
            deviation = amount / p["avg_amount"]
            if deviation > 4.0:
                alerts.append("SEVERE_SPENDING_DEVIATION")
                score += 0.4
            elif deviation > 2.5:
                alerts.append("UNUSUAL_SPENDING_SPIKE")
                score += 0.2

        # 2. Time Anomaly
        if hour not in p["usual_hours"] and p["tx_count"] > 10:
            alerts.append("OUT_OF_HOURS_ACTIVITY")
            score += 0.2

        # 3. Frequency Spike
        recent_txs = [ts for ts in p["recent_timestamps"] if current_time - ts < 600]
        if len(recent_txs) >= 8:
            alerts.append("VELOCITY_ATTACK_PATTERN")
            score += 0.4
        elif len(recent_txs) >= 5:
            alerts.append("HIGH_FREQUENCY_BURST")
            score += 0.2

        # 4. Rapid Withdrawal After Credit (Mule Pattern)
        if p["last_credit_time"] > 0 and (current_time - p["last_credit_time"] < 300):
            recent_credits = [c for c in p["credit_history"] if current_time - c[1] < 300]
            if recent_credits:
                alerts.append("RAPID_FUNDS_DISBURSEMENT")
                score += 0.4

        # 5. Geolocation Anomaly
        if location not in p["locations"] and p["tx_count"] > 15:
            alerts.append("NEW_GEOGRAPHIC_LOCATION")
            score += 0.2

        return {"score": min(1.0, score), "alerts": alerts}

    def compute_credit_anomaly_score(self, user_id: str, amount: float, sender: str) -> Dict:
        p = self.get_profile(user_id)
        current_time = time.time()
        alerts = []
        score = 0.0

        # 1. Sudden Large Incoming Transfer
        avg_credit = sum([x[0] for x in p["credit_history"]]) / max(1, len(p["credit_history"]))
        if len(p["credit_history"]) >= 3 and amount > avg_credit * 8:
            alerts.append("EXTREME_SURGE_CREDIT")
            score += 0.5
        elif len(p["credit_history"]) >= 3 and amount > avg_credit * 4:
            alerts.append("SUSPICIOUS_LARGE_CREDIT")
            score += 0.3

        # 2. Micro-deposits
        recent_credits = [x for x in p["credit_history"] if current_time - x[1] < 600]
        small_credits = [x for x in recent_credits if x[0] < 50]
        if len(small_credits) >= 5:
            alerts.append("MICRO_DEPOSIT_STRUCTURING")
            score += 0.4

        # 3. Unknown Sender Reputation
        if sender == "Unknown" or p["sender_reputation"].get(sender, 0) <= 1:
            alerts.append("UNVERIFIED_SENDER_ACCOUNT")
            score += 0.2
            
        return {"score": min(1.0, score), "alerts": alerts}


# Fraud Network Analyzer (Graph-based)
class NetworkAnalyzer:
    def __init__(self, db=None, max_txs: int = 5000):
        self.db = db
        # adjacency list: sender -> set of receivers
        self.graph = defaultdict(set)
        # incoming adjacency: receiver -> set of senders
        self.in_graph = defaultdict(set)
        # track transaction counts between nodes
        self.weight = defaultdict(int)
        # map account to its risk level
        self.node_risk = defaultdict(float)
        
        # Load from DB if available
        if self.db:
            edges = self.db.load_network()
            for s, r, w in edges:
                self.graph[s].add(r)
                self.in_graph[r].add(s)
                self.weight[(s, r)] = w

    def add_transaction(self, sender: str, receiver: str):
        if sender == "Unknown" or receiver == "Unknown" or sender == receiver:
            return
        
        # Add to graphs
        self.graph[sender].add(receiver)
        self.in_graph[receiver].add(sender)
        self.weight[(sender, receiver)] += 1
        
        # Persistence
        if self.db:
            asyncio.create_task(asyncio.to_thread(self.db.save_edge, sender, receiver, self.weight[(sender, receiver)]))

    def detect_cycles(self, start_node: str, max_depth: int = 4) -> bool:
        """DFS to find if this node is part of a small cycle (Circular Transfer)"""
        stack = [(start_node, [start_node])]
        while stack:
            (node, path) = stack.pop()
            for neighbor in self.graph[node]:
                if neighbor == start_node and len(path) > 1:
                    return True # Cycle found
                if neighbor not in path and len(path) < max_depth:
                    stack.append((neighbor, path + [neighbor]))
        return False

    def get_network_metrics(self, node: str) -> Dict:
        """Compute centrality and cluster metrics for a node"""
        out_degree = len(self.graph[node])
        in_degree = len(self.in_graph[node])
        return {
            "out_degree": out_degree,
            "in_degree": in_degree,
            "total_weight": sum(self.weight[(node, r)] for r in self.graph[node])
        }

    def compute_network_risk(self, sender: str, receiver: str) -> Dict:
        alerts = []
        score = 0.0

        # 1. Circular Transfer Detection
        if self.detect_cycles(sender):
            alerts.append("CIRCULAR_TRANSFER_RING")
            score += 0.6

        # 2. Mule Account Pattern
        metrics = self.get_network_metrics(receiver)
        if metrics["in_degree"] > 10:
            alerts.append("CRITICAL_NODE_INFLOW_SPIKE")
            score += 0.5
        elif metrics["in_degree"] > 5:
            alerts.append("SUSPICIOUS_MULE_HUB")
            score += 0.3

        # 3. Fan-out Pattern
        sender_metrics = self.get_network_metrics(sender)
        if sender_metrics["out_degree"] > 12:
            alerts.append("EXTREME_FANOUT_DISBURSEMENT")
            score += 0.4
        elif sender_metrics["out_degree"] > 6:
            alerts.append("RAPID_ACCOUNT_FANOUT")
            score += 0.2

        return {"score": min(1.0, score), "alerts": alerts}

    def get_graph_snapshot(self, node_limit: int = 40, edge_limit_per_node: int = 6) -> Dict:
        """Return subset of graph for dashboard visualization"""
        nodes = []
        edges = []
        seen_nodes = set()
        
        # Sort by activity to find important hubs
        active_senders = sorted(self.graph.keys(), key=lambda x: len(self.graph[x]), reverse=True)[:node_limit]
        
        for s in active_senders:
            if s not in seen_nodes:
                nodes.append({"id": s, "type": "account", "is_suspicious": len(self.graph[s]) > 5})
                seen_nodes.add(s)
            
            receivers = list(self.graph[s])[:edge_limit_per_node]
            for r in receivers:
                if r not in seen_nodes:
                    nodes.append({"id": r, "type": "receiver", "is_suspicious": len(self.in_graph[r]) > 5})
                    seen_nodes.add(r)
                edges.append({"source": s, "target": r, "weight": self.weight[(s, r)]})
                
        return {"nodes": nodes, "links": edges}

network_analyzer = NetworkAnalyzer(db=db_manager)
profiler = UserProfiler(db=db_manager)

@app.on_event("startup")
async def load_model_assets():
    global model, scaler, scale_cols, threshold, freq_map, explainer
    
    meta_files = ['best_fraud_model.pkl', 'scaler.pkl', 'scale_cols.pkl', 'threshold.pkl', 'freq_map.pkl']
    for f in meta_files:
        if not os.path.exists(f):
            print(f"CRITICAL ERROR: {f} not found. Ensure models are trained.")
            return

    model = joblib.load('best_fraud_model.pkl')
    scaler = joblib.load('scaler.pkl')
    scale_cols = joblib.load('scale_cols.pkl')
    threshold = joblib.load('threshold.pkl')
    freq_map = joblib.load('freq_map.pkl')
    
    # Initialize SHAP explainer
    print("Initializing SHAP TreeExplainer...")
    explainer = shap.TreeExplainer(model)
    
    print("Fraud Risk Engine loaded successfully.")

def preprocess_transaction(t: Transaction) -> pd.DataFrame:
    # Convert single transaction to DataFrame
    df = pd.DataFrame([t.dict(exclude={'TransactionID'})])
    
    # Apply Feature Engineering
    df['Log_Amount'] = np.log1p(df['Amount'])
    df['Hour'] = (df['Time'] // 3600) % 24
    
    def get_time_bucket(hour):
        if 6 <= hour < 12:
            return 'morning'
        elif 12 <= hour < 18:
            return 'afternoon'
        else:
            return 'night'
            
    df['Time_Bucket'] = df['Hour'].apply(get_time_bucket)
    
    for bucket in ['morning', 'afternoon', 'night']:
        col = f'Time_{bucket}'
        df[col] = (df['Time_Bucket'] == bucket).astype(int)
    
    df = df.drop('Time_Bucket', axis=1)
    df['Is_High_Value'] = (df['Amount'] > threshold).astype(int)
    df['Hourly_Frequency'] = df['Hour'].map(freq_map).fillna(0)
    
    # Scale
    df[scale_cols] = scaler.transform(df[scale_cols])
    
    if hasattr(model, 'feature_names_in_'):
        df = df[model.feature_names_in_]
        
    return df

@app.post("/predict", response_model=RiskScore)
async def predict_risk(transaction: Transaction):
    if model is None:
        raise HTTPException(status_code=500, detail="Model is not loaded.")
        
    try:
        # Preprocess
        df = preprocess_transaction(transaction)
        
        # Predict
        prob = model.predict_proba(df)[0, 1]
        prediction = int(model.predict(df)[0])
        
        # Determine risk level based on probability
        if prob > 0.8:
            risk_level = "CRITICAL"
        elif prob > 0.5:
            risk_level = "HIGH"
        elif prob > 0.2:
            risk_level = "MEDIUM"
        else:
            risk_level = "LOW"
            
        # SHAP Explainability
        # shap_values can return different shapes depending on model and version
        shap_vals = explainer.shap_values(df)
        
        # Robust extraction for the "First Transaction" in the request
        if isinstance(shap_vals, list):
            # Typical for Random Forest: list of [class0_vals, class1_vals]
            # Each is (samples, features)
            vals = shap_vals[1][0] if len(shap_vals) > 1 else shap_vals[0][0]
        elif len(shap_vals.shape) == 3:
            # (classes, samples, features)
            vals = shap_vals[1][0] if shap_vals.shape[0] > 1 else shap_vals[0][0]
        else:
            # (samples, features)
            vals = shap_vals[0]
            
        # Ensure vals is a list of floats
        vals = [float(v) for v in vals]
            
        feature_names = df.columns.tolist()
        importance_dict = dict(zip(feature_names, [float(v) for v in vals]))
        
        # Sort by absolute contribution to find top risk drivers
        top_factors = sorted(importance_dict.items(), key=lambda x: abs(x[1]), reverse=True)[:5]
        # Map to human readable names
        top_factor_names = [FEATURE_MAP.get(f[0], f[0]) for f in top_factors if f[1] > 0][:3]

        # --- Dual Mode Prediction Routing ---
        tx_type = transaction.transaction_type
        user_id = transaction.user_id
        merchant = transaction.merchant
        location = transaction.location
        sender = transaction.sender_account or "Unknown"
        receiver = transaction.receiver_account or "Unknown"
        hour = (transaction.Time // 3600) % 24

        if tx_type == "credit":
            # Credit specific behavioral logic
            behavioral_res = profiler.compute_credit_anomaly_score(user_id, transaction.Amount, sender)
            # Graph Network Analysis
            network_res = network_analyzer.compute_network_risk(sender, receiver)
            
            # Hybrid Scoring for Credit: 50% ML + 30% Behavioral + 20% Network
            final_score = (0.5 * prob) + (0.3 * behavioral_res["score"]) + (0.2 * network_res["score"])
        else:
            # Debit specific behavioral logic (Default)
            behavioral_res = profiler.compute_anomaly_score(user_id, transaction.Amount, hour, merchant, location)
            # Graph Network Analysis
            network_res = network_analyzer.compute_network_risk(sender, receiver)
            
            # Hybrid Scoring for Debit: 50% ML + 30% Behavioral + 20% Network
            final_score = (0.5 * prob) + (0.3 * behavioral_res["score"]) + (0.2 * network_res["score"])

        behavioral_prob = behavioral_res["score"]
        behavioral_alerts = behavioral_res["alerts"] + network_res["alerts"]
        network_risk = network_res["score"]
        
        # Categorize Risk Level based on Hybrid Score
        if final_score > 0.8:
            risk_level = "CRITICAL"
        elif final_score > 0.5:
            risk_level = "HIGH"
        elif final_score > 0.2:
            risk_level = "MEDIUM"
        else:
            risk_level = "LOW"
            
        # Update profile and network for future predictions
        profiler.update_profile(user_id, transaction.Amount, hour, merchant, location, tx_type, sender)
        network_analyzer.add_transaction(sender, receiver)
        
        # Get updated profile for summary
        final_profile = profiler.get_profile(user_id)
        profile_summary = {
            "avg_amount": round(final_profile["avg_amount"], 2),
            "total_txs": final_profile["tx_count"],
            "unique_merchants": len(final_profile["merchants"]),
            "unique_locations": len(final_profile["locations"])
        }

        result = RiskScore(
            TransactionID=transaction.TransactionID,
            IsFraud=prediction,
            FraudProbability=prob,
            RiskLevel=risk_level,
            TopRiskFactors=top_factor_names,
            FeatureImportance={k: v for k, v in top_factors},
            BehavioralProbability=behavioral_prob,
            BehavioralAlerts=behavioral_alerts,
            FinalRiskScore=final_score,
            UserProfileSummary=profile_summary
        )
        
        # Broadcast to dashboard
        # Throttle graph data to reduce overhead (send on risk or every 5th tx)
        include_graph = (risk_level in ["MEDIUM", "HIGH", "CRITICAL"]) or (final_profile["tx_count"] % 5 == 0)
        
        broadcast_data = {
            "TransactionID": transaction.TransactionID,
            "Amount": transaction.Amount,
            "Time": transaction.Time,
            "Type": tx_type.upper(),
            "Sender": sender,
            "Receiver": receiver,
            "merchant": merchant,
            "location": location,
            "IsFraud": prediction,
            "FraudProbability": prob,
            "RiskLevel": risk_level,
            "TopRiskFactors": top_factor_names,
            "FeatureImportance": {k: v for k, v in top_factors},
            "BehavioralProbability": behavioral_prob,
            "BehavioralAlerts": behavioral_alerts,
            "FinalRiskScore": final_score,
            "UserProfileSummary": profile_summary,
            "user_id": user_id,
            "NetworkScore": network_risk,
            "GraphData": network_analyzer.get_graph_snapshot() if include_graph else None
        }
        
        # Use jsonable_encoder to handle numpy/float types safely (now handled in manager.broadcast)
        await manager.broadcast(broadcast_data)
        
        # Save to database (Non-blocking)
        asyncio.create_task(asyncio.to_thread(db_manager.save_transaction, jsonable_encoder(broadcast_data)))
        
        return result

        
    except Exception as e:
        print(f"PREDICTION ERROR: {str(e)}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=400, detail=str(e))

FEATURE_MAP = {
    "V1": "Behavioral Pattern V1", "V2": "Transaction Anomaly V2", "V3": "Access Pattern V3",
    "V4": "Volume Spike V4", "V7": "Merchant Consistency V7", "V10": "Unusual behavior (V10)",
    "V11": "Frequency Anomaly V11", "V12": "Security Flag V12", "V14": "V14 anomaly detected",
    "V16": "Transaction Profile V16", "V17": "High Risk Indicator V17", "Amount": "High transaction amount",
    "Hour": "Unusual transaction time", "Log_Amount": "Relative spending spike", "Hourly_Frequency": "Network load anomaly"
}

@app.post("/webhook/payment", response_model=RiskScore)
async def bank_webhook(bt: BankTransaction):
    """Normalized endpoint for payment gateway webhooks."""
    mapped_data = {
        "Time": bt.timestamp,
        "Amount": bt.amount,
        "TransactionID": bt.transaction_id,
        "transaction_type": bt.transaction_type,
        "sender_account": bt.sender_account,
        "receiver_account": bt.receiver_account,
        "user_id": bt.user_id,
        "merchant": bt.merchant,
        "location": bt.location
    }
    # Populate V1-V28 with neutral values (0.0)
    for i in range(1, 29): mapped_data[f"V{i}"] = 0.0
    return await predict_risk(Transaction(**mapped_data))

@app.post("/transaction/email", response_model=RiskScore)
async def email_transaction(et: EmailTransaction):
    """Ingests fraud alerts or transaction notifications from emails."""
    # Simplified parsing logic for demo: try to extract amount from body
    import re
    amounts = re.findall(r"\$\d+(?:\.\d+)?", et.body)
    amount = float(amounts[0].replace("$", "")) if amounts else 10.0
    
    mapped_data = {
        "Time": et.received_at,
        "Amount": amount,
        "TransactionID": f"EMAIL-{int(et.received_at)}",
        "user_id": et.sender_email,
        "merchant": "Email_Gateway",
        "location": "Remote"
    }
    for i in range(1, 29): mapped_data[f"V{i}"] = 0.0
    return await predict_risk(Transaction(**mapped_data))

@app.post("/transaction/batch")
async def batch_transactions(batch: BatchTransaction):
    """Processes a batch of transactions from a source."""
    results = []
    for tx in batch.transactions:
        res = await bank_webhook(tx)
        results.append(res)
    return {"source": batch.source, "processed": len(results), "high_risk_count": len([r for r in results if r.RiskLevel in ["HIGH", "CRITICAL"]])}

# CSV Upload endpoint removed as part of feature decommissioning.

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    print(f"New WebSocket connection request from {websocket.client}")
    await manager.connect(websocket)
    print(f"WebSocket client connected. Total clients: {len(manager.active_connections)}")
    try:
        while True:
            # Keep connection alive and listen for any client messages (pings, etc.)
            await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(websocket)
        print(f"WebSocket client disconnected. Remaining clients: {len(manager.active_connections)}")
    except Exception as e:
        print(f"WebSocket Error: {e}")
        manager.disconnect(websocket)

@app.get("/")
async def get_index():
    return FileResponse("dashboard/index.html")

# Fallback for dashboard assets (must be last)
if os.path.exists("dashboard"):
    app.mount("/", StaticFiles(directory="dashboard", html=True), name="dashboard")
