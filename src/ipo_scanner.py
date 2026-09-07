"""
IPO Base scanner - a relaxed VCP-style base detector for recently-listed stocks,
which the standard Trend Template / VCP engine can't evaluate at all (both hard-
require ~250 trading days of history a young issue doesn't have for months).

Methodology (Minervini's documented approach to young issues, adapted for NSE):
  - Don't chase the first days/weeks post-listing (grey-market-premium-driven
    noise, no real chart yet) - MIN_DAYS_SINCE_LISTING skips this window.
  - Wait for the stock's FIRST real base: a genuine consolidation with
    contracting volatility and volume dry-up. Reuses VCPEngine's existing
    pivot/contraction/VDU logic under the "IPO" profile added to vcp_engine.py
    (shorter min/max base duration, looser sensitivity/tolerance/VDU threshold
    than STRICT/FLEX/MINI, since there's far less history to work with).
  - Tracks performance since the IPO offer price and relative strength vs the
    index over whatever window is actually available (not a fixed 90 days),
    since the standard Trend Template's 150/200-day rules can't be computed.
  - Lock-in-expiry tracking intentionally deferred (2026-09-08, per user
    decision) - add later if/when wanted.

Data sources:
  - IPO calendar (symbol, price band, subscription dates): NSE's public API,
    verified live and working 2026-09-08:
    https://www.nseindia.com/api/all-upcoming-issues?category=ipo
    Requires priming a session against the NSE homepage first (same pattern
    already used in data_ingestion.py's _fetch_nse_index_via_nselib) or NSE's
    bot-protection returns 403. This only lists CURRENTLY-OPEN subscriptions -
    once one closes it drops off NSE's feed, so discovered symbols are
    accumulated into data/ipo_watchlist.json (never removed) rather than
    replaced on every fetch, so we don't lose track of it once it lists.
  - Manual additions: config/ipo_watchlist.json (git-tracked, human-edited) -
    merged in every sync, for anything NSE's feed misses (e.g. SME-platform
    IPOs) or that you want to track ahead of/independent of the NSE feed.
  - Price history: the existing DataIngestionEngine (yfinance), same as every
    other stock in this system.

IMPORTANT SAFETY NOTE: DataIngestionEngine.fetch_historical_ohlcv() does NOT
fail cleanly when a symbol has no real data available (e.g. a stock that
hasn't listed yet) - it silently generates simulated price data and caches it
as if real (see data_ingestion.py's _generate_simulated_ohlcv, "offline
compatibility" fallback). For a scanner whose whole job is evaluating stocks
that may genuinely have zero trading history, this is a real trap - it would
happily fabricate a fake "base" for a stock that hasn't traded a single day.
This module guards against it explicitly: it never fetches price data for a
symbol until enough time has plausibly passed for it to have actually listed
(EXPECTED_LISTING_BUFFER_DAYS after the subscription closed), and sanity-
checks the row count returned against how many trading days could plausibly
exist since then - see _looks_like_real_data().

This is kept fully separate from the main scan (does not feed
strategic_watchlist, daily_focus_watchlist, or True Paper Trading) until it's
been observed and backtested the same way every other rule in this system has
been - see memory: minervini-os-fix-plan for why that discipline matters here.
"""
import os
import re
import json
import logging
from datetime import datetime, timedelta

import pandas as pd

logger = logging.getLogger("IPOScanner")

TRACKED_FILE = "data/ipo_watchlist.json"      # auto-accumulated, persists on the volume
MANUAL_FILE = "config/ipo_watchlist.json"     # human-edited, git-tracked, merged in every sync
REPORT_DIR = "reports/daily"

MIN_DAYS_SINCE_LISTING = 10   # ~2 weeks - skip the noisy listing-pop window
EXPECTED_LISTING_BUFFER_DAYS = 5   # calendar days after subscription close before we
                                     # even attempt a price fetch (SEBI T+3 listing norm
                                     # + a settling buffer), to avoid tripping the
                                     # simulated-data fallback on a not-yet-listed symbol


