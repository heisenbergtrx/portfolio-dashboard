"""
data_fetcher.py - Portföy Dashboard Veri Çekme Modülü (v5)
==========================================================

yfinance tabanlı veri çekimi - Alpha Vantage kaldırıldı (rate limit sorunu).

Veri kaynakları:
- ABD hisseleri: yfinance (limitsiz)
- Kripto: ccxt/binance 
- TEFAS: tefas-crawler
- USD/TRY: yfinance

v5 Değişiklikler:
- yfinance monkey-patch kaldırıldı (curl_cffi uyumsuzluğu)
- Rate limit koruması eklendi
- Daha akıllı fallback sistemi

Yazar: Portfolio Dashboard
Tarih: Ocak 2026
"""

# =============================================================================
# SSL FIX - EN BAŞTA OLMALI (v5)
# =============================================================================

import ssl
import os
import sys
import warnings

# Tüm uyarıları kapat
warnings.filterwarnings('ignore', message='Unverified HTTPS request')
warnings.filterwarnings('ignore', category=DeprecationWarning)

# 1. Certifi varsa environment variables ayarla
try:
    import certifi
    os.environ['SSL_CERT_FILE'] = certifi.where()
    os.environ['REQUESTS_CA_BUNDLE'] = certifi.where()
    os.environ['CURL_CA_BUNDLE'] = certifi.where()
except ImportError:
    pass

# 2. SSL context'i tamamen bypass et
try:
    _create_unverified_https_context = ssl._create_unverified_context
except AttributeError:
    pass
else:
    ssl._create_default_https_context = _create_unverified_https_context

# 3. urllib3 uyarılarını kapat
try:
    import urllib3
    urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
except:
    pass

# 4. requests session'ı verify=False ile oluştur
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

# Global session with SSL bypass ve retry
_session = requests.Session()
_session.verify = False

# Retry stratejisi - 429 için daha uzun bekleme
retry_strategy = Retry(
    total=3,
    backoff_factor=2,
    status_forcelist=[500, 502, 503, 504],
    respect_retry_after_header=True
)
adapter = HTTPAdapter(max_retries=retry_strategy)
_session.mount("http://", adapter)
_session.mount("https://", adapter)

# =============================================================================
# STANDART IMPORTS
# =============================================================================

import json
import logging
import time
import urllib.request
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Optional

import numpy as np
import pandas as pd

# yfinance import - DOĞRUDAN (patch yok)
import yfinance as yf

# CCXT import
try:
    import ccxt
    CCXT_AVAILABLE = True
except ImportError:
    CCXT_AVAILABLE = False
    logging.warning("ccxt bulunamadı.")

# TEFAS Crawler import
try:
    from tefas import Crawler as TefasCrawler
    TEFAS_CRAWLER_AVAILABLE = True
except ImportError:
    try:
        from tefas_crawler import Crawler as TefasCrawler
        TEFAS_CRAWLER_AVAILABLE = True
    except ImportError:
        TEFAS_CRAWLER_AVAILABLE = False

logger = logging.getLogger(__name__)

# Rate limit tracking
_last_yahoo_call = 0
_yahoo_call_count = 0
_YAHOO_MIN_INTERVAL = 1.5  # Minimum 1.5 saniye arası


def _rate_limit_yahoo():
    """Yahoo API rate limit koruması."""
    global _last_yahoo_call, _yahoo_call_count
    
    now = time.time()
    elapsed = now - _last_yahoo_call
    
    if elapsed < _YAHOO_MIN_INTERVAL:
        sleep_time = _YAHOO_MIN_INTERVAL - elapsed
        time.sleep(sleep_time)
    
    _last_yahoo_call = time.time()
    _yahoo_call_count += 1


# =============================================================================
# CACHE
# =============================================================================

