import duckdb
import pandas as pd
import numpy as np
import json
from sklearn.ensemble import RandomForestRegressor
from sklearn.linear_model import LinearRegression
from sklearn.model_selection import cross_val_score
from sklearn.metrics import mean_absolute_error, r2_score
import pickle
import os

def load_features():
    con = duckdb.connect("data/mart/mart.duckdb")
    df = con.execute("SELECT * FROM scored_company_year ORDER BY ticker, year").df()
    con.close()
    return df

def prepare_training_data(df):
    feature_cols = [
        "profit_margin", "ocf_margin", "debt_to_assets",
        "cash_to_debt", "revenue_growth", "margin_trend"
    ]
    rows = []
    for ticker, group in df.groupby("ticker"):
        group = group.sort_values("year").reset_index(drop=True)
        for i in range(len(group) - 1):
            current = group.iloc[i]
            next_year = group.iloc[i + 1]
            row = {}
            for col in feature_cols:
                row[col] = current[col]
            row["current_score"] = current["overall_score"]
            row["next_score"] = next_year["overall_score"]
            row["ticker"] = ticker
            row["year"] = int(current["year"])
            rows.append(row)
    return pd.DataFrame(rows)

def train_model(df):
    feature_cols = [
        "profit_margin", "ocf_margin", "debt_to_assets",
        "cash_to_debt", "revenue_growth", "margin_trend",
        "current_score"
    ]
    clean = df.dropna(subset=feature_cols + ["next_score"])
    X = clean[feature_cols]
    y = clean["next_score"]

    print(f"Training on {len(clean)} samples...")

    # Random Forest
    rf = RandomForestRegressor(n_estimators=100, random_state=42)
    rf_scores = cross_val_score(rf, X, y, cv=3, scoring="neg_mean_absolute_error")
    rf_mae = round(-rf_scores.mean(), 3)

    # Linear Regression
    lr = LinearRegression()
    lr_scores = cross_val_score(lr, X, y, cv=3, scoring="neg_mean_absolute_error")
    lr_mae = round(-lr_scores.mean(), 3)

    print(f"Random Forest MAE: {rf_mae}")
    print(f"Linear Regression MAE: {lr_mae}")

    # Train final model on all data
    rf.fit(X, y)
    lr.fit(X, y)

    # Feature importance
    importance = pd.DataFrame({
        "feature": feature_cols,
        "importance": rf.feature_importances_
    }).sort_values("importance", ascending=False)

    print("\nFeature Importance:")
    print(importance.to_string(index=False))

    return rf, lr, feature_cols, {
        "rf_mae": rf_mae,
        "lr_mae": lr_mae,
        "samples": len(clean),
        "feature_importance": importance.to_dict(orient="records")
    }

def predict_next_score(model, feature_cols, df):
    latest = df.sort_values("year").groupby("ticker").last().reset_index()
    base_feature_cols = [
        "profit_margin", "ocf_margin", "debt_to_assets",
        "cash_to_debt", "revenue_growth", "margin_trend"
    ]
    predictions = []
    for _, row in latest.iterrows():
        features = []
        for col in feature_cols:
            if col == "current_score":
                val = row["overall_score"]
            else:
                val = row.get(col, np.nan)
            if pd.isna(val):
                col_data = df[col] if col in df.columns else df["overall_score"]
                val = col_data.mean()
            features.append(val)
        pred = round(float(model.predict([features])[0]), 2)
        pred = max(0, min(10, pred))
        predictions.append({
            "ticker": row["ticker"],
            "current_score": row["overall_score"],
            "predicted_next_score": pred,
            "trend": "Up" if pred > row["overall_score"] else "Down" if pred < row["overall_score"] else "Stable"
        })
    return pd.DataFrame(predictions)

def run_ml_pipeline():
    print("Loading features...")
    df = load_features()

    print("Preparing training data...")
    train_df = prepare_training_data(df)

    print("Training models...")
    rf_model, lr_model, feature_cols, metrics = train_model(train_df)

    print("\nPredicting next year scores...")
    predictions = predict_next_score(rf_model, feature_cols, df)
    print(predictions.to_string(index=False))

    # Save model
    os.makedirs("data/mart", exist_ok=True)
    with open("data/mart/rf_model.pkl", "wb") as f:
        pickle.dump(rf_model, f)
    with open("data/mart/feature_cols.json", "w") as f:
        json.dump(feature_cols, f)

    # Save predictions and metrics
    predictions.to_csv("reports/predictions.csv", index=False)
    with open("reports/ml_metrics.json", "w") as f:
        json.dump(metrics, f, indent=2)

    print("\nDone. Model saved to data/mart/rf_model.pkl")
    return predictions, metrics

if __name__ == "__main__":
    run_ml_pipeline()