def _resolve_path(path):
    """Mirrors the fallback pattern used throughout this codebase for the
    root-vs-minervini_os working-directory ambiguity."""
    if os.path.exists(path):
        return path
    alt = os.path.join("minervini_os", path)
    return alt if os.path.exists(alt) else path


def fetch_nse_ipo_calendar():
    """
    Pulls currently-open IPO subscriptions from NSE's public API. Returns a
    list of dicts: {symbol, company_name, price_low, price_high, issue_start,
    issue_end, status}. Returns [] (logged, not raised) on any failure - this
    is a best-effort external fetch, not something that should ever crash the
    daily scan.
    """
    try:
        import requests
    except ImportError:
        logger.error("requests library not available - cannot fetch NSE IPO calendar.")
        return []

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                       "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "application/json",
        "Accept-Language": "en-US,en;q=0.9",
    }
    session = requests.Session()
    try:
        # NSE blocks direct API calls without first priming session cookies
        # against the homepage (same requirement data_ingestion.py already
        # works around for index data). The homepage itself may still return
        # a non-200 (it's aggressively bot-gated) - that's fine, the cookies
        # set during the attempt are usually enough for the API call itself.
        session.get("https://www.nseindia.com", headers=headers, timeout=10)
    except Exception as e:
        logger.warning(f"NSE homepage priming request failed (continuing anyway): {e}")

    try:
        resp = session.get(
            "https://www.nseindia.com/api/all-upcoming-issues?category=ipo",
            headers=headers, timeout=15
        )
        if resp.status_code != 200:
            logger.error(f"NSE IPO calendar fetch failed: HTTP {resp.status_code}")
            return []
        raw = resp.json()
    except Exception as e:
        logger.error(f"NSE IPO calendar fetch failed: {e}")
        return []

    results = []
    for item in raw:
        symbol = (item.get("symbol") or "").strip().upper()
        if not symbol:
            continue
        price_low, price_high = _parse_price_band(item.get("issuePrice", ""))
        results.append({
            "symbol": symbol,
            "company_name": item.get("companyName", symbol),
            "price_low": price_low,
            "price_high": price_high,
            "issue_start": _parse_nse_date(item.get("issueStartDate", "")),
            "issue_end": _parse_nse_date(item.get("issueEndDate", "")),
            "status": item.get("status", ""),
            "source": "nse_api",
        })
    logger.info(f"NSE IPO calendar: {len(results)} currently-open issue(s) found.")
    return results


def _parse_price_band(price_str):
    """'Rs.643 to Rs.676' -> (643.0, 676.0). 'Rs.100' -> (100.0, 100.0). '' -> (0.0, 0.0)."""
    nums = re.findall(r"[\d,]+\.?\d*", price_str or "")
    nums = [float(n.replace(",", "")) for n in nums if n]
    if len(nums) >= 2:
        return nums[0], nums[1]
    if len(nums) == 1:
        return nums[0], nums[0]
    return 0.0, 0.0


def _parse_nse_date(date_str):
    """'10-Sep-2026' -> '2026-09-10'. Returns '' on failure."""
    try:
        return datetime.strptime(date_str.strip(), "%d-%b-%Y").strftime("%Y-%m-%d")
    except Exception:
        return ""


