import streamlit as st
from datetime import date
from auth import (
    authenticate, register_user, get_user_data,
    save_messages, load_messages, set_current_day, delete_user
)
from coach import SunppleCoach

# --- 초기 설정 ---
st.set_page_config(page_title="Sunpple - 7일 커리어 디스커버리", page_icon="☀️", layout="centered")

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

# --- CSS ---
st.markdown("""
<style>
    .main-header { font-size: 2.5rem; font-weight: 700; color: #FF6B35; text-align: center; margin-bottom: 0.5rem; }
    .sub-header { font-size: 1.2rem; color: #666; text-align: center; margin-bottom: 2rem; }
    .day-badge { background: linear-gradient(135deg, #FF6B35, #FF8C42); color: white; padding: 0.3rem 1rem; border-radius: 20px; font-size: 0.9rem; display: inline-block; margin-bottom: 1rem; }
    .user-msg { background: #f0f0f0; padding: 0.8rem 1rem; border-radius: 15px; margin: 0.5rem 0; }
    .coach-msg { background: #FFF3ED; padding: 0.8rem 1rem; border-radius: 15px; margin: 0.5rem 0; border-left: 4px solid #FF6B35; }
    .inactive { opacity: 0.6; }
</style>
""", unsafe_allow_html=True)

# --- 로그인 / 회원가입 (기존과 동일) ---
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
                    # 현재 일차에 해당하는 메시지만 로드
                    st.session_state.current_day = user_data.get("current_day", 1)
                    st.session_state.messages = load_messages(user_id, st.session_state.current_day)
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

user_id = st.session_state.user
user_data = st.session_state.user_data
current_day = user_data.get("current_day", 1)   # 사용자가 현재 진행 중인 일차 (1~7)

day_titles = {
    1: "당신의 지도를 그리다",
    2: "에너지의 발견",
    3: "갈등과 선택의 순간",
    4: "타인의 시선, 내면의 목소리",
    5: "진짜 내가 원하는 것",
    6: "가능성의 지도",
    7: "당신의 무기와 작전 지도",
}

# --- 사이드바 ---
with st.sidebar:
    st.markdown(f"### 👋 {user_data.get('name', user_id)}님")
    st.markdown(f"**현재 Day {current_day}/7**")
    st.progress(current_day / 7, text=f"여정 {current_day}/7")
    
    # 일차별 상태 표시
    for i in range(1, 8):
        if i < current_day:
            st.markdown(f"✅ Day {i} - 완료")
        elif i == current_day:
            st.markdown(f"🔵 **Day {i} - 진행 중**")
        else:
            st.markdown(f"⏳ Day {i}")
    
    st.divider()
    
    # 과거 대화 보기
    if current_day > 1:
        past_day = st.selectbox("📖 과거 대화 보기", list(range(1, current_day)), index=None, placeholder="선택...")
        if past_day:
            st.session_state.viewing_past_day = past_day
            # 해당 일차 메시지 로드
            past_messages = load_messages(user_id, past_day)
            st.session_state.past_messages = past_messages
            st.rerun()
        if "viewing_past_day" in st.session_state:
            if st.button("현재 대화로 돌아가기"):
                del st.session_state.viewing_past_day
                st.session_state.messages = load_messages(user_id, current_day)
                st.rerun()

    st.divider()
    
    # 현재 일차 건너뛰기 (오늘 건너뛰기)
    if current_day < 7:
        if st.button("⏩ 오늘 건너뛰기", use_container_width=True):
            set_current_day(user_id, current_day + 1)
            st.session_state.user_data["current_day"] = current_day + 1
            st.session_state.messages = load_messages(user_id, current_day + 1)
            st.rerun()
    elif current_day == 7:
        st.info("마지막 날입니다. 대화를 마치면 최종 리포트를 받습니다.")
    
    st.divider()
    if st.button("로그아웃", use_container_width=True):
        st.session_state.authenticated = False
        st.session_state.user = None
        st.session_state.messages = []
        st.rerun()
    
    with st.expander("회원 탈퇴"):
        st.warning("탈퇴 시 모든 대화 기록이 영구 삭제되며 복구할 수 없습니다.")
        with st.form("delete_account_form"):
            del_pw = st.text_input("비밀번호 확인", type="password", key="delete_pw")
            del_submit = st.form_submit_button("탈퇴하기", use_container_width=True, type="primary")
            if del_submit:
                success, msg = delete_user(user_id, del_pw)
                if success:
                    st.success(msg)
                    st.session_state.authenticated = False
                    st.session_state.user = None
                    st.session_state.messages = []
                    st.rerun()
                else:
                    st.error(msg)

