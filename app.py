import streamlit as st
from datetime import datetime, timedelta
from pathlib import Path

from auth import authenticate, register_user, get_user_data, save_messages, load_messages
from coach import SunppleCoach

# --- 초기 설정 ---
st.set_page_config(
    page_title="Sunpple - 7일 커리어 디스커버리",
    page_icon="☀️",
    layout="centered"
)

# 데이터 디렉토리 생성 (더 이상 필요 없지만 Path 객체 남아도 됨)
Path("data").mkdir(exist_ok=True)

# --- 세션 상태 초기화 ---
if "user" not in st.session_state:
    st.session_state.user = None
if "authenticated" not in st.session_state:
    st.session_state.authenticated = False
if "messages" not in st.session_state:
    st.session_state.messages = []
if "coach" not in st.session_state:
    try:
        st.session_state.coach = SunppleCoach()
    except ValueError as e:
        st.error(f"API 키 설정 오류: {e}")
        st.stop()

# --- CSS 스타일 ---
st.markdown("""
<style>
    .main-header { font-size: 2.5rem; font-weight: 700; color: #FF6B35; text-align: center; margin-bottom: 0.5rem; }
    .sub-header { font-size: 1.2rem; color: #666; text-align: center; margin-bottom: 2rem; }
    .day-badge { background: linear-gradient(135deg, #FF6B35, #FF8C42); color: white; padding: 0.3rem 1rem; border-radius: 20px; font-size: 0.9rem; display: inline-block; margin-bottom: 1rem; }
    .user-msg { background: #f0f0f0; padding: 0.8rem 1rem; border-radius: 15px; margin: 0.5rem 0; }
    .coach-msg { background: #FFF3ED; padding: 0.8rem 1rem; border-radius: 15px; margin: 0.5rem 0; border-left: 4px solid #FF6B35; }
</style>
""", unsafe_allow_html=True)

# --- 로그인/회원가입 ---
if not st.session_state.authenticated:
    st.markdown('<div class="main-header">☀️ Sunpple</div>', unsafe_allow_html=True)
    st.markdown('<div class="sub-header">당신의 무기를 찾는 7일간의 여정</div>', unsafe_allow_html=True)
    
    tab1, tab2 = st.tabs(["로그인", "회원가입"])
    with tab1:
        with st.form("login_form"):
            user_id = st.text_input("아이디", key="login_id")
            password = st.text_input("비밀번호", type="password", key="login_pw")
            submit_login = st.form_submit_button("로그인", use_container_width=True)
            if submit_login:
                user_data = authenticate(user_id, password)
                if user_data:
                    st.session_state.user = user_id
                    st.session_state.authenticated = True
                    st.session_state.user_data = user_data
                    st.session_state.messages = load_messages(user_id)
                    st.rerun()
                else:
                    st.error("아이디 또는 비밀번호가 일치하지 않습니다.")
    with tab2:
        with st.form("register_form"):
            new_id = st.text_input("아이디", key="register_id")
            new_pw = st.text_input("비밀번호", type="password", key="register_pw")
            new_pw_confirm = st.text_input("비밀번호 확인", type="password", key="register_pw_confirm")
            new_name = st.text_input("이름 (닉네임)", key="register_name")
            submit_register = st.form_submit_button("회원가입", use_container_width=True)
            if submit_register:
                if new_pw != new_pw_confirm:
                    st.error("비밀번호가 일치하지 않습니다.")
                elif len(new_id) < 3:
                    st.error("아이디는 3자 이상이어야 합니다.")
                elif register_user(new_id, new_pw, new_name):
                    st.success("회원가입 완료! 로그인 탭에서 로그인해주세요.")
                else:
                    st.error("이미 존재하는 아이디입니다.")
    st.stop()

# --- 로그인 후 ---
st.markdown('<div class="main-header">☀️ Sunpple</div>', unsafe_allow_html=True)

today = datetime.now().date()
weekday = today.weekday()
day_number = weekday + 1 if weekday < 7 else 7  # 7일까지만

if day_number > 7:
    st.success("7일간의 여정이 완료되었습니다! 🎉")
    st.info("지난 대화를 복습하거나 새로운 목표를 세워보세요.")
    st.stop()

# 사이드바
with st.sidebar:
    st.markdown(f"### 👋 {st.session_state.user_data.get('name', st.session_state.user)}님")
    st.markdown(f"**Day {day_number}/7**")
    st.progress(day_number / 7, text=f"여정 {day_number}/7")
    for i in range(1, 8):
        if i < day_number:
            st.markdown(f"✅ Day {i} - 완료")
        elif i == day_number:
            st.markdown(f"🔵 **Day {i} - 오늘**")
        else:
            st.markdown(f"⏳ Day {i} - 대기")
    st.divider()
    if st.button("로그아웃", use_container_width=True):
        # 이미 매번 저장하므로 추가 저장 없이 세션만 정리
        st.session_state.authenticated = False
        st.session_state.user = None
        st.session_state.messages = []
        st.rerun()

# 오늘의 대화
day_titles = {
    1: "당신의 지도를 그리다",
    2: "에너지의 발견",
    3: "갈등과 선택의 순간",
    4: "타인의 시선, 내면의 목소리",
    5: "진짜 내가 원하는 것",
    6: "가능성의 지도",
    7: "당신의 무기와 작전 지도",
}
day_korean = ["월", "화", "수", "목", "금", "토", "일"]
st.markdown(f'<div class="day-badge">☀️ Day {day_number} - {day_korean[day_number-1]}요일</div>', unsafe_allow_html=True)
st.markdown(f"### {day_titles[day_number]}")

# 이전 대화 표시 (day_number 포함해서 저장했으므로 표시할 때는 role, content만)
for msg in st.session_state.messages:
    if msg["role"] == "user":
        st.markdown(f'<div class="user-msg">🧑‍🎓 {msg["content"]}</div>', unsafe_allow_html=True)
    else:
        st.markdown(f'<div class="coach-msg">☀️ {msg["content"]}</div>', unsafe_allow_html=True)

coach = st.session_state.coach
if len(st.session_state.messages) == 0:
    first_message = coach.get_opening(day_number, st.session_state.user_data)
    st.session_state.messages.append({"role": "assistant", "content": first_message, "day_number": day_number})
    save_messages(st.session_state.user, st.session_state.messages)
    st.markdown(f'<div class="coach-msg">☀️ {first_message}</div>', unsafe_allow_html=True)

# 입력창
with st.form("chat_form", clear_on_submit=True):
    user_input = st.text_input("당신의 이야기를 들려주세요...", key="user_input", placeholder="편안하게 답변해주세요.")
    submit = st.form_submit_button("답변하기", use_container_width=True)
    if submit and user_input:
        st.session_state.messages.append({"role": "user", "content": user_input, "day_number": day_number})
        pure_messages = [{"role": m["role"], "content": m["content"]} for m in st.session_state.messages]
        with st.spinner("Sunpple이 생각 중..."):
            response = coach.get_response(day_number=day_number, messages=pure_messages, user_data=st.session_state.user_data)
        st.session_state.messages.append({"role": "assistant", "content": response, "day_number": day_number})
        save_messages(st.session_state.user, st.session_state.messages)
        st.rerun()

st.divider()
st.caption("☀️ Sunpple - 당신의 커리어 동반자 | 7일간의 디스커버리 여정")
st.caption(f"오늘은 Day {day_number}, '{day_titles[day_number]}' 주제로 대화 중입니다.")
