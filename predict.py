import pandas as pd
import joblib
import numpy as np
import os

def predict_fraud(data, model_path='best_fraud_model.pkl', scaler_path='scaler.pkl'):
    """
    data: pd.DataFrame containing the same columns as the training data (Time, V1-V28, Amount)
    """
    meta_files = ['best_fraud_model.pkl', 'scaler.pkl', 'scale_cols.pkl', 'threshold.pkl', 'freq_map.pkl']
    for f in meta_files:
        if not os.path.exists(f):
            print(f"Error: {f} not found. Please run fraud_detection_model.py first.")
            return None

    # Load model and metadata
    model = joblib.load(model_path)
    scaler = joblib.load(scaler_path)
    scale_cols = joblib.load('scale_cols.pkl')
    threshold = joblib.load('threshold.pkl')
    freq_map = joblib.load('freq_map.pkl')

    # Preprocess
    df = data.copy()
    
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
    # Ensure all one-hot columns are present to match training (Prefix 'Time')
    for bucket in ['morning', 'afternoon', 'night']:
        col = f'Time_{bucket}'
        df[col] = (df['Time_Bucket'] == bucket).astype(int)
    
    df = df.drop('Time_Bucket', axis=1)
    
    df['Is_High_Value'] = (df['Amount'] > threshold).astype(int)
    df['Hourly_Frequency'] = df['Hour'].map(freq_map).fillna(0) # Default to 0 if hour not seen

    # Scale the required columns
    df[scale_cols] = scaler.transform(df[scale_cols])

    # Ensure column order matches training (excluding target)
    if hasattr(model, 'feature_names_in_'):
        # Just in case some extra columns leaked in
        df = df[model.feature_names_in_]

    # Predict probability
    prob = model.predict_proba(df)[:, 1]
    prediction = model.predict(df)

    return prediction, prob

def analyze_full_dataset(filepath='creditcard.csv'):
    if not os.path.exists(filepath):
        print(f"Error: {filepath} not found in current directory.")
        return

    print(f"Loading complete dataset from {filepath}...")
    df = pd.read_csv(filepath)
    
    y_true = None
    if 'Class' in df.columns:
        y_true = df['Class'].values
        X = df.drop('Class', axis=1)
    else:
        X = df.copy()

    print(f"Passing {len(X):,} transactions through the preprocessing & inference pipeline...")
    preds, probs = predict_fraud(X)

    if preds is None:
        return

    print("\n" + "="*40)
    print("      FINAL PREDICTION ANALYSIS")
    print("="*40)
    print(f"Total Transactions Processed : {len(preds):,}")
    print(f"Flagged as Fraud (Predicted): {sum(preds):,}")
    print(f"Marked as Safe   (Predicted): {len(preds) - (sum(preds)):,}")

    if y_true is not None:
        from sklearn.metrics import classification_report, confusion_matrix
        print("\n--- Accuracy Verification vs Known Labels ---")
        print("\nConfusion Matrix:")
        print(confusion_matrix(y_true, preds))
        print("\nClassification Report:")
        print(classification_report(y_true, preds))
        
    # Save the pipeline results
    output_df = df.copy()
    output_df['Fraud_Prediction'] = preds
    output_df['Fraud_Probability'] = probs
    output_file = 'pipeline_results.csv'
    output_df.to_csv(output_file, index=False)
    print(f"\nFinal complete predictions saved to: {output_file}")

def main():
    analyze_full_dataset()

if __name__ == "__main__":
    main()
