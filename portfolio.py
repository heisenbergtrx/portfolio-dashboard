"""
portfolio.py - Portföy Hesaplama ve Optimizasyon Modülü (v3)
============================================================

Supabase entegrasyonu için config dönüşüm fonksiyonları eklendi.

Yazar: Portfolio Dashboard
Tarih: Ocak 2026
"""

import logging
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

import numpy as np
import pandas as pd
import yaml

from data_fetcher import (
    fetch_all_prices,
    fetch_crypto_history,
    fetch_tefas_history,
    fetch_us_stock_history,
    fetch_usd_try_rate,
    get_cache,
    set_cache_ttl,
)

logger = logging.getLogger(__name__)


# =============================================================================
# VERİ SINIFLARI
# =============================================================================

@dataclass
class Asset:
    """Tek bir varlığı temsil eden sınıf."""
    code: str
    name: str
    asset_type: str
    shares: float
    current_price: float
    prev_week_price: float
    currency: str
    target_weight: float
    is_cash_reserve: bool = False
    
    value_original: float = 0.0
    value_try: float = 0.0
    actual_weight: float = 0.0
    weekly_return: float = 0.0
    weight_deviation: float = 0.0
    
    @property
    def is_valid(self) -> bool:
        return self.current_price is not None and self.current_price > 0 and self.shares > 0


@dataclass
class PortfolioConfig:
    """Portföy konfigürasyonu."""
    risk_free_rate: float = 0.35
    cache_ttl_seconds: int = 3600
    fetch_timeout_seconds: int = 30
    log_level: str = "INFO"
    
    weekly_loss_threshold: float = -4.0
    weekly_gain_threshold: float = 7.0
    weight_deviation_threshold: float = 5.0
    high_volatility_threshold: float = 15.0
    high_correlation_threshold: float = 0.7
    
    cash_reserve_codes: list[str] = field(default_factory=lambda: ['DLY', 'DIP', 'USD'])
    
    tefas_funds: list[dict] = field(default_factory=list)
    us_stocks: list[dict] = field(default_factory=list)
    crypto: list[dict] = field(default_factory=list)
    cash: list[dict] = field(default_factory=list)


@dataclass
class PortfolioMetrics:
    """Portföy metrikleri."""
    total_value_try: float = 0.0
    weekly_return_pct: float = 0.0
    sharpe_ratio: Optional[float] = None
    volatility_monthly: Optional[float] = None
    diversification_score: Optional[float] = None
    cash_reserve_try: float = 0.0
    cash_reserve_pct: float = 0.0
    warnings: list[str] = field(default_factory=list)


# =============================================================================
# CONFIG DÖNÜŞÜM FONKSİYONLARI (Supabase için)
# =============================================================================

def config_to_dict(config: PortfolioConfig) -> dict:
    """PortfolioConfig'i dictionary'e çevir (JSON için)."""
    return {
        'settings': {
            'risk_free_rate': config.risk_free_rate,
            'cache_ttl_seconds': config.cache_ttl_seconds,
            'fetch_timeout_seconds': config.fetch_timeout_seconds,
            'log_level': config.log_level,
        },
        'thresholds': {
            'weekly_loss_threshold': config.weekly_loss_threshold,
            'weekly_gain_threshold': config.weekly_gain_threshold,
            'weight_deviation_threshold': config.weight_deviation_threshold,
            'high_volatility_threshold': config.high_volatility_threshold,
            'high_correlation_threshold': config.high_correlation_threshold,
        },
        'cash_reserve_codes': config.cash_reserve_codes,
        'tefas_funds': config.tefas_funds,
        'us_stocks': config.us_stocks,
        'crypto': config.crypto,
        'cash': config.cash,
    }