class DataCache:
    """JSON tabanlı önbellek."""
    
    def __init__(self, cache_dir: str = ".cache", ttl_seconds: int = 3600):
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(exist_ok=True)
        self.ttl_seconds = ttl_seconds
        self.cache_file = self.cache_dir / "portfolio_cache.json"
        self._cache: dict = self._load_cache()
    
    def _load_cache(self) -> dict:
        if self.cache_file.exists():
            try:
                with open(self.cache_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except:
                pass
        return {}
    
    def _save_cache(self) -> None:
        try:
            with open(self.cache_file, 'w', encoding='utf-8') as f:
                json.dump(self._cache, f, indent=2, ensure_ascii=False, default=str)
        except Exception as e:
            logger.error(f"Cache kaydetme hatası: {e}")
    
    def get(self, key: str) -> Optional[dict]:
        if key not in self._cache:
            return None
        entry = self._cache[key]
        entry['is_stale'] = True
        try:
            cached_time = datetime.fromisoformat(entry.get('timestamp', '2000-01-01'))
            if datetime.now() - cached_time < timedelta(seconds=self.ttl_seconds):
                entry['is_stale'] = False
        except:
            pass
        return entry
    
    def set(self, key: str, data: dict) -> None:
        self._cache[key] = {
            'timestamp': datetime.now().isoformat(),
            'data': data,
            'is_stale': False
        }
        self._save_cache()


_cache = DataCache()

def get_cache() -> DataCache:
    return _cache

def set_cache_ttl(ttl_seconds: int) -> None:
    global _cache
    _cache.ttl_seconds = ttl_seconds


# =============================================================================
# USD/TRY
# =============================================================================

def fetch_usd_try_rate(timeout: int = 30) -> float:
    """USD/TRY kurunu çek."""
    cache_key = "USDTRY"
    
    # Önce cache kontrol et (fresh ise kullan)
    cached = _cache.get(cache_key)
    if cached and 'data' in cached and not cached.get('is_stale', True):
        rate = float(cached['data'].get('rate', 35.5))
        logger.info(f"USD/TRY (cache): {rate:.4f}")
        return rate
    
    _rate_limit_yahoo()
    
    try:
        logger.info("USD/TRY çekiliyor...")
        
        ticker = yf.Ticker("USDTRY=X")
        hist = ticker.history(period="5d")
        
        if not hist.empty:
            rate = float(hist['Close'].iloc[-1])
            _cache.set(cache_key, {'rate': rate})
            logger.info(f"USD/TRY: {rate:.4f}")
            return rate
        
        raise ValueError("yfinance veri boş")
        
    except Exception as e:
        logger.warning(f"yfinance USD/TRY hatası: {e}")
        
        # Fallback: direkt API dene
        try:
            time.sleep(2)
            url = "https://query1.finance.yahoo.com/v8/finance/chart/USDTRY=X?interval=1d&range=5d"
            response = _session.get(url, timeout=timeout)
            if response.status_code == 200:
                data = response.json()
                closes = data['chart']['result'][0]['indicators']['quote'][0]['close']
                rate = float([c for c in closes if c is not None][-1])
                _cache.set(cache_key, {'rate': rate})
                logger.info(f"USD/TRY (API): {rate:.4f}")
                return rate
            elif response.status_code == 429:
                logger.warning("Yahoo API rate limit - cache kullanılıyor")
        except Exception as e2:
            logger.warning(f"Yahoo API hatası: {e2}")
        
        # Cache fallback (stale olsa bile)
        if cached and 'data' in cached:
            rate = float(cached['data'].get('rate', 35.5))
            logger.info(f"USD/TRY (stale cache): {rate:.4f}")
            return rate
        return 35.5


# =============================================================================
# ABD HİSSELERİ - YFINANCE
# =============================================================================

def fetch_us_stock_price(ticker: str, timeout: int = 30) -> dict:
    """ABD hisse fiyatını yfinance ile çek."""
    cache_key = f"US_{ticker}"
    
    # Önce cache kontrol et
    cached = _cache.get(cache_key)
    if cached and 'data' in cached and not cached.get('is_stale', True):
        logger.info(f"{ticker} (cache): ${cached['data'].get('current_price', 'N/A')}")
        return cached['data']
    
    _rate_limit_yahoo()
    
    try:
        logger.info(f"yfinance ile çekiliyor: {ticker}")
        
        stock = yf.Ticker(ticker)
        hist = stock.history(period="14d")
        
        if hist.empty:
            raise ValueError(f"{ticker} için veri yok")
        
        current_price = float(hist['Close'].iloc[-1])
        
        if len(hist) >= 6:
            prev_week_price = float(hist['Close'].iloc[-6])
        else:
            prev_week_price = float(hist['Close'].iloc[0])
        
        name = ticker
        try:
            info = stock.info
            name = info.get('shortName') or info.get('longName') or ticker
        except:
            pass
        
        result = {
            'ticker': ticker,
            'name': name,
            'current_price': current_price,
            'prev_week_price': prev_week_price,
            'currency': 'USD',
            'source': 'yfinance',
            'timestamp': datetime.now().isoformat()
        }
        
        _cache.set(cache_key, result)
        logger.info(f"{ticker}: ${current_price:.2f}")
        return result
        
    except Exception as e:
        logger.warning(f"yfinance hatası ({ticker}): {e}")
        
        if '429' in str(e) or 'Too Many Requests' in str(e):
            logger.warning(f"Rate limit! 5 saniye bekleniyor...")
            time.sleep(5)
        
        # Fallback: Direkt Yahoo Finance API
        try:
            time.sleep(1)
            url = f"https://query1.finance.yahoo.com/v8/finance/chart/{ticker}?interval=1d&range=14d"
            response = _session.get(url, timeout=timeout)
            
            if response.status_code == 200:
                data = response.json()
                chart = data['chart']['result'][0]
                closes = chart['indicators']['quote'][0]['close']
                closes = [c for c in closes if c is not None]
                
                if closes:
                    current_price = float(closes[-1])
                    prev_week_price = float(closes[-6]) if len(closes) >= 6 else float(closes[0])
                    
                    meta = chart.get('meta', {})
                    name = meta.get('shortName') or meta.get('longName') or ticker
                    
                    result = {
                        'ticker': ticker,
                        'name': name,
                        'current_price': current_price,
                        'prev_week_price': prev_week_price,
                        'currency': 'USD',
                        'source': 'yahoo_api',
                        'timestamp': datetime.now().isoformat()
                    }
                    
                    _cache.set(cache_key, result)
                    logger.info(f"{ticker} (API): ${current_price:.2f}")
                    return result
            
            elif response.status_code == 429:
                logger.warning(f"Yahoo API rate limit for {ticker}")
                    
        except Exception as e2:
            logger.error(f"Yahoo API hatası ({ticker}): {e2}")
        
        # Cache fallback
        if cached and 'data' in cached:
            logger.warning(f"Cache'den (stale) {ticker}")
            return cached['data']
        
        return {
            'ticker': ticker,
            'name': ticker,
            'current_price': None,
            'prev_week_price': None,
            'currency': 'USD',
            'error': str(e),
            'timestamp': datetime.now().isoformat()
        }


def fetch_us_stock_history(ticker: str, days: int = 30) -> pd.DataFrame:
    """ABD hisse geçmiş verisi."""
    _rate_limit_yahoo()
    
    try:
        stock = yf.Ticker(ticker)
        hist = stock.history(period=f"{days}d")
        
        if hist.empty:
            time.sleep(1)
            url = f"https://query1.finance.yahoo.com/v8/finance/chart/{ticker}?interval=1d&range={days}d"
            response = _session.get(url, timeout=30)
            
            if response.status_code == 200:
                data = response.json()
                chart = data['chart']['result'][0]
                timestamps = chart['timestamp']
                closes = chart['indicators']['quote'][0]['close']
                
                df = pd.DataFrame({
                    'Date': pd.to_datetime(timestamps, unit='s'),
                    'Close': closes
                })
                df = df.dropna()
                return df
            
            return pd.DataFrame(columns=['Date', 'Close'])
        
        df = hist[['Close']].reset_index()
        df['Date'] = pd.to_datetime(df['Date']).dt.tz_localize(None)
        return df
        
    except Exception as e:
        logger.error(f"Geçmiş veri hatası ({ticker}): {e}")
        return pd.DataFrame(columns=['Date', 'Close'])


# =============================================================================
# KRİPTO - CCXT
# =============================================================================

def fetch_crypto_price(symbol: str, exchange_id: str = 'binance', timeout: int = 30) -> dict:
    """Kripto fiyatını çek."""
    cache_key = f"CRYPTO_{symbol.replace('/', '_')}"
    
    if not CCXT_AVAILABLE:
        return {
            'symbol': symbol,
            'name': symbol.split('/')[0],
            'current_price': None,
            'prev_week_price': None,
            'currency': 'USDT',
            'error': 'ccxt kurulu değil',
            'timestamp': datetime.now().isoformat()
        }
    
    try:
        logger.info(f"Kripto çekiliyor: {symbol}")
        
        exchange_class = getattr(ccxt, exchange_id)
        exchange = exchange_class({
            'enableRateLimit': True,
            'timeout': timeout * 1000
        })
        
        ticker_data = exchange.fetch_ticker(symbol)
        current_price = float(ticker_data['last'])
        
        since = exchange.parse8601((datetime.now() - timedelta(days=8)).isoformat())
        ohlcv = exchange.fetch_ohlcv(symbol, '1d', since=since, limit=8)
        
        if ohlcv and len(ohlcv) >= 2:
            prev_week_price = float(ohlcv[0][4])
        else:
            prev_week_price = current_price
        
        result = {
            'symbol': symbol,
            'name': symbol.split('/')[0],
            'current_price': current_price,
            'prev_week_price': prev_week_price,
            'currency': 'USDT',
            'source': exchange_id,
            'timestamp': datetime.now().isoformat()
        }
        
        _cache.set(cache_key, result)
        logger.info(f"{symbol}: ${current_price:.4f}")
        return result
        
    except Exception as e:
        logger.error(f"Kripto hatası ({symbol}): {e}")
        
        cached = _cache.get(cache_key)
        if cached and 'data' in cached:
            return cached['data']
        
        return {
            'symbol': symbol,
            'name': symbol.split('/')[0],
            'current_price': None,
            'prev_week_price': None,
            'currency': 'USDT',
            'error': str(e),
            'timestamp': datetime.now().isoformat()
        }


def fetch_crypto_history(symbol: str, days: int = 30, exchange_id: str = 'binance') -> pd.DataFrame:
    """Kripto geçmiş verisi."""
    if not CCXT_AVAILABLE:
        return pd.DataFrame(columns=['Date', 'Close'])
    
    try:
        exchange_class = getattr(ccxt, exchange_id)
        exchange = exchange_class({'enableRateLimit': True})
        
        since = exchange.parse8601((datetime.now() - timedelta(days=days + 1)).isoformat())
        ohlcv = exchange.fetch_ohlcv(symbol, '1d', since=since, limit=days + 1)
        
        if not ohlcv:
            return pd.DataFrame(columns=['Date', 'Close'])
        
        df = pd.DataFrame(ohlcv, columns=['Timestamp', 'Open', 'High', 'Low', 'Close', 'Volume'])
        df['Date'] = pd.to_datetime(df['Timestamp'], unit='ms')
        return df[['Date', 'Close']]
        
    except Exception as e:
        logger.error(f"Kripto geçmiş hatası ({symbol}): {e}")
        return pd.DataFrame(columns=['Date', 'Close'])


# =============================================================================
# TEFAS
# =============================================================================

def fetch_tefas_price_crawler(fund_code: str, timeout: int = 30) -> Optional[dict]:
    """TEFAS fon fiyatını tefas-crawler ile çek."""
    if not TEFAS_CRAWLER_AVAILABLE:
        return None
    
    try:
        logger.info(f"TEFAS crawler: {fund_code}")
        
        crawler = TefasCrawler()
        end_date = datetime.now()
        start_date = end_date - timedelta(days=14)
        
        df = crawler.fetch(
            start=start_date.strftime('%Y-%m-%d'),
            end=end_date.strftime('%Y-%m-%d'),
            name=fund_code,
            columns=['date', 'price', 'title']
        )
        
        if df is None or df.empty:
            return None
        
        current_price = float(df['price'].iloc[-1])
        fund_name = df['title'].iloc[0] if 'title' in df.columns else fund_code
        prev_week_price = float(df['price'].iloc[-6]) if len(df) >= 6 else float(df['price'].iloc[0])
        
        return {
            'code': fund_code,
            'name': fund_name,
            'current_price': current_price,
            'prev_week_price': prev_week_price,
            'currency': 'TRY',
            'timestamp': datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"TEFAS crawler hatası ({fund_code}): {e}")
        return None


def fetch_tefas_price_requests(fund_code: str, timeout: int = 30) -> Optional[dict]:
    """TEFAS API ile çek."""
    try:
        logger.info(f"TEFAS API: {fund_code}")
        
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Accept': 'application/json'
        }
        
        end_date = datetime.now().strftime('%Y-%m-%d')
        start_date = (datetime.now() - timedelta(days=14)).strftime('%Y-%m-%d')
        
        url = f"https://www.tefas.gov.tr/api/DB/BindHistoryInfo?fonkod={fund_code}&baession={start_date}&bitession={end_date}"
        
        response = _session.get(url, headers=headers, timeout=timeout)
        
        if response.status_code == 200:
            data = response.json()
            if data and isinstance(data, list) and len(data) > 0:
                current = data[-1]
                current_price = float(current.get('BirimPayDegeri', 0))
                fund_name = current.get('FonAdi', fund_code)
                prev_idx = max(0, len(data) - 6)
                prev_week_price = float(data[prev_idx].get('BirimPayDegeri', current_price))
                
                return {
                    'code': fund_code,
                    'name': fund_name,
                    'current_price': current_price,
                    'prev_week_price': prev_week_price,
                    'currency': 'TRY',
                    'timestamp': datetime.now().isoformat()
                }
        
        return None
        
    except Exception as e:
        logger.warning(f"TEFAS API hatası ({fund_code}): {e}")
        return None


