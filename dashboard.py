"""
dashboard.py - Barbarians Portfolio Dashboard (v7)
==================================================

Supabase ile:
- Email Authentication
- Kalici portfolio config'i
- Kalici haftalik snapshot'lar
- Benchmark karsilastirma

Kullanim:
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

from benchmark import render_benchmark_tab

# =============================================================================
# SAYFA AYARLARI
# =============================================================================

st.set_page_config(
    page_title="Barbarians Portfolio",
    page_icon="B",
    layout="wide",
    initial_sidebar_state="expanded"
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# =============================================================================
# THEME
# =============================================================================

THEME_CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;500;600;700&display=swap');

:root {
    --bg-primary: #0a0a0f;
    --bg-secondary: #12121a;
    --bg-card: #16161f;
    --accent-primary: #d4a853;
    --accent-secondary: #b8923a;
    --text-primary: #f5f5f7;
    --text-secondary: #a8a8b3;
    --text-muted: #6b6b78;
    --success: #4ade80;
    --danger: #f87171;
    --border-subtle: rgba(255, 255, 255, 0.06);
}

#MainMenu {visibility: hidden;}
footer {visibility: hidden;}
header {visibility: hidden;}
.stDeployButton {display: none;}

.stApp {
    background: var(--bg-primary) !important;
    font-family: 'Outfit', sans-serif !important;
}

section[data-testid="stSidebar"] {
    background: var(--bg-secondary) !important;
}

.stButton > button {
    background: linear-gradient(135deg, var(--accent-primary), var(--accent-secondary)) !important;
    color: var(--bg-primary) !important;
    border: none !important;
    border-radius: 12px !important;
    font-weight: 600 !important;
}

.stTextInput > div > div > input,
.stNumberInput > div > div > input {
    background: #1a1a25 !important;
    border: 1px solid var(--border-subtle) !important;
    border-radius: 8px !important;
    color: var(--text-primary) !important;
}
</style>
"""

PIE_COLORS = ['#d4a853', '#e8c068', '#4ade80', '#60a5fa', '#fbbf24', '#b8923a', '#f87171']

st.markdown(THEME_CSS, unsafe_allow_html=True)


# =============================================================================
# SESSION STATE
# =============================================================================

def init_session_state():
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
    # Add form toggles
    if 'show_add_tefas' not in st.session_state:
        st.session_state.show_add_tefas = False
    if 'show_add_us' not in st.session_state:
        st.session_state.show_add_us = False
    if 'show_add_crypto' not in st.session_state:
        st.session_state.show_add_crypto = False
    if 'show_add_cash' not in st.session_state:
        st.session_state.show_add_cash = False


# =============================================================================
# CONFIG YONETIMI
# =============================================================================

def save_config_to_cloud(config: PortfolioConfig) -> bool:
    user = get_current_user()
    if not user:
        return False
    config_dict = config_to_dict(config)
    return save_portfolio_config(user['id'], config_dict)


def load_config_from_cloud() -> PortfolioConfig:
    user = get_current_user()
    if not user:
        return PortfolioConfig()
    config_dict = load_portfolio_config(user['id'])
    if config_dict:
        return dict_to_config(config_dict)
    return PortfolioConfig()


def load_snapshots_from_cloud() -> list:
    user = get_current_user()
    if not user:
        return []
    return load_snapshots(user['id'])


def save_snapshot_to_cloud(total_value: float, assets: dict) -> bool:
    user = get_current_user()
    if not user:
        return False
    return save_snapshot(user['id'], total_value, assets)


