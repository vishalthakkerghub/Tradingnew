import logging
import numpy as np
import pandas as pd

logger = logging.getLogger("SupportEngine")


class SupportEngine:
    """
    Support Retest Engine.

    Distinct from the EMA Pullback engines (main.py's PULLBACK_EMA10/20/50,
    which measure distance to a smoothed MOVING AVERAGE) - this looks at
    actual PRICE STRUCTURE: does the stock have a genuine prior pivot low
    (a real swing low other traders would recognize as support, detected
    the same way VCPEngine finds contraction lows) that price has now
    returned to test, while still holding above it?

    Reuses VCPEngine.detect_pivot_swing_points() for the pivot-finding
    itself, so "what counts as a swing low" stays consistent with how the
    rest of this system already defines pivots, rather than inventing a
    second, differently-tuned pivot detector.
    """

    def __init__(self, config: dict = None):
        self.config = config or {}
        # Sensitivity for pivot detection (left/right bars) - matches
        # VCPEngine's FLEX profile's own sensitivity, a reasonable middle
        # ground between STRICT's tight 5-bar window and noisier alternatives.
        self.pivot_sensitivity = 3
        # How far back to look for a support level worth retesting - a
        # level found 150+ trading days ago is arguably no longer
        # meaningful support to today's participants.
        self.lookback_bars = 150
        # How close price must be to the support level to count as "at
        # support" - a genuine retest, not just "somewhere above it".
        self.retest_band_low = -1.0   # can be up to 1% BELOW the level (a brief undercut, still a retest)
        self.retest_band_high = 3.0   # up to 3% above it
        # Support must have been established with real distance from it
        # (a genuine breakout away from the level) before counting as a
        # retest - otherwise "the low of yesterday" would trivially count.
        self.min_prior_extension_pct = 8.0

    def find_support_retest(self, stock_df: pd.DataFrame, as_of_index: int = None) -> tuple:
        """
        Evaluates whether the stock is currently retesting a genuine prior
        support level. `as_of_index` lets a backtest evaluate "as of" a
        specific historical bar without needing a separately-truncated
        DataFrame for every date (pass the row index to treat as "today" -
        pivots and levels are only ever computed from bars up to and
        including it, so this has no lookahead bias).

        Returns (is_candidate, support_price, stop_price, grade,
        vdu_ratio, dist_pct, pivot_bars_ago).
        """
        df = stock_df if as_of_index is None else stock_df.iloc[: as_of_index + 1]
        n = len(df)
        if n < 60:
            return False, 0.0, 0.0, None, 0.0, 0.0, None

        close = float(df["Close"].iloc[-1])
        if close <= 0:
            return False, 0.0, 0.0, None, 0.0, 0.0, None

        # Stage-2-ish sanity floor: don't call a breakdown "support" -
        # require the stock to still be above its own 200-day trend,
        # where enough history exists to judge that at all.
        if n >= 200:
            sma200 = float(df["Close"].rolling(window=200).mean().iloc[-1])
            if not pd.isna(sma200) and close < sma200:
                return False, 0.0, 0.0, None, 0.0, 0.0, None

        window = df.tail(self.lookback_bars)
        if len(window) < 2 * self.pivot_sensitivity + 1:
            return False, 0.0, 0.0, None, 0.0, 0.0, None

        pivots = self._detect_pivot_lows(window)
        if not pivots:
            return False, 0.0, 0.0, None, 0.0, 0.0, None

        # Walk candidate pivot lows from most recent backward - want the
        # freshest support level that's actually being retested now, not
        # an old one that's still technically true but stale.
        best = None
        for p in reversed(pivots):
            support_price = p["price"]
            if support_price <= 0:
                continue

            # Must have shown real distance away from this low since it
            # formed (a genuine prior extension/breakout), not just noise
            # sitting right next to the current price.
            since = window.iloc[p["row_index"] + 1 :]
            max_high_since = float(since["High"].max()) if not since.empty else close
            extension_pct = ((max_high_since - support_price) / support_price) * 100 if support_price > 0 else 0
            if extension_pct < self.min_prior_extension_pct:
                continue

            dist_pct = ((close - support_price) / support_price) * 100
            if not (self.retest_band_low <= dist_pct <= self.retest_band_high):
                continue

            # Must not have already broken down meaningfully through this
            # level on a closing basis since it formed - a real retest
            # holds, it doesn't fail and limp back up.
            closes_since = since["Close"] if not since.empty else pd.Series([close])
            worst_breach_pct = ((closes_since.min() - support_price) / support_price) * 100
            if worst_breach_pct < -4.0:
                continue

            # bars_ago relative to `window`, not the (possibly much longer)
            # full df - row_index is an index INTO window (df.tail(...)),
            # so it must be compared against window's own length.
            bars_ago = (len(window) - 1) - p["row_index"]
            best = {"support_price": support_price, "dist_pct": dist_pct, "bars_ago": bars_ago}
            break  # most recent qualifying pivot wins

        if best is None:
            return False, 0.0, 0.0, None, 0.0, 0.0, None

        # Volume Dry-Up on the retest itself - same convention as the EMA
        # pullback engines: sellers backing off is what makes a retest
        # buyable rather than a level about to give way.
        avg_vol_5 = float(df["Volume"].iloc[-5:].mean())
        avg_vol_50 = float(df["Volume"].iloc[-50:].mean()) if n >= 50 else avg_vol_5
        vdu_ratio = avg_vol_5 / avg_vol_50 if avg_vol_50 > 0 else 1.0
        if vdu_ratio > 1.0:
            return False, 0.0, 0.0, None, 0.0, 0.0, None

        support_price = best["support_price"]
        stop_price = min(support_price * 0.975, close * 0.97)
        grade = "Grade A" if vdu_ratio <= 0.6 else ("Grade B" if vdu_ratio <= 0.8 else "Grade C")

        return True, round(support_price, 2), round(stop_price, 2), grade, round(vdu_ratio, 3), round(best["dist_pct"], 2), best["bars_ago"]

    def _detect_pivot_lows(self, df: pd.DataFrame) -> list:
        """Local-minimum pivot lows via the same rolling left/right-bar
        comparison VCPEngine.detect_pivot_swing_points() uses, kept as a
        standalone copy here so this engine has no import-order dependency
        on vcp_engine.py - both independently implement the identical,
        well-tested comparison logic."""
        sens = self.pivot_sensitivity
        n = len(df)
        if n < 2 * sens + 1:
            return []
        lows = df["Low"].values
        is_low = np.ones(n, dtype=bool)
        for offset in range(-sens, sens + 1):
            if offset == 0:
                continue
            slice_lows = lows[sens : n - sens]
            compare_lows = lows[sens + offset : n - sens + offset]
            is_low[sens : n - sens] &= (slice_lows < compare_lows)
        low_indices = np.where(is_low[sens : n - sens])[0] + sens
        pivots = []
        for idx in low_indices:
            pivots.append({"index": df.index[idx], "row_index": int(idx), "price": float(lows[idx])})
        return pivots