def fetch_nse_past_issues():
    """
    Pulls NSE's own record of CLOSED equity IPOs - unlike all-upcoming-issues
    (only currently-open subscriptions), this goes back 100+ days and, crucially,
    carries the real issue price alongside a real listing date. This is the
    backfill source for everything that already listed before we started
    tracking it going forward via fetch_nse_ipo_calendar().

    Two kinds of noise get filtered out here (found by inspecting the raw
    response): NCD/bond tranches sharing this same feed (symbols following
    NSE's debt-security convention of a leading coupon-rate digit, e.g.
    "904NACL28", with issuePrice in the thousands - a face value, not a
    share price), and the same company appearing multiple times for
    separate bond tranches. Both are dropped; only genuine equity IPOs with
    a plausible per-share price remain. (A separate, worse form of noise
    was ruled out earlier: NSE's raw equity master list (EQUITY_L.csv)
    lists 205 "recently listed" symbols in the same window, but 146 of them
    share a single listing date - a bulk technical relisting event, not
    real IPOs - which is why that source isn't used here.)
    """
    try:
        import requests
    except ImportError:
        logger.error("requests library not available - cannot fetch NSE past-issues.")
        return []

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                       "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "application/json",
    }
    session = requests.Session()
    try:
        session.get("https://www.nseindia.com", headers=headers, timeout=10)
    except Exception as e:
        logger.warning(f"NSE homepage priming request failed (continuing anyway): {e}")

    try:
        resp = session.get(
            "https://www.nseindia.com/api/public-past-issues?index=equity",
            headers=headers, timeout=15
        )
        if resp.status_code != 200:
            logger.error(f"NSE past-issues fetch failed: HTTP {resp.status_code}")
            return []
        raw = resp.json()
    except Exception as e:
        logger.error(f"NSE past-issues fetch failed: {e}")
        return []

    seen_symbols = set()
    results = []
    for item in raw:
        symbol = (item.get("symbol") or "").strip().upper()
        listing_date_raw = item.get("listingDate", "-")
        issue_price_raw = (item.get("issuePrice") or "").strip()

        if not symbol or symbol in seen_symbols:
            continue
        if not listing_date_raw or listing_date_raw == "-":
            continue  # hasn't actually listed yet, or NSE hasn't recorded it
        if symbol[0].isdigit():
            continue  # debt/NCD tranche naming convention, not an equity IPO

        try:
            issue_price = float(issue_price_raw.replace(",", ""))
        except (ValueError, AttributeError):
            continue  # "-" or "######" (Excel-width artifact for a large face value)
        if issue_price <= 0 or issue_price > 5000:
            continue  # sanity cap - genuine equity IPO price bands don't run this high

        listing_date = _parse_nse_date(listing_date_raw)
        if not listing_date:
            continue

        seen_symbols.add(symbol)
        low, high = _parse_price_band(item.get("priceRange", ""))
        results.append({
            "symbol": symbol,
            "company_name": item.get("company", symbol),
            "issue_price": issue_price,
            "price_low": low or issue_price,
            "price_high": high or issue_price,
            "listing_date": listing_date,
            "source": "nse_api_past",
        })
    logger.info(f"NSE past-issues: {len(results)} closed equity IPO(s) with a valid listing date found.")
    return results


def load_tracked_ipos():
    """Self-healing load of the auto-accumulated tracked list."""
    path = _resolve_path(TRACKED_FILE)
    if not os.path.exists(path):
        os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            json.dump([], f)
        return []
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        logger.error(f"Failed to load {TRACKED_FILE} ({e}) - starting fresh, not overwriting the file until next successful save.")
        return []


def save_tracked_ipos(tracked_list):
    path = _resolve_path(TRACKED_FILE)
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(tracked_list, f, indent=2)


def load_manual_ipos():
    """
    config/ipo_watchlist.json entries: [{"symbol", "listing_date", "offer_price"},...]
    A manual entry already has a known listing_date and a single offer_price
    (not a band), since you'd typically add these once you already know the
    stock listed - simpler shape than the NSE-sourced ones.
    """
    path = _resolve_path(MANUAL_FILE)
    if not os.path.exists(path):
        return []
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        logger.error(f"Failed to load {MANUAL_FILE}: {e}")
        return []


