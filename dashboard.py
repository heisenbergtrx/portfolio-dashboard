"""
dashboard.py - Portföy Dashboard (v5 - Supabase Edition)
========================================================

Supabase ile:
- Google Authentication
- Kalıcı portföy config'i
- Kalıcı haftalık snapshot'lar
- Benchmark karşılaştırma

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
    config_to_dict,
    dict_to_config,
)

# Supabase imports
from supabase_client import (
    init_auth_state,
    get_current_user,
    is_logged_in,
    render_login_page,
    handle_oauth_callback,
    logout,
    save_portfolio_config,
    load_portfolio_config,
    save_snapshot,
    load_snapshots,
    should_take_weekly_snapshot,
    delete_all_snapshots,
)

# Benchmark
from benchmark import render_benchmark_tab

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
# STIL
# =============================================================================

st.markdown("""
<style>
    .main-title { font-size: 2.5rem; font-weight: 700; color: #1a1a2e; margin-bottom: 0.5rem; }
    .subtitle { font-size: 1rem; color: #666; margin-bottom: 2rem; }
    .positive { color: #00d26a !important; }
    .negative { color: #ff6b6b !important; }
    .user-badge {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
        padding: 8px 15px;
        border-radius: 20px;
        font-size: 0.85rem;
    }
</style>
""", unsafe_allow_html=True)


# =============================================================================
# SESSION STATE
# =============================================================================

def init_session_state():
    """Session state'i başlat."""
    init_auth_state()
    
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
    if 'snapshots' not in st.session_state:
        st.session_state.snapshots = []


# =============================================================================
# CONFIG YÖNETİMİ (Supabase)
# =============================================================================

def save_config_to_cloud(config: PortfolioConfig) -> bool:
    """Config'i Supabase'e kaydet."""
    user = get_current_user()
    if not user:
        return False
    
    config_dict = config_to_dict(config)
    return save_portfolio_config(user['id'], config_dict)


def load_config_from_cloud() -> PortfolioConfig:
    """Config'i Supabase'den yükle."""
    user = get_current_user()
    if not user:
        return PortfolioConfig()
    
    config_dict = load_portfolio_config(user['id'])
    
    if config_dict:
        return dict_to_config(config_dict)
    
    # Varsayılan config
    return PortfolioConfig()


def load_snapshots_from_cloud() -> list[dict]:
    """Snapshot'ları Supabase'den yükle."""
    user = get_current_user()
    if not user:
        return []
    
    return load_snapshots(user['id'])


def save_snapshot_to_cloud(total_value: float, assets: dict) -> bool:
    """Snapshot'ı Supabase'e kaydet."""
    user = get_current_user()
    if not user:
        return False
    
    return save_snapshot(user['id'], total_value, assets)


def take_snapshot_if_needed(portfolio: Portfolio) -> bool:
    """Gerekirse snapshot al."""
    user = get_current_user()
    if not user:
        return False
    
    if not should_take_weekly_snapshot(user['id']):
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
    
    success = save_snapshot_to_cloud(portfolio.metrics.total_value_try, assets_summary)
    
    if success:
        # Session state'i güncelle
        st.session_state.snapshots = load_snapshots_from_cloud()
    
    return success


# =============================================================================
# SIDEBAR
# =============================================================================

def render_sidebar():
    """Sidebar'ı render et."""
    with st.sidebar:
        # Kullanıcı bilgisi
        user = get_current_user()
        if user:
            st.markdown(f"""
            <div class="user-badge">
                👤 {user.get('name', user.get('email', 'Kullanıcı'))}
            </div>
            """, unsafe_allow_html=True)
            
            if st.button("🚪 Çıkış", use_container_width=True):
                logout()
        
        st.markdown("---")
        st.markdown("# 📊 Portföy")
        
        # Navigasyon
        st.markdown("### 📍 Navigasyon")
        
        pages = [
            ("dashboard", "🏠 Dashboard"),
            ("assets", "📦 Varlık Yönetimi"),
            ("risk", "⚠️ Risk Analizi"),
            ("benchmark", "📊 Benchmark"),
            ("weekly", "📈 Haftalık Rapor"),
            ("settings", "⚙️ Ayarlar"),
        ]
        
        for page_id, page_name in pages:
            btn_type = "primary" if st.session_state.current_page == page_id else "secondary"
            if st.button(page_name, use_container_width=True, type=btn_type, key=f"nav_{page_id}"):
                st.session_state.current_page = page_id
                st.rerun()
        
        st.markdown("---")
        
        # Hızlı işlemler (dashboard'da)
        if st.session_state.current_page == "dashboard":
            st.markdown("### 🔧 İşlemler")
            
            col1, col2 = st.columns(2)
            with col1:
                if st.button("📥 Yükle", use_container_width=True):
                    with st.spinner("Yükleniyor..."):
                        st.session_state.config = load_config_from_cloud()
                        st.session_state.portfolio = Portfolio(st.session_state.config)
                        st.session_state.snapshots = load_snapshots_from_cloud()
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
            st.caption(f"Son: {st.session_state.last_refresh.strftime('%H:%M:%S')}")
        
        # Özet
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
    """Özet metrik kartlarını render et."""
    metrics = portfolio.metrics
    col1, col2, col3, col4, col5 = st.columns(5)
    
    with col1:
        st.metric(label="💰 Toplam", value=format_currency(metrics.total_value_try))
    
    with col2:
        weekly_return = metrics.weekly_return_pct
        delta_color = "normal" if weekly_return >= 0 else "inverse"
        st.metric(label="📈 Haftalık", value=format_percentage(weekly_return), 
                 delta=f"{weekly_return:+.2f}%", delta_color=delta_color)
    
    with col3:
        st.metric(label="💵 Nakit", value=format_currency(metrics.cash_reserve_try), 
                 delta=f"{metrics.cash_reserve_pct:.1f}%")
    
    with col4:
        sharpe = metrics.sharpe_ratio
        if sharpe is not None:
            icon = "🟢" if sharpe > 1 else "🟡" if sharpe > 0 else "🔴"
            st.metric(label=f"Sharpe {icon}", value=f"{sharpe:.2f}")
        else:
            st.metric(label="Sharpe", value="N/A")
    
    with col5:
        vol = metrics.volatility_monthly
        if vol is not None:
            icon = "🟢" if vol < 10 else "🟡" if vol < 20 else "🔴"
            st.metric(label=f"Volatilite {icon}", value=f"{vol:.1f}%")
        else:
            st.metric(label="Volatilite", value="N/A")


# =============================================================================
# VARLIK TABLOSU
# =============================================================================

def render_asset_table(portfolio):
    """Varlık tablosunu render et."""
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
                cash_icon = "💵 " if row.get('Nakit') == '✓' else ""
                st.write(f"**{cash_icon}{row['Kod']}**")
            with col2:
                st.write(row['Tür'])
            with col3:
                step = 0.01 if row['Tür'] in ('CRYPTO', 'CASH') else 1.0
                fmt = "%.4f" if row['Tür'] in ('CRYPTO', 'CASH') else "%.2f"
                new_val = st.number_input(
                    f"Adet_{row['Kod']}", value=float(row['Adet']), min_value=0.0,
                    step=step, format=fmt, label_visibility="collapsed", key=f"shares_{row['Kod']}"
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
        if st.button("💾 Kaydet", type="primary", disabled=not changes_made):
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
            
            if save_config_to_cloud(config):
                st.success("✅ Kaydedildi!")
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
        
        display_cols = ['Kod', 'Tür', 'Adet', 'Fiyat', 'Değer (TRY)', 'Ağırlık (%)', 'Haftalık (%)']
        display_df = df[[c for c in display_cols if c in df.columns]]
        
        styled_df = display_df.style.applymap(highlight_weekly, subset=['Haftalık (%)']).format({
            'Adet': '{:.4f}', 'Fiyat': '{:.2f}', 'Değer (TRY)': '₺{:,.0f}',
            'Ağırlık (%)': '{:.1f}%', 'Haftalık (%)': '{:+.2f}%'
        })
        st.dataframe(styled_df, use_container_width=True, hide_index=True)


# =============================================================================
# GRAFİKLER
# =============================================================================

def render_charts(portfolio):
    """Grafikleri render et."""
    df = portfolio.get_summary_dataframe()
    valid_df = df[df['Değer (TRY)'] > 0].copy()
    if valid_df.empty:
        st.warning("Grafik için yeterli veri yok.")
        return
    
    st.markdown("### 📊 Portföy Dağılımı")
    
    # Nakit gruplu pasta
    pie_data = []
    cash_total = 0
    
    for _, row in valid_df.iterrows():
        if row.get('Nakit') == '✓':
            cash_total += row['Değer (TRY)']
        else:
            pie_data.append({'Varlık': row['Kod'], 'Değer (TRY)': row['Değer (TRY)'], 'Tür': row['Tür']})
    
    if cash_total > 0:
        pie_data.append({'Varlık': '💵 Nakit Rezervi', 'Değer (TRY)': cash_total, 'Tür': 'CASH'})
    
    pie_df = pd.DataFrame(pie_data)
    
    col1, col2 = st.columns(2)
    
    with col1:
        fig = px.pie(pie_df, values='Değer (TRY)', names='Varlık', title='Varlık Dağılımı',
                    color_discrete_sequence=px.colors.qualitative.Set3)
        fig.update_traces(textposition='inside', textinfo='percent+label')
        fig.update_layout(showlegend=True, margin=dict(t=40, b=20))
        st.plotly_chart(fig, use_container_width=True)
    
    with col2:
        type_df = pie_df.groupby('Tür')['Değer (TRY)'].sum().reset_index()
        type_df['Tür'] = type_df['Tür'].replace({
            'CASH': '💵 Nakit', 'US_STOCK': '🇺🇸 ABD', 'CRYPTO': '₿ Kripto', 'TEFAS': '🏦 TEFAS'
        })
        fig = px.pie(type_df, values='Değer (TRY)', names='Tür', title='Tür Dağılımı',
                    color_discrete_map={'💵 Nakit': '#38ef7d', '🇺🇸 ABD': '#667eea', '₿ Kripto': '#f7931a', '🏦 TEFAS': '#e91e63'})
        fig.update_traces(textposition='inside', textinfo='percent+label')
        fig.update_layout(showlegend=True, margin=dict(t=40, b=20))
        st.plotly_chart(fig, use_container_width=True)
    
    # Haftalık performans
    st.markdown("### 📈 Haftalık Performans")
    df_sorted = valid_df.sort_values('Haftalık (%)', ascending=True)
    colors = ['#00d26a' if x >= 0 else '#ff6b6b' for x in df_sorted['Haftalık (%)']]
    fig = go.Figure()
    fig.add_trace(go.Bar(x=df_sorted['Kod'], y=df_sorted['Haftalık (%)'], marker_color=colors,
                        text=[f"{v:+.1f}%" for v in df_sorted['Haftalık (%)']], textposition='outside'))
    fig.update_layout(showlegend=False, yaxis=dict(zeroline=True, zerolinewidth=2, zerolinecolor='gray'), margin=dict(t=20, b=50))
    st.plotly_chart(fig, use_container_width=True)


# =============================================================================
# RİSK ANALİZİ
# =============================================================================

def render_risk_analysis_page():
    """Risk analizi sayfası."""
    st.markdown("## ⚠️ Risk Analizi")
    
    portfolio = st.session_state.portfolio
    if not portfolio or not portfolio.assets:
        st.warning("Önce portföyü yükleyin ve güncelleyin.")
        return
    
    snapshots = st.session_state.snapshots
    
    # Position sizing
    valid_assets = [a for a in portfolio.assets if a.is_valid]
    if valid_assets:
        st.markdown("### 📊 Position Sizing")
        
        position_data = [{'Kod': a.code, 'Ağırlık (%)': a.actual_weight} for a in valid_assets]
        position_df = pd.DataFrame(position_data).sort_values('Ağırlık (%)', ascending=False)
        
        col1, col2 = st.columns([2, 1])
        
        with col1:
            colors = ['#ff6b6b' if x > 20 else '#ffc107' if x > 15 else '#00d26a' for x in position_df['Ağırlık (%)']]
            fig = go.Figure()
            fig.add_trace(go.Bar(x=position_df['Kod'], y=position_df['Ağırlık (%)'], marker_color=colors,
                                text=[f"{v:.1f}%" for v in position_df['Ağırlık (%)']], textposition='outside'))
            fig.add_hline(y=20, line_dash="dash", line_color="red", annotation_text="Max %20")
            fig.update_layout(yaxis=dict(ticksuffix='%'), margin=dict(t=20, b=50))
            st.plotly_chart(fig, use_container_width=True)
        
        with col2:
            st.markdown("#### ⚠️ Uyarılar")
            over_limit = position_df[position_df['Ağırlık (%)'] > 20]
            if len(over_limit) > 0:
                for _, row in over_limit.iterrows():
                    st.error(f"🔴 **{row['Kod']}**: {row['Ağırlık (%)']:.1f}%")
            else:
                st.success("✅ Tüm pozisyonlar limit içinde")
    
    # Drawdown (snapshot'lardan)
    if snapshots and len(snapshots) >= 2:
        st.markdown("---")
        st.markdown("### 📉 Drawdown")
        
        values = [float(s['total_value_try']) for s in snapshots]
        dates = [datetime.fromisoformat(s['created_at'].replace('Z', '+00:00')) for s in snapshots]
        
        running_max = pd.Series(values).expanding().max()
        drawdowns = (pd.Series(values) - running_max) / running_max * 100
        
        col1, col2 = st.columns([2, 1])
        
        with col1:
            fig = go.Figure()
            fig.add_trace(go.Scatter(x=dates, y=drawdowns, mode='lines', fill='tozeroy',
                                    fillcolor='rgba(255, 107, 107, 0.3)', line=dict(color='#ff6b6b', width=2)))
            fig.add_hline(y=-10, line_dash="dash", line_color="orange", annotation_text="-10%")
            fig.add_hline(y=-20, line_dash="dash", line_color="red", annotation_text="-20%")
            fig.update_layout(yaxis=dict(ticksuffix='%', title='Drawdown'), margin=dict(t=20, b=40))
            st.plotly_chart(fig, use_container_width=True)
        
        with col2:
            current_dd = drawdowns.iloc[-1]
            max_dd = drawdowns.min()
            ath = running_max.iloc[-1]
            
            st.metric("Mevcut Drawdown", f"{current_dd:.1f}%")
            st.metric("Max Drawdown", f"{max_dd:.1f}%")
            st.metric("ATH Değer", f"₺{ath:,.0f}")


# =============================================================================
# HAFTALIK RAPOR
# =============================================================================

def render_weekly_report_page():
    """Haftalık rapor sayfası."""
    st.markdown("## 📈 Haftalık Büyüme Raporu")
    
    snapshots = st.session_state.snapshots
    
    if not snapshots:
        st.info("Henüz snapshot yok. Her Cuma otomatik veya manuel snapshot alınır.")
        
        if st.session_state.portfolio and st.session_state.portfolio.assets:
            if st.button("📸 Manuel Snapshot Al", type="primary"):
                assets_summary = {a.code: {'value_try': a.value_try, 'shares': a.shares, 'price': a.current_price} 
                                 for a in st.session_state.portfolio.assets if a.is_valid}
                if save_snapshot_to_cloud(st.session_state.portfolio.metrics.total_value_try, assets_summary):
                    st.success("Snapshot alındı!")
                    st.session_state.snapshots = load_snapshots_from_cloud()
                    st.rerun()
        return
    
    # Trend grafiği
    df = pd.DataFrame([{
        'Tarih': datetime.fromisoformat(s['created_at'].replace('Z', '+00:00')).strftime('%Y-%m-%d'),
        'Toplam Değer (₺)': float(s['total_value_try'])
    } for s in snapshots])
    
    st.markdown("### 📊 Portföy Değeri Trendi")
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=df['Tarih'], y=df['Toplam Değer (₺)'], mode='lines+markers',
                            line=dict(color='#667eea', width=3), marker=dict(size=8),
                            fill='tozeroy', fillcolor='rgba(102, 126, 234, 0.1)'))
    fig.update_layout(yaxis=dict(tickformat='₺,.0f'), hovermode='x unified', margin=dict(t=20, b=40))
    st.plotly_chart(fig, use_container_width=True)
    
    if len(df) >= 2:
        df['Değişim (%)'] = df['Toplam Değer (₺)'].pct_change() * 100
        
        col1, col2, col3, col4 = st.columns(4)
        first_val, last_val = df['Toplam Değer (₺)'].iloc[0], df['Toplam Değer (₺)'].iloc[-1]
        total_return = ((last_val / first_val) - 1) * 100
        
        with col1: st.metric("İlk", f"₺{first_val:,.0f}")
        with col2: st.metric("Son", f"₺{last_val:,.0f}")
        with col3: st.metric("Değişim", f"₺{last_val - first_val:+,.0f}")
        with col4: st.metric("Getiri", f"{total_return:+.1f}%")
    
    st.markdown("---")
    if st.session_state.portfolio and st.session_state.portfolio.assets:
        if st.button("📸 Manuel Snapshot Al"):
            assets_summary = {a.code: {'value_try': a.value_try, 'shares': a.shares, 'price': a.current_price} 
                             for a in st.session_state.portfolio.assets if a.is_valid}
            if save_snapshot_to_cloud(st.session_state.portfolio.metrics.total_value_try, assets_summary):
                st.success("Snapshot alındı!")
                st.session_state.snapshots = load_snapshots_from_cloud()
                st.rerun()


# =============================================================================
# BENCHMARK SAYFASI
# =============================================================================

def render_benchmark_page():
    """Benchmark karşılaştırma sayfası."""
    st.markdown("## 📊 Benchmark Karşılaştırma")
    render_benchmark_tab(st.session_state.snapshots)


# =============================================================================
# VARLIK YÖNETİMİ (Basit)
# =============================================================================

def render_asset_management_page():
    """Varlık yönetimi sayfası."""
    st.markdown("## 📦 Varlık Yönetimi")
    
    config = st.session_state.config
    if not config:
        st.warning("Önce config yükleyin.")
        return
    
    tab1, tab2, tab3, tab4 = st.tabs(["🏦 TEFAS", "🇺🇸 ABD Hisse", "₿ Kripto", "💵 Nakit"])
    
    with tab1:
        st.markdown("### TEFAS Fonları")
        for i, fund in enumerate(config.tefas_funds):
            col1, col2, col3 = st.columns([2, 2, 1])
            with col1:
                config.tefas_funds[i]['code'] = st.text_input(f"Kod {i}", fund['code'], key=f"tefas_code_{i}")
            with col2:
                config.tefas_funds[i]['shares'] = st.number_input(f"Adet {i}", fund['shares'], key=f"tefas_shares_{i}")
            with col3:
                config.tefas_funds[i]['target_weight'] = st.number_input(f"Hedef % {i}", fund.get('target_weight', 0), key=f"tefas_weight_{i}")
    
    with tab2:
        st.markdown("### ABD Hisseleri")
        for i, stock in enumerate(config.us_stocks):
            col1, col2, col3 = st.columns([2, 2, 1])
            with col1:
                config.us_stocks[i]['ticker'] = st.text_input(f"Ticker {i}", stock['ticker'], key=f"us_ticker_{i}")
            with col2:
                config.us_stocks[i]['shares'] = st.number_input(f"Adet {i}", stock['shares'], key=f"us_shares_{i}")
            with col3:
                config.us_stocks[i]['target_weight'] = st.number_input(f"Hedef % {i}", stock.get('target_weight', 0), key=f"us_weight_{i}")
    
    with tab3:
        st.markdown("### Kripto")
        for i, crypto in enumerate(config.crypto):
            col1, col2, col3 = st.columns([2, 2, 1])
            with col1:
                config.crypto[i]['symbol'] = st.text_input(f"Symbol {i}", crypto['symbol'], key=f"crypto_symbol_{i}")
            with col2:
                config.crypto[i]['amount'] = st.number_input(f"Miktar {i}", crypto['amount'], key=f"crypto_amount_{i}")
            with col3:
                config.crypto[i]['target_weight'] = st.number_input(f"Hedef % {i}", crypto.get('target_weight', 0), key=f"crypto_weight_{i}")
    
    with tab4:
        st.markdown("### USD Nakit")
        for i, cash in enumerate(config.cash):
            col1, col2 = st.columns([2, 2])
            with col1:
                config.cash[i]['code'] = st.text_input(f"Kod {i}", cash['code'], key=f"cash_code_{i}")
            with col2:
                config.cash[i]['amount'] = st.number_input(f"Miktar {i}", cash['amount'], key=f"cash_amount_{i}")
    
    st.markdown("---")
    if st.button("💾 Tümünü Kaydet", type="primary"):
        if save_config_to_cloud(config):
            st.success("✅ Kaydedildi!")
            st.session_state.portfolio = Portfolio(config)
        else:
            st.error("Kaydetme hatası!")


# =============================================================================
# AYARLAR
# =============================================================================

def render_settings_page():
    """Ayarlar sayfası."""
    st.markdown("## ⚙️ Ayarlar")
    
    user = get_current_user()
    if user:
        st.markdown(f"**Kullanıcı:** {user.get('email', 'N/A')}")
        st.markdown(f"**ID:** {user.get('id', 'N/A')}")
    
    st.markdown("---")
    
    st.markdown("### 📸 Snapshot Yönetimi")
    snapshot_count = len(st.session_state.snapshots)
    st.write(f"Toplam snapshot: **{snapshot_count}**")
    
    if st.button("🗑️ Tüm Snapshot'ları Sil", type="secondary"):
        if user and delete_all_snapshots(user['id']):
            st.session_state.snapshots = []
            st.success("Silindi!")
            st.rerun()


# =============================================================================
# DASHBOARD
# =============================================================================

def render_dashboard_page():
    """Dashboard ana sayfası."""
    st.markdown('<h1 class="main-title">📊 Portföy Dashboard</h1>', unsafe_allow_html=True)
    
    portfolio = st.session_state.portfolio
    
    if not portfolio:
        st.info("👈 Sol menüden **Yükle** butonuna basın.")
        return
    
    if not portfolio.assets or not any(a.is_valid for a in portfolio.assets):
        st.warning("⚠️ Varlık verisi yok. **Güncelle** butonuna basın.")
        return
    
    render_metric_cards(portfolio)
    st.markdown("---")
    
    tab1, tab2 = st.tabs(["📋 Varlıklar", "📊 Grafikler"])
    with tab1: render_asset_table(portfolio)
    with tab2: render_charts(portfolio)


# =============================================================================
# MAIN
# =============================================================================

def main():
    """Ana uygulama."""
    init_session_state()
    
    # OAuth callback kontrolü
    handle_oauth_callback()
    
    # Login kontrolü
    if not is_logged_in():
        render_login_page()
        return
    
    # İlk yüklemede config'i çek
    if st.session_state.config is None:
        st.session_state.config = load_config_from_cloud()
        st.session_state.portfolio = Portfolio(st.session_state.config)
        st.session_state.snapshots = load_snapshots_from_cloud()
    
    # Sidebar
    render_sidebar()
    
    # Sayfa yönlendirme
    page = st.session_state.current_page
    
    if page == "dashboard":
        render_dashboard_page()
    elif page == "assets":
        render_asset_management_page()
    elif page == "risk":
        render_risk_analysis_page()
    elif page == "benchmark":
        render_benchmark_page()
    elif page == "weekly":
        render_weekly_report_page()
    elif page == "settings":
        render_settings_page()


if __name__ == "__main__":
    main()
