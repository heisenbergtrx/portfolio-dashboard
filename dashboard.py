"""
dashboard.py - Portföy Dashboard Ana Uygulaması (v4)
====================================================

Streamlit tabanlı interaktif web dashboard.

Güncellemeler v4:
- Pasta grafiğinde Nakit Rezervi gruplaması
- Drawdown takibi
- Position Sizing uyarıları
- Risk-Adjusted Returns (Sortino)
- Nasdaq Beta hesaplaması

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
    if not SNAPSHOT_FILE.exists():
        return []
    try:
        with open(SNAPSHOT_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    except:
        return []


def save_snapshot(total_value: float, assets_summary: dict) -> None:
    SNAPSHOT_FILE.parent.mkdir(exist_ok=True)
    snapshots = load_snapshots()
    new_snapshot = {
        'date': datetime.now().isoformat(),
        'total_value_try': total_value,
        'assets': assets_summary,
        'week_number': datetime.now().isocalendar()[1]
    }
    snapshots.append(new_snapshot)
    snapshots = snapshots[-52:]
    with open(SNAPSHOT_FILE, 'w', encoding='utf-8') as f:
        json.dump(snapshots, f, indent=2, ensure_ascii=False)


def should_take_snapshot() -> bool:
    today = datetime.now()
    if today.weekday() != 4:
        return False
    current_week = today.isocalendar()[1]
    snapshots = load_snapshots()
    for snap in snapshots:
        snap_date = datetime.fromisoformat(snap['date'])
        if snap_date.isocalendar()[1] == current_week and snap_date.year == today.year:
            return False
    return True


def take_snapshot_if_needed(portfolio) -> bool:
    if not should_take_snapshot():
        return False
    if not portfolio or not portfolio.assets:
        return False
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
    .main-title { font-size: 2.5rem; font-weight: 700; color: #1a1a2e; margin-bottom: 0.5rem; }
    .subtitle { font-size: 1rem; color: #666; margin-bottom: 2rem; }
    .positive { color: #00d26a !important; }
    .negative { color: #ff6b6b !important; }
    .warning-box { background: #fff3cd; border-left: 4px solid #ffc107; padding: 10px; margin: 10px 0; border-radius: 4px; }
    .danger-box { background: #f8d7da; border-left: 4px solid #dc3545; padding: 10px; margin: 10px 0; border-radius: 4px; }
    .success-box { background: #d4edda; border-left: 4px solid #28a745; padding: 10px; margin: 10px 0; border-radius: 4px; }
</style>
""", unsafe_allow_html=True)


# =============================================================================
# SESSION STATE
# =============================================================================

def init_session_state():
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
            'cash_reserve_codes': config.cash_reserve_codes,
            'tefas_funds': config.tefas_funds,
            'us_stocks': config.us_stocks,
            'crypto': config.crypto,
            'cash': config.cash,
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
    with st.sidebar:
        st.markdown("# 📊 Portföy")
        st.markdown("---")
        
        st.markdown("### 📍 Navigasyon")
        
        if st.button("🏠 Dashboard", use_container_width=True, 
                    type="primary" if st.session_state.current_page == "dashboard" else "secondary"):
            st.session_state.current_page = "dashboard"
            st.rerun()
        
        if st.button("📦 Varlık Yönetimi", use_container_width=True,
                    type="primary" if st.session_state.current_page == "assets" else "secondary"):
            st.session_state.current_page = "assets"
            st.rerun()
        
        if st.button("⚠️ Risk Analizi", use_container_width=True,
                    type="primary" if st.session_state.current_page == "risk" else "secondary"):
            st.session_state.current_page = "risk"
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
        
        if st.session_state.current_page == "dashboard":
            st.markdown("### 🔧 İşlemler")
            config_path = st.text_input("Config Dosyası", value="config.yaml", label_visibility="collapsed")
            
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
                                if take_snapshot_if_needed(st.session_state.portfolio):
                                    st.toast("📸 Haftalık snapshot alındı!")
                                st.success("✓")
                            else:
                                st.error("!")
                    else:
                        st.warning("Önce yükle!")
            st.markdown("---")
        
        if st.session_state.last_refresh:
            st.caption(f"Son güncelleme: {st.session_state.last_refresh.strftime('%H:%M:%S')}")
        
        if st.session_state.config:
            st.markdown("### 📋 Özet")
            cfg = st.session_state.config
            col1, col2 = st.columns(2)
            with col1:
                st.metric("TEFAS", len(cfg.tefas_funds))
                st.metric("Kripto", len(cfg.crypto))
            with col2:
                st.metric("ABD", len(cfg.us_stocks))
                st.metric("Nakit", len(cfg.cash))