def sync_ipo_watchlist():
    """
    Merges NSE-fetched (both currently-open subscriptions and the closed-
    issue backfill) + manual entries into the accumulated tracked list.
    Never deletes an existing tracked entry (an entry naturally dropping out
    of a fresh NSE fetch just means it closed/listed - exactly the ones we
    most want to keep watching for a base to form).

    Every tracked entry ends up with two distinct date fields where known:
    `issue_end_date` (subscription close - a proxy, used only until the
    stock has actually listed) and `listing_date` (the real, confirmed
    listing date, once NSE's past-issues feed reports one - always
    preferred over the proxy once available).
    """
    tracked = {t["symbol"]: t for t in load_tracked_ipos()}

    nse_ipos = fetch_nse_ipo_calendar()
    for item in nse_ipos:
        sym = item["symbol"]
        if sym not in tracked:
            tracked[sym] = {
                "symbol": sym,
                "company_name": item["company_name"],
                "offer_price": round((item["price_low"] + item["price_high"]) / 2.0, 2),
                "price_low": item["price_low"],
                "price_high": item["price_high"],
                "issue_end_date": item["issue_end"],
                "listing_date": "",
                "source": "nse_api",
                "first_seen": datetime.now().strftime("%Y-%m-%d"),
            }
            logger.info(f"New IPO discovered via NSE feed: {sym} ({item['company_name']}), offer band Rs.{item['price_low']}-{item['price_high']}")

    past_ipos = fetch_nse_past_issues()
    for item in past_ipos:
        sym = item["symbol"]
        if sym in tracked:
            # Backfill/upgrade: a real listing_date + confirmed issue_price
            # beats whatever proxy we had (or fills a gap entirely).
            if not tracked[sym].get("listing_date"):
                tracked[sym]["listing_date"] = item["listing_date"]
            if not tracked[sym].get("offer_price"):
                tracked[sym]["offer_price"] = item["issue_price"]
        else:
            tracked[sym] = {
                "symbol": sym,
                "company_name": item["company_name"],
                "offer_price": item["issue_price"],
                "price_low": item["price_low"],
                "price_high": item["price_high"],
                "issue_end_date": "",
                "listing_date": item["listing_date"],
                "source": "nse_api_past",
                "first_seen": datetime.now().strftime("%Y-%m-%d"),
            }

    for item in load_manual_ipos():
        sym = (item.get("symbol") or "").strip().upper()
        if not sym:
            continue
        offer_price = float(item.get("offer_price", 0) or 0)
        if sym not in tracked:
            tracked[sym] = {
                "symbol": sym,
                "company_name": item.get("company_name", sym),
                "offer_price": offer_price,
                "price_low": offer_price,
                "price_high": offer_price,
                "issue_end_date": "",
                "listing_date": item.get("listing_date", ""),
                "source": "manual",
                "first_seen": datetime.now().strftime("%Y-%m-%d"),
            }
            logger.info(f"New IPO added manually: {sym}")

    tracked_list = list(tracked.values())
    save_tracked_ipos(tracked_list)
    return tracked_list


def _looks_like_real_data(df, reference_date_str):
    """
    Guards against DataIngestionEngine's simulated-data fallback (see module
    docstring). Rejects the data if it has far more history than could
    plausibly exist for a stock that (per our own IPO calendar) only listed
    recently - that pattern means we're looking at either simulated data or
    an unrelated stock that happens to share the ticker.
    """
    if df is None or df.empty:
        return False
    if not reference_date_str:
        # No date to sanity-check against - fall back to a conservative cap
        return len(df) <= 300
    try:
        ref_date = datetime.strptime(reference_date_str, "%Y-%m-%d")
    except Exception:
        return len(df) <= 300
    calendar_days_since = (datetime.now() - ref_date).days
    # Generous upper bound: ~72% of calendar days are trading days, plus a
    # week of slack for date-parsing/timezone edge cases.
    plausible_max_bars = max(15, int(calendar_days_since * 0.8) + 7)
    if len(df) > plausible_max_bars:
        logger.warning(
            f"Data for this symbol has {len(df)} bars, more than plausible "
            f"({plausible_max_bars}) for an issue referenced against "
            f"{reference_date_str} - likely the simulated-data fallback or a "
            f"ticker collision, not real IPO history. Skipping."
        )
        return False
    return True


