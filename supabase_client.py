"""
supabase_client.py - Supabase Authentication & Database
========================================================

Email/Password ile giris ve kullanici verisi yonetimi.

Yazar: Barbarians Trading
Tarih: Ocak 2026
"""

import logging
from datetime import datetime
from typing import Optional

import streamlit as st
from supabase import create_client, Client

logger = logging.getLogger(__name__)

# Supabase credentials
SUPABASE_URL = "https://ckxbytrgxrdrxtkbaqex.supabase.co"
SUPABASE_KEY = st.secrets.get("SUPABASE_KEY", "")

if not SUPABASE_KEY:
    SUPABASE_KEY = "sb_publishable_KRs5qGHDBj9EKdi7lWUIrA_LlWSirRN"


def get_supabase_client() -> Client:
    """Supabase client olustur."""
    return create_client(SUPABASE_URL, SUPABASE_KEY)


def init_auth_state():
    """Auth session state'i baslat."""
    if 'user' not in st.session_state:
        st.session_state.user = None
    if 'access_token' not in st.session_state:
        st.session_state.access_token = None
    if 'auth_mode' not in st.session_state:
        st.session_state.auth_mode = "login"


def get_current_user() -> Optional[dict]:
    """Mevcut kullaniciyi dondur."""
    return st.session_state.get('user', None)


def is_logged_in() -> bool:
    """Kullanici giris yapmis mi?"""
    return st.session_state.get('user') is not None


def render_login_page():
    """Login sayfasini render et."""
    col1, col2, col3 = st.columns([1, 2, 1])
    
    with col2:
        st.markdown("## Barbarians Portfolio")
        st.markdown("*Risk-First Investment Analysis*")
        
        st.markdown("---")
        
        mode = st.session_state.get('auth_mode', 'login')
        
        if mode == "login":
            render_login_form()
        elif mode == "register":
            render_register_form()
        elif mode == "forgot":
            render_forgot_password_form()
        
        st.markdown("---")
        st.caption("Verileriniz guvenle Supabase'de saklanir.")


def render_login_form():
    """Giris formu."""
    st.markdown("### Giris Yap")
    
    supabase = get_supabase_client()
    
    email = st.text_input("Email", placeholder="ornek@email.com", key="login_email")
    password = st.text_input("Sifre", type="password", placeholder="********", key="login_password")
    
    col1, col2 = st.columns(2)
    
    with col1:
        if st.button("Giris Yap", type="primary", use_container_width=True):
            if not email or not password:
                st.error("Email ve sifre gerekli!")
                return
            
            try:
                result = supabase.auth.sign_in_with_password({
                    "email": email,
                    "password": password
                })
                
                if result.user:
                    st.session_state.user = {
                        'id': result.user.id,
                        'email': result.user.email,
                        'name': result.user.user_metadata.get('full_name', result.user.email)
                    }
                    st.session_state.access_token = result.session.access_token
                    st.success("Giris basarili!")
                    st.rerun()
                else:
                    st.error("Giris hatasi!")
                    
            except Exception as e:
                error_msg = str(e)
                if "invalid" in error_msg.lower():
                    st.error("Email veya sifre yanlis!")
                else:
                    st.error(f"Hata: {error_msg}")
    
    with col2:
        if st.button("Kayit Ol", use_container_width=True):
            st.session_state.auth_mode = "register"
            st.rerun()
    
    st.markdown("")
    if st.button("Sifremi Unuttum", type="secondary"):
        st.session_state.auth_mode = "forgot"
        st.rerun()


def render_register_form():
    """Kayit formu."""
    st.markdown("### Kayit Ol")
    
    supabase = get_supabase_client()
    
    email = st.text_input("Email", placeholder="ornek@email.com", key="reg_email")
    password = st.text_input("Sifre", type="password", placeholder="En az 6 karakter", key="reg_password")
    password_confirm = st.text_input("Sifre Tekrar", type="password", placeholder="********", key="reg_password_confirm")
    
    col1, col2 = st.columns(2)
    
    with col1:
        if st.button("Kayit Ol", type="primary", use_container_width=True):
            if not email or not password:
                st.error("Email ve sifre gerekli!")
                return
            
            if password != password_confirm:
                st.error("Sifreler eslesmiyor!")
                return
            
            if len(password) < 6:
                st.error("Sifre en az 6 karakter olmali!")
                return
            
            try:
                result = supabase.auth.sign_up({
                    "email": email,
                    "password": password
                })
                
                if result.user:
                    st.success("Kayit basarili! Simdi giris yapabilirsiniz.")
                    st.session_state.auth_mode = "login"
                    st.rerun()
                else:
                    st.error("Kayit hatasi!")
                    
            except Exception as e:
                error_msg = str(e)
                if "already registered" in error_msg.lower():
                    st.error("Bu email zaten kayitli!")
                else:
                    st.error(f"Hata: {error_msg}")
    
    with col2:
        if st.button("Geri Don", use_container_width=True):
            st.session_state.auth_mode = "login"
            st.rerun()