def take_snapshot_if_needed(portfolio: Portfolio) -> bool:
    user = get_current_user()
    if not user or not should_take_weekly_snapshot(user['id']):
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
    with st.sidebar:
        st.markdown("## Barbarians")
        
        user = get_current_user()
        if user:
            st.info(f"Kullanici: {user.get('email', 'N/A')}")
            if st.button("Cikis", use_container_width=True):
                logout()
        
        st.markdown("---")
        st.markdown("### Navigasyon")
        
        pages = [
            ("dashboard", "Dashboard"),
            ("assets", "Varlik Yonetimi"),
            ("risk", "Risk Analizi"),
            ("benchmark", "Benchmark"),
            ("weekly", "Haftalik Rapor"),
            ("settings", "Ayarlar"),
        ]
        
        for page_id, page_name in pages:
            btn_type = "primary" if st.session_state.current_page == page_id else "secondary"
            if st.button(page_name, use_container_width=True, type=btn_type, key=f"nav_{page_id}"):
                st.session_state.current_page = page_id
                st.rerun()
        
        st.markdown("---")
        
        if st.session_state.current_page == "dashboard":
            st.markdown("### Islemler")
            col1, col2 = st.columns(2)
            with col1:
                if st.button("Yukle", use_container_width=True):
                    with st.spinner("Yukleniyor..."):
                        st.session_state.config = load_config_from_cloud()
                        st.session_state.portfolio = Portfolio(st.session_state.config)
                        st.session_state.snapshots = load_snapshots_from_cloud()
                        st.success("OK")
            with col2:
                if st.button("Guncelle", use_container_width=True, type="primary"):
                    if st.session_state.portfolio:
                        with st.spinner("Fiyatlar..."):
                            success = st.session_state.portfolio.refresh_prices()
                            if success:
                                st.session_state.last_refresh = datetime.now()
                                take_snapshot_if_needed(st.session_state.portfolio)
                                st.success("OK")
        
        if st.session_state.last_refresh:
            st.caption(f"Son: {st.session_state.last_refresh.strftime('%H:%M:%S')}")
        
        if st.session_state.config:
            st.markdown("### Ozet")
            cfg = st.session_state.config
            col1, col2 = st.columns(2)
            with col1:
                st.metric("TEFAS", len(cfg.tefas_funds))
                st.metric("Kripto", len(cfg.crypto))
            with col2:
                st.metric("ABD", len(cfg.us_stocks))
                st.metric("Nakit", len(cfg.cash))


# =============================================================================
# METRIK KARTLARI
# =============================================================================

def render_metric_cards(portfolio):
    metrics = portfolio.metrics
    col1, col2, col3, col4, col5 = st.columns(5)
    
    with col1:
        st.metric("Toplam", format_currency(metrics.total_value_try))
    with col2:
        st.metric("Haftalik", format_percentage(metrics.weekly_return_pct))
    with col3:
        st.metric("Nakit", format_currency(metrics.cash_reserve_try))
    with col4:
        sharpe = metrics.sharpe_ratio
        st.metric("Sharpe", f"{sharpe:.2f}" if sharpe else "N/A")
    with col5:
        vol = metrics.volatility_monthly
        st.metric("Volatilite", f"{vol:.1f}%" if vol else "N/A")


# =============================================================================
# VARLIK TABLOSU
# =============================================================================

def render_asset_table(portfolio):
    st.markdown("### Varlik Listesi")
    
    df = portfolio.get_summary_dataframe()
    if df.empty:
        st.info("Varlik bulunamadi. Varlik Yonetimi sayfasindan varlik ekleyin.")
        return
    
    display_cols = ['Kod', 'Tur', 'Adet', 'Fiyat', 'Deger (TRY)', 'Agirlik (%)', 'Haftalik (%)']
    available_cols = [c for c in display_cols if c in df.columns]
    
    # Rename columns if needed
    rename_map = {
        'Tür': 'Tur',
        'Değer (TRY)': 'Deger (TRY)',
        'Ağırlık (%)': 'Agirlik (%)',
        'Haftalık (%)': 'Haftalik (%)'
    }
    df = df.rename(columns=rename_map)
    available_cols = [c for c in display_cols if c in df.columns]
    
    st.dataframe(df[available_cols], use_container_width=True, hide_index=True)


# =============================================================================
# GRAFIKLER
# =============================================================================

