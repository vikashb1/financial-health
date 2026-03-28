import duckdb
import pandas as pd
import numpy as np

def load_staged_data():
    con = duckdb.connect("data/staged/financials.duckdb")
    df = con.execute("SELECT * FROM staged_financials ORDER BY ticker, year").df()
    con.close()
    return df

def safe_get(row, col):
    try:
        val = row[col]
        if pd.isna(val):
            return np.nan
        return val
    except KeyError:
        return np.nan

def compute_features(df):
    # Ensure all expected columns exist
    for col in ["total_assets", "long_term_debt", "cash", "operating_cash_flow", "revenue", "net_income"]:
        if col not in df.columns:
            df[col] = np.nan

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

            revenue = safe_get(row, "revenue")
            net_income = safe_get(row, "net_income")
            total_assets = safe_get(row, "total_assets")
            long_term_debt = safe_get(row, "long_term_debt")
            cash = safe_get(row, "cash")
            operating_cash_flow = safe_get(row, "operating_cash_flow")

            # Profit Margin
            if pd.notna(revenue) and revenue > 0 and pd.notna(net_income):
                features["profit_margin"] = net_income / revenue
            else:
                features["profit_margin"] = np.nan

            # OCF Margin
            if pd.notna(revenue) and revenue > 0 and pd.notna(operating_cash_flow):
                features["ocf_margin"] = operating_cash_flow / revenue
            else:
                features["ocf_margin"] = np.nan

            # Debt to Assets
            if pd.notna(total_assets) and total_assets > 0 and pd.notna(long_term_debt):
                features["debt_to_assets"] = long_term_debt / total_assets
            else:
                features["debt_to_assets"] = np.nan

            # Cash to Debt
            if pd.notna(long_term_debt) and long_term_debt > 0 and pd.notna(cash):
                features["cash_to_debt"] = cash / long_term_debt
            else:
                features["cash_to_debt"] = np.nan

            # Revenue Growth
            if len(prev_rows) > 0:
                prev_revenue = prev_rows.iloc[-1]["revenue"] if "revenue" in prev_rows.columns else np.nan
                if pd.notna(prev_revenue) and prev_revenue > 0 and pd.notna(revenue):
                    features["revenue_growth"] = (revenue - prev_revenue) / prev_revenue
                else:
                    features["revenue_growth"] = np.nan
            else:
                features["revenue_growth"] = np.nan

            # Margin Trend
            margin_series = pd.Series([
                r["net_income"] / r["revenue"]
                for _, r in group[group["year"] <= year].iterrows()
                if pd.notna(r.get("revenue")) and r.get("revenue", 0) > 0 and pd.notna(r.get("net_income"))
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