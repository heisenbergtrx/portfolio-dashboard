"""
dashboard.py - Barbarians Portfolio Dashboard (v6)
==================================================

Supabase ile:
- Email Authentication
- Kalıcı portföy config'i
- Kalıcı haftalık snapshot'lar
- Benchmark karşılaştırma

Kullanım:
    streamlit run dashboard.py

Yazar: Barbarians Trading
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
    page_title="Barbarians Portfolio Management",
    page_icon="⚔️",
    layout="wide",
    initial_sidebar_state="expanded"
)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


# =============================================================================
# BARBARIANS PREMIUM THEME
# =============================================================================

BARBARIANS_THEME = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;500;600;700&display=swap');

:root {
    --bg-primary: #0a0a0f;
    --bg-secondary: #12121a;
    --bg-tertiary: #1a1a25;
    --bg-card: #16161f;
    --bg-card-hover: #1c1c28;
    --accent-primary: #d4a853;
    --accent-secondary: #b8923a;
    --accent-tertiary: #e8c068;
    --accent-glow: rgba(212, 168, 83, 0.15);
    --text-primary: #f5f5f7;
    --text-secondary: #a8a8b3;
    --text-muted: #6b6b78;
    --success: #4ade80;
    --success-bg: rgba(74, 222, 128, 0.1);
    --danger: #f87171;
    --danger-bg: rgba(248, 113, 113, 0.1);
    --border-subtle: rgba(255, 255, 255, 0.06);
    --border-accent: rgba(212, 168, 83, 0.3);
    --radius-md: 12px;
    --radius-lg: 16px;
    --radius-xl: 24px;
}

#MainMenu {visibility: hidden;}
footer {visibility: hidden;}
header {visibility: hidden;}
.stDeployButton {display: none;}

.stApp {
    background: var(--bg-primary) !important;
    font-family: 'Outfit', -apple-system, BlinkMacSystemFont, sans-serif !important;
}

.stApp::before {
    content: '';
    position: fixed;
    top: 0; left: 0; right: 0; bottom: 0;
    background: 
        radial-gradient(ellipse at 20% 0%, rgba(212, 168, 83, 0.03) 0%, transparent 50%),
        radial-gradient(ellipse at 80% 100%, rgba(212, 168, 83, 0.02) 0%, transparent 50%);
    pointer-events: none;
    z-index: 0;
}

.block-container {
    padding-top: 2rem !important;
    padding-bottom: 2rem !important;
    max-width: 1400px !important;
}

h1, h2, h3, h4, h5, h6, p, span, div, label {
    font-family: 'Outfit', sans-serif !important;
}

::-webkit-scrollbar { width: 8px; height: 8px; }
::-webkit-scrollbar-track { background: var(--bg-secondary); border-radius: 4px; }
::-webkit-scrollbar-thumb { background: var(--bg-tertiary); border-radius: 4px; }
::-webkit-scrollbar-thumb:hover { background: var(--accent-secondary); }

.main-title {
    font-size: 1.5rem !important;
    font-weight: 700 !important;
    background: linear-gradient(135deg, #f5f5f7 0%, #e8c068 100%);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
}

.positive { color: var(--success) !important; }
.negative { color: var(--danger) !important; }

.user-badge {
    background: var(--accent-glow) !important;
    border: 1px solid var(--border-accent);
    color: var(--text-primary) !important;
    padding: 10px 15px;
    border-radius: 12px;
    font-size: 0.8rem;
}

section[data-testid="stSidebar"] {
    background: var(--bg-secondary) !important;
    border-right: 1px solid var(--border-subtle) !important;
}

.stButton > button {
    background: linear-gradient(135deg, var(--accent-primary) 0%, var(--accent-secondary) 100%) !important;
    color: var(--bg-primary) !important;
    border: none !important;
    border-radius: var(--radius-md) !important;
    font-weight: 600 !important;
    font-family: 'Outfit', sans-serif !important;
    box-shadow: 0 4px 12px rgba(212, 168, 83, 0.2) !important;
    transition: all 0.2s ease !important;
}

.stButton > button:hover {
    transform: translateY(-2px) !important;
    box-shadow: 0 6px 20px rgba(212, 168, 83, 0.3) !important;
}

.stButton > button[kind="secondary"] {
    background: transparent !important;
    color: var(--text-secondary) !important;
    border: 1px solid var(--border-subtle) !important;
    box-shadow: none !important;
}

.stButton > button[kind="secondary"]:hover {
    background: var(--bg-tertiary) !important;
    border-color: var(--border-accent) !important;
}

.stTextInput > div > div > input,
.stNumberInput > div > div > input,
.stSelectbox > div > div > div {
    background: var(--bg-tertiary) !important;
    border: 1px solid var(--border-subtle) !important;
    border-radius: var(--radius-md) !important;
    color: var(--text-primary) !important;
    font-family: 'Outfit', sans-serif !important;
}

.stTextInput > div > div > input:focus,
.stNumberInput > div > div > input:focus {
    border-color: var(--accent-primary) !important;
    box-shadow: 0 0 0 3px var(--accent-glow) !important;
}

.stTextInput > label,
.stNumberInput > label,
.stSelectbox > label {
    color: var(--text-secondary) !important;
    font-size: 0.75rem !important;
    text-transform: uppercase !important;
    letter-spacing: 0.05em !important;
}

.stTabs [data-baseweb="tab-list"] {
    background: var(--bg-tertiary) !important;
    border-radius: var(--radius-lg) !important;
    padding: 0.25rem !important;
}

.stTabs [data-baseweb="tab"] {
    background: transparent !important;
    border-radius: var(--radius-md) !important;
    color: var(--text-secondary) !important;
    font-family: 'Outfit', sans-serif !important;
}

.stTabs [data-baseweb="tab"]:hover {
    background: var(--bg-card) !important;
}

.stTabs [aria-selected="true"] {
    background: var(--accent-glow) !important;
    color: var(--accent-primary) !important;
}

.stDataFrame {
    border: 1px solid var(--border-subtle) !important;
    border-radius: var(--radius-lg) !important;
    overflow: hidden !important;
}

[data-testid="stDataFrame"] > div {
    background: var(--bg-card) !important;
}

[data-testid="stMetricValue"] {
    font-family: 'Outfit', sans-serif !important;
    font-weight: 700 !important;
    color: var(--text-primary) !important;
}

[data-testid="stMetricLabel"] {
    text-transform: uppercase !important;
    letter-spacing: 0.05em !important;
    color: var(--text-muted) !important;
    font-size: 0.75rem !important;
}

[data-testid="stMetricDelta"] {
    font-family: 'Outfit', sans-serif !important;
}

hr {
    border: none !important;
    height: 1px !important;
    background: linear-gradient(90deg, transparent, var(--border-subtle), var(--border-accent), var(--border-subtle), transparent) !important;
}

.streamlit-expanderHeader {
    background: var(--bg-tertiary) !important;
    border: 1px solid var(--border-subtle) !important;
    border-radius: var(--radius-md) !important;
}

.stAlert {
    background: var(--bg-card) !important;
    border: 1px solid var(--border-subtle) !important;
    border-radius: var(--radius-lg) !important;
}
</style>
"""