def render_charts(portfolio):
    df = portfolio.get_summary_dataframe()
    
    # Rename for consistency
    if 'Değer (TRY)' in df.columns:
        df = df.rename(columns={'Değer (TRY)': 'Deger_TRY', 'Tür': 'Tur'})
    elif 'Deger (TRY)' in df.columns:
        df = df.rename(columns={'Deger (TRY)': 'Deger_TRY'})
    
    if 'Deger_TRY' not in df.columns:
        st.warning("Grafik icin yeterli veri yok.")
        return
    
    valid_df = df[df['Deger_TRY'] > 0].copy()
    if valid_df.empty:
        return
    
    st.markdown("### Portfolio Dagilimi")
    
    col1, col2 = st.columns(2)
    
    with col1:
        fig = px.pie(valid_df, values='Deger_TRY', names='Kod', title='Varlik Dagilimi',
                    color_discrete_sequence=PIE_COLORS)
        fig.update_traces(textposition='inside', textinfo='percent+label')
        st.plotly_chart(fig, use_container_width=True)
    
    with col2:
        if 'Tur' in valid_df.columns:
            type_df = valid_df.groupby('Tur')['Deger_TRY'].sum().reset_index()
            fig = px.pie(type_df, values='Deger_TRY', names='Tur', title='Tur Dagilimi',
                        color_discrete_sequence=PIE_COLORS)
            fig.update_traces(textposition='inside', textinfo='percent+label')
            st.plotly_chart(fig, use_container_width=True)


# =============================================================================
# RISK ANALIZI
# =============================================================================

def render_risk_analysis_page():
    st.markdown("## Risk Analizi")
    
    portfolio = st.session_state.portfolio
    if not portfolio or not portfolio.assets:
        st.warning("Once portfolyoyu yukleyin ve guncelleyin.")
        return
    
    valid_assets = [a for a in portfolio.assets if a.is_valid]
    if valid_assets:
        st.markdown("### Position Sizing")
        
        position_data = [{'Kod': a.code, 'Agirlik': a.actual_weight} for a in valid_assets]
        position_df = pd.DataFrame(position_data).sort_values('Agirlik', ascending=False)
        
        colors = ['#f87171' if x > 20 else '#fbbf24' if x > 15 else '#4ade80' for x in position_df['Agirlik']]
        fig = go.Figure()
        fig.add_trace(go.Bar(x=position_df['Kod'], y=position_df['Agirlik'], marker_color=colors,
                            text=[f"{v:.1f}%" for v in position_df['Agirlik']], textposition='outside'))
        fig.add_hline(y=20, line_dash="dash", line_color="red", annotation_text="Max 20%")
        st.plotly_chart(fig, use_container_width=True)


# =============================================================================
# HAFTALIK RAPOR
# =============================================================================

def render_weekly_report_page():
    st.markdown("## Haftalik Buyume Raporu")
    
    snapshots = st.session_state.snapshots
    
    if not snapshots:
        st.info("Henuz snapshot yok.")
        if st.session_state.portfolio and st.session_state.portfolio.assets:
            if st.button("Manuel Snapshot Al", type="primary"):
                assets_summary = {a.code: {'value_try': a.value_try, 'shares': a.shares, 'price': a.current_price} 
                                 for a in st.session_state.portfolio.assets if a.is_valid}
                if save_snapshot_to_cloud(st.session_state.portfolio.metrics.total_value_try, assets_summary):
                    st.success("Snapshot alindi!")
                    st.session_state.snapshots = load_snapshots_from_cloud()
                    st.rerun()
        return
    
    df = pd.DataFrame([{
        'Tarih': datetime.fromisoformat(s['created_at'].replace('Z', '+00:00')).strftime('%Y-%m-%d'),
        'Deger': float(s['total_value_try'])
    } for s in snapshots])
    
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=df['Tarih'], y=df['Deger'], mode='lines+markers',
                            line=dict(color='#d4a853', width=3)))
    st.plotly_chart(fig, use_container_width=True)


# =============================================================================
# BENCHMARK
# =============================================================================

def render_benchmark_page():
    st.markdown("## Benchmark Karsilastirma")
    render_benchmark_tab(st.session_state.snapshots)


# =============================================================================
# VARLIK YONETIMI
# =============================================================================

def safe_float(value, default=0.0):
    """Guvenli float donusumu."""
    if value is None:
        return default
    try:
        return float(value)
    except (ValueError, TypeError):
        return default


def safe_str(value, default=''):
    """Guvenli string donusumu."""
    if value is None:
        return default
    return str(value)


