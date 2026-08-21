"""
Skill Packs — Bundled endpoints that combine multiple calls into one high-value request.
Inspired by Agent402's skill system. Higher price, higher value.

Each skill calls multiple internal endpoints and synthesizes results.
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from synthesis_data import get_token_risk, get_crypto_signal
from crypto_data import get_price, get_indicators, get_fear_greed
from onchain_data import get_whales, get_correlation_matrix
from tradfi_data import get_stock_quote, get_fx_rates


def crypto_dossier(symbol: str):
    """
    Crypto Dossier — Full intelligence report on a cryptocurrency.
    Combines: price + indicators + risk score + trading signal + fear/greed + whale activity.
    One call, one price, full picture.
    """
    result = {
        "symbol": symbol.upper(),
        "timestamp": None,
        "price": None,
        "indicators": None,
        "risk": None,
        "signal": None,
        "fear_greed": None,
        "whales": None,
    }

    # Price (free internally)
    try:
        result["price"] = get_price(symbol)
    except: pass

    # Indicators
    try:
        result["indicators"] = get_indicators(symbol)
    except: pass

    # Risk score
    cg_map = {"BTC": "bitcoin", "ETH": "ethereum", "SOL": "solana", "XRP": "ripple"}
    cg_id = cg_map.get(symbol.upper(), symbol.lower())
    try:
        result["risk"] = get_token_risk(cg_id)
    except: pass

    # Signal
    try:
        result["signal"] = get_crypto_signal(symbol)
    except: pass

    # Fear & Greed
    try:
        result["fear_greed"] = get_fear_greed()
    except: pass

    # Whales
    try:
        result["whales"] = get_whales()
    except: pass

    import datetime
    result["timestamp"] = datetime.datetime.utcnow().isoformat() + "Z"

    # Generate summary
    signal = result.get("signal", {})
    risk = result.get("risk", {})
    price_data = result.get("price", {})

    summary_parts = []
    if price_data and "price_usd" in price_data:
        summary_parts.append(f"{symbol} at ${price_data.get('price_usd', 0):,.2f}")
    if signal and "action" in signal:
        summary_parts.append(f"Signal: {signal['action']} ({signal.get('confidence', 'unknown')} confidence)")
    if risk and "risk_label" in risk:
        summary_parts.append(f"Risk: {risk['risk_label']} ({risk.get('risk_score', '?')}/100)")

    result["summary"] = " | ".join(summary_parts) if summary_parts else "Partial data available"
    result["recommendation"] = signal.get("action", "HOLD") if signal else "INSUFFICIENT_DATA"

    return result


def stock_dossier(ticker: str):
    """
    Stock Dossier — Full intelligence report on a stock.
    Combines: real-time quote + risk context + FX rates for international comparison.
    """
    result = {
        "ticker": ticker.upper(),
        "timestamp": None,
        "quote": None,
        "fx": None,
    }

    try:
        result["quote"] = get_stock_quote(ticker)
    except: pass

    try:
        result["fx"] = get_fx_rates("USD")
    except: pass

    import datetime
    result["timestamp"] = datetime.datetime.utcnow().isoformat() + "Z"

    quote = result.get("quote", {})
    price = quote.get("price", 0)
    change_pct = quote.get("change_pct", 0)

    if change_pct > 2:
        sentiment = "bullish"
    elif change_pct < -2:
        sentiment = "bearish"
    else:
        sentiment = "neutral"

    result["summary"] = f"{ticker} at ${price:,.2f} ({change_pct:+.2f}%) — {sentiment}"
    result["sentiment"] = sentiment

    return result


def market_overview():
    """
    Market Pulse — Full market overview in one call.
    Combines: fear/greed + global market data + trending + whale activity + BTC signal.
    """
    result = {
        "timestamp": None,
        "fear_greed": None,
        "btc_signal": None,
        "whales": None,
    }

    try:
        result["fear_greed"] = get_fear_greed()
    except: pass

    try:
        result["btc_signal"] = get_crypto_signal("BTC")
    except: pass

    try:
        result["whales"] = get_whales()
    except: pass

    import datetime
    result["timestamp"] = datetime.datetime.utcnow().isoformat() + "Z"

    fg = result.get("fear_greed", {})
    fg_value = fg.get("value", 50) if isinstance(fg, dict) else 50
    signal = result.get("btc_signal", {})
    action = signal.get("action", "HOLD") if signal else "HOLD"

    if fg_value < 25:
        regime = "EXTREME FEAR — potential buy zone"
    elif fg_value < 45:
        regime = "FEAR — cautious accumulation"
    elif fg_value < 55:
        regime = "NEUTRAL — range-bound"
    elif fg_value < 75:
        regime = "GREED — consider taking profits"
    else:
        regime = "EXTREME GREED — potential sell zone"

    result["regime"] = regime
    result["btc_action"] = action
    result["summary"] = f"Fear/Greed: {fg_value} ({regime}) | BTC Signal: {action}"

    return result


def available_skills():
    """List available skill packs."""
    return {
        "skills": [
            {
                "name": "crypto_dossier",
                "endpoint": "POST /v1/skills/crypto-dossier",
                "description": "Full crypto intelligence: price + indicators + risk + signal + fear/greed + whales",
                "price": "$0.10",
                "inputs": {"symbol": "string (e.g., BTC, ETH)"},
            },
            {
                "name": "stock_dossier",
                "endpoint": "POST /v1/skills/stock-dossier",
                "description": "Full stock intelligence: quote + FX rates for international comparison",
                "price": "$0.05",
                "inputs": {"ticker": "string (e.g., AAPL, TSLA)"},
            },
            {
                "name": "market_overview",
                "endpoint": "GET /v1/skills/market-overview",
                "description": "Full market pulse: fear/greed + BTC signal + whale activity + regime classification",
                "price": "$0.05",
                "inputs": {},
            },
        ]
    }
