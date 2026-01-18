"""
benchmark.py - Benchmark Karşılaştırma Modülü
=============================================

Portföy performansını S&P 500, Nasdaq ve BTC ile karşılaştır.

Yazar: Portfolio Dashboard
Tarih: Ocak 2026
"""

import logging
from datetime import datetime, timedelta
from typing import Optional

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

logger = logging.getLogger(__name__)


def fetch_benchmark_data(symbol: str, days: int = 90) -> Optional[pd.DataFrame]:
    """
    Benchmark verisini çek.
    
    Args:
        symbol: 'SPY' (S&P 500), 'QQQ' (Nasdaq), 'BTC-USD' (Bitcoin)
        days: Kaç günlük veri
        
    Returns:
        DataFrame with Date, Close columns
    """
    try:
        import yfinance as yf
        
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days)
        
        ticker = yf.Ticker(symbol)
        hist = ticker.history(start=start_date, end=end_date)
        
        if hist.empty:
            return None
        
        df = pd.DataFrame({
            'Date': hist.index,
            'Close': hist['Close'].values
        }).reset_index(drop=True)
        
        return df
        
    except Exception as e:
        logger.error(f"Benchmark veri çekme hatası ({symbol}): {e}")
        return None


def calculate_benchmark_returns(snapshots: list[dict], days: int = 90) -> dict:
    """
    Portföy ve benchmark getirilerini hesapla.
    
    Args:
        snapshots: Kullanıcının snapshot listesi
        days: Karşılaştırma periyodu (gün)
        
    Returns:
        Dictionary with returns data
    """
    result = {
        'portfolio': None,
        'spy': None,
        'qqq': None,
        'btc': None,
        'dates': None
    }
    
    if not snapshots or len(snapshots) < 2:
        return result
    
    # Portföy verisi
    portfolio_dates = [datetime.fromisoformat(s['created_at'].replace('Z', '+00:00')).date() 
                       for s in snapshots]
    portfolio_values = [float(s['total_value_try']) for s in snapshots]
    
    # Normalize et (ilk değer = 100)
    first_value = portfolio_values[0]
    portfolio_normalized = [(v / first_value) * 100 for v in portfolio_values]
    
    result['portfolio'] = {
        'dates': portfolio_dates,
        'values': portfolio_normalized,
        'total_return': ((portfolio_values[-1] / first_value) - 1) * 100
    }
    
    # Benchmark verileri
    benchmarks = {
        'spy': 'SPY',
        'qqq': 'QQQ', 
        'btc': 'BTC-USD'
    }
    
    for key, symbol in benchmarks.items():
        try:
            df = fetch_benchmark_data(symbol, days)
            
            if df is not None and not df.empty:
                # Normalize et
                first_close = df['Close'].iloc[0]
                df['Normalized'] = (df['Close'] / first_close) * 100
                
                result[key] = {
                    'dates': df['Date'].dt.date.tolist(),
                    'values': df['Normalized'].tolist(),
                    'total_return': ((df['Close'].iloc[-1] / first_close) - 1) * 100
                }
        except Exception as e:
            logger.error(f"Benchmark hesaplama hatası ({symbol}): {e}")
    
    return result


