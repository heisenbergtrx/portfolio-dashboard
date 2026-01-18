# 📊 Portföy Dashboard

Türkiye finans piyasası için kişisel portföy optimizasyonu ve takip aracı.

**Desteklenen varlık türleri:**
- 🇹🇷 TEFAS yatırım fonları
- 🇺🇸 ABD hisse senetleri
- ₿ Kripto paralar

## 🚀 Özellikler

### Veri Çekme
- **TEFAS:** `tefas-crawler` kütüphanesi + API fallback + Selenium scraping
- **ABD Hisse:** `yfinance` (Yahoo Finance)
- **Kripto:** `ccxt` (Binance varsayılan)
- **Döviz:** USD/TRY kuru otomatik çekilir

### Analiz & Metrikler
- Güncel fiyatlar ve haftalık getiriler
- Portföy toplam değeri (TRY cinsinden)
- Sharpe Ratio (Türkiye risk-free rate ile)
- Aylık volatilite
- Korelasyon matrisi
- Varlık ağırlıkları ve hedeften sapma

### İşlem Önerileri
- Haftalık getiri bazlı alım/satım önerileri
- Rebalancing önerileri (hedef ağırlıklardan sapma)
- Yüksek korelasyon uyarıları

### Görselleştirme (Plotly)
- Portföy dağılımı (pie chart)
- Haftalık getiri karşılaştırması (bar chart)
- Fiyat trendi (line chart, 30 gün)
- Korelasyon matrisi (heatmap)

### Teknik
- JSON tabanlı cache sistemi
- Robust hata yönetimi
- Rate limiting koruması
- Detaylı loglama

## 📁 Dosya Yapısı

```
portfolio-dashboard/
├── requirements.txt      # Python bağımlılıkları
├── config.yaml          # Portföy konfigürasyonu
├── data_fetcher.py      # Veri çekme modülü
├── portfolio.py         # Hesaplama ve analiz modülü
├── dashboard.py         # Streamlit ana uygulaması
├── README.md            # Bu dosya
└── .cache/              # Cache dosyaları (otomatik oluşur)
```

## 🛠️ Kurulum

### 1. Python ortamı oluşturun (önerilen: Python 3.11+)

```bash
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
```

### 2. Bağımlılıkları yükleyin

```bash
pip install -r requirements.txt
```

### 3. Config dosyasını düzenleyin

`config.yaml` dosyasını kendi portföyünüze göre güncelleyin:

```yaml
tefas_funds:
  - code: "MET"           # TEFAS fon kodu
    shares: 1500.0        # Pay sayısı
    target_weight: 15.0   # Hedef ağırlık (%)

us_stocks:
  - ticker: "AAPL"        # Yahoo Finance ticker
    shares: 25.0          # Adet
    target_weight: 15.0

crypto:
  - symbol: "BTC/USDT"    # Binance sembolü
    amount: 0.15          # Miktar
    target_weight: 15.0
```

### 4. Uygulamayı başlatın

```bash
streamlit run dashboard.py
```

Tarayıcınızda `http://localhost:8501` adresini açın.

## 📖 Kullanım

1. **Config Yükle:** Sol menüden config dosyasını yükleyin
2. **Fiyatları Güncelle:** Güncel verileri çekmek için butona basın
3. **Analiz Edin:** Tablolar ve grafiklerden portföyünüzü inceleyin
4. **Rebalancing:** Önerileri takip edin

## ⚙️ Konfigürasyon Detayları

### Genel Ayarlar

| Parametre | Açıklama | Varsayılan |
|-----------|----------|------------|
| `risk_free_rate` | Risksiz getiri oranı (TCMB faizi) | 0.35 (%35) |
| `cache_ttl_seconds` | Cache geçerlilik süresi | 3600 (1 saat) |
| `fetch_timeout_seconds` | API timeout | 30 saniye |

### Eşikler

| Parametre | Açıklama | Varsayılan |
|-----------|----------|------------|
| `weekly_loss_threshold` | Satış uyarısı eşiği | -4.0% |
| `weekly_gain_threshold` | Kar al uyarısı eşiği | 7.0% |
| `weight_deviation_threshold` | Rebalancing eşiği | 5.0% |
| `high_volatility_threshold` | Yüksek volatilite uyarısı | 15.0% |
| `high_correlation_threshold` | Korelasyon uyarısı | 0.7 |

## 🔧 Sorun Giderme

### TEFAS verisi çekilemiyor

1. `tefas-crawler` güncel mi kontrol edin: `pip install --upgrade tefas-crawler`
2. TEFAS sitesi değişmiş olabilir - `data_fetcher.py`'deki selector'ları güncelleyin
3. Selenium fallback'i aktif edin (Chrome gerekli)

### Rate limiting hatası

- Cache TTL'ini artırın (`cache_ttl_seconds`)
- API çağrıları arasında bekleme süresini artırın

### Korelasyon matrisi hesaplanamıyor

- En az 5 günlük geçmiş veri gerekli
- Varlık sayısı 2'den az olamaz

## 📚 Teknik Notlar

### TEFAS Veri Çekme Stratejisi

```
1. tefas-crawler (pip install tefas-crawler)
   ↓ başarısız ise
2. TEFAS API endpoint (requests)
   ↓ başarısız ise  
3. Selenium scraping (headless Chrome)
   ↓ başarısız ise
4. Cache'den son geçerli veri
```

### Sharpe Ratio Hesaplama

```python
# Günlük getiriler
daily_returns = prices.pct_change()

# Günlük risksiz getiri
daily_rf = annual_rf / 252

# Sharpe Ratio (yıllık)
excess_return = daily_returns.mean() - daily_rf
sharpe = (excess_return / daily_returns.std()) * sqrt(252)
```

## 🤝 Katkıda Bulunma

Pull request'ler memnuniyetle kabul edilir. Büyük değişiklikler için önce bir issue açın.

## 📄 Lisans

MIT License

## ⚠️ Sorumluluk Reddi

Bu araç yalnızca eğitim ve kişisel kullanım amaçlıdır. Yatırım tavsiyesi değildir. Yatırım kararlarınızı almadan önce profesyonel danışmanlık alın.

---

**Geliştirici:** Portfolio Dashboard Team  
**Versiyon:** 1.0.0  
**Tarih:** Ocak 2026
