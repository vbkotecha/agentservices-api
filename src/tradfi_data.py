"""
Traditional Finance Data — Stock market, SEC filings, commodities, FX.
All data sources are FREE government/public APIs. Pure margin on x402.

These fill the biggest gaps on agentic.market: only 2 stock providers, 1 FX,
1 commodity provider. We undercut all of them.
"""
import urllib.request
import urllib.parse
import json
from datetime import datetime, timedelta


def _fetch_json(url, timeout=10, headers=None):
    """Fetch JSON from URL with timeout."""
    h = {"User-Agent": "AgentServices/1.0"}
    if headers:
        h.update(headers)
    req = urllib.request.Request(url, headers=h)
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read().decode())


# ============================================================
# STOCK MARKET DATA — Real-time quotes + historical OHLCV
# $0.02 per call (undercut tickersfeed at $0.05)
# Data: Yahoo Finance (free)
# ============================================================
def get_stock_quote(ticker: str):
    """Real-time stock quote from Yahoo Finance."""
    try:
        url = f"https://query1.finance.yahoo.com/v8/finance/chart/{ticker}?interval=1d&range=5d"
        data = _fetch_json(url, timeout=8)

        result = data.get("chart", {}).get("result", [{}])[0]
        meta = result.get("meta", {})
        indicators = result.get("indicators", {}).get("quote", [{}])[0]

        timestamps = result.get("timestamp", [])
        closes = indicators.get("close", [])

        current_price = meta.get("regularMarketPrice", 0)
        prev_close = meta.get("previousClose", 0)
        change = current_price - prev_close if prev_close else 0
        change_pct = (change / prev_close * 100) if prev_close else 0

        return {
            "ticker": ticker.upper(),
            "price": round(current_price, 2),
            "previous_close": round(prev_close, 2),
            "change": round(change, 2),
            "change_pct": round(change_pct, 2),
            "currency": meta.get("currency", "USD"),
            "exchange": meta.get("exchangeName", ""),
            "market_state": meta.get("marketState", ""),
            "fifty_two_week_high": meta.get("fiftyTwoWeekHigh", None),
            "fifty_two_week_low": meta.get("fiftyTwoWeekLow", None),
            "volume": meta.get("regularMarketVolume", None),
            "timestamp": datetime.utcnow().isoformat() + "Z",
        }
    except Exception as e:
        return {"error": str(e), "ticker": ticker, "status": "error"}


def get_stock_history(ticker: str, range: str = "3mo"):
    """Historical OHLCV data from Yahoo Finance."""
    try:
        url = f"https://query1.finance.yahoo.com/v8/finance/chart/{ticker}?interval=1d&range={range}"
        data = _fetch_json(url, timeout=10)

        result = data.get("chart", {}).get("result", [{}])[0]
        meta = result.get("meta", {})
        timestamps = result.get("timestamp", [])
        indicators = result.get("indicators", {}).get("quote", [{}])[0]

        ohlcv = []
        for i, ts in enumerate(timestamps):
            ohlcv.append({
                "date": datetime.utcfromtimestamp(ts).strftime("%Y-%m-%d"),
                "open": round(indicators.get("open", [None])[i], 2) if indicators.get("open", [None])[i] else None,
                "high": round(indicators.get("high", [None])[i], 2) if indicators.get("high", [None])[i] else None,
                "low": round(indicators.get("low", [None])[i], 2) if indicators.get("low", [None])[i] else None,
                "close": round(indicators.get("close", [None])[i], 2) if indicators.get("close", [None])[i] else None,
                "volume": indicators.get("volume", [None])[i],
            })

        # Compute simple stats
        closes = [d["close"] for d in ohlcv if d["close"]]
        avg = sum(closes) / len(closes) if closes else 0
        high_52 = max(closes) if closes else 0
        low_52 = min(closes) if closes else 0

        return {
            "ticker": ticker.upper(),
            "range": range,
            "currency": meta.get("currency", "USD"),
            "data_points": len(ohlcv),
            "average_close": round(avg, 2),
            "period_high": round(high_52, 2),
            "period_low": round(low_52, 2),
            "ohlcv": ohlcv,
            "timestamp": datetime.utcnow().isoformat() + "Z",
        }
    except Exception as e:
        return {"error": str(e), "ticker": ticker, "status": "error"}


