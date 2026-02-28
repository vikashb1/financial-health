import duckdb
import pandas as pd
import numpy as np

def load_scores():
    con_mart = duckdb.connect("data/mart/mart.duckdb")
    scores = con_mart.execute("SELECT * FROM scored_company_year ORDER BY ticker, year").df()
    con_mart.close()

    con_staged = duckdb.connect("data/staged/financials.duckdb")
    staged = con_staged.execute("SELECT ticker, year, revenue FROM staged_financials").df()
    con_staged.close()

    df = scores.merge(staged, on=["ticker", "year"], how="left")
    return df

def translate_profitability(row):
    margin = row["profit_margin"]
    score = row["profitability_score"]
    if pd.isna(margin):
        return "Profitability data is unavailable for this period."
    pct = round(margin * 100, 1)
    if score >= 9:
        return f"The company keeps {pct}% of every dollar it earns as profit — an excellent result that signals strong pricing power and cost discipline."
    elif score >= 7:
        return f"The company retains {pct}% of revenue as profit, which is healthy and above average for most industries."
    elif score >= 5:
        return f"The company is profitable at {pct}% margin, but there is room for improvement. Costs may be eating into earnings."
    elif score >= 3:
        return f"Profit margins are thin at {pct}%. The company is making money but not much of it — worth watching closely."
    else:
        return f"The company is currently losing money, with a margin of {pct}%. This is a red flag unless the company is in an early growth phase."

def translate_cashflow(row):
    ocf = row["ocf_margin"]
    score = row["cashflow_score"]
    if pd.isna(ocf):
        return "Cash flow data is unavailable for this period."
    pct = round(ocf * 100, 1)
    if score >= 9:
        return f"The company generates {pct} cents of real cash for every dollar of revenue — a sign that profits are backed by actual money, not accounting tricks."
    elif score >= 7:
        return f"Cash flow is solid at {pct}% of revenue. The company is converting sales into real cash effectively."
    elif score >= 5:
        return f"Cash flow is modest at {pct}% of revenue. The company is cash positive but may face pressure if conditions worsen."
    else:
        return f"Cash flow is weak at {pct}% of revenue. The company may be struggling to turn sales into actual cash."

def translate_debt(row):
    d2a = row["debt_to_assets"]
    c2d = row["cash_to_debt"]
    score = row["debt_score"]
    if pd.isna(d2a):
        return "Debt data is unavailable for this period."
    d2a_pct = round(d2a * 100, 1)
    if score >= 9:
        return f"The company carries very manageable debt — only {d2a_pct}% of its assets are debt-financed. It has a strong financial cushion."
    elif score >= 7:
        return f"Debt levels are reasonable at {d2a_pct}% of total assets. The company appears to be managing its obligations well."
    elif score >= 5:
        return f"Debt is moderate at {d2a_pct}% of assets. Not alarming, but worth monitoring as interest rates or revenues shift."
    else:
        return f"Debt is elevated at {d2a_pct}% of assets. The company may be over-leveraged, which increases financial risk."

def translate_growth(row):
    growth = row["revenue_growth"]
    trend = row["margin_trend"]
    if pd.isna(growth):
        return "Growth data is unavailable for this period."
    growth_pct = round(growth * 100, 1)
    if growth > 0.15 and pd.notna(trend) and trend > 0:
        return f"Revenue grew {growth_pct}% this year and profit margins are improving — a strong combination suggesting the company is scaling efficiently."
    elif growth > 0.15 and pd.notna(trend) and trend < 0:
        return f"Revenue grew strongly at {growth_pct}%, but profit margins are shrinking. The company is growing fast but spending more to do it."
    elif growth > 0.05:
        return f"Revenue grew {growth_pct}% — steady, healthy growth that keeps the company moving forward."
    elif growth > 0:
        return f"Revenue grew only {growth_pct}% — the company is still expanding but momentum is slowing."
    else:
        return f"Revenue declined {abs(growth_pct)}% this year. This warrants attention — the company may be losing market share or facing demand issues."

def translate_overall(row):
    score = row["overall_score"]
    ticker = row["ticker"]
    year = row["year"]
    if score >= 9:
        return f"{ticker} is in exceptional financial health in {year}. It scores highly across profitability, cash flow, and debt management."
    elif score >= 7.5:
        return f"{ticker} is financially strong in {year} with no major concerns. A few areas could improve but the overall picture is positive."
    elif score >= 6:
        return f"{ticker} shows mixed financial health in {year}. Some pillars are strong but others need attention."
    elif score >= 4:
        return f"{ticker} is showing signs of financial stress in {year}. Multiple areas are underperforming and warrant close monitoring."
    else:
        return f"{ticker} is in poor financial health in {year}. Significant risks are present across multiple dimensions."

def generate_report(ticker, df):
    company_df = df[df["ticker"] == ticker].sort_values("year")
    latest = company_df.iloc[-1]

    print(f"\n{'='*60}")
    print(f"  FINANCIAL HEALTH REPORT — {ticker}")
    print(f"  Year: {int(latest['year'])}")
    print(f"{'='*60}")
    print(f"\nOVERALL SCORE: {latest['overall_score']} / 10")
    print(f"\n{translate_overall(latest)}")

    print(f"\n--- PROFITABILITY (Score: {latest['profitability_score']}/10) ---")
    print(translate_profitability(latest))

    print(f"\n--- CASH FLOW (Score: {latest['cashflow_score']}/10) ---")
    print(translate_cashflow(latest))

    print(f"\n--- DEBT (Score: {latest['debt_score']}/10) ---")
    print(translate_debt(latest))

    print(f"\n--- GROWTH (Score: {latest['growth_score']}/10) ---")
    print(translate_growth(latest))

    print(f"\n--- TREND STORY ---")
    first = company_df.iloc[0]
    last = company_df.iloc[-1]
    if pd.notna(first["revenue"]) and pd.notna(last["revenue"]):
        rev_change = round(((last["revenue"] - first["revenue"]) / first["revenue"]) * 100, 1)
        print(f"Over the past {len(company_df)} years, {ticker}'s revenue has {'grown' if rev_change > 0 else 'declined'} by {abs(rev_change)}%.", end=" ")
    if pd.notna(first["profit_margin"]) and pd.notna(last["profit_margin"]):
        margin_change = round((last["profit_margin"] - first["profit_margin"]) * 100, 1)
        direction = "improved" if margin_change > 0 else "declined"
        print(f"Profit margins have {direction} by {abs(margin_change)} percentage points over this period.")

if __name__ == "__main__":
    df = load_scores()
    for ticker in ["AAPL", "MSFT", "AMZN", "NVDA", "TSLA"]:
        generate_report(ticker, df)