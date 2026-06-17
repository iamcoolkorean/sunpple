import hashlib
import streamlit as st
from supabase import create_client, Client
from datetime import date

@st.cache_resource
def get_supabase_client():
    url = st.secrets["SUPABASE_URL"]
    key = st.secrets["SUPABASE_KEY"]
    return create_client(url, key)

def _hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

def register_user(user_id, password, name):
    supabase = get_supabase_client()
    existing = supabase.table("users").select("user_id").eq("user_id", user_id).execute()
    if existing.data:
        return False
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

def set_journey_start_date(user_id, start_date_str):
    supabase = get_supabase_client()
    current = supabase.table("users").select("journey_start_date").eq("user_id", user_id).execute()
    if current.data and current.data[0]["journey_start_date"] is not None:
        return
    supabase.table("users").update({"journey_start_date": start_date_str}).eq("user_id", user_id).execute()

def save_messages(user_id, messages):
    supabase = get_supabase_client()
    supabase.table("messages").delete().eq("user_id", user_id).execute()
    for msg in messages:
        supabase.table("messages").insert({
            "user_id": user_id,
            "day_number": msg.get("day_number", 1),
            "role": msg["role"],
            "content": msg["content"]
        }).execute()

def load_messages(user_id):
    supabase = get_supabase_client()
    result = supabase.table("messages").select("*").eq("user_id", user_id).order("created_at").execute()
    if result.data:
        return [{"role": m["role"], "content": m["content"], "day_number": m["day_number"]} for m in result.data]
    return []

def delete_user(user_id, password):
    supabase = get_supabase_client()
    result = supabase.table("users").select("password_hash").eq("user_id", user_id).execute()
    if not result.data or len(result.data) == 0:
        return False, "존재하지 않는 사용자입니다."
    stored_hash = result.data[0]["password_hash"]
    if stored_hash != _hash_password(password):
        return False, "비밀번호가 일치하지 않습니다."
    supabase.table("users").delete().eq("user_id", user_id).execute()
    return True, "탈퇴가 완료되었습니다."