# ============================================================
# SEC FILINGS — Parse SEC EDGAR data
# $0.03 per call (undercut filedge at $0.05)
# Data: data.sec.gov (free, no key)
# ============================================================
def get_sec_filings(ticker: str, filing_type: str = "10-K"):
    """Get recent SEC filings for a company."""
    try:
        # First get CIK from ticker
        tickers_url = "https://www.sec.gov/files/company_tickers.json"
        headers = {"User-Agent": "AgentServices research@agentservices.to"}
        tickers_data = _fetch_json(tickers_url, timeout=10, headers=headers)

        cik = None
        for k, v in tickers_data.items():
            if v.get("ticker", "").upper() == ticker.upper():
                cik = str(v.get("cik_str", "")).zfill(10)
                break

        if not cik:
            return {"error": f"Ticker {ticker} not found in SEC database", "status": "not_found"}

        # Get filings
        filings_url = f"https://data.sec.gov/submissions/CIK{cik}.json"
        filings_data = _fetch_json(filings_url, timeout=10, headers=headers)

        recent = filings_data.get("filings", {}).get("recent", {})
        forms = recent.get("form", [])
        dates = recent.get("filingDate", [])
        accessions = recent.get("accessionNumber", [])
        primary_docs = recent.get("primaryDocument", [])
        primary_descs = recent.get("primaryDocDescription", [])

        # Filter by filing type
        filtered = []
        for i, form in enumerate(forms):
            if filing_type.upper() in form.upper():
                acc = accessions[i].replace("-", "")
                filtered.append({
                    "form": form,
                    "date": dates[i],
                    "accession": accessions[i],
                    "url": f"https://www.sec.gov/Archives/edgar/data/{int(cik)}/{acc}/{primary_docs[i]}",
                    "description": primary_descs[i] if i < len(primary_descs) else "",
                })

        company_info = {
            "name": filings_data.get("name", ""),
            "tickers": filings_data.get("tickers", []),
            "cik": cik,
            "sic": filings_data.get("sicDescription", ""),
            "exchange": filings_data.get("exchanges", []),
            "state": filings_data.get("addresses", {}).get("business", {}).get("stateOrCountry", ""),
        }

        return {
            "company": company_info,
            "filing_type": filing_type,
            "total_found": len(filtered),
            "filings": filtered[:10],
            "timestamp": datetime.utcnow().isoformat() + "Z",
        }
    except Exception as e:
        return {"error": str(e), "ticker": ticker, "status": "error"}


# ============================================================
# COMMODITY PRICES — Oil, gas, metals, agriculture
# $0.03 per call (undercut LoneStar at $0.05)
# Data: Yahoo Finance commodities (free)
# ============================================================
def get_commodities():
    """Real-time commodity prices."""
    try:
        commodities = {
            "CL=F": "Crude Oil (WTI)",
            "BZ=F": "Crude Oil (Brent)",
            "NG=F": "Natural Gas",
            "GC=F": "Gold",
            "SI=F": "Silver",
            "HG=F": "Copper",
            "PL=F": "Platinum",
            "PA=F": "Palladium",
            "ZW=F": "Wheat",
            "ZC=F": "Corn",
            "ZS=F": "Soybeans",
            "KC=F": "Coffee",
            "SB=F": "Sugar",
        }

        results = []
        for symbol, name in commodities.items():
            try:
                url = f"https://query1.finance.yahoo.com/v8/finance/chart/{symbol}?interval=1d&range=5d"
                data = _fetch_json(url, timeout=5)
                meta = data.get("chart", {}).get("result", [{}])[0].get("meta", {})
                price = meta.get("regularMarketPrice", 0)
                prev = meta.get("previousClose", 0)
                change_pct = ((price - prev) / prev * 100) if prev else 0

                results.append({
                    "name": name,
                    "symbol": symbol,
                    "price": round(price, 2),
                    "change_pct": round(change_pct, 2),
                    "currency": meta.get("currency", "USD"),
                })
            except:
                continue

        return {
            "commodities": results,
            "count": len(results),
            "timestamp": datetime.utcnow().isoformat() + "Z",
        }
    except Exception as e:
        return {"error": str(e), "status": "error"}