def dict_to_config(data: dict) -> PortfolioConfig:
    """Dictionary'den PortfolioConfig oluştur."""
    if not data:
        return PortfolioConfig()
    
    settings = data.get('settings', {})
    thresholds = data.get('thresholds', {})
    
    return PortfolioConfig(
        risk_free_rate=settings.get('risk_free_rate', 0.35),
        cache_ttl_seconds=settings.get('cache_ttl_seconds', 3600),
        fetch_timeout_seconds=settings.get('fetch_timeout_seconds', 30),
        log_level=settings.get('log_level', 'INFO'),
        
        weekly_loss_threshold=thresholds.get('weekly_loss_threshold', -4.0),
        weekly_gain_threshold=thresholds.get('weekly_gain_threshold', 7.0),
        weight_deviation_threshold=thresholds.get('weight_deviation_threshold', 5.0),
        high_volatility_threshold=thresholds.get('high_volatility_threshold', 15.0),
        high_correlation_threshold=thresholds.get('high_correlation_threshold', 0.7),
        
        cash_reserve_codes=data.get('cash_reserve_codes', ['DLY', 'DIP', 'USD']),
        tefas_funds=data.get('tefas_funds', []),
        us_stocks=data.get('us_stocks', []),
        crypto=data.get('crypto', []),
        cash=data.get('cash', []),
    )


# =============================================================================
# KONFİGÜRASYON YÖNETİMİ (Dosya)
# =============================================================================

def load_config(config_path: str = "config.yaml") -> PortfolioConfig:
    """YAML config dosyasını yükle."""
    config_file = Path(config_path)
    
    if not config_file.exists():
        logger.warning(f"Config bulunamadı: {config_path}")
        return PortfolioConfig()
    
    try:
        with open(config_file, 'r', encoding='utf-8') as f:
            data = yaml.safe_load(f)
        
        return dict_to_config(data)
        
    except Exception as e:
        logger.error(f"Config yükleme hatası: {e}")
        return PortfolioConfig()


# =============================================================================
# PORTFÖY SINIFI
# =============================================================================

