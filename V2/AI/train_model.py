import pandas as pd
import numpy as np
import os
import joblib
from sklearn.model_selection import train_test_split
from sklearn.ensemble import GradientBoostingClassifier
from sklearn.metrics import classification_report, accuracy_score
from sklearn.utils.class_weight import compute_class_weight

def train_model():
    # 1. Load Data
    data_path = os.path.join(os.path.dirname(__file__), 'training_data.csv')
    if not os.path.exists(data_path):
        print("Dataset not found. Run generate_data.py first.")
        return

    df = pd.read_csv(data_path)
    print(f"Loaded {len(df)} samples.")
    
    # Check balance
    print("Label Distribution:")
    val_counts = df['Label'].value_counts()
    print(val_counts)
    
    # 2. Prepare X/y
    exclude_cols = ['Label', 'Signal_Dir'] 
    
    feature_cols = [c for c in df.columns if c not in ['Label']]
    X = df[feature_cols]
    y = df['Label']
    
    # Drop rows with NaN
    X = X.dropna()
    y = y[X.index]
    
    if len(X) < 10:
        print("Not enough data to train.")
        return

    # 3. Train/Test Split
    # 3. Train/Test Split
    # CRITICAL: Shuffle=False for Time Series validation [WorldQuant: Probabilistic not Deterministic, but order matters]
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.20, random_state=42, shuffle=False)
    
    # 4. Train Model - IMPROVED
    # Using GradientBoosting for better accuracy than RF
    print("Training GradientBoostingClassifier...")
    clf = GradientBoostingClassifier(
        n_estimators=200, 
        learning_rate=0.05,
        max_depth=5,
        subsample=0.8,
        random_state=42
    )
    clf.fit(X_train, y_train)
    
    # 5. Evaluate
    y_pred = clf.predict(X_test)
    y_prob = clf.predict_proba(X_test)[:, 1]
    
    acc = accuracy_score(y_test, y_pred)
    print("\nModel Performance:")
    print(f"Accuracy: {acc:.2%}")
    print("\nClassification Report:")
    print(classification_report(y_test, y_pred))
    
    # Feature Importance
    print("\nFeature Importance:")
    importances = pd.Series(clf.feature_importances_, index=feature_cols).sort_values(ascending=False)
    print(importances)
    
    # 6. Save Model
    model_path = os.path.join(os.path.dirname(__file__), 'model.pkl')
    joblib.dump(clf, model_path)
    print(f"\nModel saved to {model_path}")
    
if __name__ == "__main__":
    train_model()