def fetch_tefas_price(fund_code: str, timeout: int = 30) -> dict:
    """TEFAS fon fiyatını çek."""
    cache_key = f"TEFAS_{fund_code}"
    
    result = fetch_tefas_price_crawler(fund_code, timeout)
    if result and result.get('current_price'):
        _cache.set(cache_key, result)
        return result
    
    result = fetch_tefas_price_requests(fund_code, timeout)
    if result and result.get('current_price'):
        _cache.set(cache_key, result)
        return result
    
    cached = _cache.get(cache_key)
    if cached and 'data' in cached:
        logger.warning(f"Cache'den TEFAS: {fund_code}")
        return cached['data']
    
    return {
        'code': fund_code,
        'name': fund_code,
        'current_price': None,
        'prev_week_price': None,
        'currency': 'TRY',
        'error': 'Veri alınamadı',
        'timestamp': datetime.now().isoformat()
    }


def fetch_tefas_history(fund_code: str, days: int = 30) -> pd.DataFrame:
    """TEFAS geçmiş verisi."""
    if not TEFAS_CRAWLER_AVAILABLE:
        return pd.DataFrame(columns=['Date', 'Close'])
    
    try:
        crawler = TefasCrawler()
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days + 5)
        
        df = crawler.fetch(
            start=start_date.strftime('%Y-%m-%d'),
            end=end_date.strftime('%Y-%m-%d'),
            name=fund_code,
            columns=['date', 'price']
        )
        
        if df is None or df.empty:
            return pd.DataFrame(columns=['Date', 'Close'])
        
        df = df.rename(columns={'date': 'Date', 'price': 'Close'})
        df['Date'] = pd.to_datetime(df['Date'])
        return df[['Date', 'Close']]
        
    except Exception as e:
        logger.error(f"TEFAS geçmiş hatası ({fund_code}): {e}")
        return pd.DataFrame(columns=['Date', 'Close'])


