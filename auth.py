import hashlib
import streamlit as st
from supabase import create_client, Client

# Supabase 클라이언트 초기화
@st.cache_resource
def get_supabase_client():
    url = st.secrets["SUPABASE_URL"]
    key = st.secrets["SUPABASE_KEY"]
    return create_client(url, key)

def _hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

def register_user(user_id, password, name):
    supabase = get_supabase_client()
    # 중복 확인
    existing = supabase.table("users").select("user_id").eq("user_id", user_id).execute()
    if existing.data:
        return False
    # 저장
    supabase.table("users").insert({
        "user_id": user_id,
        "password_hash": _hash_password(password),
        "name": name
    }).execute()
    return True

def authenticate(user_id, password):
    supabase = get_supabase_client()
    result = supabase.table("users").select("*").eq("user_id", user_id).execute()
    if result.data and len(result.data) > 0:
        user = result.data[0]
        if user["password_hash"] == _hash_password(password):
            return user
    return None

def get_user_data(user_id):
    supabase = get_supabase_client()
    result = supabase.table("users").select("*").eq("user_id", user_id).execute()
    if result.data and len(result.data) > 0:
        return result.data[0]
    return None

def save_messages(user_id, messages):
    """해당 사용자의 기존 메시지를 모두 지우고 새로 저장 (간단한 방법)"""
    supabase = get_supabase_client()
    # 기존 메시지 삭제
    supabase.table("messages").delete().eq("user_id", user_id).execute()
    # 새로 삽입
    for msg in messages:
        supabase.table("messages").insert({
            "user_id": user_id,
            "day_number": msg.get("day_number", 1),  # day_number 정보가 필요하므로 messages에 day_number를 포함해야 함
            "role": msg["role"],
            "content": msg["content"]
        }).execute()

def load_messages(user_id):
    """해당 사용자의 모든 메시지를 시간순으로 불러오기"""
    supabase = get_supabase_client()
    result = supabase.table("messages").select("*").eq("user_id", user_id).order("created_at").execute()
    if result.data:
        # 반환 형식을 [{"role": ..., "content": ...}] 형태로 변환
        return [{"role": m["role"], "content": m["content"], "day_number": m["day_number"]} for m in result.data]
    return []