def get_ipo_status(ingestion_engine, entry, index_df=None):
    """
    Fetches real price data for one tracked IPO entry (with the simulated-
    data guard applied) and returns a plain status dict - current price,
    days since listing, performance since offer, RS vs index - regardless
    of whether it has formed a VCP base yet. Returns None if the symbol
    isn't plausibly listed/tradeable yet, or if the data doesn't pass the
    simulated-data sanity check.

    This is the broader building block behind build_bucket_report(); a
    stricter VCP-base check on top of this same fetched df is what
    evaluate_ipo_candidate() below adds for the daily scan.
    """
    symbol = entry["symbol"]
    offer_price = float(entry.get("offer_price", 0) or 0)
    listing_date = entry.get("listing_date", "")
    issue_end_date = entry.get("issue_end_date", "")
    reference_date = listing_date or issue_end_date

    if offer_price <= 0:
        return None

    if listing_date:
        # Confirmed real listing date - no need to wait out a buffer, it has
        # definitely listed.
        pass
    elif issue_end_date:
        try:
            end_dt = datetime.strptime(issue_end_date, "%Y-%m-%d")
            if (datetime.now() - end_dt).days < EXPECTED_LISTING_BUFFER_DAYS:
                logger.info(f"{symbol}: subscription closed too recently ({issue_end_date}) - not plausibly listed and trading yet, skipping fetch.")
                return None
        except Exception:
            pass
    else:
        logger.info(f"{symbol}: no listing date or subscription-close date on record - skipping.")
        return None

    df = ingestion_engine.fetch_historical_ohlcv(symbol, lookback_days=250)
    if not _looks_like_real_data(df, reference_date):
        return None

    days_since_listing = len(df)
    current_price = float(df["Close"].iloc[-1])
    pct_from_offer = ((current_price - offer_price) / offer_price * 100.0) if offer_price > 0 else 0.0

    rs_window = min(days_since_listing, 90)
    rs_vs_index = None
    try:
        stock_return = (current_price / float(df["Close"].iloc[-rs_window]) - 1.0) * 100.0
        if index_df is not None and len(index_df) >= rs_window:
            index_return = (float(index_df["Close"].iloc[-1]) / float(index_df["Close"].iloc[-rs_window]) - 1.0) * 100.0
            rs_vs_index = round(stock_return - index_return, 1)
    except Exception as e:
        logger.warning(f"{symbol}: RS calculation failed: {e}")

    return {
        "symbol": symbol,
        "company_name": entry.get("company_name", symbol),
        "listing_date": listing_date,
        "days_since_listing": days_since_listing,
        "offer_price": offer_price,
        "current_price": round(current_price, 2),
        "pct_from_offer": round(pct_from_offer, 1),
        "rs_vs_index": rs_vs_index,
        "df": df,
    }


DAY_BUCKETS = [5, 10, 20, 30, 60, 100]


def _bucket_label(days_since_listing):
    """Places a stock into the tightest cohort in DAY_BUCKETS it has crossed,
    e.g. 27 trading days -> the '30' bucket (21-30 range)."""
    prev = 0
    for b in DAY_BUCKETS:
        if prev < days_since_listing <= b:
            return f"{prev+1}-{b}d"
        prev = b
    return f"{DAY_BUCKETS[-1]}d+"