def render_asset_management_page():
    st.markdown("## Varlik Yonetimi")
    
    config = st.session_state.config
    if not config:
        st.warning("Once sol menuden Yukle butonuna basin.")
        return
    
    tab1, tab2, tab3, tab4 = st.tabs(["TEFAS", "ABD Hisse", "Kripto", "Nakit"])
    
    # ========== TEFAS ==========
    with tab1:
        st.markdown("### TEFAS Fonlari")
        
        if not config.tefas_funds:
            st.info("Henuz TEFAS fonu eklenmemis.")
        else:
            for i, fund in enumerate(list(config.tefas_funds)):
                col1, col2, col3, col4 = st.columns([2, 2, 1, 0.5])
                with col1:
                    new_code = st.text_input("Kod", safe_str(fund.get('code') if isinstance(fund, dict) else getattr(fund, 'code', '')), 
                                            key=f"tefas_code_{i}", label_visibility="collapsed")
                    if isinstance(fund, dict):
                        config.tefas_funds[i]['code'] = new_code
                with col2:
                    shares_val = fund.get('shares', 0) if isinstance(fund, dict) else getattr(fund, 'shares', 0)
                    new_shares = st.number_input("Adet", safe_float(shares_val), key=f"tefas_shares_{i}", 
                                                label_visibility="collapsed", min_value=0.0, step=1.0)
                    if isinstance(fund, dict):
                        config.tefas_funds[i]['shares'] = new_shares
                with col3:
                    weight_val = fund.get('target_weight', 0) if isinstance(fund, dict) else getattr(fund, 'target_weight', 0)
                    new_weight = st.number_input("Hedef", safe_float(weight_val), key=f"tefas_weight_{i}", 
                                                label_visibility="collapsed", min_value=0.0, max_value=100.0)
                    if isinstance(fund, dict):
                        config.tefas_funds[i]['target_weight'] = new_weight
                with col4:
                    if st.button("Sil", key=f"del_tefas_{i}"):
                        config.tefas_funds.pop(i)
                        st.rerun()
        
        st.markdown("---")
        if st.button("+ TEFAS Ekle", key="btn_add_tefas"):
            st.session_state.show_add_tefas = not st.session_state.show_add_tefas
        
        if st.session_state.show_add_tefas:
            col1, col2, col3 = st.columns([2, 2, 1])
            with col1:
                new_code = st.text_input("Fon Kodu", key="new_tefas_code")
            with col2:
                new_shares = st.number_input("Adet", min_value=0.0, step=1.0, key="new_tefas_shares")
            with col3:
                new_weight = st.number_input("Hedef %", min_value=0.0, max_value=100.0, key="new_tefas_weight")
            
            if st.button("Ekle", key="confirm_add_tefas", type="primary"):
                if new_code:
                    config.tefas_funds.append({'code': new_code.upper(), 'shares': new_shares, 'target_weight': new_weight})
                    st.session_state.show_add_tefas = False
                    st.rerun()
    
    # ========== ABD HISSE ==========
    with tab2:
        st.markdown("### ABD Hisseleri")
        
        if not config.us_stocks:
            st.info("Henuz ABD hissesi eklenmemis.")
        else:
            for i, stock in enumerate(list(config.us_stocks)):
                col1, col2, col3, col4 = st.columns([2, 2, 1, 0.5])
                with col1:
                    new_ticker = st.text_input("Ticker", safe_str(stock.get('ticker') if isinstance(stock, dict) else getattr(stock, 'ticker', '')), 
                                              key=f"us_ticker_{i}", label_visibility="collapsed")
                    if isinstance(stock, dict):
                        config.us_stocks[i]['ticker'] = new_ticker
                with col2:
                    shares_val = stock.get('shares', 0) if isinstance(stock, dict) else getattr(stock, 'shares', 0)
                    new_shares = st.number_input("Adet", safe_float(shares_val), key=f"us_shares_{i}", 
                                                label_visibility="collapsed", min_value=0.0, step=0.01)
                    if isinstance(stock, dict):
                        config.us_stocks[i]['shares'] = new_shares
                with col3:
                    weight_val = stock.get('target_weight', 0) if isinstance(stock, dict) else getattr(stock, 'target_weight', 0)
                    new_weight = st.number_input("Hedef", safe_float(weight_val), key=f"us_weight_{i}", 
                                                label_visibility="collapsed", min_value=0.0, max_value=100.0)
                    if isinstance(stock, dict):
                        config.us_stocks[i]['target_weight'] = new_weight
                with col4:
                    if st.button("Sil", key=f"del_us_{i}"):
                        config.us_stocks.pop(i)
                        st.rerun()
        
        st.markdown("---")
        if st.button("+ Hisse Ekle", key="btn_add_us"):
            st.session_state.show_add_us = not st.session_state.show_add_us
        
        if st.session_state.show_add_us:
            col1, col2, col3 = st.columns([2, 2, 1])
            with col1:
                new_ticker = st.text_input("Ticker", key="new_us_ticker")
            with col2:
                new_shares = st.number_input("Adet", min_value=0.0, step=0.01, key="new_us_shares")
            with col3:
                new_weight = st.number_input("Hedef %", min_value=0.0, max_value=100.0, key="new_us_weight")
            
            if st.button("Ekle", key="confirm_add_us", type="primary"):
                if new_ticker:
                    config.us_stocks.append({'ticker': new_ticker.upper(), 'shares': new_shares, 'target_weight': new_weight})
                    st.session_state.show_add_us = False
                    st.rerun()
    
    # ========== KRIPTO ==========
    with tab3:
        st.markdown("### Kripto Varliklar")
        
        if not config.crypto:
            st.info("Henuz kripto varlik eklenmemis.")
        else:
            for i, crypto in enumerate(list(config.crypto)):
                col1, col2, col3, col4 = st.columns([2, 2, 1, 0.5])
                with col1:
                    new_symbol = st.text_input("Symbol", safe_str(crypto.get('symbol') if isinstance(crypto, dict) else getattr(crypto, 'symbol', '')), 
                                              key=f"crypto_symbol_{i}", label_visibility="collapsed")
                    if isinstance(crypto, dict):
                        config.crypto[i]['symbol'] = new_symbol
                with col2:
                    amount_val = crypto.get('amount', 0) if isinstance(crypto, dict) else getattr(crypto, 'amount', 0)
                    new_amount = st.number_input("Miktar", safe_float(amount_val), key=f"crypto_amount_{i}", 
                                                label_visibility="collapsed", min_value=0.0, step=0.0001, format="%.4f")
                    if isinstance(crypto, dict):
                        config.crypto[i]['amount'] = new_amount
                with col3:
                    weight_val = crypto.get('target_weight', 0) if isinstance(crypto, dict) else getattr(crypto, 'target_weight', 0)
                    new_weight = st.number_input("Hedef", safe_float(weight_val), key=f"crypto_weight_{i}", 
                                                label_visibility="collapsed", min_value=0.0, max_value=100.0)
                    if isinstance(crypto, dict):
                        config.crypto[i]['target_weight'] = new_weight
                with col4:
                    if st.button("Sil", key=f"del_crypto_{i}"):
                        config.crypto.pop(i)
                        st.rerun()
        
        st.markdown("---")
        if st.button("+ Kripto Ekle", key="btn_add_crypto"):
            st.session_state.show_add_crypto = not st.session_state.show_add_crypto
        
        if st.session_state.show_add_crypto:
            col1, col2, col3 = st.columns([2, 2, 1])
            with col1:
                new_symbol = st.text_input("Symbol", key="new_crypto_symbol")
            with col2:
                new_amount = st.number_input("Miktar", min_value=0.0, step=0.0001, format="%.4f", key="new_crypto_amount")
            with col3:
                new_weight = st.number_input("Hedef %", min_value=0.0, max_value=100.0, key="new_crypto_weight")
            
            if st.button("Ekle", key="confirm_add_crypto", type="primary"):
                if new_symbol:
                    config.crypto.append({'symbol': new_symbol.upper(), 'amount': new_amount, 'target_weight': new_weight})
                    st.session_state.show_add_crypto = False
                    st.rerun()
    
    # ========== NAKIT ==========
    with tab4:
        st.markdown("### Nakit Varliklar")
        
        if not config.cash:
            st.info("Henuz nakit varlik eklenmemis.")
        else:
            for i, cash in enumerate(list(config.cash)):
                col1, col2, col3 = st.columns([2, 2, 0.5])
                with col1:
                    new_code = st.text_input("Kod", safe_str(cash.get('code') if isinstance(cash, dict) else getattr(cash, 'code', '')), 
                                            key=f"cash_code_{i}", label_visibility="collapsed")
                    if isinstance(cash, dict):
                        config.cash[i]['code'] = new_code
                with col2:
                    amount_val = cash.get('amount', 0) if isinstance(cash, dict) else getattr(cash, 'amount', 0)
                    new_amount = st.number_input("Miktar", safe_float(amount_val), key=f"cash_amount_{i}", 
                                                label_visibility="collapsed", min_value=0.0, step=1.0)
                    if isinstance(cash, dict):
                        config.cash[i]['amount'] = new_amount
                with col3:
                    if st.button("Sil", key=f"del_cash_{i}"):
                        config.cash.pop(i)
                        st.rerun()
        
        st.markdown("---")
        if st.button("+ Nakit Ekle", key="btn_add_cash"):
            st.session_state.show_add_cash = not st.session_state.show_add_cash
        
        if st.session_state.show_add_cash:
            col1, col2 = st.columns([2, 2])
            with col1:
                new_code = st.text_input("Kod", key="new_cash_code")
            with col2:
                new_amount = st.number_input("Miktar", min_value=0.0, step=1.0, key="new_cash_amount")
            
            if st.button("Ekle", key="confirm_add_cash", type="primary"):
                if new_code:
                    config.cash.append({'code': new_code.upper(), 'amount': new_amount})
                    st.session_state.show_add_cash = False
                    st.rerun()
    
    # ========== KAYDET ==========
    st.markdown("---")
    col1, col2 = st.columns([3, 1])
    with col1:
        if st.button("Tumunu Kaydet", type="primary", use_container_width=True):
            if save_config_to_cloud(config):
                st.success("Portfolio kaydedildi!")
                st.session_state.portfolio = Portfolio(config)
            else:
                st.error("Kaydetme hatasi!")
    with col2:
        total = len(config.tefas_funds) + len(config.us_stocks) + len(config.crypto) + len(config.cash)
        st.metric("Toplam", total)


