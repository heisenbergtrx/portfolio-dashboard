"""
barbarians_theme.py - Barbarians Premium UI Theme
=================================================

Premium dark theme with amber/gold accents.
Import this module and call inject_theme() at the start of your Streamlit app.

Yazar: Barbarians Trading
Tarih: Ocak 2026
"""

import streamlit as st

# =============================================================================
# CHART COLORS
# =============================================================================

CHART_COLORS = {
    'primary': '#d4a853',
    'secondary': '#b8923a', 
    'tertiary': '#e8c068',
    'success': '#4ade80',
    'danger': '#f87171',
    'warning': '#fbbf24',
    'info': '#60a5fa',
    'background': '#0a0a0f',
    'card': '#16161f',
    'text': '#f5f5f7',
    'muted': '#6b6b78',
    'grid': 'rgba(255, 255, 255, 0.06)'
}

# =============================================================================
# PLOTLY LAYOUT TEMPLATE
# =============================================================================

PLOTLY_LAYOUT = dict(
    paper_bgcolor='rgba(0,0,0,0)',
    plot_bgcolor='rgba(0,0,0,0)',
    font=dict(family='Outfit, sans-serif', color=CHART_COLORS['text'], size=12),
    margin=dict(l=20, r=20, t=40, b=20),
    xaxis=dict(
        gridcolor=CHART_COLORS['grid'],
        zerolinecolor=CHART_COLORS['grid'],
        tickfont=dict(size=11)
    ),
    yaxis=dict(
        gridcolor=CHART_COLORS['grid'],
        zerolinecolor=CHART_COLORS['grid'],
        tickfont=dict(size=11)
    ),
    hoverlabel=dict(
        bgcolor=CHART_COLORS['card'],
        font_size=12,
        font_family='Outfit, sans-serif'
    )
)

# =============================================================================
# CSS THEME
# =============================================================================