# --- 메인 화면: 현재 일차 대화 ---
# 과거 대화 보기 상태라면 해당 대화만 표시하고 입력창 숨기기
if "viewing_past_day" in st.session_state:
    past_day = st.session_state.viewing_past_day
    st.markdown(f"## 📖 Day {past_day} 대화 기록")
    for msg in st.session_state.past_messages:
        if msg["role"] == "user":
            st.markdown(f'<div class="user-msg">🧑‍🎓 {msg["content"]}</div>', unsafe_allow_html=True)
        else:
            st.markdown(f'<div class="coach-msg">☀️ {msg["content"]}</div>', unsafe_allow_html=True)
    st.stop()   # 과거 대화만 보여주고 종료

# 현재 일차 진행
day_number = current_day   # 표시할 일차
st.markdown(f'<div class="day-badge">☀️ Day {day_number} - {day_titles[day_number]}</div>', unsafe_allow_html=True)
st.markdown(f"### {day_titles[day_number]}")

# 대화 표시
for msg in st.session_state.messages:
    if msg["role"] == "user":
        st.markdown(f'<div class="user-msg">🧑‍🎓 {msg["content"]}</div>', unsafe_allow_html=True)
    else:
        st.markdown(f'<div class="coach-msg">☀️ {msg["content"]}</div>', unsafe_allow_html=True)

coach = st.session_state.coach

# 첫 진입 시 오프닝 메시지
if len(st.session_state.messages) == 0:
    opening = coach.get_opening(day_number, user_data)
    st.session_state.messages.append({"role": "assistant", "content": opening, "day_number": day_number})
    save_messages(user_id, st.session_state.messages)
    st.markdown(f'<div class="coach-msg">☀️ {opening}</div>', unsafe_allow_html=True)

# 대화 입력창 (현재 일차가 완료된 상태가 아니면 활성화)
# 완료 상태: current_day가 day_number보다 커지면 완료.
if current_day == day_number and current_day <= 7:
    with st.form("chat_form", clear_on_submit=True):
        user_input = st.text_input("당신의 이야기를 들려주세요...", key="user_input", placeholder="편안하게 답변해주세요.")
        submit = st.form_submit_button("답변하기", use_container_width=True)
        if submit and user_input:
            st.session_state.messages.append({"role": "user", "content": user_input, "day_number": day_number})
            pure = [{"role": m["role"], "content": m["content"]} for m in st.session_state.messages]
            with st.spinner("Sunpple이 생각 중..."):
                response = coach.get_response(day_number=day_number, messages=pure, user_data=user_data)
            st.session_state.messages.append({"role": "assistant", "content": response, "day_number": day_number})
            save_messages(user_id, st.session_state.messages)
            st.rerun()

    # 오늘의 대화 마치기 버튼
    if len(st.session_state.messages) > 1:   # 대화가 시작된 후에만
        st.divider()
        if st.button("✅ 오늘의 대화 마치기", use_container_width=True):
            if current_day < 7:
                set_current_day(user_id, current_day + 1)
                st.session_state.user_data["current_day"] = current_day + 1
                st.session_state.messages = load_messages(user_id, current_day + 1)
                st.rerun()
            else:
                # Day 7 완료 처리
                set_current_day(user_id, 8)   # 8로 세팅하여 완료 표시
                st.session_state.user_data["current_day"] = 8
                st.balloons()
                st.success("🎉 7일간의 여정을 완수했습니다! 아래 최종 리포트를 확인하세요.")
                # 최종 리포트 안내 표시
                st.markdown("""
                ## ☀️ 당신의 여정이 완성되었습니다.

                **지금까지의 대화를 분석한 `당신만의 무기`와 `3가지 커리어 가설`, 그리고 `3단계 검증 로드맵`이 준비되어 있습니다.**

                아래 버튼을 눌러 최종 리포트를 확인하세요.
                """)
                # (실제로는 여기서 리포트 생성 로직을 호출할 수 있습니다)
                # 이후 입력창은 사라짐
else:
    # 이미 오늘의 대화를 마친 상태 (current_day > day_number)
    if current_day <= 7:
        st.info("오늘의 대화가 완료되었습니다. 내일 다시 방문하여 다음 이야기를 나눠주세요. ☀️")
    else:
        st.balloons()
        st.success("🎉 전체 여정이 종료되었습니다! 최종 리포트를 확인하세요.")
        # 최종 리포트 보기 버튼 (추후 구현)

st.divider()
st.caption("☀️ Sunpple - 당신의 커리어 동반자 | 7일간의 디스커버리 여정")
