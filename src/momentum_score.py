import pandas as pd
import numpy as np
import os
import logging

logger = logging.getLogger("MomentumEngine")

class AntigravityMomentumEngine:
    """
    Antigravity Momentum Score (AMS) calculation engine.
    Computes a score from 0 to 100 based on Trend Quality, Price Momentum,
    Volume & Institutional Participation, Relative Strength, Smart Money, and VCP/Base Quality.
    """
    def __init__(self, cache_dir="data/cache"):
        self.cache_dir = cache_dir

    def calculate_ams(self, symbol: str, index_df: pd.DataFrame = None) -> dict:
        # Load cache data for stock
        cache_file = os.path.join(self.cache_dir, f"{symbol.upper()}.csv")
        if not os.path.exists(cache_file):
            cache_file = os.path.join("minervini_os", cache_file)
            
        if not os.path.exists(cache_file):
            return self._default_score(symbol)
            
        try:
            df = pd.read_csv(cache_file)
            df.columns = [c.strip() for c in df.columns]
            df['Date'] = pd.to_datetime(df['Date'])
            df = df.sort_values('Date').reset_index(drop=True)
        except Exception as e:
            logger.warning(f"Error reading cache for {symbol}: {e}")
            return self._default_score(symbol)
            
        if df.empty or len(df) < 15:
            return self._default_score(symbol)

        # Load Nifty index data for Relative Strength if not provided
        if index_df is None or index_df.empty:
            nifty_file = os.path.join(self.cache_dir, "NIFTY_50.csv")
            if not os.path.exists(nifty_file):
                nifty_file = os.path.join("minervini_os", nifty_file)
            if os.path.exists(nifty_file):
                try:
                    index_df = pd.read_csv(nifty_file)
                    index_df.columns = [c.strip() for c in index_df.columns]
                    index_df['Date'] = pd.to_datetime(index_df['Date'])
                    index_df = index_df.sort_values('Date').reset_index(drop=True)
                except Exception:
                    pass

        # Perform scoring components
        trend_score = self._score_trend_quality(df)
        momentum_score = self._score_price_momentum(df)
        volume_score = self._score_volume_participation(df)
        rs_score = self._score_relative_strength(df, index_df)
        sm_score = self._score_smart_money(df)
        vcp_score = self._score_vcp_quality(df)
        
        total = trend_score + momentum_score + volume_score + rs_score + sm_score + vcp_score
        total = min(100, max(0, int(round(total))))
        
        rating, rating_stars = self._get_rating(total)
        status = self._get_status(total, trend_score, volume_score)
        
        return {
            "Symbol": symbol,
            "Trend": int(trend_score),
            "Momentum": int(momentum_score),
            "Volume": int(volume_score),
            "RS": int(rs_score),
            "SmartMoney": int(sm_score),
            "VCP": int(vcp_score),
            "Total": total,
            "Rating": rating,
            "RatingStars": rating_stars,
            "Status": status
        }

    def _default_score(self, symbol: str):
        return {
            "Symbol": symbol,
            "Trend": 0,
            "Momentum": 0,
            "Volume": 0,
            "RS": 0,
            "SmartMoney": 0,
            "VCP": 0,
            "Total": 50,
            "Rating": "⭐",
            "RatingStars": "★☆☆☆☆",
            "Status": "Insufficient Data"
        }

    def _score_trend_quality(self, df: pd.DataFrame) -> int:
        close = float(df["Close"].iloc[-1])
        
        # Compute moving averages
        ema20 = df["Close"].ewm(span=20, adjust=False).mean()
        ema50 = df["Close"].ewm(span=50, adjust=False).mean()
        sma150 = df["Close"].rolling(window=150, min_periods=5).mean()
        sma200 = df["Close"].rolling(window=200, min_periods=5).mean()
        
        c_ema20 = float(ema20.iloc[-1])
        c_ema50 = float(ema50.iloc[-1])
        c_sma150 = float(sma150.iloc[-1]) if not sma150.empty and not pd.isna(sma150.iloc[-1]) else close * 0.90
        c_sma200 = float(sma200.iloc[-1]) if not sma200.empty and not pd.isna(sma200.iloc[-1]) else close * 0.85
        
        points = 0
        
        # Price above EMA20 (3 points)
        if close > c_ema20:
            points += 3
            
        # EMA20 > EMA50 (4 points)
        if c_ema20 > c_ema50:
            points += 4
            
        # EMA50 > SMA150 (4 points)
        if c_ema50 > c_sma150:
            points += 4
            
        # SMA150 > SMA200 (4 points)
        if c_sma150 > c_sma200:
            points += 4
            
        # Higher Highs and Higher Lows (4 points)
        if len(df) >= 20:
            h1 = float(df["High"].iloc[-10:].max())
            h2 = float(df["High"].iloc[-20:-10].max())
            l1 = float(df["Low"].iloc[-10:].min())
            l2 = float(df["Low"].iloc[-20:-10].min())
            if h1 > h2:
                points += 2
            if l1 > l2:
                points += 2
        else:
            points += 2
            
        # Distance above 200 SMA (3 points)
        if c_sma200 > 0:
            dist = (close - c_sma200) / c_sma200
            if dist > 0.15:
                points += 3
            elif dist > 0.05:
                points += 2
            elif dist > 0:
                points += 1
                
        # Trend consistency over last 50 bars (3 points)
        if len(df) >= 50:
            above_200 = (df["Close"].iloc[-50:] > sma200.iloc[-50:]).sum()
            pct = above_200 / 50.0
            if pct >= 0.90:
                points += 3
            elif pct >= 0.70:
                points += 2
            elif pct >= 0.50:
                points += 1
        else:
            points += 1
            
        return min(25, points)

    def _score_price_momentum(self, df: pd.DataFrame) -> int:
        close = float(df["Close"].iloc[-1])
        high = float(df["High"].iloc[-1])
        low = float(df["Low"].iloc[-1])
        open_p = float(df["Open"].iloc[-1])
        
        points = 0
        
        # Close near day's high (3 points)
        daily_range = high - low
        if daily_range > 0:
            pos = (close - low) / daily_range
            if pos >= 0.80:
                points += 3
            elif pos >= 0.60:
                points += 2
            elif pos >= 0.40:
                points += 1
                
        # Strong bullish candle body (3 points)
        if daily_range > 0:
            body = abs(close - open_p)
            body_pct = body / daily_range
            if close > open_p and body_pct > 0.60:
                points += 3
            elif close > open_p and body_pct > 0.40:
                points += 2
            elif close > open_p:
                points += 1
                
        # Positive Rate of Change (ROC) (3 points)
        if len(df) >= 10:
            prev_close = float(df["Close"].iloc[-10])
            roc = ((close - prev_close) / prev_close) * 100 if prev_close > 0 else 0.0
            if roc > 5.0:
                points += 3
            elif roc > 0:
                points += 2
        else:
            points += 1
            
        # Positive EMA20 slope (4 points)
        if len(df) >= 5:
            ema20 = df["Close"].ewm(span=20, adjust=False).mean()
            slopes = ema20.iloc[-5:].diff().dropna()
            positive_days = (slopes > 0).sum()
            if positive_days >= 4:
                points += 4
            elif positive_days >= 2:
                points += 2
        else:
            points += 2
            
        # ATR expansion during advances (3 points)
        if len(df) >= 20:
            avg_range = (df["High"] - df["Low"]).iloc[-20:].mean()
            if close > open_p and daily_range > avg_range * 1.2:
                points += 3
            elif close > open_p and daily_range > avg_range:
                points += 2
            else:
                points += 1
        else:
            points += 1
            
        # Strong follow-through after breakout (4 points)
        if len(df) >= 5:
            ret_5d = ((close - float(df["Close"].iloc[-5])) / float(df["Close"].iloc[-5])) * 100
            if ret_5d > 8.0:
                points += 4
            elif ret_5d > 3.0:
                points += 3
            elif ret_5d > 0:
                points += 2
        else:
            points += 2
            
        return min(20, points)

    def _score_volume_participation(self, df: pd.DataFrame) -> int:
        vol = float(df["Volume"].iloc[-1])
        close = float(df["Close"].iloc[-1])
        open_p = float(df["Open"].iloc[-1])
        
        points = 0
        
        vol_ma20 = df["Volume"].rolling(window=20, min_periods=5).mean()
        c_vol_ma20 = float(vol_ma20.iloc[-1]) if not vol_ma20.empty and not pd.isna(vol_ma20.iloc[-1]) else 1.0
        
        # Breakout volume above 20-day average (4 points)
        if vol > c_vol_ma20 * 2.0 and close > open_p:
            points += 4
        elif vol > c_vol_ma20 * 1.5 and close > open_p:
            points += 3
        elif vol > c_vol_ma20 and close > open_p:
            points += 2
        elif close > open_p:
            points += 1
            
        # Volume Dry-Up during pullbacks (4 points)
        if close < open_p:
            if vol < c_vol_ma20 * 0.50:
                points += 4
            elif vol < c_vol_ma20 * 0.80:
                points += 2
        else:
            red_days = df[df["Close"] < df["Open"]].iloc[-5:]
            if not red_days.empty:
                min_red_vol = float(red_days["Volume"].min())
                if min_red_vol < c_vol_ma20 * 0.60:
                    points += 4
                else:
                    points += 2
            else:
                points += 3
                
        # Accumulation Days > Distribution Days (4 points)
        if len(df) >= 20:
            recent_df = df.iloc[-20:]
            acc_days = 0
            dist_days = 0
            for idx, r in recent_df.iterrows():
                r_vol = float(r["Volume"])
                r_close = float(r["Close"])
                r_open = float(r["Open"])
                r_ma = float(vol_ma20.loc[idx]) if idx in vol_ma20.index and not pd.isna(vol_ma20.loc[idx]) else c_vol_ma20
                if r_close > r_open and r_vol > r_ma:
                    acc_days += 1
                elif r_close < r_open and r_vol > r_ma:
                    dist_days += 1
            if acc_days > dist_days:
                points += 4
            elif acc_days == dist_days:
                points += 2
        else:
            points += 2
            
        # OBV making Higher Highs (3 points)
        direction = np.where(df["Close"].diff() > 0, 1, -1)
        direction[0] = 0
        obv = pd.Series((df["Volume"] * direction).cumsum())
        if len(obv) >= 20:
            o_max_recent = float(obv.iloc[-10:].max())
            o_max_prev = float(obv.iloc[-20:-10].max())
            if o_max_recent > o_max_prev:
                points += 3
            else:
                points += 1
        else:
            points += 1
            
        # Rising volume on advances / declining volume on corrections (5 points)
        if len(df) >= 20:
            returns = df["Close"].pct_change().iloc[-20:]
            volumes = df["Volume"].iloc[-20:]
            corr = returns.corr(volumes)
            if corr > 0.3:
                points += 5
            elif corr > 0.1:
                points += 3
            elif corr > -0.1:
                points += 1
        else:
            points += 2
            
        return min(20, points)

    def _score_relative_strength(self, df: pd.DataFrame, index_df: pd.DataFrame) -> int:
        points = 0
        if index_df is None or index_df.empty:
            return 5
            
        try:
            merged = pd.merge(df[['Date', 'Close']], index_df[['Date', 'Close']], on='Date', suffixes=('_stock', '_index'))
            if len(merged) < 20:
                return 5
                
            merged['RS_Ratio'] = merged['Close_stock'] / merged['Close_index']
            
            stock_perf_3m = (merged['Close_stock'].iloc[-1] / merged['Close_stock'].iloc[-min(60, len(merged))]) - 1
            index_perf_3m = (merged['Close_index'].iloc[-1] / merged['Close_index'].iloc[-min(60, len(merged))]) - 1
            
            if stock_perf_3m > index_perf_3m + 0.10:
                points += 3
            elif stock_perf_3m > index_perf_3m:
                points += 2
            else:
                points += 1
                
            recent_rs_max = float(merged['RS_Ratio'].iloc[-20:].max())
            prev_rs_max = float(merged['RS_Ratio'].iloc[-40:-20].max()) if len(merged) >= 40 else 0.0
            if recent_rs_max > prev_rs_max:
                points += 3
            else:
                points += 1
                
            rs_ma = merged['RS_Ratio'].ewm(span=20, adjust=False).mean()
            if merged['RS_Ratio'].iloc[-1] > rs_ma.iloc[-1]:
                points += 2
                
            if stock_perf_3m > index_perf_3m:
                points += 2
        except Exception as e:
            logger.warning(f"Error calculating relative strength score: {e}")
            return 5
            
        return min(10, points)

    def _score_smart_money(self, df: pd.DataFrame) -> int:
        points = 0
        
        # Bullish BOS (2 points)
        if len(df) >= 15:
            recent_high = float(df["High"].iloc[-10:-1].max())
            if float(df["Close"].iloc[-1]) > recent_high:
                points += 2
        else:
            points += 1
            
        # Bullish CHOCH (2 points)
        ema50 = df["Close"].ewm(span=50, adjust=False).mean()
        if len(df) >= 5:
            if float(df["Close"].iloc[-1]) > float(ema50.iloc[-1]) and float(ema50.iloc[-1]) > float(ema50.iloc[-5]):
                points += 2
            else:
                points += 1
        else:
            points += 1
            
        # Liquidity Sweep (3 points)
        if len(df) >= 3:
            prev_low = float(df["Low"].iloc[-2])
            today_low = float(df["Low"].iloc[-1])
            today_close = float(df["Close"].iloc[-1])
            today_open = float(df["Open"].iloc[-1])
            if today_low < prev_low and today_close > today_open and today_close > (float(df["High"].iloc[-1]) + today_low)/2:
                points += 3
            else:
                points += 1
        else:
            points += 1
            
        # Holding above Demand Zone (2 points)
        if len(df) >= 10:
            support = float(df["Low"].iloc[-10:-1].min())
            if float(df["Close"].iloc[-1]) > support:
                points += 2
        else:
            points += 1
            
        # No recent bearish BOS (1 point)
        if len(df) >= 20:
            recent_min_low = float(df["Low"].iloc[-20:-2].min())
            if float(df["Close"].iloc[-1]) > recent_min_low:
                points += 1
        else:
            points += 1
            
        return min(10, points)

    def _score_vcp_quality(self, df: pd.DataFrame) -> int:
        points = 0
        
        # Volatility contractions becoming smaller (4 points)
        if len(df) >= 30:
            r1 = (df["High"].iloc[-10:] - df["Low"].iloc[-10:]).mean() / df["Close"].iloc[-1]
            r2 = (df["High"].iloc[-20:-10] - df["Low"].iloc[-20:-10]).mean() / df["Close"].iloc[-1]
            r3 = (df["High"].iloc[-30:-20] - df["Low"].iloc[-30:-20]).mean() / df["Close"].iloc[-1]
            if r1 < r2 and r2 < r3:
                points += 4
            elif r1 < r2:
                points += 2
            else:
                points += 1
        else:
            points += 2
            
        # Volume contraction within base (3 points)
        vol_ma = df["Volume"].rolling(window=20, min_periods=5).mean()
        if len(df) >= 10 and not vol_ma.empty:
            recent_vol = df["Volume"].iloc[-5:].mean()
            if recent_vol < vol_ma.iloc[-1] * 0.70:
                points += 3
            elif recent_vol < vol_ma.iloc[-1]:
                points += 2
        else:
            points += 1
            
        # Tight weekly closes (3 points)
        if len(df) >= 15:
            weekly_closes = df["Close"].iloc[-15::5]
            if len(weekly_closes) >= 3:
                w_max = weekly_closes.max()
                w_min = weekly_closes.min()
                spread = (w_max - w_min) / w_min
                if spread < 0.02:
                    points += 3
                elif spread < 0.05:
                    points += 2
            else:
                points += 1
        else:
            points += 1
            
        # Pivot within 5% of highs (3 points)
        if len(df) >= 20:
            high_20d = float(df["High"].iloc[-20:].max())
            if (high_20d - float(df["Close"].iloc[-1])) / high_20d <= 0.05:
                points += 3
            elif (high_20d - float(df["Close"].iloc[-1])) / high_20d <= 0.10:
                points += 2
        else:
            points += 1
            
        # Healthy base duration (1 point)
        if len(df) >= 30:
            points += 1
            
        # No abnormal distribution (1 point)
        if len(df) >= 5 and not vol_ma.empty:
            recent = df.iloc[-5:]
            distribution_days = 0
            for idx, r in recent.iterrows():
                if r["Close"] < r["Open"] and idx in vol_ma.index and r["Volume"] > vol_ma.loc[idx]:
                    distribution_days += 1
            if distribution_days == 0:
                points += 1
        else:
            points += 1
            
        return min(15, points)

    def _get_rating(self, total: int):
        if total >= 95:
            return "⭐⭐⭐⭐⭐", "★★★★★"
        elif total >= 90:
            return "⭐⭐⭐⭐☆", "★★★★☆"
        elif total >= 80:
            return "⭐⭐⭐⭐", "★★★★☆"
        elif total >= 70:
            return "⭐⭐⭐", "★★★☆☆"
        elif total >= 60:
            return "⭐⭐", "★★☆☆☆"
        else:
            return "⭐", "★☆☆☆☆"

    def _get_status(self, total: int, trend: int, volume: int):
        if total >= 90:
            return "Institutional Accumulation"
        elif total >= 80:
            return "Strong Accumulation"
        elif total >= 70:
            return "Breakout Contender"
        elif total >= 60:
            if volume > 10:
                return "High Volatility Consolidation"
            else:
                return "Neutral / Base Building"
        else:
            if trend < 10:
                return "Downtrend / Avoiding"
            else:
                return "Distribution / Sell Pressure"
