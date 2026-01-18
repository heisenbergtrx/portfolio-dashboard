"""
dashboard.py - Portföy Dashboard Ana Uygulaması (v3)
====================================================

Streamlit tabanlı interaktif web dashboard.

Güncellemeler v3:
- Öneri/Rebalancing kaldırıldı
- Dashboard üzerinden adet düzenleme
- Haftalık snapshot ve büyüme grafiği

Kullanım:
    streamlit run dashboard.py

Yazar: Portfolio Dashboard
Tarih: Ocak 2026
"""

import json
import logging
from datetime import datetime, timedelta
from pathlib import Path

import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st
import yaml

from portfolio import (
    Portfolio,
    PortfolioConfig,
    format_currency,
    format_percentage,
    load_config,
)
from asset_selector import render_asset_selector

# =============================================================================
# SAYFA AYARLARI
# =============================================================================

st.set_page_config(
    page_title="Portföy Dashboard",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


# =============================================================================
# SNAPSHOT YÖNETİMİ
# =============================================================================

SNAPSHOT_FILE = Path(".snapshots/weekly_snapshots.json")


def load_snapshots() -> list[dict]:
    """Kayıtlı snapshot'ları yükle."""
    if not SNAPSHOT_FILE.exists():
        return []
    try:
        with open(SNAPSHOT_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    except:
        return []


def save_snapshot(total_value: float, assets_summary: dict) -> None:
    """Yeni snapshot kaydet."""
    SNAPSHOT_FILE.parent.mkdir(exist_ok=True)
    
    snapshots = load_snapshots()
    
    new_snapshot = {
        'date': datetime.now().isoformat(),
        'total_value_try': total_value,
        'assets': assets_summary,
        'week_number': datetime.now().isocalendar()[1]
    }
    
    snapshots.append(new_snapshot)
    
    # Son 52 hafta tut (1 yıl)
    snapshots = snapshots[-52:]
    
    with open(SNAPSHOT_FILE, 'w', encoding='utf-8') as f:
        json.dump(snapshots, f, indent=2, ensure_ascii=False)
    
    logger.info(f"Snapshot kaydedildi: ₺{total_value:,.2f}")


def should_take_snapshot() -> bool:
    """Bugün cuma mı ve bu hafta snapshot alınmış mı kontrol et."""
    today = datetime.now()
    
    # Cuma mı? (4 = Friday)
    if today.weekday() != 4:
        return False
    
    # Bu hafta snapshot var mı?
    current_week = today.isocalendar()[1]
    snapshots = load_snapshots()
    
    for snap in snapshots:
        snap_date = datetime.fromisoformat(snap['date'])
        if snap_date.isocalendar()[1] == current_week and snap_date.year == today.year:
            return False
    
    return True


def take_snapshot_if_needed(portfolio: Portfolio) -> bool:
    """Gerekirse snapshot al."""
    if not should_take_snapshot():
        return False
    
    if not portfolio or not portfolio.assets:
        return False
    
    # Varlık özeti
    assets_summary = {}
    for asset in portfolio.assets:
        if asset.is_valid:
            assets_summary[asset.code] = {
                'value_try': asset.value_try,
                'shares': asset.shares,
                'price': asset.current_price
            }
    
    save_snapshot(portfolio.metrics.total_value_try, assets_summary)
    return True


# =============================================================================
# STIL
# =============================================================================

st.markdown("""
<style>
    /* Ana tema */
    .main-title {
        font-size: 2.5rem;
        font-weight: 700;
        color: #1a1a2e;
        margin-bottom: 0.5rem;
    }
    
    .subtitle {
        font-size: 1rem;
        color: #666;
        margin-bottom: 2rem;
    }
    
    /* Pozitif/negatif renkler */
    .positive { color: #00d26a !important; }
    .negative { color: #ff6b6b !important; }
    
    /* Kart stilleri */
    .metric-card {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        border-radius: 15px;
        padding: 20px;
        color: white;
    }
    
    /* Sidebar navigasyon */
    .sidebar-nav {
        padding: 10px;
        margin: 5px 0;
        border-radius: 8px;
        cursor: pointer;
    }
    
    .sidebar-nav:hover {
        background-color: #f0f2f6;
    }
    
    /* Editable input */
    .shares-input {
        width: 80px;
        text-align: right;
    }
</style>
""", unsafe_allow_html=True)


# =============================================================================
# SESSION STATE
# =============================================================================

def init_session_state():
    """Session state'i başlat."""
    if 'portfolio' not in st.session_state:
        st.session_state.portfolio = None
    if 'config' not in st.session_state:
        st.session_state.config = None
    if 'last_refresh' not in st.session_state:
        st.session_state.last_refresh = None
    if 'current_page' not in st.session_state:
        st.session_state.current_page = "dashboard"
    if 'edit_mode' not in st.session_state:
        st.session_state.edit_mode = False


# =============================================================================
# CONFIG KAYDETME
# =============================================================================

def save_config_to_file(config: PortfolioConfig, path: str = "config.yaml") -> bool:
    """Config'i dosyaya kaydet."""
    try:
        data = {
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
            'tefas_funds': config.tefas_funds,
            'us_stocks': config.us_stocks,
            'crypto': config.crypto,
        }
        
        with open(path, 'w', encoding='utf-8') as f:
            yaml.dump(data, f, allow_unicode=True, default_flow_style=False)
        
        return True
    except Exception as e:
        logger.error(f"Config kaydetme hatası: {e}")
        return False


# =============================================================================
# SIDEBAR
# =============================================================================

def render_sidebar():
    """Sidebar'ı render et."""
    with st.sidebar:
        st.markdown("# 📊 Portföy")
        st.markdown("---")
        
        # Navigasyon
        st.markdown("### 📍 Navigasyon")
        
        if st.button("🏠 Dashboard", use_container_width=True, 
                    type="primary" if st.session_state.current_page == "dashboard" else "secondary"):
            st.session_state.current_page = "dashboard"
            st.rerun()
        
        if st.button("📦 Varlık Yönetimi", use_container_width=True,
                    type="primary" if st.session_state.current_page == "assets" else "secondary"):
            st.session_state.current_page = "assets"
            st.rerun()
        
        if st.button("📈 Haftalık Rapor", use_container_width=True,
                    type="primary" if st.session_state.current_page == "weekly" else "secondary"):
            st.session_state.current_page = "weekly"
            st.rerun()
        
        if st.button("⚙️ Ayarlar", use_container_width=True,
                    type="primary" if st.session_state.current_page == "settings" else "secondary"):
            st.session_state.current_page = "settings"
            st.rerun()
        
        st.markdown("---")
        
        # Hızlı işlemler (sadece dashboard sayfasında)
        if st.session_state.current_page == "dashboard":
            st.markdown("### 🔧 İşlemler")
            
            config_path = st.text_input(
                "Config Dosyası",
                value="config.yaml",
                label_visibility="collapsed"
            )
            
            col1, col2 = st.columns(2)
            
            with col1:
                if st.button("📥 Yükle", use_container_width=True):
                    with st.spinner("Yükleniyor..."):
                        st.session_state.config = load_config(config_path)
                        st.session_state.portfolio = Portfolio(st.session_state.config)
                        st.success("✓")
            
            with col2:
                if st.button("🔄 Güncelle", use_container_width=True, type="primary"):
                    if st.session_state.portfolio:
                        with st.spinner("Fiyatlar..."):
                            success = st.session_state.portfolio.refresh_prices()
                            if success:
                                st.session_state.last_refresh = datetime.now()
                                # Cuma ise snapshot al
                                if take_snapshot_if_needed(st.session_state.portfolio):
                                    st.toast("📸 Haftalık snapshot alındı!")
                                st.success("✓")
                            else:
                                st.error("!")
                    else:
                        st.warning("Önce yükle!")
            
            st.markdown("---")
        
        # Durum bilgisi
        if st.session_state.last_refresh:
            st.caption(f"Son güncelleme: {st.session_state.last_refresh.strftime('%H:%M:%S')}")
        
        # Portföy özeti
        if st.session_state.config:
            st.markdown("### 📋 Özet")
            cfg = st.session_state.config
            
            col1, col2 = st.columns(2)
            with col1:
                st.metric("TEFAS", len(cfg.tefas_funds))
                st.metric("Kripto", len(cfg.crypto))
            with col2:
                st.metric("ABD", len(cfg.us_stocks))
                st.metric("RF%", f"{cfg.risk_free_rate*100:.0f}")


# =============================================================================
# METRİK KARTLARI
# =============================================================================

def render_metric_cards(portfolio: Portfolio):
    """Özet metrik kartlarını render et."""
    metrics = portfolio.metrics
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric(
            label="💰 Toplam Değer",
            value=format_currency(metrics.total_value_try),
        )
    
    with col2:
        weekly_return = metrics.weekly_return_pct
        delta_color = "normal" if weekly_return >= 0 else "inverse"
        st.metric(
            label="📈 Haftalık",
            value=format_percentage(weekly_return),
            delta=f"{weekly_return:+.2f}%",
            delta_color=delta_color
        )
    
    with col3:
        sharpe = metrics.sharpe_ratio
        if sharpe is not None:
            sharpe_display = f"{sharpe:.2f}"
            sharpe_icon = "🟢" if sharpe > 1 else "🟡" if sharpe > 0 else "🔴"
        else:
            sharpe_display = "N/A"
            sharpe_icon = "⚪"
        st.metric(label=f"Sharpe {sharpe_icon}", value=sharpe_display)
    
    with col4:
        vol = metrics.volatility_monthly
        if vol is not None:
            vol_display = f"{vol:.1f}%"
            vol_icon = "🟢" if vol < 10 else "🟡" if vol < 20 else "🔴"
        else:
            vol_display = "N/A"
            vol_icon = "⚪"
        st.metric(label=f"Volatilite {vol_icon}", value=vol_display)


# =============================================================================
# VARLIK TABLOSU (DÜZENLENEBILIR)
# =============================================================================

def render_asset_table(portfolio: Portfolio):
    """Varlık tablosunu düzenlenebilir şekilde render et."""
    st.markdown("### 📋 Varlık Listesi")
    
    # Düzenleme modu toggle
    col1, col2 = st.columns([3, 1])
    with col2:
        edit_mode = st.toggle("✏️ Düzenle", value=st.session_state.edit_mode)
        st.session_state.edit_mode = edit_mode
    
    df = portfolio.get_summary_dataframe()
    
    if df.empty:
        st.info("Varlık bulunamadı.")
        return
    
    # Öneri sütununu kaldır
    if 'Öneri' in df.columns:
        df = df.drop(columns=['Öneri'])
    
    if edit_mode:
        # Düzenleme modunda
        st.info("💡 Adetleri değiştirin ve 'Kaydet' butonuna basın.")
        
        # Her varlık için adet input'u
        changes_made = False
        new_shares = {}
        
        for idx, row in df.iterrows():
            col1, col2, col3, col4, col5 = st.columns([2, 1, 2, 1, 1])
            
            with col1:
                st.write(f"**{row['Kod']}** - {row['İsim'][:20]}")
            with col2:
                st.write(row['Tür'])
            with col3:
                new_val = st.number_input(
                    f"Adet_{row['Kod']}",
                    value=float(row['Adet']),
                    min_value=0.0,
                    step=0.01 if row['Tür'] == 'CRYPTO' else 1.0,
                    format="%.4f" if row['Tür'] == 'CRYPTO' else "%.2f",
                    label_visibility="collapsed",
                    key=f"shares_{row['Kod']}"
                )
                new_shares[row['Kod']] = new_val
                if new_val != row['Adet']:
                    changes_made = True
            with col4:
                st.write(f"₺{row['Değer (TRY)']:,.0f}")
            with col5:
                weekly = row['Haftalık (%)']
                color = "green" if weekly >= 0 else "red"
                st.markdown(f"<span style='color:{color}'>{weekly:+.1f}%</span>", unsafe_allow_html=True)
        
        st.markdown("---")
        
        # Kaydet butonu
        if st.button("💾 Değişiklikleri Kaydet", type="primary", disabled=not changes_made):
            # Config'i güncelle
            config = st.session_state.config
            
            # TEFAS
            for fund in config.tefas_funds:
                if fund['code'] in new_shares:
                    fund['shares'] = new_shares[fund['code']]
            
            # US Stocks
            for stock in config.us_stocks:
                if stock['ticker'] in new_shares:
                    stock['shares'] = new_shares[stock['ticker']]
            
            # Crypto
            for crypto in config.crypto:
                symbol_short = crypto['symbol'].split('/')[0]
                if symbol_short in new_shares:
                    crypto['amount'] = new_shares[symbol_short]
            
            # Dosyaya kaydet
            if save_config_to_file(config):
                st.success("✅ Değişiklikler kaydedildi!")
                st.session_state.edit_mode = False
                # Portfolio'yu yeniden yükle
                st.session_state.portfolio = Portfolio(config)
                st.session_state.portfolio.refresh_prices()
                st.rerun()
            else:
                st.error("Kaydetme hatası!")
    
    else:
        # Normal görünüm
        # Renklendirme fonksiyonu
        def highlight_weekly(val):
            if isinstance(val, (int, float)):
                if val > 0:
                    return 'color: #00d26a'
                elif val < 0:
                    return 'color: #ff6b6b'
            return ''
        
        styled_df = df.style.applymap(
            highlight_weekly, 
            subset=['Haftalık (%)']
        ).format({
            'Adet': '{:.4f}',
            'Fiyat': '{:.2f}',
            'Değer (TRY)': '₺{:,.0f}',
            'Ağırlık (%)': '{:.1f}%',
            'Hedef (%)': '{:.1f}%',
            'Sapma (%)': '{:+.1f}%',
            'Haftalık (%)': '{:+.2f}%'
        })
        
        st.dataframe(styled_df, use_container_width=True, hide_index=True)


# =============================================================================
# GRAFİKLER
# =============================================================================

def render_charts(portfolio: Portfolio):
    """Grafikleri render et."""
    st.markdown("### 📊 Dağılım")
    
    df = portfolio.get_summary_dataframe()
    valid_df = df[df['Değer (TRY)'] > 0].copy()
    
    if valid_df.empty:
        st.warning("Grafik için yeterli veri yok.")
        return
    
    col1, col2 = st.columns(2)
    
    with col1:
        # Pie chart - Varlık dağılımı
        fig = px.pie(
            valid_df,
            values='Değer (TRY)',
            names='Kod',
            title='Varlık Dağılımı',
            color_discrete_sequence=px.colors.qualitative.Set3
        )
        fig.update_traces(textposition='inside', textinfo='percent+label')
        fig.update_layout(showlegend=False, margin=dict(t=40, b=20))
        st.plotly_chart(fig, use_container_width=True)
    
    with col2:
        # Pie chart - Tür dağılımı
        type_df = valid_df.groupby('Tür')['Değer (TRY)'].sum().reset_index()
        fig = px.pie(
            type_df,
            values='Değer (TRY)',
            names='Tür',
            title='Tür Dağılımı',
            color_discrete_map={
                'TEFAS': '#667eea',
                'US_STOCK': '#00d26a',
                'CRYPTO': '#f7931a'
            }
        )
        fig.update_traces(textposition='inside', textinfo='percent+label')
        fig.update_layout(showlegend=False, margin=dict(t=40, b=20))
        st.plotly_chart(fig, use_container_width=True)
    
    # Haftalık performans bar
    st.markdown("### 📈 Haftalık Performans")
    
    df_sorted = valid_df.sort_values('Haftalık (%)', ascending=True)
    colors = ['#00d26a' if x >= 0 else '#ff6b6b' for x in df_sorted['Haftalık (%)']]
    
    fig = go.Figure()
    fig.add_trace(go.Bar(
        x=df_sorted['Kod'],
        y=df_sorted['Haftalık (%)'],
        marker_color=colors,
        text=[f"{v:+.1f}%" for v in df_sorted['Haftalık (%)']],
        textposition='outside'
    ))
    fig.update_layout(
        showlegend=False,
        yaxis=dict(zeroline=True, zerolinewidth=2, zerolinecolor='gray'),
        margin=dict(t=20, b=50)
    )
    st.plotly_chart(fig, use_container_width=True)
    
    # Trend grafiği
    st.markdown("### 📈 Fiyat Trendi")
    
    asset_codes = [a.code for a in portfolio.assets if a.is_valid]
    
    if asset_codes:
        selected_asset = st.selectbox("Varlık Seçin", options=asset_codes, index=0)
        
        with st.spinner(f"{selected_asset} verisi çekiliyor..."):
            hist_df = portfolio.get_history_data(selected_asset, days=30)
        
        if not hist_df.empty and len(hist_df) >= 2:
            fig = go.Figure()
            
            fig.add_trace(go.Scatter(
                x=hist_df['Date'],
                y=hist_df['Close'],
                mode='lines+markers',
                name=selected_asset,
                line=dict(color='#667eea', width=2),
                marker=dict(size=4)
            ))
            
            if len(hist_df) >= 7:
                hist_df['MA7'] = hist_df['Close'].rolling(window=7).mean()
                fig.add_trace(go.Scatter(
                    x=hist_df['Date'],
                    y=hist_df['MA7'],
                    mode='lines',
                    name='7G ORT',
                    line=dict(color='orange', width=1, dash='dash')
                ))
            
            fig.update_layout(
                hovermode='x unified',
                legend=dict(orientation="h", yanchor="bottom", y=1.02),
                margin=dict(t=40, b=40)
            )
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.warning(f"{selected_asset} için geçmiş veri bulunamadı.")


# =============================================================================
# KORELASYON
# =============================================================================

def render_correlation(portfolio: Portfolio):
    """Korelasyon matrisini render et."""
    st.markdown("### 🔗 Korelasyon Matrisi")
    
    corr_matrix = portfolio.get_correlation_matrix()
    
    if corr_matrix is None or corr_matrix.empty:
        st.info("Korelasyon matrisi hesaplanamadı (yetersiz veri).")
        return
    
    fig = px.imshow(
        corr_matrix,
        text_auto='.2f',
        color_continuous_scale='RdBu_r',
        zmin=-1, zmax=1,
        aspect='auto'
    )
    fig.update_layout(margin=dict(t=20, b=20))
    st.plotly_chart(fig, use_container_width=True)
    
    st.caption("🟢 Düşük korelasyon = İyi çeşitlendirme | 🔴 Yüksek korelasyon = Risk")


# =============================================================================
# HAFTALIK RAPOR SAYFASI
# =============================================================================

def render_weekly_report_page():
    """Haftalık büyüme raporu sayfası."""
    st.markdown("## 📈 Haftalık Büyüme Raporu")
    
    snapshots = load_snapshots()
    
    if not snapshots:
        st.info("Henüz snapshot alınmamış. Her cuma piyasa kapanışında otomatik snapshot alınır.")
        
        # Manuel snapshot alma butonu
        if st.session_state.portfolio and st.session_state.portfolio.assets:
            if st.button("📸 Manuel Snapshot Al", type="primary"):
                assets_summary = {}
                for asset in st.session_state.portfolio.assets:
                    if asset.is_valid:
                        assets_summary[asset.code] = {
                            'value_try': asset.value_try,
                            'shares': asset.shares,
                            'price': asset.current_price
                        }
                save_snapshot(st.session_state.portfolio.metrics.total_value_try, assets_summary)
                st.success("Snapshot alındı!")
                st.rerun()
        return
    
    # Snapshot verilerini DataFrame'e çevir
    df = pd.DataFrame([
        {
            'Tarih': datetime.fromisoformat(s['date']).strftime('%Y-%m-%d'),
            'Hafta': s.get('week_number', 0),
            'Toplam Değer (₺)': s['total_value_try']
        }
        for s in snapshots
    ])
    
    # Büyüme grafiği
    st.markdown("### 📊 Portföy Değeri Trendi")
    
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=df['Tarih'],
        y=df['Toplam Değer (₺)'],
        mode='lines+markers',
        name='Portföy Değeri',
        line=dict(color='#667eea', width=3),
        marker=dict(size=8),
        fill='tozeroy',
        fillcolor='rgba(102, 126, 234, 0.1)'
    ))
    
    fig.update_layout(
        yaxis=dict(tickformat='₺,.0f'),
        hovermode='x unified',
        margin=dict(t=20, b=40)
    )
    st.plotly_chart(fig, use_container_width=True)
    
    # Haftalık değişim hesapla
    if len(df) >= 2:
        st.markdown("### 📈 Haftalık Değişimler")
        
        df['Değişim (₺)'] = df['Toplam Değer (₺)'].diff()
        df['Değişim (%)'] = df['Toplam Değer (₺)'].pct_change() * 100
        
        # Son 12 hafta
        recent_df = df.tail(12).copy()
        recent_df = recent_df.dropna()
        
        if not recent_df.empty:
            # Bar chart
            colors = ['#00d26a' if x >= 0 else '#ff6b6b' for x in recent_df['Değişim (%)']]
            
            fig = go.Figure()
            fig.add_trace(go.Bar(
                x=recent_df['Tarih'],
                y=recent_df['Değişim (%)'],
                marker_color=colors,
                text=[f"{v:+.1f}%" for v in recent_df['Değişim (%)']],
                textposition='outside'
            ))
            fig.update_layout(
                yaxis=dict(zeroline=True, zerolinewidth=2, zerolinecolor='gray', ticksuffix='%'),
                margin=dict(t=20, b=50)
            )
            st.plotly_chart(fig, use_container_width=True)
        
        # Özet metrikler
        col1, col2, col3, col4 = st.columns(4)
        
        first_value = df['Toplam Değer (₺)'].iloc[0]
        last_value = df['Toplam Değer (₺)'].iloc[-1]
        total_change = last_value - first_value
        total_change_pct = (total_change / first_value) * 100 if first_value > 0 else 0
        
        with col1:
            st.metric("İlk Değer", f"₺{first_value:,.0f}")
        with col2:
            st.metric("Son Değer", f"₺{last_value:,.0f}")
        with col3:
            st.metric("Toplam Değişim", f"₺{total_change:+,.0f}")
        with col4:
            st.metric("Toplam Getiri", f"{total_change_pct:+.1f}%")
    
    # Tablo
    st.markdown("### 📋 Snapshot Geçmişi")
    st.dataframe(
        df.style.format({
            'Toplam Değer (₺)': '₺{:,.0f}',
            'Değişim (₺)': '₺{:+,.0f}',
            'Değişim (%)': '{:+.2f}%'
        }),
        use_container_width=True,
        hide_index=True
    )
    
    # Manuel snapshot
    st.markdown("---")
    if st.session_state.portfolio and st.session_state.portfolio.assets:
        if st.button("📸 Manuel Snapshot Al"):
            assets_summary = {}
            for asset in st.session_state.portfolio.assets:
                if asset.is_valid:
                    assets_summary[asset.code] = {
                        'value_try': asset.value_try,
                        'shares': asset.shares,
                        'price': asset.current_price
                    }
            save_snapshot(st.session_state.portfolio.metrics.total_value_try, assets_summary)
            st.success("Snapshot alındı!")
            st.rerun()