def build_bucket_report(vcp_engine=None, ingestion_engine=None):
    """
    Groups every tracked IPO by days-since-listing into the cohorts a swing
    trader actually cares about (5/10/20/30/60/100 days), showing current
    performance since offer and whether a VCP-style base has formed yet -
    the report Vishal asked for directly ("ipo that are trading since
    5-10-20-30-60-100 days"). Unlike scan_ipos()/evaluate_ipo_candidate(),
    this returns EVERY tradeable tracked IPO, not just ones that already
    qualify as a base candidate - the point here is visibility into the
    whole recent-IPO universe at each stage of its life, not just picks.
    """
    if vcp_engine is None:
        from vcp_engine import VCPEngine
        vcp_engine = VCPEngine({"vcp_parameters": {}})
    if ingestion_engine is None:
        from data_ingestion import DataIngestionEngine
        ingestion_engine = DataIngestionEngine()

    tracked = sync_ipo_watchlist()
    index_df = None
    try:
        index_df = ingestion_engine.fetch_historical_ohlcv("NIFTY_50", lookback_days=100)
    except Exception as e:
        logger.warning(f"Could not load index data for RS calculation: {e}")

    buckets = {f"{([0]+DAY_BUCKETS)[i]+1}-{b}d": [] for i, b in enumerate(DAY_BUCKETS)}
    for entry in tracked:
        try:
            status = get_ipo_status(ingestion_engine, entry, index_df)
        except Exception as e:
            logger.error(f"Error evaluating {entry.get('symbol')}: {e}")
            continue
        if status is None:
            continue
        if status["days_since_listing"] > DAY_BUCKETS[-1]:
            continue  # outside the requested 100-day window entirely

        df = status.pop("df")
        try:
            is_candidate, pivot_price, grade, contraction_count, depths_str, vdu_ratio, final_low = \
                vcp_engine.is_vcp_candidate(df, mode="IPO")
        except Exception as e:
            logger.warning(f"{status['symbol']}: VCP base check failed: {e}")
            is_candidate, grade = False, None
        status["forming_base"] = bool(is_candidate)
        status["base_grade"] = grade if is_candidate else None

        label = _bucket_label(status["days_since_listing"])
        if label in buckets:
            buckets[label].append(status)

    for label in buckets:
        buckets[label].sort(key=lambda s: s["days_since_listing"])

    return buckets


def save_bucket_report(vcp_engine=None, ingestion_engine=None):
    """
    Runs build_bucket_report() and flattens it to reports/daily/
    ipo_bucket_report.csv (+ a dated copy) - one row per tracked IPO with
    real data, tagged with its age cohort. This is the "IPOs trading since
    5/10/20/30/60/100 days" view Vishal asked for directly, kept as its own
    artifact separate from scan_ipos()'s stricter VCP-candidates-only output.
    """
    buckets = build_bucket_report(vcp_engine, ingestion_engine)
    rows = []
    for label, items in buckets.items():
        for it in items:
            rows.append({
                "Bucket": label,
                "Symbol": it["symbol"],
                "Company_Name": it["company_name"],
                "Listing_Date": it["listing_date"],
                "Days_Since_Listing": it["days_since_listing"],
                "Offer_Price": it["offer_price"],
                "Current_Price": it["current_price"],
                "Pct_From_Offer": it["pct_from_offer"],
                "RS_Vs_Index": it["rs_vs_index"],
                "Forming_Base": it["forming_base"],
                "Base_Grade": it["base_grade"],
            })
    out_dir = _resolve_path(REPORT_DIR)
    os.makedirs(out_dir, exist_ok=True)
    df_out = pd.DataFrame(rows)
    df_out.to_csv(os.path.join(out_dir, "ipo_bucket_report.csv"), index=False)
    df_out.to_csv(os.path.join(out_dir, f"ipo_bucket_report_{datetime.now().strftime('%Y%m%d')}.csv"), index=False)
    logger.info(f"IPO bucket report: {len(rows)} row(s) across {len(buckets)} cohort(s) saved.")
    return buckets