def render_forgot_password_form():
    """Sifremi unuttum formu."""
    st.markdown("### Sifremi Unuttum")
    st.info("Email adresinize sifre sifirlama linki gonderilecek.")
    
    supabase = get_supabase_client()
    
    email = st.text_input("Email", placeholder="ornek@email.com", key="forgot_email")
    
    col1, col2 = st.columns(2)
    
    with col1:
        if st.button("Link Gonder", type="primary", use_container_width=True):
            if not email:
                st.error("Email gerekli!")
                return
            
            try:
                supabase.auth.reset_password_email(email)
                st.success("Sifre sifirlama linki gonderildi! Email'inizi kontrol edin.")
            except Exception as e:
                st.error(f"Hata: {e}")
    
    with col2:
        if st.button("Geri Don", use_container_width=True):
            st.session_state.auth_mode = "login"
            st.rerun()


def handle_oauth_callback():
    """OAuth callback - artik kullanilmiyor."""
    pass


def logout():
    """Cikis yap."""
    try:
        supabase = get_supabase_client()
        supabase.auth.sign_out()
    except:
        pass
    
    st.session_state.user = None
    st.session_state.access_token = None
    st.session_state.config = None
    st.session_state.portfolio = None
    st.rerun()


# =============================================================================
# DATABASE OPERATIONS
# =============================================================================

def save_portfolio_config(user_id: str, config: dict) -> bool:
    """Portfolio config'ini kaydet."""
    try:
        supabase = get_supabase_client()
        
        result = supabase.table('portfolios').upsert({
            'user_id': user_id,
            'config': config,
            'updated_at': datetime.now().isoformat()
        }, on_conflict='user_id').execute()
        
        return True
        
    except Exception as e:
        logger.error(f"Config kaydetme hatasi: {e}")
        return False


def load_portfolio_config(user_id: str) -> Optional[dict]:
    """Portfolio config'ini yukle."""
    try:
        supabase = get_supabase_client()
        
        result = supabase.table('portfolios').select('config').eq('user_id', user_id).single().execute()
        
        if result.data:
            return result.data['config']
        
        return None
        
    except Exception as e:
        logger.error(f"Config yukleme hatasi: {e}")
        return None


def save_snapshot(user_id: str, total_value: float, assets: dict) -> bool:
    """Haftalik snapshot kaydet."""
    try:
        supabase = get_supabase_client()
        
        result = supabase.table('snapshots').insert({
            'user_id': user_id,
            'total_value_try': total_value,
            'assets': assets,
            'week_number': datetime.now().isocalendar()[1]
        }).execute()
        
        return True
        
    except Exception as e:
        logger.error(f"Snapshot kaydetme hatasi: {e}")
        return False


def load_snapshots(user_id: str, limit: int = 52) -> list:
    """Kullanicinin snapshot'larini yukle."""
    try:
        supabase = get_supabase_client()
        
        result = supabase.table('snapshots')\
            .select('*')\
            .eq('user_id', user_id)\
            .order('created_at', desc=True)\
            .limit(limit)\
            .execute()
        
        if result.data:
            return list(reversed(result.data))
        
        return []
        
    except Exception as e:
        logger.error(f"Snapshot yukleme hatasi: {e}")
        return []


def get_latest_snapshot(user_id: str) -> Optional[dict]:
    """En son snapshot'i getir."""
    try:
        supabase = get_supabase_client()
        
        result = supabase.table('snapshots')\
            .select('*')\
            .eq('user_id', user_id)\
            .order('created_at', desc=True)\
            .limit(1)\
            .single()\
            .execute()
        
        return result.data
        
    except Exception as e:
        return None


def should_take_weekly_snapshot(user_id: str) -> bool:
    """Bu hafta snapshot alinmis mi kontrol et."""
    today = datetime.now()
    
    if today.weekday() != 4:
        return False
    
    current_week = today.isocalendar()[1]
    
    try:
        supabase = get_supabase_client()
        
        result = supabase.table('snapshots')\
            .select('week_number')\
            .eq('user_id', user_id)\
            .eq('week_number', current_week)\
            .execute()
        
        return len(result.data) == 0
        
    except Exception as e:
        return False


def delete_all_snapshots(user_id: str) -> bool:
    """Kullanicinin tum snapshot'larini sil."""
    try:
        supabase = get_supabase_client()
        
        supabase.table('snapshots').delete().eq('user_id', user_id).execute()
        
        return True
        
    except Exception as e:
        logger.error(f"Snapshot silme hatasi: {e}")
        return False
