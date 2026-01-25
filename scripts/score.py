#!/usr/bin/env python3
import sys
import yfinance as yf
import pandas as pd
import numpy as np
import json

def calculate_score(val, min_val, max_val, max_points):
    """Linear interpolation of score."""
    if val >= max_val:
        return max_points
    if val <= min_val:
        return 0
    return ((val - min_val) / (max_val - min_val)) * max_points

def get_metric_display(val, is_percent=True):
    if val is None:
        return "N/A"
    if is_percent:
        return f"{val:.1f}%"
    return f"{val:.2f}"

def analyze_ticker(ticker_symbol):
    try:
        stock = yf.Ticker(ticker_symbol)
        
        # Fetch data
        try:
            income_stmt = stock.financials
            balance_sheet = stock.balance_sheet
            cash_flow = stock.cashflow
            info = stock.info
            market_cap = info.get('marketCap')
        except Exception as e:
            return {"error": f"Failed to fetch data: {str(e)}"}

        if income_stmt.empty or balance_sheet.empty or cash_flow.empty:
            return {"error": "Missing financial statements"}

        # Helper for latest annual data
        def get_latest(df, key):
            try:
                if key in df.index:
                    return df.loc[key].iloc[0]
                return 0
            except:
                return 0

        def get_historical(df, key, years_back=3):
            try:
                if key in df.index:
                    cols = df.columns
                    idx = min(years_back, len(cols) - 1)
                    return df.loc[key].iloc[idx]
                return None
            except:
                return None

        # --- 1. ROIC (35 pts) ---
        # NOPAT / Invested Capital
        ebit = get_latest(income_stmt, 'Ebit')
        if ebit == 0: ebit = get_latest(income_stmt, 'Operating Income')
        
        tax_provision = get_latest(income_stmt, 'Tax Provision')
        pretax_income = get_latest(income_stmt, 'Pretax Income')
        tax_rate = tax_provision / pretax_income if pretax_income and pretax_income != 0 else 0.21
        nopat = ebit * (1 - tax_rate)
        
        total_assets = get_latest(balance_sheet, 'Total Assets')
        current_liabs = get_latest(balance_sheet, 'Current Liabilities')
        invested_capital = total_assets - current_liabs
        
        roic = (nopat / invested_capital * 100) if invested_capital else 0
        score_roic = calculate_score(roic, 10, 20, 35)

        # --- 2. FCF Margin (25 pts) ---
        ocf = get_latest(cash_flow, 'Operating Cash Flow')
        capex = get_latest(cash_flow, 'Capital Expenditure')
        fcf = ocf - abs(capex)
        revenue = get_latest(income_stmt, 'Total Revenue')
        fcf_margin = (fcf / revenue * 100) if revenue else 0
        score_margin = calculate_score(fcf_margin, 10, 25, 25)

        # --- 3. Growth (FCF CAGR 3yr) (20 pts) ---
        # Fallback to Rev Growth if FCF is messy
        ocf_3y = get_historical(cash_flow, 'Operating Cash Flow', 3)
        capex_3y = get_historical(cash_flow, 'Capital Expenditure', 3)
        fcf_growth = 0
        growth_metric = "FCF CAGR (3y)"
        
        if ocf_3y is not None:
            fcf_3y = ocf_3y - abs(capex_3y if capex_3y else 0)
            if fcf_3y > 0 and fcf > 0:
                fcf_growth = ((fcf / fcf_3y) ** (1/3) - 1) * 100
            else:
                # Fallback to revenue
                rev_3y = get_historical(income_stmt, 'Total Revenue', 3)
                if rev_3y and rev_3y > 0:
                    fcf_growth = ((revenue / rev_3y) ** (1/3) - 1) * 100
                    growth_metric = "Rev CAGR (3y) [FCF invalid]"
        
        score_growth = calculate_score(fcf_growth, 5, 15, 20)

        # --- 4. Valuation (FCF Yield) (20 pts) ---
        if not market_cap:
            # Try to calc from price * shares
            try:
                price = info.get('currentPrice') or info.get('previousClose')
                shares = info.get('sharesOutstanding')
                if price and shares:
                    market_cap = price * shares
            except:
                pass
        
        fcf_yield = (fcf / market_cap * 100) if market_cap else 0
        score_val = calculate_score(fcf_yield, 2, 4, 20)

        total_score = score_roic + score_margin + score_growth + score_val

        # Recommendation
        if total_score >= 70:
            rec = "BUY / ACCUMULATE"
            rec_emoji = "✅"
        elif total_score >= 50:
            rec = "HOLD"
            rec_emoji = "⚠️"
        else:
            rec = "PASS / SELL"
            rec_emoji = "🛑"

        return {
            "symbol": ticker_symbol,
            "price": info.get('currentPrice', 'N/A'),
            "score": round(total_score, 1),
            "recommendation": rec,
            "emoji": rec_emoji,
            "metrics": {
                "ROIC": {
                    "value": roic, 
                    "display": get_metric_display(roic),
                    "score": round(score_roic, 1), 
                    "max": 35
                },
                "FCF Margin": {
                    "value": fcf_margin, 
                    "display": get_metric_display(fcf_margin),
                    "score": round(score_margin, 1), 
                    "max": 25
                },
                "Growth": {
                    "name": growth_metric,
                    "value": fcf_growth, 
                    "display": get_metric_display(fcf_growth),
                    "score": round(score_growth, 1), 
                    "max": 20
                },
                "Valuation": {
                    "name": "FCF Yield",
                    "value": fcf_yield, 
                    "display": get_metric_display(fcf_yield),
                    "score": round(score_val, 1), 
                    "max": 20
                }
            }
        }

    except Exception as e:
        return {"error": str(e)}

def main():
    if len(sys.argv) < 2:
        print("Usage: score.py <SYMBOL> [SYMBOL...]")
        sys.exit(1)

    tickers = sys.argv[1:]
    results = []

    print(f"\n🧠 **Quality Compounder Score (QCS)** Analysis")
    print(f"Targeting: ROIC > 20%, FCF Margin > 25%, Growth > 15%, FCF Yield > 4%\n")

    for ticker in tickers:
        data = analyze_ticker(ticker)
        if "error" in data:
            print(f"❌ **{ticker}**: {data['error']}")
            continue
        
        r = data
        m = r['metrics']
        
        print(f"**{r['symbol']}**: {r['emoji']} **{r['score']}/100** ({r['recommendation']})")
        print(f"   • ROIC: {m['ROIC']['display']} ({m['ROIC']['score']}/{m['ROIC']['max']})")
        print(f"   • Margin: {m['FCF Margin']['display']} ({m['FCF Margin']['score']}/{m['FCF Margin']['max']})")
        print(f"   • {m['Growth']['name']}: {m['Growth']['display']} ({m['Growth']['score']}/{m['Growth']['max']})")
        print(f"   • Valuation: {m['Valuation']['display']} ({m['Valuation']['score']}/{m['Valuation']['max']})")
        print("")

if __name__ == "__main__":
    main()