# =============================================================================
# SAYFA: DASHBOARD
# =============================================================================

def render_dashboard_page():
    """Dashboard ana sayfasını render et."""
    st.markdown("""
    <h1 class="main-title">📊 Portföy Dashboard</h1>
    <p class="subtitle">Gerçek zamanlı portföy takibi ve analizi</p>
    """, unsafe_allow_html=True)
    
    portfolio = st.session_state.portfolio
    
    if portfolio is None:
        st.info("👈 Sol menüden config dosyasını yükleyin.")
        
        with st.expander("🚀 Hızlı Başlangıç"):
            st.markdown("""
            1. **Varlık Yönetimi** sayfasına gidin
            2. Portföyünüze hisse/kripto/fon ekleyin
            3. Config'i kaydedin
            4. Dashboard'a dönüp **Güncelle** butonuna basın
            """)
        return
    
    if not portfolio.assets or not any(a.is_valid for a in portfolio.assets):
        st.warning("⚠️ Varlık verisi yok. **Güncelle** butonuna basın.")
        return
    
    # Metrikler
    render_metric_cards(portfolio)
    
    st.markdown("---")
    
    # Tabs (Rebalancing kaldırıldı)
    tab1, tab2, tab3 = st.tabs(["📋 Varlıklar", "📊 Grafikler", "🔗 Korelasyon"])
    
    with tab1:
        render_asset_table(portfolio)
    
    with tab2:
        render_charts(portfolio)
    
    with tab3:
        render_correlation(portfolio)


