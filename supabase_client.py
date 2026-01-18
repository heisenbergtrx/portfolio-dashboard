"""
supabase_client.py - Supabase Authentication & Database
========================================================

Google Auth + Email/Password ile giriş ve kullanıcı verisi yönetimi.

Yazar: Portfolio Dashboard
Tarih: Ocak 2026
"""

import json
import logging
from datetime import datetime
from typing import Any, Optional

import streamlit as st
from supabase import create_client, Client

logger = logging.getLogger(__name__)

# Supabase credentials
SUPABASE_URL = "https://ckxbytrgxrdrxtkbaqex.supabase.co"
SUPABASE_KEY = st.secrets.get("SUPABASE_KEY", "")

# Fallback for local development
if not SUPABASE_KEY:
    SUPABASE_KEY = "sb_publishable_KRs5qGHDBj9EKdi7lWUIrA_LlWSirRN"


def get_supabase_client() -> Client:
    """Supabase client oluştur."""
    return create_client(SUPABASE_URL, SUPABASE_KEY)


def init_auth_state():
    """Auth session state'i başlat."""
    if 'user' not in st.session_state:
        st.session_state.user = None
    if 'access_token' not in st.session_state:
        st.session_state.access_token = None


def get_current_user() -> Optional[dict]:
    """Mevcut kullanıcıyı döndür."""
    return st.session_state.get('user', None)


def is_logged_in() -> bool:
    """Kullanıcı giriş yapmış mı?"""
    return st.session_state.get('user') is not None


def render_login_page():
    """Login sayfasını render et."""
    st.markdown("""
    <style>
        .login-container {
            max-width: 400px;
            margin: 100px auto;
            padding: 40px;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            border-radius: 20px;
            text-align: center;
            color: white;
        }
    </style>
    """, unsafe_allow_html=True)
    
    col1, col2, col3 = st.columns([1, 2, 1])
    
    with col2:
        st.markdown("# 📊 Portföy Dashboard")
        st.markdown("### Profesyonel Portföy Takibi")
        st.markdown("---")
        
        st.markdown("""
        ✅ Gerçek zamanlı fiyat takibi  
        ✅ Risk analizi & Beta hesaplama  
        ✅ Haftalık snapshot'lar  
        ✅ Benchmark karşılaştırma  
        """)
        
        st.markdown("---")
        
        # Tab seçimi: Email veya Google
        tab1, tab2 = st.tabs(["📧 Email ile Giriş", "🔑 Google ile Giriş"])
        
        with tab1:
            render_email_login()
        
        with tab2:
            render_google_login()
        
        st.markdown("---")
        st.caption("Verileriniz güvenle Supabase'de saklanır.")


def render_email_login():
    """Email/Password login formu."""
    supabase = get_supabase_client()
    
    # Login veya Register seçimi
    auth_mode = st.radio("", ["Giriş Yap", "Kayıt Ol"], horizontal=True, label_visibility="collapsed")
    
    email = st.text_input("Email", placeholder="ornek@email.com", key="email_input")
    password = st.text_input("Şifre", type="password", placeholder="••••••••", key="password_input")
    
    if auth_mode == "Kayıt Ol":
        password_confirm = st.text_input("Şifre Tekrar", type="password", placeholder="••••••••", key="password_confirm")
        
        if st.button("📝 Kayıt Ol", type="primary", use_container_width=True):
            if not email or not password:
                st.error("Email ve şifre gerekli!")
                return
            
            if password != password_confirm:
                st.error("Şifreler eşleşmiyor!")
                return
            
            if len(password) < 6:
                st.error("Şifre en az 6 karakter olmalı!")
                return
            
            try:
                result = supabase.auth.sign_up({
                    "email": email,
                    "password": password
                })
                
                if result.user:
                    st.success("✅ Kayıt başarılı! Email'inizi kontrol edin veya direkt giriş yapın.")
                else:
                    st.error("Kayıt hatası!")
                    
            except Exception as e:
                error_msg = str(e)
                if "already registered" in error_msg.lower():
                    st.error("Bu email zaten kayıtlı!")
                else:
                    st.error(f"Hata: {error_msg}")
    
    else:  # Giriş Yap
        if st.button("🔓 Giriş Yap", type="primary", use_container_width=True):
            if not email or not password:
                st.error("Email ve şifre gerekli!")
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
                    st.success("✅ Giriş başarılı!")
                    st.rerun()
                else:
                    st.error("Giriş hatası!")
                    
            except Exception as e:
                error_msg = str(e)
                if "invalid" in error_msg.lower():
                    st.error("Email veya şifre yanlış!")
                else:
                    st.error(f"Hata: {error_msg}")


