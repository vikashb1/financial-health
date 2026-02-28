import duckdb
import pandas as pd
import numpy as np

def load_features():
    con = duckdb.connect("data/mart/mart.duckdb")
    df = con.execute("SELECT * FROM mart_company_year ORDER BY ticker, year").df()
    con.close()
    return df

def score_profitability(row):
    margin = row["profit_margin"]
    if pd.isna(margin):
        return 5.0
    if margin > 0.25:
        return 10.0
    elif margin > 0.15:
        return 8.0
    elif margin > 0.08:
        return 6.0
    elif margin > 0.0:
        return 4.0
    else:
        return 2.0

def score_cash_flow(row):
    ocf = row["ocf_margin"]
    if pd.isna(ocf):
        return 5.0
    if ocf > 0.25:
        return 10.0
    elif ocf > 0.15:
        return 8.0
    elif ocf > 0.05:
        return 6.0
    elif ocf > 0.0:
        return 4.0
    else:
        return 2.0

def score_debt(row):
    d2a = row["debt_to_assets"]
    c2d = row["cash_to_debt"]
    if pd.isna(d2a):
        return 5.0
    score = 5.0
    if d2a < 0.2:
        score += 2.5
    elif d2a < 0.4:
        score += 1.0
    elif d2a > 0.6:
        score -= 2.0
    if pd.notna(c2d):
        if c2d > 0.5:
            score += 2.5
        elif c2d > 0.2:
            score += 1.0
        elif c2d < 0.1:
            score -= 1.0
    return max(0.0, min(10.0, score))

def score_growth(row):
    growth = row["revenue_growth"]
    trend = row["margin_trend"]
    if pd.isna(growth):
        return 5.0
    score = 5.0
    if growth > 0.15:
        score += 2.0
    elif growth > 0.05:
        score += 1.0
    elif growth < 0.0:
        score -= 2.0
    if pd.notna(trend):
        if trend > 0.01:
            score += 1.5
        elif trend < -0.01:
            score -= 1.5
    return max(0.0, min(10.0, score))

def compute_overall(row):
    return round(
        row["profitability_score"] * 0.30 +
        row["cashflow_score"]      * 0.30 +
        row["debt_score"]          * 0.25 +
        row["growth_score"]        * 0.15,
        2
    )

def compute_scores(df):
    df = df.copy()
    df["profitability_score"] = df.apply(score_profitability, axis=1)
    df["cashflow_score"]      = df.apply(score_cash_flow, axis=1)
    df["debt_score"]          = df.apply(score_debt, axis=1)
    df["growth_score"]        = df.apply(score_growth, axis=1)
    df["overall_score"]       = df.apply(compute_overall, axis=1)
    return df

def save_scores(df):
    con = duckdb.connect("data/mart/mart.duckdb")
    con.execute("DROP TABLE IF EXISTS scored_company_year")
    con.execute("CREATE TABLE scored_company_year AS SELECT * FROM df")
    print("Scores saved. Rows:", len(df))
    con.close()

if __name__ == "__main__":
    print("Loading features...")
    df = load_features()

    print("Computing scores...")
    scored = compute_scores(df)

    print("Saving scores...")
    save_scores(scored)

    print("\nSample output:")
    cols = ["ticker", "year", "profitability_score", "cashflow_score", "debt_score", "growth_score", "overall_score"]
    print(scored[cols].to_string())