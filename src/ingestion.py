import requests
import pandas as pd
import duckdb

TICKERS = {
    "AAPL": "0000320193",
    "MSFT": "0000789019",
    "AMZN": "0001018724",
    "NVDA": "0001045810",
    "TSLA": "0001318605"
}

HEADERS = {"User-Agent": "vikashraghavenderbabu@gmail.com"}

def get_company_facts(cik):
    url = f"https://data.sec.gov/api/xbrl/companyfacts/CIK{cik}.json"
    response = requests.get(url, headers=HEADERS)
    return response.json()

def extract_metric(facts, col_name, metric_names):
    for metric_name in metric_names:
        try:
            data = facts["facts"]["us-gaap"][metric_name]["units"]["USD"]
            df = pd.DataFrame(data)
            df = df[df["form"] == "10-K"]
            if "start" not in df.columns:
                df["start"] = pd.to_datetime(df["end"]) - pd.DateOffset(years=1)
            df = df.dropna(subset=["start"])
            df["start"] = pd.to_datetime(df["start"])
            df["end_dt"] = pd.to_datetime(df["end"])
            df["period_days"] = (df["end_dt"] - df["start"]).dt.days
            df = df[df["period_days"] >= 300]
            df["year"] = df["end_dt"].dt.year
            df = df.sort_values("period_days", ascending=False).drop_duplicates("year")
            df = df[["year", "val"]].rename(columns={"val": col_name})
            return df
        except KeyError:
            continue
    print(f"  Could not find {col_name}")
    return pd.DataFrame()

def build_staged_table():
    con = duckdb.connect("data/staged/financials.duckdb")
    all_rows = []

    for ticker, cik in TICKERS.items():
        print(f"Fetching {ticker}...")
        facts = get_company_facts(cik)

        metrics = {
            "revenue":             ["RevenueFromContractWithCustomerExcludingAssessedTax", "Revenues", "SalesRevenueNet"],
            "net_income":          ["NetIncomeLoss"],
            "total_assets":        ["Assets"],
            "long_term_debt":      ["LongTermDebt", "LongTermDebtNoncurrent"],
            "cash":                ["CashAndCashEquivalentsAtCarryingValue"],
            "operating_cash_flow": ["NetCashProvidedByUsedInOperatingActivities"]
        }

        base = None
        for col_name, label_options in metrics.items():
            df = extract_metric(facts, col_name, label_options)
            if df.empty:
                continue
            if base is None:
                base = df
            else:
                base = base.merge(df, on="year", how="outer")

        if base is not None:
            base["ticker"] = ticker
            base = base[base["year"] >= 2019]
            base = base.sort_values("year")
            all_rows.append(base)

    if not all_rows:
        print("No data collected.")
        return

    final = pd.concat(all_rows, ignore_index=True)
    con.execute("DROP TABLE IF EXISTS staged_financials")
    con.execute("CREATE TABLE staged_financials AS SELECT * FROM final")
    print("\nDone. Rows saved:", len(final))
    con.close()

if __name__ == "__main__":
    build_staged_table()