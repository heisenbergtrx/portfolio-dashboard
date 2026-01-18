# =============================================================================
# BARBARIANS PORTFOLIO MANAGEMENT - UI UPDATE GUIDE
# =============================================================================
#
# Bu dosya, mevcut dashboard.py'nizi Barbarians Premium UI temasına 
# dönüştürmek için yapılması gereken değişiklikleri içerir.
#
# Değişiklikler 3 adımda uygulanır:
# 1. Sayfa ayarlarını güncelleyin
# 2. Stil bölümünü değiştirin  
# 3. Sidebar'ı güncelleyin
#
# =============================================================================

# =============================================================================
# ADIM 1: SAYFA AYARLARINI GÜNCELLEYİN (satır 59-63)
# =============================================================================
# ESKİ:
# st.set_page_config(
#     page_title="Portföy Dashboard",
#     page_icon="📊",
#     ...
# )

# YENİ:
"""
st.set_page_config(
    page_title="Barbarians Portfolio Management",
    page_icon="⚔️",
    layout="wide",
    initial_sidebar_state="expanded"
)
"""


# =============================================================================
# ADIM 2: STİL BÖLÜMÜNÜ DEĞİŞTİRİN (satır 77-95)
# =============================================================================
# Mevcut st.markdown("""<style>...</style>""") bölümünü tamamen silin
# ve aşağıdaki kodu ekleyin:

BARBARIANS_THEME = '''
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

.stTextInput > div > div > input,
.stNumberInput > div > div > input,
.stSelectbox > div > div > div {
    background: var(--bg-tertiary) !important;
    border: 1px solid var(--border-subtle) !important;
    border-radius: var(--radius-md) !important;
    color: var(--text-primary) !important;
    font-family: 'Outfit', sans-serif !important;
}

.stTextInput > div > div > input:focus {
    border-color: var(--accent-primary) !important;
    box-shadow: 0 0 0 3px var(--accent-glow) !important;
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

.stTabs [aria-selected="true"] {
    background: var(--accent-glow) !important;
    color: var(--accent-primary) !important;
}

.stDataFrame {
    border: 1px solid var(--border-subtle) !important;
    border-radius: var(--radius-lg) !important;
    overflow: hidden !important;
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
}

hr {
    border: none !important;
    height: 1px !important;
    background: linear-gradient(90deg, transparent, var(--border-subtle), var(--border-accent), var(--border-subtle), transparent) !important;
}
</style>
'''


# =============================================================================
# ADIM 3: HEADER FONKSİYONU EKLEYİN
# =============================================================================
# render_dashboard_page() fonksiyonunun başına ekleyin:

def render_barbarians_header():
    """Barbarians branded header."""
    st.markdown("""
    <div style="
        background: linear-gradient(135deg, #12121a 0%, #16161f 100%);
        border: 1px solid rgba(255, 255, 255, 0.06);
        border-radius: 24px;
        padding: 1.5rem 2rem;
        margin-bottom: 1.5rem;
        position: relative;
        overflow: hidden;
    ">
        <div style="
            position: absolute;
            top: 0; left: 0; right: 0;
            height: 3px;
            background: linear-gradient(90deg, transparent, #d4a853, #e8c068, #d4a853, transparent);
        "></div>
        <div style="display: flex; align-items: center; gap: 1rem;">
            <div style="
                width: 44px; height: 44px;
                background: #1a1a25;
                border-radius: 12px;
                display: flex;
                align-items: center;
                justify-content: center;
                font-size: 1.5rem;
            ">⚔️</div>
            <div>
                <h1 style="
                    font-size: 1.375rem !important;
                    font-weight: 700 !important;
                    background: linear-gradient(135deg, #f5f5f7 0%, #e8c068 100%);
                    -webkit-background-clip: text;
                    -webkit-text-fill-color: transparent;
                    margin: 0 !important;
                ">Barbarians Portfolio Management</h1>
                <p style="
                    font-size: 0.6875rem !important;
                    color: #6b6b78 !important;
                    letter-spacing: 0.1em;
                    text-transform: uppercase;
                    margin: 0 !important;
                ">Risk-First Investment Analysis</p>
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)


# =============================================================================
# ADIM 4: SIDEBAR BAŞLIĞINI GÜNCELLEYİN
# =============================================================================
# render_sidebar() fonksiyonunda kullanıcı badge'ini güncelleyin:

# ESKİ (satır ~207-211):
# st.markdown(f"""
# <div class="user-badge">
#     👤 {user.get('name', user.get('email', 'Kullanıcı'))}
# </div>
# """, unsafe_allow_html=True)

# YENİ:
"""
st.markdown('''
<div style="
    display: flex;
    align-items: center;
    gap: 0.75rem;
    padding: 0.5rem;
    margin-bottom: 1rem;
">
    <div style="
        width: 32px; height: 32px;
        background: linear-gradient(135deg, #d4a853, #b8923a);
        border-radius: 8px;
        display: flex;
        align-items: center;
        justify-content: center;
        font-size: 1rem;
    ">⚔️</div>
    <div style="font-size: 1rem; font-weight: 700; color: #d4a853;">Barbarians</div>
</div>
''', unsafe_allow_html=True)

if user:
    st.markdown(f'''
    <div class="user-badge">
        <div style="font-size: 0.5625rem; color: #6b6b78; text-transform: uppercase; letter-spacing: 0.1em;">
            Signed in as
        </div>
        <div style="font-size: 0.75rem; color: #f5f5f7; font-weight: 500; margin-top: 2px;">
            {user.get('name', user.get('email', 'Kullanıcı'))}
        </div>
    </div>
    ''', unsafe_allow_html=True)
"""


# =============================================================================
# ADIM 5: CHART COLORS'I GÜNCELLEYİN
# =============================================================================
# Grafiklerde kullanılan renkleri güncelleyin:

CHART_COLORS = {
    'primary': '#d4a853',      # Ana amber/gold
    'secondary': '#b8923a',    # Koyu amber
    'tertiary': '#e8c068',     # Açık amber
    'success': '#4ade80',      # Yeşil
    'danger': '#f87171',       # Kırmızı
    'warning': '#fbbf24',      # Turuncu
    'info': '#60a5fa',         # Mavi
    'text': '#f5f5f7',
    'muted': '#6b6b78',
    'grid': 'rgba(255, 255, 255, 0.06)'
}

# Pasta grafiklerinde renk paleti:
# px.colors.qualitative.Set3 yerine:
PIE_COLORS = ['#d4a853', '#e8c068', '#4ade80', '#60a5fa', '#fbbf24', '#b8923a', '#f87171']


# =============================================================================
# KULLANIM
# =============================================================================
# 
# 1. barbarians_theme.py dosyasını projenize ekleyin
# 2. dashboard.py'da import edin:
#    from barbarians_theme import inject_theme, CHART_COLORS, PLOTLY_LAYOUT
# 3. main() fonksiyonunun başında inject_theme() çağırın
# 4. Veya yukarıdaki ADIM'ları manuel olarak uygulayın
#
# =============================================================================
