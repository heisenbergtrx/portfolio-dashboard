"""
portfolio.py - Portföy Hesaplama ve Optimizasyon Modülü (v2)
============================================================

Bu modül portföy analizi için gerekli tüm hesaplamaları yapar:
- Getiri hesaplamaları (günlük, haftalık, aylık)
- Portföy değeri ve ağırlık hesaplamaları
- Risk metrikleri (volatilite, Sharpe Ratio)
- Korelasyon matrisi
- Nakit rezervi takibi

v2 Güncellemeler:
- USD nakit desteği
- Nakit rezervi kategorisi (DLY, DIP, USD)

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
    code: str                    # Varlık kodu/ticker/sembol
    name: str                    # Varlık adı
    asset_type: str              # "TEFAS", "US_STOCK", "CRYPTO", "CASH"
    shares: float                # Adet/miktar
    current_price: float         # Güncel fiyat
    prev_week_price: float       # Önceki hafta fiyatı
    currency: str                # Para birimi
    target_weight: float         # Hedef ağırlık (%)
    is_cash_reserve: bool = False  # Nakit rezervi mi?
    
    # Hesaplanan alanlar
    value_original: float = 0.0  # Orijinal para birimi cinsinden değer
    value_try: float = 0.0       # TRY cinsinden değer
    actual_weight: float = 0.0   # Gerçek ağırlık (%)
    weekly_return: float = 0.0   # Haftalık getiri (%)
    weight_deviation: float = 0.0  # Hedeften sapma (%)
    
    @property
    def is_valid(self) -> bool:
        """Varlık verisi geçerli mi?"""
        return (
            self.current_price is not None and 
            self.current_price > 0 and
            self.shares > 0
        )


@dataclass
class PortfolioConfig:
    """Portföy konfigürasyonu."""
    # Genel ayarlar
    risk_free_rate: float = 0.35
    cache_ttl_seconds: int = 3600
    fetch_timeout_seconds: int = 30
    log_level: str = "INFO"
    
    # Eşikler
    weekly_loss_threshold: float = -4.0
    weekly_gain_threshold: float = 7.0
    weight_deviation_threshold: float = 5.0
    high_volatility_threshold: float = 15.0
    high_correlation_threshold: float = 0.7
    
    # Nakit rezervi kodları
    cash_reserve_codes: list[str] = field(default_factory=lambda: ['DLY', 'DIP', 'USD'])
    
    # Varlık listeleri
    tefas_funds: list[dict] = field(default_factory=list)
    us_stocks: list[dict] = field(default_factory=list)
    crypto: list[dict] = field(default_factory=list)
    cash: list[dict] = field(default_factory=list)  # USD nakit


@dataclass
class PortfolioMetrics:
    """Portföy metrikleri."""
    total_value_try: float = 0.0
    weekly_return_pct: float = 0.0
    sharpe_ratio: Optional[float] = None
    volatility_monthly: Optional[float] = None
    diversification_score: Optional[float] = None
    
    # Nakit rezervi
    cash_reserve_try: float = 0.0
    cash_reserve_pct: float = 0.0
    
    # Uyarılar
    warnings: list[str] = field(default_factory=list)


# =============================================================================
# KONFİGÜRASYON YÖNETİMİ
# =============================================================================

def load_config(config_path: str = "config.yaml") -> PortfolioConfig:
    """
    YAML konfigürasyon dosyasını yükle.
    
    Args:
        config_path: Config dosya yolu
        
    Returns:
        PortfolioConfig nesnesi
    """
    config_file = Path(config_path)
    
    if not config_file.exists():
        logger.warning(f"Config dosyası bulunamadı: {config_path}")
        return PortfolioConfig()
    
    try:
        with open(config_file, 'r', encoding='utf-8') as f:
            data = yaml.safe_load(f)
        
        # Settings
        settings = data.get('settings', {})
        thresholds = data.get('thresholds', {})
        
        config = PortfolioConfig(
            # Settings
            risk_free_rate=settings.get('risk_free_rate', 0.35),
            cache_ttl_seconds=settings.get('cache_ttl_seconds', 3600),
            fetch_timeout_seconds=settings.get('fetch_timeout_seconds', 30),
            log_level=settings.get('log_level', 'INFO'),
            
            # Thresholds
            weekly_loss_threshold=thresholds.get('weekly_loss_threshold', -4.0),
            weekly_gain_threshold=thresholds.get('weekly_gain_threshold', 7.0),
            weight_deviation_threshold=thresholds.get('weight_deviation_threshold', 5.0),
            high_volatility_threshold=thresholds.get('high_volatility_threshold', 15.0),
            high_correlation_threshold=thresholds.get('high_correlation_threshold', 0.7),
            
            # Cash reserve codes
            cash_reserve_codes=data.get('cash_reserve_codes', ['DLY', 'DIP', 'USD']),
            
            # Assets
            tefas_funds=data.get('tefas_funds', []),
            us_stocks=data.get('us_stocks', []),
            crypto=data.get('crypto', []),
            cash=data.get('cash', [])
        )
        
        logger.info(f"Config yüklendi: {len(config.tefas_funds)} TEFAS, "
                   f"{len(config.us_stocks)} ABD, {len(config.crypto)} Kripto, "
                   f"{len(config.cash)} Nakit")
        
        return config
        
    except Exception as e:
        logger.error(f"Config yükleme hatası: {e}")
        return PortfolioConfig()


# =============================================================================
# PORTFÖY SINIFI
# =============================================================================

class Portfolio:
    """
    Ana portföy sınıfı.
    
    Tüm varlıkları yönetir, fiyatları çeker ve metrikleri hesaplar.
    """
    
    def __init__(self, config: PortfolioConfig):
        """
        Args:
            config: Portföy konfigürasyonu
        """
        self.config = config
        self.assets: list[Asset] = []
        self.metrics = PortfolioMetrics()
        self.usd_try_rate: float = 35.0
        self.last_update: Optional[datetime] = None
        self.price_data: dict[str, Any] = {}
        
        # Cache TTL'ini ayarla
        set_cache_ttl(config.cache_ttl_seconds)
    
    def refresh_prices(self) -> bool:
        """
        Tüm fiyatları güncelle.
        
        Returns:
            Başarılı mı?
        """
        try:
            logger.info("Fiyatlar güncelleniyor...")
            
            # Varlık kodlarını topla
            tefas_codes = [f['code'] for f in self.config.tefas_funds]
            us_tickers = [s['ticker'] for s in self.config.us_stocks]
            crypto_symbols = [c['symbol'] for c in self.config.crypto]
            
            # Fiyatları çek
            self.price_data = fetch_all_prices(
                tefas_codes=tefas_codes,
                us_tickers=us_tickers,
                crypto_symbols=crypto_symbols,
                timeout=self.config.fetch_timeout_seconds
            )
            
            # USD/TRY kuru
            self.usd_try_rate = self.price_data.get('usd_try', 35.0)
            
            # Asset nesnelerini oluştur
            self._build_assets()
            
            # Metrikleri hesapla
            self._calculate_metrics()
            
            self.last_update = datetime.now()
            logger.info(f"Fiyatlar güncellendi. Toplam: {len(self.assets)} varlık")
            
            return True
            
        except Exception as e:
            logger.error(f"Fiyat güncelleme hatası: {e}")
            return False
    
    def _build_assets(self) -> None:
        """Fiyat verisinden Asset nesnelerini oluştur."""
        self.assets = []
        
        # TEFAS fonları
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
        
        # ABD hisseleri
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
        
        # Kripto
        for crypto in self.config.crypto:
            symbol = crypto['symbol']
            price_info = self.price_data.get('crypto', {}).get(symbol, {})
            
            # Kod olarak sembolün ilk kısmını al (BTC/USDT -> BTC)
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
        
        # USD Nakit
        for cash_item in self.config.cash:
            code = cash_item['code']
            
            # USD için fiyat = 1 USD (TRY'ye çevrilecek)
            asset = Asset(
                code=code,
                name="USD Nakit",
                asset_type="CASH",
                shares=cash_item['amount'],
                current_price=1.0,  # 1 USD = 1 USD
                prev_week_price=1.0,
                currency='USD',
                target_weight=cash_item.get('target_weight', 0),
                is_cash_reserve=True
            )
            self.assets.append(asset)
        
        # Değerleri hesapla
        self._calculate_values()
    
    def _calculate_values(self) -> None:
        """Her varlık için değer ve ağırlık hesapla."""
        # Önce toplam değeri hesapla
        total_try = 0.0
        
        for asset in self.assets:
            if not asset.is_valid:
                continue
            
            # Orijinal değer
            asset.value_original = asset.shares * asset.current_price
            
            # TRY değeri
            if asset.currency in ('USD', 'USDT'):
                asset.value_try = asset.value_original * self.usd_try_rate
            else:
                asset.value_try = asset.value_original
            
            total_try += asset.value_try
        
        # Şimdi ağırlıkları ve diğer metrikleri hesapla
        for asset in self.assets:
            if not asset.is_valid:
                continue
            
            # Ağırlık
            if total_try > 0:
                asset.actual_weight = (asset.value_try / total_try) * 100
            
            # Sapma
            asset.weight_deviation = asset.actual_weight - asset.target_weight
            
            # Haftalık getiri
            if asset.prev_week_price and asset.prev_week_price > 0:
                asset.weekly_return = (
                    (asset.current_price - asset.prev_week_price) / 
                    asset.prev_week_price * 100
                )
    
    def _calculate_metrics(self) -> None:
        """Portföy metriklerini hesapla."""
        valid_assets = [a for a in self.assets if a.is_valid]
        
        if not valid_assets:
            return
        
        # Toplam değer
        self.metrics.total_value_try = sum(a.value_try for a in valid_assets)
        
        # Nakit rezervi
        cash_assets = [a for a in valid_assets if a.is_cash_reserve]
        self.metrics.cash_reserve_try = sum(a.value_try for a in cash_assets)
        
        if self.metrics.total_value_try > 0:
            self.metrics.cash_reserve_pct = (
                self.metrics.cash_reserve_try / self.metrics.total_value_try * 100
            )
        
        # Ağırlıklı haftalık getiri
        weighted_return = 0.0
        for asset in valid_assets:
            weight = asset.value_try / self.metrics.total_value_try if self.metrics.total_value_try > 0 else 0
            weighted_return += asset.weekly_return * weight
        
        self.metrics.weekly_return_pct = weighted_return
        
        # Uyarılar
        self.metrics.warnings = []
        
        if self.metrics.weekly_return_pct < self.config.weekly_loss_threshold:
            self.metrics.warnings.append(
                f"⚠️ Haftalık kayıp yüksek: {self.metrics.weekly_return_pct:.1f}%"
            )
        
        # Risk metrikleri
        self._calculate_risk_metrics()
    
    def _calculate_risk_metrics(self) -> None:
        """Risk metriklerini hesapla."""
        try:
            # Geçmiş verileri topla
            all_returns = []
            
            for asset in self.assets:
                if not asset.is_valid:
                    continue
                
                # Nakit için volatilite hesaplama
                if asset.asset_type == "CASH":
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
                # Portföy volatilitesi
                portfolio_returns = pd.Series(dtype=float)
                
                for item in all_returns:
                    if len(portfolio_returns) == 0:
                        portfolio_returns = item['returns'] * item['weight']
                    else:
                        aligned = portfolio_returns.align(item['returns'] * item['weight'], join='inner')
                        portfolio_returns = aligned[0] + aligned[1]
                
                if len(portfolio_returns) > 5:
                    # Aylık volatilite (annualize)
                    daily_vol = portfolio_returns.std()
                    self.metrics.volatility_monthly = daily_vol * np.sqrt(21) * 100
                    
                    # Sharpe Ratio
                    daily_rf = self.config.risk_free_rate / 252
                    excess_return = portfolio_returns.mean() - daily_rf
                    
                    if daily_vol > 0:
                        self.metrics.sharpe_ratio = (
                            excess_return / daily_vol * np.sqrt(252)
                        )
                
                # Korelasyon kontrolü
                returns_df = pd.DataFrame()
                for item in all_returns:
                    returns_df[item['code']] = item['returns']
                
                corr_matrix = returns_df.corr()
                
                if not corr_matrix.empty:
                    # Yüksek korelasyonları bul
                    high_corrs = []
                    for i in range(len(corr_matrix)):
                        for j in range(i + 1, len(corr_matrix)):
                            corr = corr_matrix.iloc[i, j]
                            if abs(corr) > self.config.high_correlation_threshold:
                                high_corrs.append(
                                    (corr_matrix.columns[i], 
                                     corr_matrix.columns[j], 
                                     corr)
                                )
                    
                    for c1, c2, corr in high_corrs:
                        self.metrics.warnings.append(
                            f"⚠️ Yüksek korelasyon: {c1}-{c2} ({corr:.2f})"
                        )
                    
                    # Çeşitlendirme skoru
                    avg_corr = corr_matrix.values[np.triu_indices_from(
                        corr_matrix.values, k=1
                    )].mean()
                    self.metrics.diversification_score = (1 - avg_corr) * 100
            
        except Exception as e:
            logger.error(f"Risk metrikleri hesaplama hatası: {e}")
    
    def get_summary_dataframe(self) -> pd.DataFrame:
        """
        Portföy özet tablosunu DataFrame olarak döndür.
        
        Returns:
            Tüm varlıkları içeren DataFrame
        """
        data = []
        
        for asset in self.assets:
            data.append({
                'Kod': asset.code,
                'Tür': asset.asset_type,
                'İsim': asset.name[:30] + '...' if len(asset.name) > 30 else asset.name,
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
        """
        Nakit rezervi dağılımını döndür.
        
        Returns:
            Nakit varlıklarını içeren DataFrame
        """
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
        """
        Korelasyon matrisini hesapla ve döndür.
        
        Returns:
            Korelasyon matrisi DataFrame veya None
        """
        all_returns = []
        
        for asset in self.assets:
            if not asset.is_valid:
                continue
            
            # Nakit için korelasyon hesaplama
            if asset.asset_type == "CASH":
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
                        'returns': returns
                    })
            except:
                continue
        
        if len(all_returns) < 2:
            return None
        
        returns_df = pd.DataFrame()
        for item in all_returns:
            returns_df[item['code']] = item['returns']
        
        return returns_df.corr()
    
    def get_history_data(self, asset_code: str, days: int = 30) -> pd.DataFrame:
        """
        Belirli bir varlığın geçmiş verisini döndür.
        
        Args:
            asset_code: Varlık kodu
            days: Gün sayısı
            
        Returns:
            Geçmiş veri DataFrame
        """
        # Varlık tipini bul
        asset = next((a for a in self.assets if a.code == asset_code), None)
        
        if not asset:
            return pd.DataFrame(columns=['Date', 'Close'])
        
        if asset.asset_type == "TEFAS":
            return fetch_tefas_history(asset_code, days)
        elif asset.asset_type == "US_STOCK":
            return fetch_us_stock_history(asset_code, days)
        elif asset.asset_type == "CRYPTO":
            symbol = f"{asset_code}/USDT"
            return fetch_crypto_history(symbol, days)
        elif asset.asset_type == "CASH":
            # Nakit için sabit fiyat döndür
            dates = pd.date_range(end=datetime.now(), periods=days, freq='D')
            return pd.DataFrame({'Date': dates, 'Close': [1.0] * days})
        
        return pd.DataFrame(columns=['Date', 'Close'])


# =============================================================================
# YARDIMCI FONKSİYONLAR
# =============================================================================

def format_currency(value: float, currency: str = "TRY") -> str:
    """Para birimini formatla."""
    if currency == "TRY":
        return f"₺{value:,.2f}"
    elif currency in ("USD", "USDT"):
        return f"${value:,.2f}"
    else:
        return f"{value:,.2f} {currency}"


def format_percentage(value: float, include_sign: bool = True) -> str:
    """Yüzdeyi formatla."""
    if include_sign and value > 0:
        return f"+{value:.2f}%"
    return f"{value:.2f}%"


# =============================================================================
# TEST
# =============================================================================

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    
    print("=" * 60)
    print("PORTFOLIO MODULE TEST")
    print("=" * 60)
    
    # Config yükle
    config = load_config("config.yaml")
    print(f"\nConfig yüklendi:")
    print(f"  - Risk-free rate: {config.risk_free_rate * 100}%")
    print(f"  - TEFAS fonları: {len(config.tefas_funds)}")
    print(f"  - ABD hisseleri: {len(config.us_stocks)}")
    print(f"  - Kripto: {len(config.crypto)}")
    print(f"  - Nakit: {len(config.cash)}")
    
    # Portföy oluştur
    portfolio = Portfolio(config)
    
    # Fiyatları güncelle
    print("\nFiyatlar güncelleniyor...")
    success = portfolio.refresh_prices()
    
    if success:
        print(f"\nUSD/TRY: {portfolio.usd_try_rate:.4f}")
        print(f"Toplam Değer: {format_currency(portfolio.metrics.total_value_try)}")
        print(f"Nakit Rezervi: {format_currency(portfolio.metrics.cash_reserve_try)} ({portfolio.metrics.cash_reserve_pct:.1f}%)")
        print(f"Haftalık Getiri: {format_percentage(portfolio.metrics.weekly_return_pct)}")
        
        print("\n" + "-" * 60)
        print("VARLIK ÖZETİ:")
        print("-" * 60)
        
        df = portfolio.get_summary_dataframe()
        print(df.to_string(index=False))
    
    print("\n" + "=" * 60)
    print("TEST TAMAMLANDI")
    print("=" * 60)
