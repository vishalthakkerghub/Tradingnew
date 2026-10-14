"""
Chart payload builder for the stock chart view (served by /api/stock_chart).

Everything is derived from data the system already has:
  - OHLCV from the local cache (data/cache/<SYMBOL>.csv, yfinance-adjusted)
  - SMA/EMA computed here on the full cached history
  - Consolidation zones from FlagEngine, evaluated "as of" each historical bar
    (only past bars are used for detection, so no lookahead in *finding* a zone;
    the breakout / failure outcome is marked with hindsight, as on any chart)
"""
import json
import logging
import os
from datetime import date, datetime

import numpy as np
import pandas as pd

from src.flag_engine import FlagEngine

logger = logging.getLogger("ChartData")

MIN_BARS_FOR_ZONES = 50      # FlagEngine needs >= 50 bars of history
OUTCOME_LOOKAHEAD = 10       # bars after a zone in which a breakout / failure is looked for
ACTIVE_WITHIN = 3            # a zone ending within this many bars of the last bar is still "active"


def _resolve(path: str) -> str:
    return path if os.path.exists(path) else os.path.join("minervini_os", path)


def load_ohlcv(symbol: str) -> pd.DataFrame:
    path = _resolve(os.path.join("data", "cache", f"{symbol.upper()}.csv"))
    if not os.path.exists(path):
        return pd.DataFrame()
    df = pd.read_csv(path, index_col="Date")
    df.index = df.index.astype(str).str.slice(0, 10)
    df = df[~df.index.duplicated(keep="last")].sort_index()
    for col in ("Open", "High", "Low", "Close", "Volume"):
        df[col] = pd.to_numeric(df[col], errors="coerce")
    df = df.dropna(subset=["Open", "High", "Low", "Close"])
    df = df[(df[["Open", "High", "Low", "Close"]] > 0).all(axis=1)]
    df["Volume"] = df["Volume"].fillna(0)
    return df


def _series(index, values):
    """[{time, value}] skipping NaN warm-up values."""
    return [{"time": t, "value": round(float(v), 2)} for t, v in zip(index, values) if not np.isnan(v)]


def detect_flag_zones(df: pd.DataFrame, config: dict, window: int) -> list:
    """Consolidation zones over the last `window` bars using the live FlagEngine rules."""
    n = len(df)
    if n < MIN_BARS_FOR_ZONES + 5:
        return []
    engine = FlagEngine(config)
    first = max(MIN_BARS_FOR_ZONES, n - window)
    hits = []   # (end_idx, start_idx, high, low)
    for i in range(first, n):
        try:
            ok, trigger, _stop, _t1, _t2, _rng, _vdu, length = engine.is_flag_candidate(df.iloc[: i + 1], None)
        except Exception:
            continue
        if ok and length:
            sub = df.iloc[i + 1 - length: i + 1]
            hits.append((i, i + 1 - length, float(sub["High"].max()), float(sub["Low"].min())))

    # Group consecutive detections into one zone each.
    runs, cur = [], []
    for h in hits:
        if cur and h[0] - cur[-1][0] > 2:
            runs.append(cur)
            cur = []
        cur.append(h)
    if cur:
        runs.append(cur)

    zones = []
    dates = list(df.index)
    for run in runs:
        s = min(r[1] for r in run)
        e = max(r[0] for r in run)
        high = max(r[2] for r in run)
        low = min(r[3] for r in run)
        outcome, out_idx = "ACTIVE" if e >= n - 1 - ACTIVE_WITHIN else "NO_BREAK", None
        for j in range(e + 1, min(n, e + 1 + OUTCOME_LOOKAHEAD)):
            c = float(df["Close"].iloc[j])
            if c > high:
                outcome, out_idx = "BREAKOUT", j
                break
            if c < low:
                outcome, out_idx = "FAILED", j
                break
        zones.append({
            "start": dates[s], "end": dates[e], "high": round(high, 2), "low": round(low, 2),
            "label": "FLAG", "outcome": outcome,
            "outcome_time": dates[out_idx] if out_idx is not None else None,
        })
    return zones


def earnings_info(symbol: str) -> dict:
    path = _resolve(os.path.join("data", "earnings_calendar.json"))
    try:
        with open(path, "r", encoding="utf-8") as f:
            row = json.load(f).get(symbol.upper())
        if row and row.get("Earnings_Date"):
            d = datetime.strptime(row["Earnings_Date"], "%Y-%m-%d").date()
            return {"date": row["Earnings_Date"], "days": (d - date.today()).days}
    except Exception:
        pass
    return {"date": None, "days": None}


def build_chart_payload(symbol: str, config: dict, bars: int = 250) -> dict:
    symbol = symbol.strip().upper()
    df = load_ohlcv(symbol)
    if df.empty or len(df) < 2:
        return {"symbol": symbol, "error": "No price history cached for this symbol."}

    close, vol = df["Close"], df["Volume"]
    ind = {
        "sma20": close.rolling(20).mean(), "sma50": close.rolling(50).mean(),
        "sma150": close.rolling(150).mean(), "sma200": close.rolling(200).mean(),
        "ema10": close.ewm(span=10, adjust=False).mean(), "ema20": close.ewm(span=20, adjust=False).mean(),
    }
    vol_sma50 = vol.rolling(50).mean()

    view = df.tail(bars)
    idx = list(view.index)
    last, prev = float(close.iloc[-1]), float(close.iloc[-2])
    hi_52w = float(df["High"].iloc[-252:].max())
    avg_vol_prior = float(vol.iloc[-51:-1].mean()) if len(vol) > 51 else float(vol.mean())

    return {
        "symbol": symbol,
        "as_of": df.index[-1],
        "candles": [{"time": t, "open": round(float(r.Open), 2), "high": round(float(r.High), 2),
                     "low": round(float(r.Low), 2), "close": round(float(r.Close), 2)}
                    for t, r in zip(idx, view.itertuples())],
        "volume": [{"time": t, "value": int(v), "up": bool(c >= o)}
                   for t, v, c, o in zip(idx, view["Volume"], view["Close"], view["Open"])],
        "vol_sma50": _series(idx, vol_sma50.reindex(idx).values),
        "indicators": {k: _series(idx, s.reindex(idx).values) for k, s in ind.items()},
        "zones": detect_flag_zones(df, config, window=min(bars, 200)),
        "stats": {
            "last": round(last, 2), "prev": round(prev, 2),
            "change_pct": round((last / prev - 1) * 100, 2) if prev else 0.0,
            "open": round(float(df["Open"].iloc[-1]), 2), "high": round(float(df["High"].iloc[-1]), 2),
            "low": round(float(df["Low"].iloc[-1]), 2), "volume": int(vol.iloc[-1]),
            "rvol": round(float(vol.iloc[-1]) / avg_vol_prior, 2) if avg_vol_prior > 0 else None,
            "high_52w": round(hi_52w, 2),
            "off_52w_high_pct": round((last / hi_52w - 1) * 100, 1) if hi_52w else None,
            "sma20": round(float(ind["sma20"].iloc[-1]), 2) if len(df) >= 20 else None,
            "bars": len(df),
        },
        "earnings": earnings_info(symbol),
    }