THEME_CSS = """
<style>
/* ===== IMPORTS ===== */
@import url('https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;500;600;700&family=JetBrains+Mono:wght@400;500&display=swap');

/* ===== CSS VARIABLES ===== */
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
    --warning: #fbbf24;
    --warning-bg: rgba(251, 191, 36, 0.1);
    
    --border-subtle: rgba(255, 255, 255, 0.06);
    --border-accent: rgba(212, 168, 83, 0.3);
    
    --radius-sm: 8px;
    --radius-md: 12px;
    --radius-lg: 16px;
    --radius-xl: 24px;
}

/* ===== GLOBAL ===== */
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
    top: 0;
    left: 0;
    right: 0;
    bottom: 0;
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

/* ===== TYPOGRAPHY ===== */
h1, h2, h3, h4, h5, h6, p, span, div, label {
    font-family: 'Outfit', sans-serif !important;
}

.main-title {
    font-size: 1.5rem !important;
    font-weight: 700 !important;
    background: linear-gradient(135deg, #f5f5f7 0%, #e8c068 100%);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    background-clip: text;
}

/* ===== SCROLLBAR ===== */
::-webkit-scrollbar { width: 8px; height: 8px; }
::-webkit-scrollbar-track { background: var(--bg-secondary); border-radius: 4px; }
::-webkit-scrollbar-thumb { background: var(--bg-tertiary); border-radius: 4px; }
::-webkit-scrollbar-thumb:hover { background: var(--accent-secondary); }

/* ===== HEADER ===== */
.barbarians-header {
    background: linear-gradient(135deg, var(--bg-secondary) 0%, var(--bg-card) 100%);
    border: 1px solid var(--border-subtle);
    border-radius: var(--radius-xl);
    padding: 1.5rem 2rem;
    margin-bottom: 1.5rem;
    position: relative;
    overflow: hidden;
}

.barbarians-header::before {
    content: '';
    position: absolute;
    top: 0;
    left: 0;
    right: 0;
    height: 3px;
    background: linear-gradient(90deg, transparent, var(--accent-primary), var(--accent-tertiary), var(--accent-primary), transparent);
}

.header-content {
    display: flex;
    align-items: center;
    gap: 1rem;
}

.header-icon {
    width: 44px;
    height: 44px;
    background: var(--bg-tertiary);
    border-radius: 12px;
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 1.5rem;
}

.header-title {
    font-size: 1.375rem !important;
    font-weight: 700 !important;
    background: linear-gradient(135deg, var(--text-primary) 0%, var(--accent-tertiary) 100%);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    background-clip: text;
    margin: 0 !important;
    line-height: 1.2;
}

.header-subtitle {
    font-size: 0.6875rem !important;
    color: var(--text-muted) !important;
    font-weight: 400 !important;
    letter-spacing: 0.1em;
    text-transform: uppercase;
    margin: 0 !important;
}

/* ===== METRIC CARDS ===== */
.metric-card {
    background: var(--bg-card);
    border: 1px solid var(--border-subtle);
    border-radius: var(--radius-lg);
    padding: 1.25rem;
    transition: all 0.25s ease;
    position: relative;
    overflow: hidden;
}

.metric-card:hover {
    background: var(--bg-card-hover);
    border-color: var(--border-accent);
    box-shadow: 0 0 30px rgba(212, 168, 83, 0.08);
    transform: translateY(-2px);
}

.metric-card::after {
    content: '';
    position: absolute;
    top: 0;
    left: 0;
    width: 4px;
    height: 100%;
    background: linear-gradient(180deg, var(--accent-primary), var(--accent-secondary));
    opacity: 0;
    transition: opacity 0.25s ease;
}

.metric-card:hover::after {
    opacity: 1;
}

.metric-label {
    font-size: 0.625rem;
    font-weight: 500;
    color: var(--text-muted) !important;
    text-transform: uppercase;
    letter-spacing: 0.1em;
    margin-bottom: 0.375rem;
}

.metric-value {
    font-size: 1.375rem;
    font-weight: 700;
    color: var(--text-primary) !important;
    line-height: 1.2;
}

.metric-value.positive { color: var(--success) !important; }
.metric-value.negative { color: var(--danger) !important; }

.metric-delta {
    display: inline-flex;
    align-items: center;
    gap: 0.25rem;
    font-size: 0.6875rem;
    font-weight: 500;
    padding: 0.1875rem 0.5rem;
    border-radius: 6px;
    margin-top: 0.375rem;
}

.metric-delta.positive {
    background: var(--success-bg);
    color: var(--success);
}

.metric-delta.negative {
    background: var(--danger-bg);
    color: var(--danger);
}

/* ===== SIDEBAR ===== */
section[data-testid="stSidebar"] {
    background: var(--bg-secondary) !important;
    border-right: 1px solid var(--border-subtle) !important;
}

section[data-testid="stSidebar"] > div {
    padding: 1.25rem 1rem !important;
}

.sidebar-brand {
    display: flex;
    align-items: center;
    gap: 0.75rem;
    padding: 0.5rem;
    margin-bottom: 1.25rem;
}

.sidebar-logo {
    width: 32px;
    height: 32px;
    background: linear-gradient(135deg, var(--accent-primary), var(--accent-secondary));
    border-radius: 8px;
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 1rem;
}

.sidebar-title {
    font-size: 1rem;
    font-weight: 700;
    color: var(--accent-primary) !important;
}

.user-badge {
    background: var(--accent-glow);
    border: 1px solid var(--border-accent);
    border-radius: var(--radius-md);
    padding: 0.625rem 0.875rem;
    margin-bottom: 1rem;
}

.user-label {
    font-size: 0.5625rem;
    color: var(--text-muted) !important;
    text-transform: uppercase;
    letter-spacing: 0.1em;
}

.user-email {
    font-size: 0.75rem;
    color: var(--text-primary) !important;
    font-weight: 500;
    margin-top: 0.125rem;
}

.nav-label {
    font-size: 0.5625rem;
    color: var(--text-muted) !important;
    text-transform: uppercase;
    letter-spacing: 0.12em;
    padding: 0 0.5rem;
    margin-bottom: 0.5rem;
}

/* ===== BUTTONS ===== */
.stButton > button {
    background: linear-gradient(135deg, var(--accent-primary) 0%, var(--accent-secondary) 100%) !important;
    color: var(--bg-primary) !important;
    border: none !important;
    border-radius: var(--radius-md) !important;
    padding: 0.5rem 1rem !important;
    font-weight: 600 !important;
    font-size: 0.75rem !important;
    font-family: 'Outfit', sans-serif !important;
    letter-spacing: 0.02em !important;
    transition: all 0.2s ease !important;
    box-shadow: 0 4px 12px rgba(212, 168, 83, 0.2) !important;
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
    color: var(--text-primary) !important;
    border-color: var(--border-accent) !important;
}

/* ===== INPUTS ===== */
.stTextInput > div > div > input,
.stNumberInput > div > div > input,
.stSelectbox > div > div > div {
    background: var(--bg-tertiary) !important;
    border: 1px solid var(--border-subtle) !important;
    border-radius: var(--radius-md) !important;
    color: var(--text-primary) !important;
    font-family: 'Outfit', sans-serif !important;
    padding: 0.5rem 0.75rem !important;
    font-size: 0.8125rem !important;
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
    font-size: 0.6875rem !important;
    font-weight: 500 !important;
    text-transform: uppercase !important;
    letter-spacing: 0.05em !important;
}

/* ===== TABS ===== */
.stTabs [data-baseweb="tab-list"] {
    background: var(--bg-tertiary) !important;
    border-radius: var(--radius-lg) !important;
    padding: 0.25rem !important;
    gap: 0.25rem !important;
}

.stTabs [data-baseweb="tab"] {
    background: transparent !important;
    border-radius: var(--radius-md) !important;
    color: var(--text-secondary) !important;
    font-weight: 500 !important;
    font-size: 0.75rem !important;
    padding: 0.5rem 1rem !important;
    font-family: 'Outfit', sans-serif !important;
}

.stTabs [data-baseweb="tab"]:hover {
    color: var(--text-primary) !important;
    background: var(--bg-card) !important;
}

.stTabs [aria-selected="true"] {
    background: var(--accent-glow) !important;
    color: var(--accent-primary) !important;
}

/* ===== DATAFRAMES ===== */
.stDataFrame {
    border: 1px solid var(--border-subtle) !important;
    border-radius: var(--radius-lg) !important;
    overflow: hidden !important;
}

[data-testid="stDataFrame"] > div {
    background: var(--bg-card) !important;
}

/* ===== ALERTS ===== */
.stAlert {
    background: var(--bg-card) !important;
    border: 1px solid var(--border-subtle) !important;
    border-radius: var(--radius-lg) !important;
    color: var(--text-primary) !important;
}

div[data-baseweb="notification"][kind="positive"],
.stSuccess { 
    border-color: rgba(74, 222, 128, 0.3) !important; 
    background: var(--success-bg) !important; 
}

div[data-baseweb="notification"][kind="negative"],
.stError { 
    border-color: rgba(248, 113, 113, 0.3) !important; 
    background: var(--danger-bg) !important; 
}

div[data-baseweb="notification"][kind="warning"],
.stWarning { 
    border-color: rgba(251, 191, 36, 0.3) !important; 
    background: var(--warning-bg) !important; 
}

div[data-baseweb="notification"][kind="info"],
.stInfo { 
    border-color: rgba(96, 165, 250, 0.3) !important; 
    background: rgba(96, 165, 250, 0.1) !important; 
}

/* ===== METRICS ===== */
[data-testid="stMetricValue"] {
    font-family: 'Outfit', sans-serif !important;
    font-weight: 700 !important;
    font-size: 1.375rem !important;
    color: var(--text-primary) !important;
}

[data-testid="stMetricDelta"] {
    font-family: 'Outfit', sans-serif !important;
}

[data-testid="stMetricLabel"] {
    font-size: 0.6875rem !important;
    text-transform: uppercase !important;
    letter-spacing: 0.05em !important;
    color: var(--text-muted) !important;
}

/* ===== EXPANDER ===== */
.streamlit-expanderHeader {
    background: var(--bg-tertiary) !important;
    border: 1px solid var(--border-subtle) !important;
    border-radius: var(--radius-md) !important;
    color: var(--text-primary) !important;
    font-family: 'Outfit', sans-serif !important;
}

/* ===== DIVIDER ===== */
hr {
    border: none !important;
    height: 1px !important;
    background: linear-gradient(90deg, transparent, var(--border-subtle), var(--border-accent), var(--border-subtle), transparent) !important;
    margin: 1.25rem 0 !important;
}

/* ===== COLOR CLASSES ===== */
.positive { color: var(--success) !important; }
.negative { color: var(--danger) !important; }
.warning { color: var(--warning) !important; }
.muted { color: var(--text-muted) !important; }

/* ===== ANIMATIONS ===== */
@keyframes fadeIn {
    from { opacity: 0; transform: translateY(10px); }
    to { opacity: 1; transform: translateY(0); }
}

.animate-in {
    animation: fadeIn 0.3s ease forwards;
}

/* ===== RESPONSIVE ===== */
@media (max-width: 768px) {
    .barbarians-header { padding: 1rem 1.25rem; }
    .header-title { font-size: 1.125rem !important; }
    .metric-card { padding: 0.875rem; }
    .metric-value { font-size: 1.125rem; }
}
</style>
"""


