import os
import time
import logging
import pandas as pd
import numpy as np
import yfinance as yf
import urllib.request
from datetime import datetime, timedelta

logger = logging.getLogger("DataIngestion")

class DataIngestionEngine:
    """
    Handles daily OHLCV (Open, High, Low, Close, Volume) data ingestion.
    Performs local caching, 18-hour cache expiration validation, download fallbacks, 
    and strict data health checks to support the trading scanner.
    """
    def __init__(self, cache_dir: str = "data/cache"):
        self.cache_dir = cache_dir
        if not os.path.exists(self.cache_dir):
            os.makedirs(self.cache_dir)
            logger.info(f"Created cache directory: {self.cache_dir}")
        else:
            logger.info(f"DataIngestionEngine active. Cache path: {self.cache_dir}")

    def is_cache_stale(self, symbol: str, latest_date: str = None) -> bool:
        """
        Evaluates cache freshness under four rules:
        1. If cache file is missing, it is stale.
        2. If cache file age is < 4 hours, it is considered fresh (safeguard to prevent infinite loops).
        3. If cache file age is >= 18 hours, it is stale.
        4. If Indian market closes (after 4:00 PM / 16:00 IST) but cache has not been EOD updated.
        5. If a latest_date is known (from index benchmark), and the cache does not contain this date.
        """
        if os.environ.get("FORCE_STALE") == "1":
            return True

        cache_file = os.path.join(self.cache_dir, f"{symbol.upper()}.csv")
        if not os.path.exists(cache_file):
            return True
            
        # Try to resolve latest benchmark trading date if not provided
        if not latest_date and symbol.upper() not in ["NIFTY_50", "NIFTY_MIDSML400", "NIFTY50", "NIFTYMIDSML400", "^NSEI", "NIFTYMIDSML400.NS"]:
            latest_date = self._get_latest_benchmark_date()
            
        if latest_date:
            last_date_in_cache = self._get_last_date_in_csv(cache_file)
            if last_date_in_cache and last_date_in_cache < latest_date:
                # Cache is stale because it is missing the latest trading session
                return True
                
        # Safeguard: if the cache was updated within the last 4 hours, do not download again
        file_age_hours = (time.time() - os.path.getmtime(cache_file)) / 3600
        if file_age_hours < 4:
            return False
            
        if file_age_hours >= 18:
            return True
            
        try:
            current_time = datetime.now()
            # Indian market EOD data is ready on yfinance by 4:00 PM (16:00 IST)
            if current_time.hour >= 16:
                eod_update_time = current_time.replace(hour=16, minute=0, second=0, microsecond=0)
                mtime_ts = os.path.getmtime(cache_file)
                mtime_dt = datetime.fromtimestamp(mtime_ts)
                if mtime_dt < eod_update_time:
                    return True
        except Exception:
            pass
            
        return False

    def _get_latest_benchmark_date(self) -> str:
        """
        Attempts to read the latest date from the benchmark index cache file.
        """
        for index_name in ["NIFTY_50", "NIFTY_MIDSML400"]:
            index_path = os.path.join(self.cache_dir, f"{index_name}.csv")
            if os.path.exists(index_path):
                last_date = self._get_last_date_in_csv(index_path)
                if last_date:
                    return last_date
        return None

    def _get_last_date_in_csv(self, filepath: str) -> str:
        """
        Reads the date field from the very last line of the CSV cache file.
        Extremely fast, reads only the end of the file.
        """
        try:
            with open(filepath, "rb") as f:
                try:
                    f.seek(-150, os.SEEK_END)
                except OSError:
                    f.seek(0)
                last_bytes = f.read()
                lines = last_bytes.decode("utf-8", errors="ignore").strip().split("\n")
                if lines:
                    last_line = lines[-1].strip()
                    parts = last_line.split(",")
                    if parts:
                        date_str = parts[0].strip()
                        if len(date_str) == 10 and date_str[4] == '-' and date_str[7] == '-':
                            return date_str
        except Exception:
            pass
        return None

    def fetch_historical_ohlcv(self, symbol: str, lookback_days: int = 250) -> pd.DataFrame:
        """
        Fetches daily historical OHLCV data for a given stock symbol.
        1. Checks if a local cache file exists.
        2. Checks freshness using is_cache_stale.
        3. If fresh, loads cache. If stale or missing, downloads from yfinance.
        4. If yfinance download fails, attempts to load stale cache as fallback.
        5. If no cache exists, generates simulated data (offline fallback).
        """
        cache_file = os.path.join(self.cache_dir, f"{symbol.upper()}.csv")
        yf_ticker = self._format_nse_ticker(symbol)
        
        # 1. Check cache freshness
        if os.path.exists(cache_file) and not self.is_cache_stale(symbol):
            file_age_hours = (time.time() - os.path.getmtime(cache_file)) / 3600
            logger.info(f"Cache hit. Loading fresh data for {symbol} (Age: {file_age_hours:.2f} hours).")
            try:
                df = self._load_cache_file(cache_file)
                if self.validate_data(df, symbol):
                    return df.tail(lookback_days)
            except Exception as e:
                logger.warning(f"Failed to load cache file for {symbol} despite hit: {e}")
        else:
            if os.path.exists(cache_file):
                logger.info(f"Cache stale for {symbol}. Initiating download.")
            else:
                logger.info(f"No cache found for {symbol}. Initiating download.")

        # 2. Attempt yfinance download
        try:
            logger.info(f"Downloading historical data from yfinance for ticker: {yf_ticker}")
            ticker_obj = yf.Ticker(yf_ticker)
            # Fetch slightly more than lookback_days to allow indicator calculations (e.g. 200 SMA needs 200 prior bars)
            df = ticker_obj.history(period="2y")
            
            # Patch potential yfinance NaN issues for the latest date
            if not df.empty:
                try:
                    latest_df = ticker_obj.history(period="1d")
                    if not latest_df.empty:
                        latest_date = latest_df.index[-1]
                        latest_row = latest_df.iloc[-1]
                        if not pd.isna(latest_row['Close']) and latest_row['Close'] > 0:
                            if latest_date in df.index:
                                for col in ['Open', 'High', 'Low', 'Close', 'Volume']:
                                    df.loc[latest_date, col] = latest_row[col]
                            else:
                                df.loc[latest_date] = latest_row
                except Exception as patch_ex:
                    logger.warning(f"Failed to patch latest candle for {symbol}: {patch_ex}")
            
            if not df.empty:
                df = self._normalize_columns(df, symbol)
                if self.validate_data(df, symbol):
                    self._save_cache_file(df, cache_file)
                    logger.info(f"Successfully cached and validated data for {symbol}.")
                    return df.tail(lookback_days)
            logger.warning(f"yfinance returned empty DataFrame for ticker: {yf_ticker}")
        except Exception as e:
            logger.error(f"Network error downloading data for {symbol} from yfinance: {e}")

        # 3. Fallback to stale cache if download failed
        if os.path.exists(cache_file):
            logger.warning(f"Network download failed. Falling back to stale cache for {symbol}.")
            try:
                df = self._load_cache_file(cache_file)
                if self.validate_data(df, symbol):
                    return df.tail(lookback_days)
            except Exception as e:
                logger.critical(f"Stale cache fallback failed for {symbol}: {e}")

        # 4. Final Fallback: Generate high-quality simulated price data (Offline compatibility)
        logger.warning(f"No active data feed or cache available. Generating simulated data for {symbol}.")
        df = self._generate_simulated_ohlcv(symbol, lookback_days * 2)
        self._save_cache_file(df, cache_file)
        return df.tail(lookback_days)

    def fetch_index_ohlcv(self, index_symbol: str, lookback_days: int = 250) -> pd.DataFrame:
        """
        Fetches historical data for the index benchmark (e.g. NIFTY_MIDSML400).
        Utilizes the same caching, validation, and fallback mechanisms as equities.
        """
        logger.info(f"Requesting historical data for index benchmark: {index_symbol}")
        return self.fetch_historical_ohlcv(index_symbol, lookback_days)

    def bulk_fetch_ohlcv(self, symbols: list, lookback_days: int = 250) -> dict:
        """
        Downloads OHLCV data for multiple symbols in parallel batches using yfinance.
        Saves each verified symbol to its local cache file to enable instant EOD scans.
        """
        logger.info(f"Initiating bulk download for {len(symbols)} symbols...")
        formatted_tickers = {self._format_nse_ticker(sym): sym for sym in symbols}
        tickers_list = list(formatted_tickers.keys())
        
        # Split into batches of 100 to avoid HTTP header/URL length limits
        batch_size = 100
        results = {}
        
        for i in range(0, len(tickers_list), batch_size):
            batch = tickers_list[i:i+batch_size]
            logger.info(f"Downloading batch {i//batch_size + 1} ({len(batch)} tickers)...")
            try:
                # Download using multithreading
                data = yf.download(batch, period="2y", group_by="ticker", threads=True, progress=False)
                
                # Download latest 1d data to patch potential yfinance NaN issues for the latest date
                try:
                    latest_data = yf.download(batch, period="1d", group_by="ticker", threads=True, progress=False)
                except Exception as latest_e:
                    logger.warning(f"Failed to download bulk 1d patch data: {latest_e}")
                    latest_data = pd.DataFrame()
                
                for yf_ticker in batch:
                    symbol = formatted_tickers[yf_ticker]
                    cache_file = os.path.join(self.cache_dir, f"{symbol.upper()}.csv")
                    
                    try:
                        if len(batch) == 1:
                            df_sym = data.copy()
                        else:
                            if yf_ticker in data.columns.levels[0]:
                                df_sym = data[yf_ticker].copy()
                            else:
                                logger.warning(f"No data found in bulk download for: {yf_ticker}")
                                continue
                                
                        if not df_sym.empty:
                            # Patch latest row if available in latest_data
                            if not latest_data.empty:
                                try:
                                    if len(batch) == 1:
                                        latest_df_sym = latest_data.copy()
                                    else:
                                        latest_df_sym = latest_data[yf_ticker] if yf_ticker in latest_data.columns.levels[0] else pd.DataFrame()
                                    
                                    if not latest_df_sym.empty:
                                        latest_date = latest_df_sym.index[-1]
                                        latest_row = latest_df_sym.iloc[-1]
                                        if not pd.isna(latest_row['Close']) and latest_row['Close'] > 0:
                                            if latest_date in df_sym.index:
                                                for col in ['Open', 'High', 'Low', 'Close', 'Volume']:
                                                    df_sym.loc[latest_date, col] = latest_row[col]
                                            else:
                                                df_sym.loc[latest_date] = latest_row
                                except Exception as sym_patch_e:
                                    logger.warning(f"Failed to patch bulk ticker {yf_ticker}: {sym_patch_e}")
                                    
                            df_sym = self._normalize_columns(df_sym, symbol)
                            if self.validate_data(df_sym, symbol):
                                self._save_cache_file(df_sym, cache_file)
                                results[symbol] = df_sym.tail(lookback_days)
                            else:
                                logger.warning(f"Data validation failed for bulk ticker: {yf_ticker}")
                    except Exception as sym_e:
                        logger.error(f"Error processing bulk data for {symbol}: {sym_e}")
                        
            except Exception as e:
                logger.error(f"Failed to download batch starting at index {i}: {e}")
                
        return results

    def validate_data(self, df: pd.DataFrame, symbol: str = None) -> bool:
        """
        Validates OHLCV DataFrame structure and value integrity:
        - Must not be empty.
        - Must contain standard columns: Open, High, Low, Close, Volume.
        - Open, High, Low, Close must be strictly positive. Volume must be positive (except for index symbols where zero volume is permitted).
        """
        if df is None or df.empty:
            logger.error("Data validation failed: DataFrame is empty or None.")
            return False

        required_cols = ["Open", "High", "Low", "Close", "Volume"]
        missing_cols = [col for col in required_cols if col not in df.columns]
        if missing_cols:
            logger.error(f"Data validation failed: Missing required columns: {missing_cols}")
            return False

        is_index = False
        if symbol:
            s_upper = symbol.upper()
            if s_upper.startswith("^") or "NIFTY" in s_upper:
                is_index = True

        # Validate values (prices and volumes must be positive numbers)
        for col in required_cols:
            if df[col].isnull().any():
                logger.warning(f"Data contains null values in column: {col}. Dropping affected rows.")
                df.dropna(subset=[col], inplace=True)
            
            # Check for negative or zero values (allow zero for volume on index symbols)
            if col == "Volume" and is_index:
                non_positive = df[df[col] < 0]
            else:
                non_positive = df[df[col] <= 0]

            if not non_positive.empty:
                logger.error(f"Data validation failed: Column {col} contains zero or negative values on rows:\n{non_positive}")
                return False

        return True

    def _format_nse_ticker(self, symbol: str) -> str:
        """
        Formats symbol for Yahoo Finance retrieval.
        Appends '.NS' suffix for Indian NSE equities unless it is an index indicator (e.g. starts with ^).
        """
        s = symbol.upper()
        if s.startswith("^") or s.endswith(".NS"):
            return s
        if s == "GANESH BENZO" or s == "GANESH_BENZO":
            return "GANESHBE.NS"
        # Special case index benchmark name (Yahoo Finance ticker has no underscore)
        if s == "NIFTY_MIDSML400" or s == "NIFTYMIDSML400":
            return "NIFTYMIDSML400.NS"
        if s == "NIFTY_50" or s == "NIFTY50":
            return "^NSEI"
        return f"{s}.NS"

    def _normalize_columns(self, df: pd.DataFrame, symbol: str = None) -> pd.DataFrame:
        """
        Normalizes DataFrame index to string Date formats, standardizes column names,
        and filters out invalid rows (zero/negative volume, non-positive prices, NaNs).
        """
        df = df.copy()
        # Flatten MultiIndex if yfinance returns multi-level column headers
        if isinstance(df.columns, pd.MultiIndex):
            # Determine which level contains the metric names (Open, High, Low, Close, Volume)
            if any(str(col).title() in ["Open", "High", "Low", "Close", "Volume"] for col in df.columns.get_level_values(0)):
                df.columns = df.columns.get_level_values(0)
            else:
                df.columns = df.columns.get_level_values(1)
        # Ensure standard column casing (Title Case)
        df.columns = [str(col).title() for col in df.columns]
        
        # If Date is index, convert to string YYYY-MM-DD
        if isinstance(df.index, pd.DatetimeIndex):
            df.index = df.index.strftime("%Y-%m-%d")
        df.index.name = "Date"
        
        required_cols = ["Open", "High", "Low", "Close", "Volume"]
        is_index = False
        if symbol:
            s_upper = symbol.upper()
            if s_upper.startswith("^") or "NIFTY" in s_upper:
                is_index = True

        if is_index:
            # For indexes, volume is optional or can be 0/NaN. Don't drop rows if only Volume is NaN.
            required_cols = ["Open", "High", "Low", "Close"]

        # Clean data: drop any rows with NaN values in required columns
        valid_cols = [col for col in required_cols if col in df.columns]
        df.dropna(subset=valid_cols, inplace=True)
        
        # If it's an index, fill NaN volume with 0
        if is_index and "Volume" in df.columns:
            df["Volume"] = df["Volume"].fillna(0)

        # Drop rows with zero or negative volume (indexes allow zero volume)
        if "Volume" in df.columns:
            df["Volume"] = pd.to_numeric(df["Volume"], errors="coerce")
            if is_index:
                df = df[df["Volume"] >= 0]
            else:
                df = df[df["Volume"] > 0]
            
        # Drop rows with non-positive prices
        for col in ["Open", "High", "Low", "Close"]:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors="coerce")
                df = df[df[col] > 0]
                
        return df

    def _load_cache_file(self, cache_file: str) -> pd.DataFrame:
        """
        Helper method to load CSV files from local storage.
        """
        df = pd.read_csv(cache_file, index_col="Date")
        return df

    def _save_cache_file(self, df: pd.DataFrame, cache_file: str):
        """
        Helper method to write DataFrame to local CSV storage with a retry lock loop.
        """
        for attempt in range(5):
            try:
                df.to_csv(cache_file)
                logger.info(f"Saved cache file to: {cache_file}")
                return
            except PermissionError as e:
                logger.warning(f"File locked, retrying save for {cache_file} (Attempt {attempt+1}/5): {e}")
                time.sleep(0.2)
        # Final attempt to report exception if still locked
        df.to_csv(cache_file)
        logger.info(f"Saved cache file to: {cache_file}")

    def _generate_simulated_ohlcv(self, symbol: str, size: int) -> pd.DataFrame:
        """
        Generates simulated daily price data for offline local runs and unit testing.
        Uses a deterministic seed based on symbol name to keep price history repeatable.
        """
        logger.info(f"Generating simulated price path for {symbol} (Size: {size} bars).")
        # Generate repeatable random seed from symbol string bytes
        seed = sum(ord(c) for c in symbol)
        np.random.seed(seed)
        
        # Start at ₹100 for stocks, ₹10,000 for index
        start_price = 10000.0 if symbol.upper().startswith("NIFTY") or symbol.upper().startswith("^") else 100.0
        
        # Geometric Brownian Motion simulation
        returns = np.random.normal(loc=0.0005, scale=0.015, size=size) # slight uptrend bias
        price_path = start_price * np.exp(np.cumsum(returns))
        
        dates = pd.date_range(end=pd.Timestamp.now(), periods=size, freq="B").strftime("%Y-%m-%d")
        
        df = pd.DataFrame(index=dates)
        df.index.name = "Date"
        
        df["Close"] = np.round(price_path, 2)
        # Generate High/Low/Open bounds around Close
        noise = np.random.uniform(0.001, 0.01, size=size)
        df["High"] = np.round(df["Close"] * (1 + noise), 2)
        df["Low"] = np.round(df["Close"] * (1 - noise), 2)
        df["Open"] = np.round(df["Close"] * np.random.uniform(0.995, 1.005, size=size), 2)
        
        # Volume between 20,000 and 150,000 shares
        df["Volume"] = np.random.randint(20000, 150000, size=size)
        
        # Clip open/high/low bounds to make them mathematically clean
        df["High"] = df[["Open", "High", "Close"]].max(axis=1)
        df["Low"] = df[["Open", "Low", "Close"]].min(axis=1)
        
        return df

    def fetch_nse_delivery_data(self, date_str: str) -> dict:
        """
        Downloads and parses NSE delivery data (MTO file) for a specific date (YYYY-MM-DD).
        Supports automatic historical fallback up to 5 days.
        """
        try:
            base_dt = datetime.strptime(date_str, "%Y-%m-%d")
        except Exception as e:
            logger.error(f"Invalid date format for delivery data fetch: {date_str} - {e}")
            return {}

        for offset in range(6):  # Try requested day, then up to 5 previous days
            current_dt = base_dt - timedelta(days=offset)
            current_date_str = current_dt.strftime("%Y-%m-%d")
            
            # Check if there is already a local cache of this MTO file in data/mto/
            local_mto_dir = "data/mto"
            if not os.path.exists(local_mto_dir):
                local_mto_dir = os.path.join("minervini_os", local_mto_dir)
            os.makedirs(local_mto_dir, exist_ok=True)
            
            formatted_date = current_dt.strftime("%d%m%Y")
            local_mto_file = os.path.join(local_mto_dir, f"MTO_{formatted_date}.DAT")
            
            content = None
            if os.path.exists(local_mto_file):
                try:
                    logger.info(f"Loading local MTO file: {local_mto_file}")
                    with open(local_mto_file, "r", encoding="utf-8") as f:
                        content = f.read()
                except Exception as e:
                    logger.warning(f"Failed to read local MTO file {local_mto_file}: {e}")
            
            if content is None:
                url = f"https://archives.nseindia.com/archives/equities/mto/MTO_{formatted_date}.DAT"
                headers = {"User-Agent": "Mozilla/5.0"}
                req = urllib.request.Request(url, headers=headers)
                
                try:
                    logger.info(f"Downloading delivery data from NSE archives: {url}")
                    with urllib.request.urlopen(req, timeout=5) as response:
                        content = response.read().decode("utf-8")
                    
                    # Save to local cache folder
                    with open(local_mto_file, "w", encoding="utf-8") as f:
                        f.write(content)
                    logger.info(f"Saved local MTO file cache: {local_mto_file}")
                except Exception as e:
                    logger.warning(f"No delivery data found on NSE for {current_date_str}: {e}")
                    continue
                    
            if content:
                delivery_map = {}
                for line in content.split("\n"):
                    parts = line.strip().split(",")
                    if len(parts) >= 6:
                        sec_name = parts[2].strip().upper()
                        series = parts[3].strip()
                        if series in ["EQ", "BE", "SM"]:
                            try:
                                delivery_map[sec_name] = {
                                    "Traded": int(parts[4]),
                                    "Deliverable": int(parts[5]),
                                    "Delivery_Pct": float(parts[6])
                                }
                            except ValueError:
                                continue
                if delivery_map:
                    logger.info(f"Successfully loaded {len(delivery_map)} delivery records for {current_date_str} (requested: {date_str})")
                    return delivery_map
                    
        return {}

    def update_delivery_percentages(self, symbols: list, date_str: str):
        """
        Fetches today's delivery data and writes the Delivery_Pct to the corresponding date row
        for each stock's cached CSV file.
        """
        logger.info(f"Updating delivery percentages in cache CSV files for date: {date_str}...")
        delivery_map = self.fetch_nse_delivery_data(date_str)
        if not delivery_map:
            logger.warning(f"No delivery data available to update cache CSVs for date {date_str}.")
            return
            
        updated_count = 0
        for symbol in symbols:
            sym_upper = symbol.upper()
            cache_file = os.path.join(self.cache_dir, f"{sym_upper}.csv")
            if not os.path.exists(cache_file):
                cache_file = os.path.join("minervini_os", cache_file)
                
            if os.path.exists(cache_file):
                try:
                    df = pd.read_csv(cache_file, index_col="Date")
                    # Ensure Delivery_Pct column exists
                    if "Delivery_Pct" not in df.columns:
                        df["Delivery_Pct"] = 0.0
                        
                    # Get delivery percentage from MTO
                    mto_info = delivery_map.get(sym_upper)
                    deliv_pct = float(mto_info["Delivery_Pct"]) if mto_info else 0.0
                    
                    # Update row
                    if date_str in df.index:
                        df.loc[date_str, "Delivery_Pct"] = deliv_pct
                    elif not df.empty:
                        # Fallback: if last row date matches date_str or is close
                        df.iloc[-1, df.columns.get_loc("Delivery_Pct")] = deliv_pct
                        
                    # Save back to CSV using robust retry helper
                    self._save_cache_file(df, cache_file)
                    updated_count += 1
                except Exception as e:
                    logger.error(f"Failed to update delivery pct for {sym_upper}: {e}")
                    
        logger.info(f"Updated delivery percentages for {updated_count} cache files on {date_str}.")