# =============================================================================
# METRİK KARTLARI
# =============================================================================

def render_metric_cards(portfolio):
    metrics = portfolio.metrics
    col1, col2, col3, col4, col5 = st.columns(5)
    
    with col1:
        st.metric(label="💰 Toplam Değer", value=format_currency(metrics.total_value_try))
    
    with col2:
        weekly_return = metrics.weekly_return_pct
        delta_color = "normal" if weekly_return >= 0 else "inverse"
        st.metric(label="📈 Haftalık", value=format_percentage(weekly_return), 
                 delta=f"{weekly_return:+.2f}%", delta_color=delta_color)
    
    with col3:
        st.metric(label="💵 Nakit Rezervi", value=format_currency(metrics.cash_reserve_try), 
                 delta=f"{metrics.cash_reserve_pct:.1f}%")
    
    with col4:
        sharpe = metrics.sharpe_ratio
        if sharpe is not None:
            sharpe_display = f"{sharpe:.2f}"
            sharpe_icon = "🟢" if sharpe > 1 else "🟡" if sharpe > 0 else "🔴"
        else:
            sharpe_display = "N/A"
            sharpe_icon = "⚪"
        st.metric(label=f"Sharpe {sharpe_icon}", value=sharpe_display)
    
    with col5:
        vol = metrics.volatility_monthly
        if vol is not None:
            vol_display = f"{vol:.1f}%"
            vol_icon = "🟢" if vol < 10 else "🟡" if vol < 20 else "🔴"
        else:
            vol_display = "N/A"
            vol_icon = "⚪"
        st.metric(label=f"Volatilite {vol_icon}", value=vol_display)


# =============================================================================
# VARLIK TABLOSU
# =============================================================================