# =============================================================================
# AYARLAR
# =============================================================================

def render_settings_page():
    st.markdown("## Ayarlar")
    
    user = get_current_user()
    if user:
        st.markdown(f"**Kullanici:** {user.get('email', 'N/A')}")
        st.markdown(f"**ID:** {user.get('id', 'N/A')}")
    
    st.markdown("---")
    st.markdown("### Snapshot Yonetimi")
    
    snapshot_count = len(st.session_state.snapshots)
    st.write(f"Toplam snapshot: **{snapshot_count}**")
    
    if st.button("Tum Snapshot'lari Sil", type="secondary"):
        if user and delete_all_snapshots(user['id']):
            st.session_state.snapshots = []
            st.success("Silindi!")
            st.rerun()


# =============================================================================
# DASHBOARD
# =============================================================================

def render_dashboard_page():
    st.markdown("## Barbarians Portfolio Management")
    st.caption("Risk-First Investment Analysis")
    
    portfolio = st.session_state.portfolio
    
    if not portfolio:
        st.info("Sol menuden Yukle butonuna basin.")
        return
    
    if not portfolio.assets or not any(a.is_valid for a in portfolio.assets):
        st.warning("Varlik verisi yok. Guncelle butonuna basin veya Varlik Yonetimi'nden varlik ekleyin.")
        return
    
    render_metric_cards(portfolio)
    st.markdown("---")
    
    tab1, tab2 = st.tabs(["Varliklar", "Grafikler"])
    with tab1:
        render_asset_table(portfolio)
    with tab2:
        render_charts(portfolio)


# =============================================================================
# MAIN
# =============================================================================

def main():
    init_session_state()
    handle_oauth_callback()
    
    if not is_logged_in():
        render_login_page()
        return
    
    if st.session_state.config is None:
        st.session_state.config = load_config_from_cloud()
        st.session_state.portfolio = Portfolio(st.session_state.config)
        st.session_state.snapshots = load_snapshots_from_cloud()
    
    render_sidebar()
    
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
