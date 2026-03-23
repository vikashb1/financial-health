import yfinance as yf
import duckdb
import pandas as pd
import json

def load_scores():
    con = duckdb.connect("data/mart/mart.duckdb")
    df = con.execute("SELECT ticker, year, overall_score FROM scored_company_year ORDER BY ticker, year").df()
    con.close()
    return df

def get_stock_volatility(ticker, year):
    try:
        start = f"{year}-01-01"
        end = f"{year}-12-31"
        data = yf.download(ticker, start=start, end=end, progress=False)
        if data.empty:
            return None
        daily_returns = data["Close"].pct_change().dropna()
        volatility = round(float(daily_returns.std() * (252 ** 0.5)), 4)
        return volatility
    except:
        return None

def run_evaluation():
    print("Loading scores...")
    scores_df = load_scores()

    results = []
    for _, row in scores_df.iterrows():
        ticker = row["ticker"]
        year = int(row["year"])
        score = row["overall_score"]

        print(f"  Fetching volatility for {ticker} {year}...")
        volatility = get_stock_volatility(ticker, year)

        if volatility is not None:
            results.append({
                "ticker": ticker,
                "year": year,
                "overall_score": score,
                "volatility": volatility
            })

    eval_df = pd.DataFrame(results)

    # Correlation between health score and volatility
    correlation = round(eval_df["overall_score"].corr(eval_df["volatility"]), 4)
    print(f"\nCorrelation between health score and volatility: {correlation}")
    print("(Negative = healthier companies have lower volatility, which is expected)")

    # Summary by company
    print("\nAverage scores and volatility by company:")
    summary = eval_df.groupby("ticker")[["overall_score", "volatility"]].mean().round(3)
    print(summary)

    # Save results
    eval_df.to_csv("reports/evaluation.csv", index=False)
    with open("reports/evaluation_summary.json", "w") as f:
        json.dump({
            "correlation": correlation,
            "interpretation": "Negative correlation means healthier companies tend to have lower stock volatility.",
            "company_averages": summary.reset_index().to_dict(orient="records")
        }, f, indent=2)

    print("\nSaved to reports/evaluation.csv and reports/evaluation_summary.json")
    return eval_df, correlation

if __name__ == "__main__":
    run_evaluation()