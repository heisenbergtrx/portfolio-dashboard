"""
portfolio.py - Portföy Hesaplama ve Optimizasyon Modülü
=======================================================

Bu modül portföy analizi için gerekli tüm hesaplamaları yapar:
- Getiri hesaplamaları (günlük, haftalık, aylık)
- Portföy değeri ve ağırlık hesaplamaları
- Risk metrikleri (volatilite, Sharpe Ratio)
- Korelasyon matrisi
- Rebalancing önerileri
- İşlem önerileri

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
    asset_type: str              # "TEFAS", "US_STOCK", "CRYPTO"
    shares: float                # Adet/miktar
    current_price: float         # Güncel fiyat
    prev_week_price: float       # Önceki hafta fiyatı
    currency: str                # Para birimi
    target_weight: float         # Hedef ağırlık (%)
    
    # Hesaplanan alanlar
    value_original: float = 0.0  # Orijinal para birimi cinsinden değer
    value_try: float = 0.0       # TRY cinsinden değer
    actual_weight: float = 0.0   # Gerçek ağırlık (%)
    weekly_return: float = 0.0   # Haftalık getiri (%)
    weight_deviation: float = 0.0  # Hedeften sapma (%)
    recommendation: str = ""     # İşlem önerisi
    
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
    
    # Varlık listeleri
    tefas_funds: list[dict] = field(default_factory=list)
    us_stocks: list[dict] = field(default_factory=list)
    crypto: list[dict] = field(default_factory=list)


@dataclass
class PortfolioMetrics:
    """Portföy metrikleri."""
    total_value_try: float = 0.0
    weekly_return_pct: float = 0.0
    sharpe_ratio: Optional[float] = None
    volatility_monthly: Optional[float] = None
    diversification_score: Optional[float] = None
    
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
            
            # Assets
            tefas_funds=data.get('tefas_funds', []),
            us_stocks=data.get('us_stocks', []),
            crypto=data.get('crypto', [])
        )
        
        logger.info(f"Config yüklendi: {len(config.tefas_funds)} TEFAS, "
                   f"{len(config.us_stocks)} ABD, {len(config.crypto)} Kripto")
        
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
        for fund_config in self.config.tefas_funds:
            code = fund_config['code']
            price_info = self.price_data.get('tefas', {}).get(code, {})
            
            asset = Asset(
                code=code,
                name=price_info.get('name', code),
                asset_type="TEFAS",
                shares=fund_config.get('shares', 0),
                current_price=price_info.get('current_price') or 0,
                prev_week_price=price_info.get('prev_week_price') or 0,
                currency='TRY',
                target_weight=fund_config.get('target_weight', 0)
            )
            self.assets.append(asset)
        
        # ABD hisseleri
        for stock_config in self.config.us_stocks:
            ticker = stock_config['ticker']
            price_info = self.price_data.get('us_stocks', {}).get(ticker, {})
            
            asset = Asset(
                code=ticker,
                name=price_info.get('name', ticker),
                asset_type="US_STOCK",
                shares=stock_config.get('shares', 0),
                current_price=price_info.get('current_price') or 0,
                prev_week_price=price_info.get('prev_week_price') or 0,
                currency='USD',
                target_weight=stock_config.get('target_weight', 0)
            )
            self.assets.append(asset)
        
        # Kripto
        for crypto_config in self.config.crypto:
            symbol = crypto_config['symbol']
            price_info = self.price_data.get('crypto', {}).get(symbol, {})
            
            asset = Asset(
                code=symbol,
                name=price_info.get('name', symbol.split('/')[0]),
                asset_type="CRYPTO",
                shares=crypto_config.get('amount', 0),
                current_price=price_info.get('current_price') or 0,
                prev_week_price=price_info.get('prev_week_price') or 0,
                currency='USDT',
                target_weight=crypto_config.get('target_weight', 0)
            )
            self.assets.append(asset)
    
    def _calculate_metrics(self) -> None:
        """Tüm metrikleri hesapla."""
        # Her varlık için değer ve getiri hesapla
        total_value = 0.0
        prev_total_value = 0.0
        
        for asset in self.assets:
            if not asset.is_valid:
                continue
            
            # Orijinal değer
            asset.value_original = asset.current_price * asset.shares
            
            # TRY değeri
            if asset.currency in ('USD', 'USDT'):
                asset.value_try = asset.value_original * self.usd_try_rate
            else:
                asset.value_try = asset.value_original
            
            total_value += asset.value_try
            
            # Önceki hafta değeri (TRY)
            if asset.prev_week_price and asset.prev_week_price > 0:
                prev_value_orig = asset.prev_week_price * asset.shares
                if asset.currency in ('USD', 'USDT'):
                    prev_value_try = prev_value_orig * self.usd_try_rate
                else:
                    prev_value_try = prev_value_orig
                prev_total_value += prev_value_try
                
                # Haftalık getiri (%)
                asset.weekly_return = (
                    (asset.current_price - asset.prev_week_price) / 
                    asset.prev_week_price * 100
                )
        
        # Portföy toplam değeri
        self.metrics.total_value_try = total_value
        
        # Ağırlıklar
        for asset in self.assets:
            if total_value > 0 and asset.is_valid:
                asset.actual_weight = (asset.value_try / total_value) * 100
                asset.weight_deviation = asset.actual_weight - asset.target_weight
        
        # Portföy haftalık getirisi
        if prev_total_value > 0:
            self.metrics.weekly_return_pct = (
                (total_value - prev_total_value) / prev_total_value * 100
            )
        
        # İşlem önerilerini hesapla
        self._calculate_recommendations()
        
        # Risk metriklerini hesapla
        self._calculate_risk_metrics()
    
    def _calculate_recommendations(self) -> None:
        """Her varlık için işlem önerisi hesapla."""
        for asset in self.assets:
            if not asset.is_valid:
                asset.recommendation = "⚠️ Veri yok"
                continue
            
            recommendations = []
            
            # Haftalık getiri bazlı öneri
            if asset.weekly_return <= self.config.weekly_loss_threshold:
                recommendations.append(f"📉 Satış düşün (-%{abs(asset.weekly_return):.1f})")
            elif asset.weekly_return >= self.config.weekly_gain_threshold:
                recommendations.append(f"💰 Kar al (+%{asset.weekly_return:.1f})")
            
            # Ağırlık sapması bazlı öneri
            if abs(asset.weight_deviation) >= self.config.weight_deviation_threshold:
                if asset.weight_deviation > 0:
                    recommendations.append(f"⚖️ Azalt (hedef: %{asset.target_weight:.0f})")
                else:
                    recommendations.append(f"⚖️ Artır (hedef: %{asset.target_weight:.0f})")
            
            asset.recommendation = " | ".join(recommendations) if recommendations else "✓ Tut"
    
    def _calculate_risk_metrics(self) -> None:
        """Risk metriklerini hesapla (Sharpe, volatilite, vb.)."""
        self.metrics.warnings = []
        
        # Geçmiş verileri topla
        all_returns = []
        
        for asset in self.assets:
            if not asset.is_valid:
                continue
            
            # 30 günlük geçmiş veri
            try:
                if asset.asset_type == "TEFAS":
                    hist = fetch_tefas_history(asset.code, days=30)
                elif asset.asset_type == "US_STOCK":
                    hist = fetch_us_stock_history(asset.code, days=30)
                elif asset.asset_type == "CRYPTO":
                    hist = fetch_crypto_history(asset.code, days=30)
                else:
                    continue
                
                if hist is not None and len(hist) > 5:
                    # Günlük getirileri hesapla
                    returns = hist['Close'].pct_change().dropna()
                    all_returns.append({
                        'code': asset.code,
                        'returns': returns,
                        'weight': asset.actual_weight / 100
                    })
            except Exception as e:
                logger.warning(f"Geçmiş veri alınamadı ({asset.code}): {e}")
        
        if not all_returns:
            logger.warning("Risk metrikleri hesaplanamadı: yetersiz veri")
            return
        
        # Portföy getirilerini ağırlıklı hesapla
        try:
            # DataFrame oluştur
            returns_df = pd.DataFrame()
            for item in all_returns:
                returns_df[item['code']] = item['returns']
            
            returns_df = returns_df.dropna()
            
            if len(returns_df) < 5:
                logger.warning("Yetersiz veri noktası")
                return
            
            # Ağırlıklar
            weights = np.array([item['weight'] for item in all_returns])
            weights = weights / weights.sum()  # Normalize
            
            # Portföy günlük getirisi
            portfolio_returns = (returns_df * weights).sum(axis=1)
            
            # Aylık volatilite (günlük std * sqrt(21))
            daily_vol = portfolio_returns.std()
            monthly_vol = daily_vol * np.sqrt(21) * 100  # %
            self.metrics.volatility_monthly = monthly_vol
            
            if monthly_vol > self.config.high_volatility_threshold:
                self.metrics.warnings.append(
                    f"⚠️ Yüksek volatilite: %{monthly_vol:.1f}"
                )
            
            # Sharpe Ratio (yıllık)
            # Günlük risk-free rate
            daily_rf = self.config.risk_free_rate / 252
            excess_return = portfolio_returns.mean() - daily_rf
            
            if daily_vol > 0:
                sharpe_daily = excess_return / daily_vol
                sharpe_annual = sharpe_daily * np.sqrt(252)
                self.metrics.sharpe_ratio = sharpe_annual
            
            # Korelasyon matrisi analizi
            if len(returns_df.columns) > 1:
                corr_matrix = returns_df.corr()
                
                # Yüksek korelasyonları bul
                high_corrs = []
                for i in range(len(corr_matrix.columns)):
                    for j in range(i + 1, len(corr_matrix.columns)):
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
                
                # Çeşitlendirme skoru (ortalama korelasyonun tersi)
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
                'Öneri': asset.recommendation
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
            
            try:
                if asset.asset_type == "TEFAS":
                    hist = fetch_tefas_history(asset.code, days=30)
                elif asset.asset_type == "US_STOCK":
                    hist = fetch_us_stock_history(asset.code, days=30)
                elif asset.asset_type == "CRYPTO":
                    hist = fetch_crypto_history(asset.code, days=30)
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
    
    def get_rebalancing_suggestions(self) -> list[dict]:
        """
        Rebalancing önerilerini hesapla.
        
        Returns:
            Önerileri içeren liste
        """
        suggestions = []
        
        for asset in self.assets:
            if not asset.is_valid:
                continue
            
            if abs(asset.weight_deviation) >= self.config.weight_deviation_threshold:
                # Hedef değere ulaşmak için gerekli işlem
                target_value = (
                    self.metrics.total_value_try * 
                    asset.target_weight / 100
                )
                current_value = asset.value_try
                diff_value = target_value - current_value
                
                # Birim fiyat (TRY)
                if asset.currency in ('USD', 'USDT'):
                    unit_price_try = asset.current_price * self.usd_try_rate
                else:
                    unit_price_try = asset.current_price
                
                diff_shares = diff_value / unit_price_try if unit_price_try > 0 else 0
                
                suggestions.append({
                    'code': asset.code,
                    'name': asset.name,
                    'current_weight': asset.actual_weight,
                    'target_weight': asset.target_weight,
                    'deviation': asset.weight_deviation,
                    'action': 'AL' if diff_shares > 0 else 'SAT',
                    'shares': abs(diff_shares),
                    'value_try': abs(diff_value)
                })
        
        return sorted(suggestions, key=lambda x: abs(x['deviation']), reverse=True)
    
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
            return fetch_crypto_history(asset_code, days)
        
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
    
    # Portföy oluştur
    portfolio = Portfolio(config)
    
    # Fiyatları güncelle
    print("\nFiyatlar güncelleniyor...")
    success = portfolio.refresh_prices()
    
    if success:
        print(f"\nUSD/TRY: {portfolio.usd_try_rate:.4f}")
        print(f"Toplam Değer: {format_currency(portfolio.metrics.total_value_try)}")
        print(f"Haftalık Getiri: {format_percentage(portfolio.metrics.weekly_return_pct)}")
        
        if portfolio.metrics.sharpe_ratio:
            print(f"Sharpe Ratio: {portfolio.metrics.sharpe_ratio:.2f}")
        
        if portfolio.metrics.volatility_monthly:
            print(f"Aylık Volatilite: {portfolio.metrics.volatility_monthly:.2f}%")
        
        print("\n" + "-" * 60)
        print("VARLIK ÖZETİ:")
        print("-" * 60)
        
        df = portfolio.get_summary_dataframe()
        print(df.to_string(index=False))
        
        print("\n" + "-" * 60)
        print("REBALANCING ÖNERİLERİ:")
        print("-" * 60)
        
        suggestions = portfolio.get_rebalancing_suggestions()
        for s in suggestions:
            print(f"  {s['code']}: {s['action']} {s['shares']:.4f} adet "
                  f"({format_currency(s['value_try'])})")
    
    print("\n" + "=" * 60)
    print("TEST TAMAMLANDI")
    print("=" * 60)