def render_benchmark_comparison(snapshots: list[dict]):
    """Benchmark karşılaştırma grafiklerini render et."""
    
    st.markdown("### 📊 Benchmark Karşılaştırma")
    
    if not snapshots or len(snapshots) < 2:
        st.info("Benchmark karşılaştırma için en az 2 snapshot gerekli. Birkaç hafta veri biriktikten sonra burada karşılaştırma göreceksiniz.")
        return
    
    with st.spinner("Benchmark verileri yükleniyor..."):
        data = calculate_benchmark_returns(snapshots)
    
    if not data['portfolio']:
        st.warning("Portföy verisi hesaplanamadı.")
        return
    
    # Performans kartları
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        port_return = data['portfolio']['total_return']
        color = "normal" if port_return >= 0 else "inverse"
        st.metric(
            label="📊 Portföy",
            value=f"{port_return:+.1f}%",
            delta=f"Toplam getiri",
            delta_color=color
        )
    
    with col2:
        if data['spy']:
            spy_return = data['spy']['total_return']
            diff = port_return - spy_return
            st.metric(
                label="🇺🇸 S&P 500",
                value=f"{spy_return:+.1f}%",
                delta=f"{diff:+.1f}% fark",
                delta_color="normal" if diff >= 0 else "inverse"
            )
        else:
            st.metric(label="🇺🇸 S&P 500", value="N/A")
    
    with col3:
        if data['qqq']:
            qqq_return = data['qqq']['total_return']
            diff = port_return - qqq_return
            st.metric(
                label="📱 Nasdaq",
                value=f"{qqq_return:+.1f}%",
                delta=f"{diff:+.1f}% fark",
                delta_color="normal" if diff >= 0 else "inverse"
            )
        else:
            st.metric(label="📱 Nasdaq", value="N/A")
    
    with col4:
        if data['btc']:
            btc_return = data['btc']['total_return']
            diff = port_return - btc_return
            st.metric(
                label="₿ Bitcoin",
                value=f"{btc_return:+.1f}%",
                delta=f"{diff:+.1f}% fark",
                delta_color="normal" if diff >= 0 else "inverse"
            )
        else:
            st.metric(label="₿ Bitcoin", value="N/A")
    
    st.markdown("---")
    
    # Karşılaştırma grafiği
    st.markdown("#### 📈 Normalize Performans (Başlangıç = 100)")
    
    fig = go.Figure()
    
    # Portföy
    fig.add_trace(go.Scatter(
        x=data['portfolio']['dates'],
        y=data['portfolio']['values'],
        mode='lines+markers',
        name='📊 Portföy',
        line=dict(color='#667eea', width=3),
        marker=dict(size=6)
    ))
    
    # S&P 500
    if data['spy']:
        fig.add_trace(go.Scatter(
            x=data['spy']['dates'],
            y=data['spy']['values'],
            mode='lines',
            name='🇺🇸 S&P 500',
            line=dict(color='#00d26a', width=2, dash='dash')
        ))
    
    # Nasdaq
    if data['qqq']:
        fig.add_trace(go.Scatter(
            x=data['qqq']['dates'],
            y=data['qqq']['values'],
            mode='lines',
            name='📱 Nasdaq',
            line=dict(color='#ffc107', width=2, dash='dash')
        ))
    
    # Bitcoin
    if data['btc']:
        fig.add_trace(go.Scatter(
            x=data['btc']['dates'],
            y=data['btc']['values'],
            mode='lines',
            name='₿ Bitcoin',
            line=dict(color='#f7931a', width=2, dash='dot')
        ))
    
    # 100 çizgisi (başlangıç noktası)
    fig.add_hline(y=100, line_dash="solid", line_color="gray", opacity=0.5, 
                  annotation_text="Başlangıç")
    
    fig.update_layout(
        hovermode='x unified',
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="center", x=0.5),
        yaxis=dict(title='Değer (Normalize)', ticksuffix=''),
        xaxis=dict(title='Tarih'),
        margin=dict(t=60, b=40)
    )
    
    st.plotly_chart(fig, use_container_width=True)
    
    # Alpha hesaplama
    st.markdown("---")
    st.markdown("#### 🎯 Alpha (Fazla Getiri)")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        if data['spy']:
            alpha_spy = port_return - data['spy']['total_return']
            if alpha_spy > 0:
                st.success(f"**S&P 500'e göre:** +{alpha_spy:.1f}% alpha ✅")
            else:
                st.error(f"**S&P 500'e göre:** {alpha_spy:.1f}% ❌")
        else:
            st.info("S&P 500 verisi yok")
    
    with col2:
        if data['qqq']:
            alpha_qqq = port_return - data['qqq']['total_return']
            if alpha_qqq > 0:
                st.success(f"**Nasdaq'a göre:** +{alpha_qqq:.1f}% alpha ✅")
            else:
                st.error(f"**Nasdaq'a göre:** {alpha_qqq:.1f}% ❌")
        else:
            st.info("Nasdaq verisi yok")
    
    with col3:
        if data['btc']:
            alpha_btc = port_return - data['btc']['total_return']
            if alpha_btc > 0:
                st.success(f"**Bitcoin'e göre:** +{alpha_btc:.1f}% alpha ✅")
            else:
                st.error(f"**Bitcoin'e göre:** {alpha_btc:.1f}% ❌")
        else:
            st.info("Bitcoin verisi yok")
    
    st.markdown("---")
    st.caption("💡 **Alpha**: Benchmark'ı ne kadar geçtiğiniz. Pozitif alpha = başarılı yönetim.")


def render_benchmark_tab(snapshots: list[dict]):
    """Benchmark sekmesini render et."""
    render_benchmark_comparison(snapshots)