def render_asset_table(portfolio):
    st.markdown("### 📋 Varlık Listesi")
    
    col1, col2 = st.columns([3, 1])
    with col2:
        edit_mode = st.toggle("✏️ Düzenle", value=st.session_state.edit_mode)
        st.session_state.edit_mode = edit_mode
    
    df = portfolio.get_summary_dataframe()
    if df.empty:
        st.info("Varlık bulunamadı.")
        return
    
    if edit_mode:
        st.info("💡 Adetleri değiştirin ve 'Kaydet' butonuna basın.")
        changes_made = False
        new_shares = {}
        
        for idx, row in df.iterrows():
            col1, col2, col3, col4, col5 = st.columns([2, 1, 2, 1, 1])
            with col1:
                cash_icon = "💵 " if row['Nakit'] == '✓' else ""
                st.write(f"**{cash_icon}{row['Kod']}** - {row['İsim'][:20]}")
            with col2:
                st.write(row['Tür'])
            with col3:
                new_val = st.number_input(
                    f"Adet_{row['Kod']}", value=float(row['Adet']), min_value=0.0,
                    step=0.01 if row['Tür'] in ('CRYPTO', 'CASH') else 1.0,
                    format="%.4f" if row['Tür'] in ('CRYPTO', 'CASH') else "%.2f",
                    label_visibility="collapsed", key=f"shares_{row['Kod']}"
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
        if st.button("💾 Değişiklikleri Kaydet", type="primary", disabled=not changes_made):
            config = st.session_state.config
            for fund in config.tefas_funds:
                if fund['code'] in new_shares:
                    fund['shares'] = new_shares[fund['code']]
            for stock in config.us_stocks:
                if stock['ticker'] in new_shares:
                    stock['shares'] = new_shares[stock['ticker']]
            for crypto in config.crypto:
                symbol_short = crypto['symbol'].split('/')[0]
                if symbol_short in new_shares:
                    crypto['amount'] = new_shares[symbol_short]
            for cash_item in config.cash:
                if cash_item['code'] in new_shares:
                    cash_item['amount'] = new_shares[cash_item['code']]
            
            if save_config_to_file(config):
                st.success("✅ Değişiklikler kaydedildi!")
                st.session_state.edit_mode = False
                st.session_state.portfolio = Portfolio(config)
                st.session_state.portfolio.refresh_prices()
                st.rerun()
            else:
                st.error("Kaydetme hatası!")
    else:
        def highlight_weekly(val):
            if isinstance(val, (int, float)):
                if val > 0: return 'color: #00d26a'
                elif val < 0: return 'color: #ff6b6b'
            return ''
        
        styled_df = df.style.applymap(highlight_weekly, subset=['Haftalık (%)']).format({
            'Adet': '{:.4f}', 'Fiyat': '{:.2f}', 'Değer (TRY)': '₺{:,.0f}',
            'Ağırlık (%)': '{:.1f}%', 'Hedef (%)': '{:.1f}%', 'Sapma (%)': '{:+.1f}%', 'Haftalık (%)': '{:+.2f}%'
        })
        st.dataframe(styled_df, use_container_width=True, hide_index=True)


# =============================================================================
# GRAFİKLER - GRUPLU PASTA
# =============================================================================

def render_charts(portfolio):
    df = portfolio.get_summary_dataframe()
    valid_df = df[df['Değer (TRY)'] > 0].copy()
    if valid_df.empty:
        st.warning("Grafik için yeterli veri yok.")
        return
    
    st.markdown("### 📊 Portföy Dağılımı")
    
    # Gruplu pasta grafiği için veri hazırla
    # Nakit rezervi olanları "Nakit Rezervi" olarak grupla
    pie_data = []
    cash_total = 0
    
    for _, row in valid_df.iterrows():
        if row['Nakit'] == '✓':
            cash_total += row['Değer (TRY)']
        else:
            pie_data.append({
                'Varlık': row['Kod'],
                'Değer (TRY)': row['Değer (TRY)'],
                'Tür': row['Tür']
            })
    
    # Nakit rezervini tek dilim olarak ekle
    if cash_total > 0:
        pie_data.append({
            'Varlık': '💵 Nakit Rezervi',
            'Değer (TRY)': cash_total,
            'Tür': 'CASH'
        })
    
    pie_df = pd.DataFrame(pie_data)
    
    col1, col2 = st.columns(2)
    
    with col1:
        # Ana pasta grafiği - Nakit Rezervi gruplu
        color_map = {
            '💵 Nakit Rezervi': '#38ef7d',
            'BTC': '#f7931a',
            'ETH': '#627eea',
            'SOL': '#00ffa3',
        }
        # Diğer varlıklar için renk paleti
        colors = px.colors.qualitative.Set3
        
        fig = px.pie(
            pie_df,
            values='Değer (TRY)',
            names='Varlık',
            title='Portföy Dağılımı (Nakit Gruplu)',
            color_discrete_sequence=colors
        )
        fig.update_traces(textposition='inside', textinfo='percent+label')
        fig.update_layout(showlegend=True, margin=dict(t=40, b=20))
        st.plotly_chart(fig, use_container_width=True)
    
    with col2:
        # Tür bazlı pasta (CASH = Nakit Rezervi)
        type_df = pie_df.groupby('Tür')['Değer (TRY)'].sum().reset_index()
        type_df['Tür'] = type_df['Tür'].replace({'CASH': '💵 Nakit Rezervi', 'US_STOCK': '🇺🇸 ABD Hisse', 'CRYPTO': '₿ Kripto', 'TEFAS': '🏦 TEFAS'})
        
        fig = px.pie(
            type_df,
            values='Değer (TRY)',
            names='Tür',
            title='Varlık Türü Dağılımı',
            color_discrete_map={
                '💵 Nakit Rezervi': '#38ef7d',
                '🇺🇸 ABD Hisse': '#667eea',
                '₿ Kripto': '#f7931a',
                '🏦 TEFAS': '#e91e63'
            }
        )
        fig.update_traces(textposition='inside', textinfo='percent+label')
        fig.update_layout(showlegend=True, margin=dict(t=40, b=20))
        st.plotly_chart(fig, use_container_width=True)
    
    # Nakit rezervi detay (küçük)
    cash_df = portfolio.get_cash_reserve_breakdown()
    if not cash_df.empty and len(cash_df) > 1:
        st.markdown("#### 💵 Nakit Rezervi Bileşenleri")
        col1, col2 = st.columns([2, 1])
        with col1:
            fig = px.bar(
                cash_df, 
                x='Kod', 
                y='Değer (TRY)',
                color='Kod',
                color_discrete_sequence=['#11998e', '#38ef7d', '#56ab2f']
            )
            fig.update_layout(showlegend=False, margin=dict(t=20, b=20))
            st.plotly_chart(fig, use_container_width=True)
        with col2:
            total_cash = cash_df['Değer (TRY)'].sum()
            for _, row in cash_df.iterrows():
                pct = (row['Değer (TRY)'] / total_cash * 100) if total_cash > 0 else 0
                st.write(f"**{row['Kod']}:** ₺{row['Değer (TRY)']:,.0f} ({pct:.1f}%)")
    
    # Haftalık performans
    st.markdown("### 📈 Haftalık Performans")
    df_sorted = valid_df.sort_values('Haftalık (%)', ascending=True)
    colors = ['#00d26a' if x >= 0 else '#ff6b6b' for x in df_sorted['Haftalık (%)']]
    fig = go.Figure()
    fig.add_trace(go.Bar(x=df_sorted['Kod'], y=df_sorted['Haftalık (%)'], marker_color=colors,
                        text=[f"{v:+.1f}%" for v in df_sorted['Haftalık (%)']], textposition='outside'))
    fig.update_layout(showlegend=False, yaxis=dict(zeroline=True, zerolinewidth=2, zerolinecolor='gray'), margin=dict(t=20, b=50))
    st.plotly_chart(fig, use_container_width=True)
    
    # Trend grafiği
    st.markdown("### 📈 Fiyat Trendi")
    asset_codes = [a.code for a in portfolio.assets if a.is_valid and a.asset_type != "CASH"]
    if asset_codes:
        selected_asset = st.selectbox("Varlık Seçin", options=asset_codes, index=0)
        with st.spinner(f"{selected_asset} verisi çekiliyor..."):
            hist_df = portfolio.get_history_data(selected_asset, days=30)
        if not hist_df.empty and len(hist_df) >= 2:
            fig = go.Figure()
            fig.add_trace(go.Scatter(x=hist_df['Date'], y=hist_df['Close'], mode='lines+markers', name=selected_asset,
                                    line=dict(color='#667eea', width=2), marker=dict(size=4)))
            if len(hist_df) >= 7:
                hist_df['MA7'] = hist_df['Close'].rolling(window=7).mean()
                fig.add_trace(go.Scatter(x=hist_df['Date'], y=hist_df['MA7'], mode='lines', name='7G ORT',
                                        line=dict(color='orange', width=1, dash='dash')))
            fig.update_layout(hovermode='x unified', legend=dict(orientation="h", yanchor="bottom", y=1.02), margin=dict(t=40, b=40))
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.warning(f"{selected_asset} için geçmiş veri bulunamadı.")


# =============================================================================
# KORELASYON
# =============================================================================

def render_correlation(portfolio):
    st.markdown("### 🔗 Korelasyon Matrisi")
    corr_matrix = portfolio.get_correlation_matrix()
    if corr_matrix is None or corr_matrix.empty:
        st.info("Korelasyon matrisi hesaplanamadı.")
        return
    fig = px.imshow(corr_matrix, text_auto='.2f', color_continuous_scale='RdBu_r', zmin=-1, zmax=1, aspect='auto')
    fig.update_layout(margin=dict(t=20, b=20))
    st.plotly_chart(fig, use_container_width=True)
    st.caption("🟢 Düşük korelasyon = İyi çeşitlendirme | 🔴 Yüksek korelasyon = Risk")


# =============================================================================
# RİSK ANALİZİ SAYFASI
# =============================================================================

def render_risk_analysis_page():
    """Risk analizi sayfası - Drawdown, Position Sizing, Beta, Sortino"""
    st.markdown("## ⚠️ Risk Analizi")
    
    portfolio = st.session_state.portfolio
    if portfolio is None or not portfolio.assets:
        st.warning("Önce portföyü yükleyin ve güncelleyin.")
        return
    
    # Risk metrikleri hesapla
    risk_metrics = calculate_risk_metrics(portfolio)
    
    # Üst metrik kartları
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        drawdown = risk_metrics.get('drawdown', 0)
        dd_color = "🟢" if drawdown > -5 else "🟡" if drawdown > -15 else "🔴"
        st.metric(
            label=f"📉 Drawdown {dd_color}",
            value=f"{drawdown:.1f}%",
            help="Son 30 günde ATH'den düşüş"
        )
    
    with col2:
        beta = risk_metrics.get('beta', None)
        if beta is not None:
            beta_color = "🟢" if 0.8 <= beta <= 1.2 else "🟡" if 0.5 <= beta <= 1.5 else "🔴"
            st.metric(
                label=f"β Beta (QQQ) {beta_color}",
                value=f"{beta:.2f}",
                help="Nasdaq'a göre beta. 1 = piyasa ile aynı hareket"
            )
        else:
            st.metric(label="β Beta (QQQ)", value="N/A")
    
    with col3:
        sortino = risk_metrics.get('sortino', None)
        if sortino is not None:
            sortino_color = "🟢" if sortino > 1 else "🟡" if sortino > 0 else "🔴"
            st.metric(
                label=f"Sortino {sortino_color}",
                value=f"{sortino:.2f}",
                help="Risk-adjusted return (sadece downside volatilite)"
            )
        else:
            st.metric(label="Sortino", value="N/A")
    
    with col4:
        max_position = risk_metrics.get('max_position_pct', 0)
        pos_color = "🟢" if max_position <= 20 else "🟡" if max_position <= 30 else "🔴"
        st.metric(
            label=f"Max Pozisyon {pos_color}",
            value=f"{max_position:.1f}%",
            help="En büyük tek pozisyon ağırlığı"
        )
    
    st.markdown("---")
    
    # Drawdown Grafiği
    st.markdown("### 📉 Drawdown Analizi")
    drawdown_df = risk_metrics.get('drawdown_series', None)
    
    if drawdown_df is not None and not drawdown_df.empty:
        col1, col2 = st.columns([2, 1])
        
        with col1:
            fig = go.Figure()
            fig.add_trace(go.Scatter(
                x=drawdown_df['Date'],
                y=drawdown_df['Drawdown'],
                mode='lines',
                fill='tozeroy',
                fillcolor='rgba(255, 107, 107, 0.3)',
                line=dict(color='#ff6b6b', width=2),
                name='Drawdown'
            ))
            fig.add_hline(y=-10, line_dash="dash", line_color="orange", annotation_text="-10% Uyarı")
            fig.add_hline(y=-20, line_dash="dash", line_color="red", annotation_text="-20% Tehlike")
            fig.update_layout(
                yaxis=dict(ticksuffix='%', title='Drawdown'),
                xaxis=dict(title='Tarih'),
                hovermode='x unified',
                margin=dict(t=20, b=40)
            )
            st.plotly_chart(fig, use_container_width=True)
        
        with col2:
            st.markdown("#### 📊 Drawdown Özeti")
            st.write(f"**Mevcut Drawdown:** {risk_metrics.get('drawdown', 0):.1f}%")
            st.write(f"**Max Drawdown (30g):** {risk_metrics.get('max_drawdown', 0):.1f}%")
            st.write(f"**ATH Değer:** ₺{risk_metrics.get('ath_value', 0):,.0f}")
            
            # Drawdown durumu
            dd = risk_metrics.get('drawdown', 0)
            if dd > -5:
                st.success("✅ Drawdown normal seviyede")
            elif dd > -15:
                st.warning("⚠️ Dikkat: Drawdown artıyor")
            else:
                st.error("🚨 Yüksek drawdown! Risk yönetimi gerekli")
    else:
        st.info("Drawdown hesaplamak için yeterli geçmiş veri yok.")
    
    st.markdown("---")
    
    # Position Sizing
    st.markdown("### 📊 Position Sizing Analizi")
    
    position_df = risk_metrics.get('position_analysis', None)
    
    if position_df is not None and not position_df.empty:
        col1, col2 = st.columns([2, 1])
        
        with col1:
            # Position ağırlıkları bar chart
            fig = go.Figure()
            colors = ['#ff6b6b' if x > 20 else '#ffc107' if x > 15 else '#00d26a' for x in position_df['Ağırlık (%)']]
            fig.add_trace(go.Bar(
                x=position_df['Kod'],
                y=position_df['Ağırlık (%)'],
                marker_color=colors,
                text=[f"{v:.1f}%" for v in position_df['Ağırlık (%)']],
                textposition='outside'
            ))
            fig.add_hline(y=20, line_dash="dash", line_color="red", annotation_text="Max %20 Limit")
            fig.add_hline(y=15, line_dash="dash", line_color="orange", annotation_text="Uyarı %15")
            fig.update_layout(
                yaxis=dict(ticksuffix='%', title='Portföy Ağırlığı'),
                margin=dict(t=20, b=50)
            )
            st.plotly_chart(fig, use_container_width=True)
        
        with col2:
            st.markdown("#### ⚠️ Position Uyarıları")
            
            over_limit = position_df[position_df['Ağırlık (%)'] > 20]
            warning_zone = position_df[(position_df['Ağırlık (%)'] > 15) & (position_df['Ağırlık (%)'] <= 20)]
            
            if len(over_limit) > 0:
                st.error("**Limit Aşımı (>20%):**")
                for _, row in over_limit.iterrows():
                    st.write(f"🔴 **{row['Kod']}**: {row['Ağırlık (%)']:.1f}%")
            
            if len(warning_zone) > 0:
                st.warning("**Uyarı Bölgesi (15-20%):**")
                for _, row in warning_zone.iterrows():
                    st.write(f"🟡 **{row['Kod']}**: {row['Ağırlık (%)']:.1f}%")
            
            if len(over_limit) == 0 and len(warning_zone) == 0:
                st.success("✅ Tüm pozisyonlar limit içinde")
            
            st.markdown("---")
            st.markdown("#### 📐 Position Sizing Kuralları")
            st.write("• Tek pozisyon max **%20**")
            st.write("• Sektör başına max **%30**")
            st.write("• Nakit rezervi min **%10**")
    
    st.markdown("---")
    
    # Beta ve Korelasyon
    st.markdown("### β Beta & Benchmark Analizi")
    
    col1, col2 = st.columns(2)
    
    with col1:
        beta = risk_metrics.get('beta', None)
        if beta is not None:
            # Beta gauge chart
            fig = go.Figure(go.Indicator(
                mode="gauge+number",
                value=beta,
                domain={'x': [0, 1], 'y': [0, 1]},
                title={'text': "Nasdaq Beta"},
                gauge={
                    'axis': {'range': [0, 2]},
                    'bar': {'color': "#667eea"},
                    'steps': [
                        {'range': [0, 0.5], 'color': "#d4edda"},
                        {'range': [0.5, 1], 'color': "#fff3cd"},
                        {'range': [1, 1.5], 'color': "#ffeeba"},
                        {'range': [1.5, 2], 'color': "#f8d7da"}
                    ],
                    'threshold': {
                        'line': {'color': "red", 'width': 4},
                        'thickness': 0.75,
                        'value': 1
                    }
                }
            ))
            fig.update_layout(margin=dict(t=40, b=20))
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("Beta hesaplanamadı.")
    
    with col2:
        st.markdown("#### 📖 Beta Yorumu")
        if beta is not None:
            if beta < 0.5:
                st.success("**Düşük Beta (<0.5):** Portföy defansif. Piyasa düşüşlerinde daha az etkilenir.")
            elif beta < 1:
                st.info("**Orta Beta (0.5-1):** Piyasadan daha az volatil. Dengeli risk profili.")
            elif beta < 1.2:
                st.warning("**Nötr Beta (1-1.2):** Piyasa ile benzer hareket. Ortalama risk.")
            else:
                st.error("**Yüksek Beta (>1.2):** Agresif portföy. Piyasa hareketlerini amplifiye eder.")
            
            st.markdown("---")
            st.write(f"**Örnek:** Nasdaq %10 düşerse, portföyünüz yaklaşık **%{beta*10:.1f}** düşer.")
        
        # Sortino açıklama
        st.markdown("#### 📊 Sortino Ratio")
        sortino = risk_metrics.get('sortino', None)
        if sortino is not None:
            if sortino > 2:
                st.success(f"**{sortino:.2f}:** Mükemmel risk-adjusted return")
            elif sortino > 1:
                st.info(f"**{sortino:.2f}:** İyi risk-adjusted return")
            elif sortino > 0:
                st.warning(f"**{sortino:.2f}:** Ortalama, geliştirilebilir")
            else:
                st.error(f"**{sortino:.2f}:** Düşük, risk yönetimi gerekli")


def calculate_risk_metrics(portfolio) -> dict:
    """Risk metriklerini hesapla"""
    from data_fetcher import fetch_us_stock_history
    
    result = {
        'drawdown': 0,
        'max_drawdown': 0,
        'ath_value': 0,
        'beta': None,
        'sortino': None,
        'max_position_pct': 0,
        'drawdown_series': None,
        'position_analysis': None
    }
    
    try:
        # Position Analysis
        valid_assets = [a for a in portfolio.assets if a.is_valid]
        if valid_assets:
            position_data = [{
                'Kod': a.code,
                'Ağırlık (%)': a.actual_weight,
                'Değer (TRY)': a.value_try
            } for a in valid_assets]
            position_df = pd.DataFrame(position_data).sort_values('Ağırlık (%)', ascending=False)
            result['position_analysis'] = position_df
            result['max_position_pct'] = position_df['Ağırlık (%)'].max()
        
        # Snapshot'lardan drawdown hesapla
        snapshots = load_snapshots()
        if len(snapshots) >= 2:
            values = [s['total_value_try'] for s in snapshots]
            dates = [datetime.fromisoformat(s['date']) for s in snapshots]
            
            # Running maximum (ATH)
            running_max = pd.Series(values).expanding().max()
            drawdowns = (pd.Series(values) - running_max) / running_max * 100
            
            result['drawdown'] = drawdowns.iloc[-1]
            result['max_drawdown'] = drawdowns.min()
            result['ath_value'] = running_max.iloc[-1]
            
            # Drawdown series for chart
            result['drawdown_series'] = pd.DataFrame({
                'Date': dates,
                'Drawdown': drawdowns.values
            })
        
        # Beta hesaplama (QQQ benchmark)
        try:
            # Portföy returns (snapshot'lardan)
            if len(snapshots) >= 5:
                portfolio_values = pd.Series([s['total_value_try'] for s in snapshots])
                portfolio_returns = portfolio_values.pct_change().dropna()
                
                # QQQ returns
                qqq_hist = fetch_us_stock_history("QQQ", days=len(snapshots) * 7)
                if not qqq_hist.empty and len(qqq_hist) >= len(portfolio_returns):
                    # Haftalık returns'e çevir (her 5 günde bir)
                    qqq_weekly = qqq_hist['Close'].iloc[::5].pct_change().dropna()
                    
                    # Uzunlukları eşitle
                    min_len = min(len(portfolio_returns), len(qqq_weekly))
                    if min_len >= 3:
                        port_ret = portfolio_returns.iloc[-min_len:].values
                        qqq_ret = qqq_weekly.iloc[-min_len:].values
                        
                        # Beta = Cov(portfolio, market) / Var(market)
                        covariance = np.cov(port_ret, qqq_ret)[0][1]
                        variance = np.var(qqq_ret)
                        if variance > 0:
                            result['beta'] = covariance / variance
        except Exception as e:
            logger.warning(f"Beta hesaplama hatası: {e}")
        
        # Sortino Ratio
        try:
            if len(snapshots) >= 5:
                portfolio_values = pd.Series([s['total_value_try'] for s in snapshots])
                returns = portfolio_values.pct_change().dropna()
                
                if len(returns) >= 3:
                    # Downside returns only
                    downside_returns = returns[returns < 0]
                    
                    if len(downside_returns) > 0:
                        downside_std = downside_returns.std()
                        if downside_std > 0:
                            # Annualize (weekly data assumed)
                            avg_return = returns.mean() * 52
                            downside_std_annual = downside_std * np.sqrt(52)
                            risk_free = portfolio.config.risk_free_rate
                            
                            result['sortino'] = (avg_return - risk_free) / downside_std_annual
        except Exception as e:
            logger.warning(f"Sortino hesaplama hatası: {e}")
        
    except Exception as e:
        logger.error(f"Risk metrics hesaplama hatası: {e}")
    
    return result


# =============================================================================
# HAFTALIK RAPOR
# =============================================================================

def render_weekly_report_page():
    st.markdown("## 📈 Haftalık Büyüme Raporu")
    snapshots = load_snapshots()
    if not snapshots:
        st.info("Henüz snapshot alınmamış. Her cuma piyasa kapanışında otomatik snapshot alınır.")
        if st.session_state.portfolio and st.session_state.portfolio.assets:
            if st.button("📸 Manuel Snapshot Al", type="primary"):
                assets_summary = {a.code: {'value_try': a.value_try, 'shares': a.shares, 'price': a.current_price} 
                                 for a in st.session_state.portfolio.assets if a.is_valid}
                save_snapshot(st.session_state.portfolio.metrics.total_value_try, assets_summary)
                st.success("Snapshot alındı!")
                st.rerun()
        return
    
    df = pd.DataFrame([{'Tarih': datetime.fromisoformat(s['date']).strftime('%Y-%m-%d'), 'Hafta': s.get('week_number', 0),
                       'Toplam Değer (₺)': s['total_value_try']} for s in snapshots])
    
    st.markdown("### 📊 Portföy Değeri Trendi")
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=df['Tarih'], y=df['Toplam Değer (₺)'], mode='lines+markers', name='Portföy Değeri',
                            line=dict(color='#667eea', width=3), marker=dict(size=8), fill='tozeroy', fillcolor='rgba(102, 126, 234, 0.1)'))
    fig.update_layout(yaxis=dict(tickformat='₺,.0f'), hovermode='x unified', margin=dict(t=20, b=40))
    st.plotly_chart(fig, use_container_width=True)
    
    if len(df) >= 2:
        st.markdown("### 📈 Haftalık Değişimler")
        df['Değişim (₺)'] = df['Toplam Değer (₺)'].diff()
        df['Değişim (%)'] = df['Toplam Değer (₺)'].pct_change() * 100
        recent_df = df.tail(12).dropna()
        if not recent_df.empty:
            colors = ['#00d26a' if x >= 0 else '#ff6b6b' for x in recent_df['Değişim (%)']]
            fig = go.Figure()
            fig.add_trace(go.Bar(x=recent_df['Tarih'], y=recent_df['Değişim (%)'], marker_color=colors,
                                text=[f"{v:+.1f}%" for v in recent_df['Değişim (%)']], textposition='outside'))
            fig.update_layout(yaxis=dict(zeroline=True, zerolinewidth=2, zerolinecolor='gray', ticksuffix='%'), margin=dict(t=20, b=50))
            st.plotly_chart(fig, use_container_width=True)
        
        col1, col2, col3, col4 = st.columns(4)
        first_value, last_value = df['Toplam Değer (₺)'].iloc[0], df['Toplam Değer (₺)'].iloc[-1]
        total_change = last_value - first_value
        total_change_pct = (total_change / first_value) * 100 if first_value > 0 else 0
        with col1: st.metric("İlk Değer", f"₺{first_value:,.0f}")
        with col2: st.metric("Son Değer", f"₺{last_value:,.0f}")
        with col3: st.metric("Toplam Değişim", f"₺{total_change:+,.0f}")
        with col4: st.metric("Toplam Getiri", f"{total_change_pct:+.1f}%")
    
    st.markdown("### 📋 Snapshot Geçmişi")
    display_df = df.copy()
    st.dataframe(display_df, use_container_width=True, hide_index=True)
    
    st.markdown("---")
    if st.session_state.portfolio and st.session_state.portfolio.assets:
        if st.button("📸 Manuel Snapshot Al"):
            assets_summary = {a.code: {'value_try': a.value_try, 'shares': a.shares, 'price': a.current_price} 
                             for a in st.session_state.portfolio.assets if a.is_valid}
            save_snapshot(st.session_state.portfolio.metrics.total_value_try, assets_summary)
            st.success("Snapshot alındı!")
            st.rerun()