def inject_theme():
    """Inject Barbarians theme CSS into the Streamlit app."""
    st.markdown(THEME_CSS, unsafe_allow_html=True)


def render_header(title: str = "Barbarians Portfolio Management", subtitle: str = "Risk-First Investment Analysis"):
    """Render the premium header with branding."""
    st.markdown(f"""
    <div class="barbarians-header animate-in">
        <div class="header-content">
            <div class="header-icon">⚔️</div>
            <div>
                <h1 class="header-title">{title}</h1>
                <p class="header-subtitle">{subtitle}</p>
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)


def render_sidebar_brand():
    """Render sidebar brand section."""
    st.markdown("""
    <div class="sidebar-brand">
        <div class="sidebar-logo">⚔️</div>
        <div class="sidebar-title">Barbarians</div>
    </div>
    """, unsafe_allow_html=True)


def render_user_badge(user_name: str):
    """Render user badge in sidebar."""
    st.markdown(f"""
    <div class="user-badge">
        <div class="user-label">Signed in as</div>
        <div class="user-email">{user_name}</div>
    </div>
    """, unsafe_allow_html=True)


def render_nav_label(label: str):
    """Render navigation section label."""
    st.markdown(f'<div class="nav-label">{label}</div>', unsafe_allow_html=True)


def render_metric_card(label: str, value: str, delta: str = None, delta_type: str = "neutral"):
    """
    Render a styled metric card.
    
    Args:
        label: Metric label text
        value: Main value to display
        delta: Optional delta/change value
        delta_type: "positive", "negative", "neutral", or "auto" (determines from delta sign)
    """
    delta_html = ""
    value_class = ""
    
    if delta:
        if delta_type == "positive" or (delta_type == "auto" and not str(delta).startswith("-")):
            delta_class = "positive"
            delta_icon = "↑"
            value_class = "positive"
        elif delta_type == "negative" or (delta_type == "auto" and str(delta).startswith("-")):
            delta_class = "negative"
            delta_icon = "↓"
            value_class = "negative"
        else:
            delta_class = ""
            delta_icon = ""
        
        delta_html = f'<div class="metric-delta {delta_class}">{delta_icon} {delta}</div>'
    
    st.markdown(f"""
    <div class="metric-card">
        <div class="metric-label">{label}</div>
        <div class="metric-value {value_class}">{value}</div>
        {delta_html}
    </div>
    """, unsafe_allow_html=True)


def render_version_badge(version: str = "v6.0.0"):
    """Render version badge at bottom of sidebar."""
    st.markdown(f"""
    <div style="position: fixed; bottom: 1rem; left: 1rem; font-size: 0.5625rem; color: #6b6b78;">
        {version} • Barbarians Trading
    </div>
    """, unsafe_allow_html=True)


def get_plotly_colors():
    """Return a list of theme-appropriate colors for Plotly charts."""
    return [
        CHART_COLORS['primary'],
        CHART_COLORS['tertiary'],
        CHART_COLORS['success'],
        CHART_COLORS['info'],
        CHART_COLORS['warning'],
        CHART_COLORS['secondary'],
        CHART_COLORS['danger']
    ]


def apply_plotly_layout(fig, **kwargs):
    """Apply Barbarians theme to a Plotly figure."""
    layout = {**PLOTLY_LAYOUT, **kwargs}
    fig.update_layout(**layout)
    return fig