class Portfolio:
    """Ana portföy sınıfı."""
    
    def __init__(self, config: PortfolioConfig):
        self.config = config
        self.assets: list[Asset] = []
        self.metrics = PortfolioMetrics()
        self.usd_try_rate: float = 35.0
        self.last_update: Optional[datetime] = None
        self.price_data: dict[str, Any] = {}
        
        set_cache_ttl(config.cache_ttl_seconds)
    
    def refresh_prices(self) -> bool:
        """Tüm fiyatları güncelle."""
        try:
            logger.info("Fiyatlar güncelleniyor...")
            
            tefas_codes = [f['code'] for f in self.config.tefas_funds]
            us_tickers = [s['ticker'] for s in self.config.us_stocks]
            crypto_symbols = [c['symbol'] for c in self.config.crypto]
            
            self.price_data = fetch_all_prices(
                tefas_codes=tefas_codes,
                us_tickers=us_tickers,
                crypto_symbols=crypto_symbols,
                timeout=self.config.fetch_timeout_seconds
            )
            
            self.usd_try_rate = self.price_data.get('usd_try', 35.0)
            
            self._build_assets()
            self._calculate_metrics()
            
            self.last_update = datetime.now()
            logger.info(f"Güncellendi: {len(self.assets)} varlık")
            
            return True
            
        except Exception as e:
            logger.error(f"Güncelleme hatası: {e}")
            return False
    
    def _build_assets(self) -> None:
        """Asset nesnelerini oluştur."""
        self.assets = []
        
        # TEFAS
        for fund in self.config.tefas_funds:
            code = fund['code']
            price_info = self.price_data.get('tefas', {}).get(code, {})
            is_cash = code in self.config.cash_reserve_codes
            
            asset = Asset(
                code=code,
                name=price_info.get('name', code),
                asset_type="TEFAS",
                shares=fund['shares'],
                current_price=price_info.get('current_price', 0) or 0,
                prev_week_price=price_info.get('prev_week_price', 0) or 0,
                currency='TRY',
                target_weight=fund.get('target_weight', 0),
                is_cash_reserve=is_cash
            )
            self.assets.append(asset)
        
        # US Stocks
        for stock in self.config.us_stocks:
            ticker = stock['ticker']
            price_info = self.price_data.get('us_stocks', {}).get(ticker, {})
            
            asset = Asset(
                code=ticker,
                name=price_info.get('name', ticker),
                asset_type="US_STOCK",
                shares=stock['shares'],
                current_price=price_info.get('current_price', 0) or 0,
                prev_week_price=price_info.get('prev_week_price', 0) or 0,
                currency='USD',
                target_weight=stock.get('target_weight', 0),
                is_cash_reserve=False
            )
            self.assets.append(asset)
        
        # Crypto
        for crypto in self.config.crypto:
            symbol = crypto['symbol']
            price_info = self.price_data.get('crypto', {}).get(symbol, {})
            code = symbol.split('/')[0]
            
            asset = Asset(
                code=code,
                name=price_info.get('name', code),
                asset_type="CRYPTO",
                shares=crypto['amount'],
                current_price=price_info.get('current_price', 0) or 0,
                prev_week_price=price_info.get('prev_week_price', 0) or 0,
                currency='USDT',
                target_weight=crypto.get('target_weight', 0),
                is_cash_reserve=False
            )
            self.assets.append(asset)
        
        # Cash
        for cash_item in self.config.cash:
            code = cash_item['code']
            
            asset = Asset(
                code=code,
                name="USD Nakit",
                asset_type="CASH",
                shares=cash_item['amount'],
                current_price=1.0,
                prev_week_price=1.0,
                currency='USD',
                target_weight=cash_item.get('target_weight', 0),
                is_cash_reserve=True
            )
            self.assets.append(asset)
        
        self._calculate_values()
    
    def _calculate_values(self) -> None:
        """Değer ve ağırlık hesapla."""
        total_try = 0.0
        
        for asset in self.assets:
            if not asset.is_valid:
                continue
            
            asset.value_original = asset.shares * asset.current_price
            
            if asset.currency in ('USD', 'USDT'):
                asset.value_try = asset.value_original * self.usd_try_rate
            else:
                asset.value_try = asset.value_original
            
            total_try += asset.value_try
        
        for asset in self.assets:
            if not asset.is_valid:
                continue
            
            if total_try > 0:
                asset.actual_weight = (asset.value_try / total_try) * 100
            
            asset.weight_deviation = asset.actual_weight - asset.target_weight
            
            if asset.prev_week_price and asset.prev_week_price > 0:
                asset.weekly_return = ((asset.current_price - asset.prev_week_price) / asset.prev_week_price) * 100
    
    def _calculate_metrics(self) -> None:
        """Portföy metriklerini hesapla."""
        valid_assets = [a for a in self.assets if a.is_valid]
        
        if not valid_assets:
            return
        
        self.metrics.total_value_try = sum(a.value_try for a in valid_assets)
        
        cash_assets = [a for a in valid_assets if a.is_cash_reserve]
        self.metrics.cash_reserve_try = sum(a.value_try for a in cash_assets)
        
        if self.metrics.total_value_try > 0:
            self.metrics.cash_reserve_pct = (self.metrics.cash_reserve_try / self.metrics.total_value_try) * 100
        
        # Ağırlıklı haftalık getiri
        weighted_return = 0.0
        for asset in valid_assets:
            weight = asset.value_try / self.metrics.total_value_try if self.metrics.total_value_try > 0 else 0
            weighted_return += asset.weekly_return * weight
        
        self.metrics.weekly_return_pct = weighted_return
        self.metrics.warnings = []
        
        if self.metrics.weekly_return_pct < self.config.weekly_loss_threshold:
            self.metrics.warnings.append(f"⚠️ Yüksek kayıp: {self.metrics.weekly_return_pct:.1f}%")
        
        self._calculate_risk_metrics()
    
    def _calculate_risk_metrics(self) -> None:
        """Risk metriklerini hesapla."""
        try:
            all_returns = []
            
            for asset in self.assets:
                if not asset.is_valid or asset.asset_type == "CASH":
                    continue
                
                try:
                    if asset.asset_type == "TEFAS":
                        hist = fetch_tefas_history(asset.code, days=30)
                    elif asset.asset_type == "US_STOCK":
                        hist = fetch_us_stock_history(asset.code, days=30)
                    elif asset.asset_type == "CRYPTO":
                        symbol = f"{asset.code}/USDT"
                        hist = fetch_crypto_history(symbol, days=30)
                    else:
                        continue
                    
                    if hist is not None and len(hist) > 5:
                        returns = hist['Close'].pct_change().dropna()
                        all_returns.append({
                            'code': asset.code,
                            'returns': returns,
                            'weight': asset.actual_weight / 100
                        })
                except:
                    continue
            
            if len(all_returns) >= 2:
                portfolio_returns = pd.Series(dtype=float)
                
                for item in all_returns:
                    if len(portfolio_returns) == 0:
                        portfolio_returns = item['returns'] * item['weight']
                    else:
                        aligned = portfolio_returns.align(item['returns'] * item['weight'], join='inner')
                        portfolio_returns = aligned[0] + aligned[1]
                
                if len(portfolio_returns) > 5:
                    daily_vol = portfolio_returns.std()
                    self.metrics.volatility_monthly = daily_vol * np.sqrt(21) * 100
                    
                    daily_rf = self.config.risk_free_rate / 252
                    excess_return = portfolio_returns.mean() - daily_rf
                    
                    if daily_vol > 0:
                        self.metrics.sharpe_ratio = (excess_return / daily_vol) * np.sqrt(252)
                
        except Exception as e:
            logger.error(f"Risk hesaplama hatası: {e}")
    
    def get_summary_dataframe(self) -> pd.DataFrame:
        """Özet DataFrame döndür."""
        data = []
        
        for asset in self.assets:
            data.append({
                'Kod': asset.code,
                'Tür': asset.asset_type,
                'İsim': asset.name[:25] + '...' if len(asset.name) > 25 else asset.name,
                'Adet': asset.shares,
                'Fiyat': asset.current_price,
                'Birim': asset.currency,
                'Değer (TRY)': asset.value_try,
                'Ağırlık (%)': asset.actual_weight,
                'Hedef (%)': asset.target_weight,
                'Sapma (%)': asset.weight_deviation,
                'Haftalık (%)': asset.weekly_return,
                'Nakit': '✓' if asset.is_cash_reserve else ''
            })
        
        return pd.DataFrame(data)
    
    def get_cash_reserve_breakdown(self) -> pd.DataFrame:
        """Nakit rezervi dağılımı."""
        data = []
        
        for asset in self.assets:
            if asset.is_cash_reserve and asset.is_valid:
                data.append({
                    'Kod': asset.code,
                    'İsim': asset.name,
                    'Değer (TRY)': asset.value_try
                })
        
        return pd.DataFrame(data)
    
    def get_correlation_matrix(self) -> Optional[pd.DataFrame]:
        """Korelasyon matrisi."""
        all_returns = []
        
        for asset in self.assets:
            if not asset.is_valid or asset.asset_type == "CASH":
                continue
            
            try:
                if asset.asset_type == "TEFAS":
                    hist = fetch_tefas_history(asset.code, days=30)
                elif asset.asset_type == "US_STOCK":
                    hist = fetch_us_stock_history(asset.code, days=30)
                elif asset.asset_type == "CRYPTO":
                    symbol = f"{asset.code}/USDT"
                    hist = fetch_crypto_history(symbol, days=30)
                else:
                    continue
                
                if hist is not None and len(hist) > 5:
                    returns = hist['Close'].pct_change().dropna()
                    all_returns.append({'code': asset.code, 'returns': returns})
            except:
                continue
        
        if len(all_returns) < 2:
            return None
        
        returns_df = pd.DataFrame()
        for item in all_returns:
            returns_df[item['code']] = item['returns']
        
        return returns_df.corr()
    
    def get_history_data(self, asset_code: str, days: int = 30) -> pd.DataFrame:
        """Varlık geçmiş verisi."""
        asset = next((a for a in self.assets if a.code == asset_code), None)
        
        if not asset:
            return pd.DataFrame(columns=['Date', 'Close'])
        
        if asset.asset_type == "TEFAS":
            return fetch_tefas_history(asset_code, days)
        elif asset.asset_type == "US_STOCK":
            return fetch_us_stock_history(asset_code, days)
        elif asset.asset_type == "CRYPTO":
            return fetch_crypto_history(f"{asset_code}/USDT", days)
        elif asset.asset_type == "CASH":
            dates = pd.date_range(end=datetime.now(), periods=days, freq='D')
            return pd.DataFrame({'Date': dates, 'Close': [1.0] * days})
        
        return pd.DataFrame(columns=['Date', 'Close'])


# =============================================================================
# YARDIMCI FONKSİYONLAR
# =============================================================================

def format_currency(value: float, currency: str = "TRY") -> str:
    if currency == "TRY":
        return f"₺{value:,.2f}"
    elif currency in ("USD", "USDT"):
        return f"${value:,.2f}"
    return f"{value:,.2f} {currency}"


def format_percentage(value: float, include_sign: bool = True) -> str:
    if include_sign and value > 0:
        return f"+{value:.2f}%"
    return f"{value:.2f}%"