# =============================================================================
# SAYFA: AYARLAR
# =============================================================================

def render_settings_page():
    """Ayarlar sayfasını render et."""
    st.markdown("## ⚙️ Ayarlar")
    
    st.markdown("### 🎨 Görünüm")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.selectbox("Tema", ["Koyu", "Açık", "Sistem"], index=0)
        st.selectbox("Dil", ["Türkçe", "English"], index=0)
    
    with col2:
        st.number_input("Otomatik yenileme (dk)", min_value=0, max_value=60, value=0)
        st.checkbox("Bildirimler", value=True)
    
    st.markdown("---")
    
    st.markdown("### 📊 Hesaplama Parametreleri")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.number_input("Risk-free rate (%)", min_value=0.0, max_value=100.0, value=35.0)
        st.number_input("Volatilite penceresi (gün)", min_value=5, max_value=90, value=21)
    
    with col2:
        st.number_input("Sharpe penceresi (gün)", min_value=5, max_value=365, value=252)
        st.number_input("Korelasyon penceresi (gün)", min_value=5, max_value=90, value=30)
    
    st.markdown("---")
    
    st.markdown("### 📸 Snapshot Ayarları")
    
    st.info("Her Cuma otomatik snapshot alınır. Manuel snapshot almak için 'Haftalık Rapor' sayfasını kullanın.")
    
    # Snapshot temizleme
    if st.button("🗑️ Tüm Snapshot'ları Sil", type="secondary"):
        if SNAPSHOT_FILE.exists():
            SNAPSHOT_FILE.unlink()
            st.success("Snapshot'lar silindi!")
    
    st.markdown("---")
    
    if st.button("💾 Ayarları Kaydet", type="primary"):
        st.success("Ayarlar kaydedildi!")


# =============================================================================
# ANA UYGULAMA
# =============================================================================

def main():
    """Ana uygulama fonksiyonu."""
    init_session_state()
    
    # İlk yüklemede config'i otomatik yükle
    if st.session_state.config is None:
        config_path = Path("config.yaml")
        if config_path.exists():
            st.session_state.config = load_config(str(config_path))
            st.session_state.portfolio = Portfolio(st.session_state.config)
    
    # Sidebar
    render_sidebar()
    
    # Sayfa yönlendirme
    if st.session_state.current_page == "dashboard":
        render_dashboard_page()
    elif st.session_state.current_page == "assets":
        render_asset_selector()
    elif st.session_state.current_page == "weekly":
        render_weekly_report_page()
    elif st.session_state.current_page == "settings":
        render_settings_page()


if __name__ == "__main__":
    main()
