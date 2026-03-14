import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler
from sklearn.linear_model import LogisticRegression
from sklearn.ensemble import RandomForestClassifier, GradientBoostingClassifier
from sklearn.metrics import (
    classification_report,
    roc_auc_score,
    precision_score,
    recall_score,
    f1_score,
    confusion_matrix,
    roc_curve
)
from imblearn.over_sampling import SMOTE
import joblib
import os

# Set random seed for reproducibility
RANDOM_SEED = 42

def load_data(file_path):
    print(f"Loading data from {file_path}...")
    df = pd.read_csv(file_path)
    print(f"Dataset Shape: {df.shape}")
    return df

def feature_engineering(df):
    print("Engineering new features...")
    
    # 1. Log transformed transaction amount
    df['Log_Amount'] = np.log1p(df['Amount'])
    
    # 2. Transaction time bucket (morning, afternoon, night)
    # Time is in seconds from first transaction
    df['Hour'] = (df['Time'] // 3600) % 24
    
    def get_time_bucket(hour):
        if 6 <= hour < 12:
            return 'morning'
        elif 12 <= hour < 18:
            return 'afternoon'
        else:
            return 'night'
            
    df['Time_Bucket'] = df['Hour'].apply(get_time_bucket)
    # One-hot encode Time_Bucket
    df = pd.get_dummies(df, columns=['Time_Bucket'], prefix='Time')
    
    # 3. High value transaction indicator
    # Using 95th percentile as a threshold for "High Value"
    threshold = df['Amount'].quantile(0.95)
    df['Is_High_Value'] = (df['Amount'] > threshold).astype(int)
    
    # 4. Transaction frequency indicators
    # Since we don't have UserID, we use "Transactions per Hour" as a proxy for network load/patterns
    freq_map = df['Hour'].value_counts().to_dict()
    df['Hourly_Frequency'] = df['Hour'].map(freq_map)
    
    return df

def preprocess_data(df):
    print("Preprocessing data...")
    
    # Check for missing values
    if df.isnull().sum().sum() > 0:
        print("Handling missing values...")
        df = df.dropna()
    
    # Apply Feature Engineering
    df = feature_engineering(df)
    
    # Features to scale: Amount, Time, Log_Amount, Hourly_Frequency, Hour
    scale_cols = ['Amount', 'Time', 'Log_Amount', 'Hourly_Frequency', 'Hour']
    scaler = StandardScaler()
    df[scale_cols] = scaler.fit_transform(df[scale_cols])
    
    X = df.drop('Class', axis=1)
    y = df['Class']
    
    return X, y, scale_cols

def train_and_evaluate(X_train, X_test, y_train, y_test):
    # Handle Class Imbalance using SMOTE
    print("Applying SMOTE to handle class imbalance...")
    smote = SMOTE(random_state=RANDOM_SEED)
    X_train_sm, y_train_sm = smote.fit_resample(X_train, y_train)
    print(f"Original training shape: {y_train.value_counts().to_dict()}")
    print(f"Resampled training shape: {y_train_sm.value_counts().to_dict()}")

    models = {
        "Logistic Regression": LogisticRegression(max_iter=1000, random_state=RANDOM_SEED),
        "Random Forest": RandomForestClassifier(n_estimators=100, random_state=RANDOM_SEED, n_jobs=-1),
        "Gradient Boosting": GradientBoostingClassifier(random_state=RANDOM_SEED)
    }

    results = {}
    best_model = None
    best_f1 = 0

    for name, model in models.items():
        print(f"\nTraining {name}...")
        model.fit(X_train_sm, y_train_sm)
        
        y_pred = model.predict(X_test)
        y_prob = model.predict_proba(X_test)[:, 1]
        
        auc = roc_auc_score(y_test, y_prob)
        precision = precision_score(y_test, y_pred)
        recall = recall_score(y_test, y_pred)
        f1 = f1_score(y_test, y_pred)
        
        results[name] = {
            "AUC": auc,
            "Precision": precision,
            "Recall": recall,
            "F1": f1
        }
        
        print(f"{name} Metrics:")
        print(f"  ROC-AUC: {auc:.4f}")
        print(f"  Precision: {precision:.4f}")
        print(f"  Recall: {recall:.4f}")
        print(f"  F1-Score: {f1:.4f}")
        print("\nClassification Report:")
        print(classification_report(y_test, y_pred))
        
        if f1 > best_f1:
            best_f1 = f1
            best_model = (name, model)

    return results, best_model

def main():
    file_path = 'creditcard.csv'
    if not os.path.exists(file_path):
        print(f"Error: {file_path} not found in the current directory.")
        return

    df = load_data(file_path)
    
    # Minimal EDA Plot (Class Distribution)
    plt.figure(figsize=(8, 6))
    sns.countplot(x='Class', data=df)
    plt.title('Class Distribution (0: Legitimate, 1: Fraudulent)')
    plt.savefig('class_distribution.png')
    print("Saved class distribution plot to 'class_distribution.png'")

    X, y, scale_cols = preprocess_data(df)
    
    # Stratified split to maintain class ratios
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=RANDOM_SEED, stratify=y
    )

    results, (best_name, best_model) = train_and_evaluate(X_train, X_test, y_train, y_test)

    print(f"\nBest Model: {best_name} with F1-score {results[best_name]['F1']:.4f}")
    
    # Save the best model, scaler, and the list of columns to scale
    joblib.dump(best_model, 'best_fraud_model.pkl')
    
    # Re-fit scaler on full dataset for the designated columns
    # We need to re-run the whole feature engineering on the full df to save the final scaler
    full_df = load_data(file_path)
    full_df = feature_engineering(full_df)
    full_scaler = StandardScaler()
    full_scaler.fit(full_df[scale_cols])
    
    joblib.dump(full_scaler, 'scaler.pkl')
    joblib.dump(scale_cols, 'scale_cols.pkl')
    # Save the quantile threshold for Is_High_Value
    threshold = full_df['Amount'].quantile(0.95)
    joblib.dump(threshold, 'threshold.pkl')
    # Save hourly frequency map
    freq_map = full_df['Hour'].value_counts().to_dict()
    joblib.dump(freq_map, 'freq_map.pkl')
    
    print("Saved model, scaler, and feature metadata.")

if __name__ == "__main__":
    main()