# =============================================================================
# TOPLU VERİ ÇEKİMİ
# =============================================================================

def fetch_all_prices(
    tefas_codes: list,
    us_tickers: list,
    crypto_symbols: list,
    timeout: int = 30
) -> dict:
    """Tüm varlık fiyatlarını çek."""
    
    results = {
        'usd_try': fetch_usd_try_rate(timeout),
        'tefas': {},
        'us_stocks': {},
        'crypto': {},
        'fetch_time': datetime.now().isoformat()
    }
    
    # TEFAS (rate limit yok)
    for code in tefas_codes:
        results['tefas'][code] = fetch_tefas_price(code, timeout)
        time.sleep(0.3)
    
    # Kripto (Binance rate limit düşük)
    for symbol in crypto_symbols:
        results['crypto'][symbol] = fetch_crypto_price(symbol, timeout=timeout)
        time.sleep(0.3)
    
    # ABD hisseleri EN SONA (Yahoo rate limit)
    for ticker in us_tickers:
        results['us_stocks'][ticker] = fetch_us_stock_price(ticker, timeout)
    
    return results


# =============================================================================
# TEST
# =============================================================================

if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s'
    )
    
    print("=" * 60)
    print("DATA FETCHER TEST (v5 - Rate Limit Korumalı)")
    print("=" * 60)
    
    print("\n[1] USD/TRY testi...")
    rate = fetch_usd_try_rate()
    print(f"    USD/TRY: {rate}")
    
    print("\n[2] ABD Hisse testi (AAPL)...")
    aapl = fetch_us_stock_price("AAPL")
    print(f"    AAPL: ${aapl.get('current_price', 'HATA')}")
    
    print("\n[3] Kripto testi (BTC/USDT)...")
    btc = fetch_crypto_price("BTC/USDT")
    print(f"    BTC/USDT: ${btc.get('current_price', 'HATA')}")
    
    print("\n" + "=" * 60)
    print("TEST TAMAMLANDI")
    print("=" * 60)