def render_google_login():
    """Google OAuth login."""
    supabase = get_supabase_client()
    
    st.info("⚠️ Google OAuth şu an yapılandırılıyor. Sorun yaşarsanız Email ile giriş yapın.")
    
    if st.button("🔑 Google ile Giriş Yap", type="primary", use_container_width=True):
        try:
            auth_response = supabase.auth.sign_in_with_oauth({
                "provider": "google"
            })
            
            if auth_response and auth_response.url:
                st.markdown(f'<meta http-equiv="refresh" content="0;url={auth_response.url}">', unsafe_allow_html=True)
                st.info("Google'a yönlendiriliyorsunuz...")
                
        except Exception as e:
            st.error(f"Giriş hatası: {e}")


def handle_oauth_callback():
    """OAuth callback'i işle."""
    query_params = st.query_params
    
    # Hash fragment'tan token al (Supabase bazen böyle gönderiyor)
    if 'access_token' in query_params:
        access_token = query_params['access_token']
        refresh_token = query_params.get('refresh_token', '')
        
        try:
            supabase = get_supabase_client()
            session = supabase.auth.set_session(access_token, refresh_token)
            
            if session and session.user:
                st.session_state.user = {
                    'id': session.user.id,
                    'email': session.user.email,
                    'name': session.user.user_metadata.get('full_name', session.user.email)
                }
                st.session_state.access_token = access_token
                st.query_params.clear()
                return True
                
        except Exception as e:
            logger.error(f"OAuth callback hatası: {e}")
    
    return False


def logout():
    """Çıkış yap."""
    try:
        supabase = get_supabase_client()
        supabase.auth.sign_out()
    except:
        pass
    
    st.session_state.user = None
    st.session_state.access_token = None
    st.rerun()


# =============================================================================
# DATABASE OPERATIONS
# =============================================================================

def save_portfolio_config(user_id: str, config: dict) -> bool:
    """Portföy config'ini kaydet."""
    try:
        supabase = get_supabase_client()
        
        result = supabase.table('portfolios').upsert({
            'user_id': user_id,
            'config': config,
            'updated_at': datetime.now().isoformat()
        }, on_conflict='user_id').execute()
        
        return True
        
    except Exception as e:
        logger.error(f"Config kaydetme hatası: {e}")
        return False


def load_portfolio_config(user_id: str) -> Optional[dict]:
    """Portföy config'ini yükle."""
    try:
        supabase = get_supabase_client()
        
        result = supabase.table('portfolios').select('config').eq('user_id', user_id).single().execute()
        
        if result.data:
            return result.data['config']
        
        return None
        
    except Exception as e:
        logger.error(f"Config yükleme hatası: {e}")
        return None


def save_snapshot(user_id: str, total_value: float, assets: dict) -> bool:
    """Haftalık snapshot kaydet."""
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
        logger.error(f"Snapshot kaydetme hatası: {e}")
        return False


def load_snapshots(user_id: str, limit: int = 52) -> list[dict]:
    """Kullanıcının snapshot'larını yükle."""
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
        logger.error(f"Snapshot yükleme hatası: {e}")
        return []


def get_latest_snapshot(user_id: str) -> Optional[dict]:
    """En son snapshot'ı getir."""
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
    """Bu hafta snapshot alınmış mı kontrol et."""
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
    """Kullanıcının tüm snapshot'larını sil."""
    try:
        supabase = get_supabase_client()
        
        supabase.table('snapshots').delete().eq('user_id', user_id).execute()
        
        return True
        
    except Exception as e:
        logger.error(f"Snapshot silme hatası: {e}")
        return False