# Chart colors for Barbarians theme
CHART_COLORS = {
    'primary': '#d4a853',
    'secondary': '#b8923a',
    'tertiary': '#e8c068',
    'success': '#4ade80',
    'danger': '#f87171',
    'text': '#f5f5f7',
    'grid': 'rgba(255, 255, 255, 0.06)'
}

PIE_COLORS = ['#d4a853', '#e8c068', '#4ade80', '#60a5fa', '#fbbf24', '#b8923a', '#f87171']

st.markdown(BARBARIANS_THEME, unsafe_allow_html=True)


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
        st.session_state.snapshots = load_snapshots_from_cloud()
    
    return success


# =============================================================================
# SIDEBAR
# =============================================================================

def render_sidebar():
    """Sidebar'ı render et."""
    with st.sidebar:
        # Barbarians Brand
        st.markdown("""
        <div style="display: flex; align-items: center; gap: 0.75rem; padding: 0.5rem; margin-bottom: 1rem;">
            <div style="width: 32px; height: 32px; background: linear-gradient(135deg, #d4a853, #b8923a); border-radius: 8px; display: flex; align-items: center; justify-content: center; font-size: 1rem;">⚔️</div>
            <div style="font-size: 1rem; font-weight: 700; color: #d4a853;">Barbarians</div>
        </div>
        """, unsafe_allow_html=True)
        
        # Kullanıcı bilgisi
        user = get_current_user()
        if user:
            user_name = user.get('name', user.get('email', 'Kullanıcı'))
            st.markdown(f"""
            <div class="user-badge">
                <div style="font-size: 0.5625rem; color: #6b6b78; text-transform: uppercase; letter-spacing: 0.1em;">Signed in as</div>
                <div style="font-size: 0.75rem; color: #f5f5f7; font-weight: 500; margin-top: 2px;">👤 {user_name}</div>
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
        st.info("Varlık bulunamadı. Varlık Yönetimi sayfasından varlık ekleyin.")
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
                if val > 0: return 'color: #4ade80'
                elif val < 0: return 'color: #f87171'
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
                    color_discrete_sequence=PIE_COLORS)
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
    colors = ['#4ade80' if x >= 0 else '#f87171' for x in df_sorted['Haftalık (%)']]
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
            colors = ['#f87171' if x > 20 else '#fbbf24' if x > 15 else '#4ade80' for x in position_df['Ağırlık (%)']]
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
                                    fillcolor='rgba(248, 113, 113, 0.2)', line=dict(color='#f87171', width=2)))
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
                            line=dict(color='#d4a853', width=3), marker=dict(size=8),
                            fill='tozeroy', fillcolor='rgba(212, 168, 83, 0.1)'))
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
# VARLIK YÖNETİMİ (Düzeltilmiş - Varlık Ekleme Destekli)
# =============================================================================

def render_asset_management_page():
    """Varlık yönetimi sayfası - Ekleme destekli."""
    st.markdown("## 📦 Varlık Yönetimi")
    
    config = st.session_state.config
    if not config:
        st.warning("Önce sol menüden **Yükle** butonuna basın.")
        return
    
    tab1, tab2, tab3, tab4 = st.tabs(["🏦 TEFAS", "🇺🇸 ABD Hisse", "₿ Kripto", "💵 Nakit"])
    
    # ========== TEFAS ==========
    with tab1:
        st.markdown("### TEFAS Fonları")
        
        if not config.tefas_funds:
            st.info("Henüz TEFAS fonu eklenmemiş.")
        
        for i, fund in enumerate(config.tefas_funds):
            col1, col2, col3, col4 = st.columns([2, 2, 1, 0.5])
            with col1:
                config.tefas_funds[i]['code'] = st.text_input(
                    f"Kod", fund['code'], key=f"tefas_code_{i}", label_visibility="collapsed",
                    placeholder="Örn: TCD"
                )
            with col2:
                config.tefas_funds[i]['shares'] = st.number_input(
                    f"Adet", float(fund['shares']), key=f"tefas_shares_{i}", label_visibility="collapsed",
                    min_value=0.0, step=1.0
                )
            with col3:
                config.tefas_funds[i]['target_weight'] = st.number_input(
                    f"Hedef %", float(fund.get('target_weight', 0)), key=f"tefas_weight_{i}", 
                    label_visibility="collapsed", min_value=0.0, max_value=100.0
                )
            with col4:
                if st.button("🗑️", key=f"del_tefas_{i}", help="Sil"):
                    config.tefas_funds.pop(i)
                    st.rerun()
        
        # Yeni TEFAS Ekle
        st.markdown("---")
        with st.expander("➕ Yeni TEFAS Fonu Ekle"):
            col1, col2, col3 = st.columns([2, 2, 1])
            with col1:
                new_tefas_code = st.text_input("Fon Kodu", placeholder="Örn: TCD, AFT", key="new_tefas_code")
            with col2:
                new_tefas_shares = st.number_input("Adet", min_value=0.0, step=1.0, key="new_tefas_shares")
            with col3:
                new_tefas_weight = st.number_input("Hedef %", min_value=0.0, max_value=100.0, key="new_tefas_weight")
            
            if st.button("✅ TEFAS Ekle", key="add_tefas"):
                if new_tefas_code:
                    config.tefas_funds.append({
                        'code': new_tefas_code.upper(),
                        'shares': new_tefas_shares,
                        'target_weight': new_tefas_weight
                    })
                    st.success(f"✅ {new_tefas_code.upper()} eklendi!")
                    st.rerun()
                else:
                    st.error("Fon kodu gerekli!")
    
    # ========== ABD HİSSE ==========
    with tab2:
        st.markdown("### ABD Hisseleri")
        
        if not config.us_stocks:
            st.info("Henüz ABD hissesi eklenmemiş.")
        
        for i, stock in enumerate(config.us_stocks):
            col1, col2, col3, col4 = st.columns([2, 2, 1, 0.5])
            with col1:
                config.us_stocks[i]['ticker'] = st.text_input(
                    f"Ticker", stock['ticker'], key=f"us_ticker_{i}", label_visibility="collapsed",
                    placeholder="Örn: AAPL"
                )
            with col2:
                config.us_stocks[i]['shares'] = st.number_input(
                    f"Adet", float(stock['shares']), key=f"us_shares_{i}", label_visibility="collapsed",
                    min_value=0.0, step=0.01
                )
            with col3:
                config.us_stocks[i]['target_weight'] = st.number_input(
                    f"Hedef %", float(stock.get('target_weight', 0)), key=f"us_weight_{i}",
                    label_visibility="collapsed", min_value=0.0, max_value=100.0
                )
            with col4:
                if st.button("🗑️", key=f"del_us_{i}", help="Sil"):
                    config.us_stocks.pop(i)
                    st.rerun()
        
        # Yeni ABD Hisse Ekle
        st.markdown("---")
        with st.expander("➕ Yeni ABD Hissesi Ekle"):
            col1, col2, col3 = st.columns([2, 2, 1])
            with col1:
                new_us_ticker = st.text_input("Ticker", placeholder="Örn: AAPL, GOOGL, MSFT", key="new_us_ticker")
            with col2:
                new_us_shares = st.number_input("Adet", min_value=0.0, step=0.01, key="new_us_shares")
            with col3:
                new_us_weight = st.number_input("Hedef %", min_value=0.0, max_value=100.0, key="new_us_weight")
            
            if st.button("✅ Hisse Ekle", key="add_us"):
                if new_us_ticker:
                    config.us_stocks.append({
                        'ticker': new_us_ticker.upper(),
                        'shares': new_us_shares,
                        'target_weight': new_us_weight
                    })
                    st.success(f"✅ {new_us_ticker.upper()} eklendi!")
                    st.rerun()
                else:
                    st.error("Ticker gerekli!")
    
    # ========== KRİPTO ==========
    with tab3:
        st.markdown("### Kripto Varlıklar")
        
        if not config.crypto:
            st.info("Henüz kripto varlık eklenmemiş.")
        
        for i, crypto in enumerate(config.crypto):
            col1, col2, col3, col4 = st.columns([2, 2, 1, 0.5])
            with col1:
                config.crypto[i]['symbol'] = st.text_input(
                    f"Symbol", crypto['symbol'], key=f"crypto_symbol_{i}", label_visibility="collapsed",
                    placeholder="Örn: BTC"
                )
            with col2:
                config.crypto[i]['amount'] = st.number_input(
                    f"Miktar", float(crypto['amount']), key=f"crypto_amount_{i}", label_visibility="collapsed",
                    min_value=0.0, step=0.0001, format="%.4f"
                )
            with col3:
                config.crypto[i]['target_weight'] = st.number_input(
                    f"Hedef %", float(crypto.get('target_weight', 0)), key=f"crypto_weight_{i}",
                    label_visibility="collapsed", min_value=0.0, max_value=100.0
                )
            with col4:
                if st.button("🗑️", key=f"del_crypto_{i}", help="Sil"):
                    config.crypto.pop(i)
                    st.rerun()
        
        # Yeni Kripto Ekle
        st.markdown("---")
        with st.expander("➕ Yeni Kripto Ekle"):
            col1, col2, col3 = st.columns([2, 2, 1])
            with col1:
                new_crypto_symbol = st.text_input("Symbol", placeholder="Örn: BTC, ETH, SOL", key="new_crypto_symbol")
            with col2:
                new_crypto_amount = st.number_input("Miktar", min_value=0.0, step=0.0001, format="%.4f", key="new_crypto_amount")
            with col3:
                new_crypto_weight = st.number_input("Hedef %", min_value=0.0, max_value=100.0, key="new_crypto_weight")
            
            if st.button("✅ Kripto Ekle", key="add_crypto"):
                if new_crypto_symbol:
                    config.crypto.append({
                        'symbol': new_crypto_symbol.upper(),
                        'amount': new_crypto_amount,
                        'target_weight': new_crypto_weight
                    })
                    st.success(f"✅ {new_crypto_symbol.upper()} eklendi!")
                    st.rerun()
                else:
                    st.error("Symbol gerekli!")
    
    # ========== NAKİT ==========
    with tab4:
        st.markdown("### Nakit Varlıklar")
        
        if not config.cash:
            st.info("Henüz nakit varlık eklenmemiş.")
        
        for i, cash in enumerate(config.cash):
            col1, col2, col3 = st.columns([2, 2, 0.5])
            with col1:
                config.cash[i]['code'] = st.text_input(
                    f"Kod", cash['code'], key=f"cash_code_{i}", label_visibility="collapsed",
                    placeholder="Örn: USD"
                )
            with col2:
                config.cash[i]['amount'] = st.number_input(
                    f"Miktar", float(cash['amount']), key=f"cash_amount_{i}", label_visibility="collapsed",
                    min_value=0.0, step=1.0
                )
            with col3:
                if st.button("🗑️", key=f"del_cash_{i}", help="Sil"):
                    config.cash.pop(i)
                    st.rerun()
        
        # Yeni Nakit Ekle
        st.markdown("---")
        with st.expander("➕ Yeni Nakit Ekle"):
            col1, col2 = st.columns([2, 2])
            with col1:
                new_cash_code = st.text_input("Kod", placeholder="Örn: USD, DLY, DIP", key="new_cash_code")
            with col2:
                new_cash_amount = st.number_input("Miktar", min_value=0.0, step=1.0, key="new_cash_amount")
            
            if st.button("✅ Nakit Ekle", key="add_cash"):
                if new_cash_code:
                    config.cash.append({
                        'code': new_cash_code.upper(),
                        'amount': new_cash_amount
                    })
                    st.success(f"✅ {new_cash_code.upper()} eklendi!")
                    st.rerun()
                else:
                    st.error("Kod gerekli!")
    
    # ========== KAYDET ==========
    st.markdown("---")
    col1, col2 = st.columns([3, 1])
    with col1:
        if st.button("💾 Tümünü Kaydet", type="primary", use_container_width=True):
            if save_config_to_cloud(config):
                st.success("✅ Portföy kaydedildi!")
                st.session_state.portfolio = Portfolio(config)
            else:
                st.error("Kaydetme hatası!")
    
    with col2:
        # Özet
        total_assets = len(config.tefas_funds) + len(config.us_stocks) + len(config.crypto) + len(config.cash)
        st.metric("Toplam Varlık", total_assets)


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
    # Barbarians Header
    st.markdown("""
    <div style="background: linear-gradient(135deg, #12121a 0%, #16161f 100%); border: 1px solid rgba(255, 255, 255, 0.06); border-radius: 24px; padding: 1.5rem 2rem; margin-bottom: 1.5rem; position: relative; overflow: hidden;">
        <div style="position: absolute; top: 0; left: 0; right: 0; height: 3px; background: linear-gradient(90deg, transparent, #d4a853, #e8c068, #d4a853, transparent);"></div>
        <div style="display: flex; align-items: center; gap: 1rem;">
            <div style="width: 44px; height: 44px; background: #1a1a25; border-radius: 12px; display: flex; align-items: center; justify-content: center; font-size: 1.5rem;">⚔️</div>
            <div>
                <h1 style="font-size: 1.375rem !important; font-weight: 700 !important; background: linear-gradient(135deg, #f5f5f7 0%, #e8c068 100%); -webkit-background-clip: text; -webkit-text-fill-color: transparent; margin: 0 !important;">Barbarians Portfolio Management</h1>
                <p style="font-size: 0.6875rem !important; color: #6b6b78 !important; letter-spacing: 0.1em; text-transform: uppercase; margin: 0 !important;">Risk-First Investment Analysis</p>
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)
    
    portfolio = st.session_state.portfolio
    
    if not portfolio:
        st.info("👈 Sol menüden **Yükle** butonuna basın.")
        return
    
    if not portfolio.assets or not any(a.is_valid for a in portfolio.assets):
        st.warning("⚠️ Varlık verisi yok. **Güncelle** butonuna basın veya **Varlık Yönetimi**'nden varlık ekleyin.")
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
    
    # OAuth callback kontrolü (artık kullanılmıyor ama uyumluluk için)
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