# =============================================================================
# DASHBOARD
# =============================================================================

def render_dashboard_page():
    st.markdown('<h1 class="main-title">📊 Portföy Dashboard</h1><p class="subtitle">Gerçek zamanlı portföy takibi ve analizi</p>', unsafe_allow_html=True)
    portfolio = st.session_state.portfolio
    if portfolio is None:
        st.info("👈 Sol menüden config dosyasını yükleyin.")
        return
    if not portfolio.assets or not any(a.is_valid for a in portfolio.assets):
        st.warning("⚠️ Varlık verisi yok. **Güncelle** butonuna basın.")
        return
    render_metric_cards(portfolio)
    st.markdown("---")
    tab1, tab2, tab3 = st.tabs(["📋 Varlıklar", "📊 Grafikler", "🔗 Korelasyon"])
    with tab1: render_asset_table(portfolio)
    with tab2: render_charts(portfolio)
    with tab3: render_correlation(portfolio)


# =============================================================================
# AYARLAR
# =============================================================================

def render_settings_page():
    st.markdown("## ⚙️ Ayarlar")
    st.info("Her Cuma otomatik snapshot alınır. Manuel snapshot almak için 'Haftalık Rapor' sayfasını kullanın.")
    if st.button("🗑️ Tüm Snapshot'ları Sil", type="secondary"):
        if SNAPSHOT_FILE.exists():
            SNAPSHOT_FILE.unlink()
            st.success("Snapshot'lar silindi!")


# =============================================================================
# MAIN
# =============================================================================

def main():
    init_session_state()
    if st.session_state.config is None:
        config_path = Path("config.yaml")
        if config_path.exists():
            st.session_state.config = load_config(str(config_path))
            st.session_state.portfolio = Portfolio(st.session_state.config)
    render_sidebar()
    if st.session_state.current_page == "dashboard": render_dashboard_page()
    elif st.session_state.current_page == "assets": render_asset_selector()
    elif st.session_state.current_page == "risk": render_risk_analysis_page()
    elif st.session_state.current_page == "weekly": render_weekly_report_page()
    elif st.session_state.current_page == "settings": render_settings_page()


if __name__ == "__main__":
    main()