def evaluate_ipo_candidate(vcp_engine, ingestion_engine, entry, index_df=None):
    """
    Evaluates a single tracked IPO entry for an "IPO Base" setup.
    Returns a dict (matching the vcp_candidates.csv column shape) if it
    qualifies, otherwise None.
    """
    status = get_ipo_status(ingestion_engine, entry, index_df)
    if status is None:
        return None
    symbol = status["symbol"]
    offer_price = status["offer_price"]
    current_price = status["current_price"]
    days_since_listing = status["days_since_listing"]
    rs_vs_index = status["rs_vs_index"]
    pct_from_offer = status["pct_from_offer"]
    df = status["df"]

    if days_since_listing < MIN_DAYS_SINCE_LISTING:
        logger.info(f"{symbol}: only {days_since_listing} trading days available (<{MIN_DAYS_SINCE_LISTING}) - too early, skipping to avoid chasing listing-pop noise.")
        return None

    is_candidate, pivot_price, grade, contraction_count, depths_str, vdu_ratio, final_low = \
        vcp_engine.is_vcp_candidate(df, mode="IPO")
    if not is_candidate:
        return None

    risk_per_share = pivot_price - final_low
    if risk_per_share <= 0:
        return None
    risk_pct = risk_per_share / pivot_price * 100.0

    return {
        "Symbol": symbol,
        "Engine_Type": "IPO_BASE",
        "Grade": grade,
        "Company_Name": entry.get("company_name", symbol),
        "Listing_Reference_Date": status["listing_date"] or entry.get("issue_end_date", ""),
        "Days_Since_Listing": days_since_listing,
        "Offer_Price": offer_price,
        "Pct_From_Offer": round(pct_from_offer, 1),
        "RS_Vs_Index": rs_vs_index,
        "Contraction_Count": contraction_count,
        "Contraction_Sequence": depths_str,
        "VDU_Ratio": round(vdu_ratio, 2),
        "Pivot_Price": round(pivot_price, 2),
        "Current_Price": round(current_price, 2),
        "Stop_Loss": round(final_low, 2),
        "Risk_Pct": round(risk_pct, 2),
        "Target_1": round(pivot_price + 1.5 * risk_per_share, 2),
        "Target_2": round(pivot_price + 2.5 * risk_per_share, 2),
    }


def scan_ipos(vcp_engine=None, ingestion_engine=None):
    """
    Main entry point. Syncs the IPO watchlist from NSE + manual entries, then
    evaluates every tracked symbol and writes qualifying candidates to
    reports/daily/ipo_candidates.csv (+ a dated copy), mirroring the shape of
    the existing vcp_candidates.csv. NOT wired into strategic_watchlist,
    daily_focus_watchlist, or True Paper Trading yet - review this output
    directly first.
    """
    if vcp_engine is None:
        from vcp_engine import VCPEngine
        vcp_engine = VCPEngine({"vcp_parameters": {}})
    if ingestion_engine is None:
        from data_ingestion import DataIngestionEngine
        ingestion_engine = DataIngestionEngine()

    tracked = sync_ipo_watchlist()
    if not tracked:
        logger.info("No IPOs tracked yet (NSE feed empty and no manual entries) - nothing to scan.")
        return []

    index_df = None
    try:
        index_df = ingestion_engine.fetch_historical_ohlcv("NIFTY_50", lookback_days=100)
    except Exception as e:
        logger.warning(f"Could not load index data for RS calculation: {e}")

    candidates = []
    for entry in tracked:
        try:
            result = evaluate_ipo_candidate(vcp_engine, ingestion_engine, entry, index_df)
        except Exception as e:
            logger.error(f"Error evaluating {entry.get('symbol')}: {e}")
            continue
        if result:
            candidates.append(result)
            logger.info(f"IPO BASE CANDIDATE: {result['Symbol']} - {result['Grade']}, Pivot Rs.{result['Pivot_Price']}, {result['Days_Since_Listing']}d of history, {result['Pct_From_Offer']:+.1f}% from offer")

    out_dir = _resolve_path(REPORT_DIR)
    os.makedirs(out_dir, exist_ok=True)
    df_out = pd.DataFrame(candidates)
    df_out.to_csv(os.path.join(out_dir, "ipo_candidates.csv"), index=False)
    df_out.to_csv(os.path.join(out_dir, f"ipo_candidates_{datetime.now().strftime('%Y%m%d')}.csv"), index=False)

    logger.info(f"IPO scan complete: {len(candidates)} candidate(s) out of {len(tracked)} tracked IPO(s).")
    return candidates


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(name)s] %(message)s")
    from vcp_engine import VCPEngine
    from data_ingestion import DataIngestionEngine
    engine = VCPEngine({"vcp_parameters": {}})
    ingestion = DataIngestionEngine()
    scan_ipos(engine, ingestion)
    save_bucket_report(engine, ingestion)