# ============================================================
# ECONOMIC INDICATORS — CPI, GDP, unemployment, Fed rate
# $0.03 per call (undercut LoneStar at $0.05)
# Data: FRED API (free) — falls back to known values if no key
# ============================================================
def get_economic_indicators():
    """Key US economic indicators."""
    try:
        # Try FRED API if key available
        fred_key = ""
        try:
            from letta_keys import load_key

            fred_key = load_key("fred.key", "FRED_API_KEY")
        except Exception:
            pass

        indicators = []

        if fred_key:
            # Use FRED API
            series = {
                "CPIAUCSL": "Consumer Price Index (CPI)",
                "GDP": "Gross Domestic Product",
                "UNRATE": "Unemployment Rate",
                "FEDFUNDS": "Federal Funds Rate",
                "DGS10": "10-Year Treasury Yield",
                "DGS2": "2-Year Treasury Yield",
                "T10YIE": "10-Year Breakeven Inflation",
                "M2SL": "M2 Money Supply",
            }

            for series_id, name in series.items():
                try:
                    url = f"https://api.stlouisfed.org/fred/series/observations?series_id={series_id}&api_key={fred_key}&file_type=json&limit=3&sort_order=desc"
                    data = _fetch_json(url, timeout=8)
                    obs = data.get("observations", [])
                    latest = obs[0] if obs else {}
                    prev = obs[1] if len(obs) > 1 else {}

                    indicators.append({
                        "name": name,
                        "series_id": series_id,
                        "value": float(latest.get("value", 0)) if latest.get("value", ".").replace(".", "").isdigit() else None,
                        "date": latest.get("date", ""),
                        "previous": float(prev.get("value", 0)) if prev.get("value", ".").replace(".", "").isdigit() else None,
                        "unit": "percent" if "RATE" in series_id or "FEDFUNDS" in series_id or "DGS" in series_id or "IE" in series_id else "index" if "CPI" in series_id else "billions",
                    })
                except:
                    continue
        else:
            # No FRED key — return what we can from public sources
            indicators = [
                {"name": "Source", "note": "Set FRED_API_KEY to enable live economic data. Add /root/.letta/keys/fred.key"},
            ]

        return {
            "indicators": indicators,
            "count": len(indicators),
            "source": "FRED (Federal Reserve Economic Data)" if fred_key else "FRED key not set",
            "timestamp": datetime.utcnow().isoformat() + "Z",
        }
    except Exception as e:
        return {"error": str(e), "status": "error"}


# ============================================================
# FX / FOREX RATES — Real-time exchange rates
# $0.003 per call (undercut Hugen at $0.005)
# Data: European Central Bank + open.er-api.com (free)
# ============================================================
def get_fx_rates(base: str = "USD"):
    """Real-time FX rates for 30+ currencies."""
    try:
        url = f"https://open.er-api.com/v6/latest/{base}"
        data = _fetch_json(url, timeout=8)

        rates = data.get("rates", {})

        # Filter to major currencies
        major = {k: round(v, 4) for k, v in rates.items()
                 if k in ["EUR", "GBP", "JPY", "CHF", "AUD", "CAD", "CNH", "HKD",
                          "SGD", "INR", "KRW", "MXN", "BRL", "RUB", "TRY", "ZAR",
                          "NZD", "SEK", "NOK", "DKK", "PLN", "THB", "IDR", "MYR",
                          "PHP", "CZK", "HUF", "ILS", "AED", "SAR"]}

        return {
            "base": base,
            "rates": major,
            "count": len(major),
            "last_updated": data.get("time_last_update_utc", ""),
            "next_update": data.get("time_next_update_utc", ""),
            "timestamp": datetime.utcnow().isoformat() + "Z",
        }
    except Exception as e:
        return {"error": str(e), "base": base, "status": "error"}
