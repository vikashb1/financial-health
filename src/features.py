import duckdb
import pandas as pd
import numpy as np

def load_staged_data():
    con = duckdb.connect("data/staged/financials.duckdb")
    df = con.execute("SELECT * FROM staged_financials ORDER BY ticker, year").df()
    con.close()
    return df

def compute_features(df):
    results = []

    for ticker, group in df.groupby("ticker"):
        group = group.sort_values("year").copy()

        for i, row in group.iterrows():
            year = row["year"]
            prev_rows = group[group["year"] < year]

            features = {
                "ticker": ticker,
                "year": year,
            }

            # --- Profit Margin ---
            if pd.notna(row["revenue"]) and row["revenue"] > 0:
                features["profit_margin"] = row["net_income"] / row["revenue"]
            else:
                features["profit_margin"] = np.nan

            # --- OCF Margin ---
            if pd.notna(row["revenue"]) and row["revenue"] > 0:
                features["ocf_margin"] = row["operating_cash_flow"] / row["revenue"]
            else:
                features["ocf_margin"] = np.nan

            # --- Debt to Assets ---
            if pd.notna(row["total_assets"]) and row["total_assets"] > 0:
                features["debt_to_assets"] = row["long_term_debt"] / row["total_assets"]
            else:
                features["debt_to_assets"] = np.nan

            # --- Cash to Debt ---
            if pd.notna(row["long_term_debt"]) and row["long_term_debt"] > 0:
                features["cash_to_debt"] = row["cash"] / row["long_term_debt"]
            else:
                features["cash_to_debt"] = np.nan

            # --- Revenue Growth (vs prior year) ---
            if len(prev_rows) > 0:
                prev_revenue = prev_rows.iloc[-1]["revenue"]
                if pd.notna(prev_revenue) and prev_revenue > 0 and pd.notna(row["revenue"]):
                    features["revenue_growth"] = (row["revenue"] - prev_revenue) / prev_revenue
                else:
                    features["revenue_growth"] = np.nan
            else:
                features["revenue_growth"] = np.nan

            # --- Margin Trend (slope over available years) ---
            margin_series = pd.Series([
                r["net_income"] / r["revenue"]
                for _, r in group[group["year"] <= year].iterrows()
                if pd.notna(r["revenue"]) and r["revenue"] > 0 and pd.notna(r["net_income"])
            ])
            if len(margin_series) >= 3:
                x = np.arange(len(margin_series))
                slope = np.polyfit(x, margin_series.values, 1)[0]
                features["margin_trend"] = slope
            else:
                features["margin_trend"] = np.nan

            results.append(features)

    return pd.DataFrame(results)

def save_mart(features_df):
    con = duckdb.connect("data/mart/mart.duckdb")
    con.execute("DROP TABLE IF EXISTS mart_company_year")
    con.execute("CREATE TABLE mart_company_year AS SELECT * FROM features_df")
    print("Mart table saved. Rows:", len(features_df))
    con.close()

if __name__ == "__main__":
    print("Loading staged data...")
    df = load_staged_data()

    print("Computing features...")
    features_df = compute_features(df)

    print("Saving to mart...")
    save_mart(features_df)

    print("\nSample output:")
    print(features_df[features_df["ticker"] == "AAPL"].to_string())