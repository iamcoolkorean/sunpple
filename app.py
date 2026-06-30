import streamlit as st
from datetime import date, datetime
from auth import (
    authenticate, register_user, get_user_data,
    save_messages, load_messages, set_current_day,
    delete_messages_by_day, delete_user
)
from coach import SunppleCoach

st.set_page_config(page_title="Sunpple - 7일 커리어 디스커버리", page_icon="☀️", layout="centered")

if "user" not in st.session_state: st.session_state.user = None
if "authenticated" not in st.session_state: st.session_state.authenticated = False
if "messages" not in st.session_state: st.session_state.messages = []
if "viewing_past_day" not in st.session_state: st.session_state.viewing_past_day = None
if "coach" not in st.session_state:
    try: st.session_state.coach = SunppleCoach()
    except ValueError as e: st.error(f"API 키 설정 오류: {e}"); st.stop()

st.markdown("""<style>
    .main-header { font-size: 2.5rem; font-weight: 700; color: #FF6B35; text-align: center; }
    .day-badge { background: linear-gradient(135deg, #FF6B35, #FF8C42); color: white; padding: 0.3rem 1rem; border-radius: 20px; }
    .user-msg { background: #f0f0f0; padding: 0.8rem; border-radius: 15px; margin: 0.5rem 0; }
    .coach-msg { background: #FFF3ED; padding: 0.8rem; border-radius: 15px; margin: 0.5rem 0; border-left: 4px solid #FF6B35; }
</style>""", unsafe_allow_html=True)

# ── 로그인 / 회원가입 ──
if not st.session_state.authenticated:
    st.markdown('<div class="main-header">☀️ Sunpple</div>', unsafe_allow_html=True)
    tab1, tab2 = st.tabs(["로그인", "회원가입"])
    with tab1:
        with st.form("login"):
            uid = st.text_input("아이디"); pw = st.text_input("비밀번호", type="password")
            if st.form_submit_button("로그인"):
                u = authenticate(uid, pw)
                if u:
                    st.session_state.user = uid; st.session_state.authenticated = True
                    st.session_state.user_data = u
                    st.session_state.current_day = u.get("current_day", 1)
                    st.session_state.messages = load_messages(uid, st.session_state.current_day)
                    st.rerun()
                else: st.error("불일치")
    with tab2:
        with st.form("register"):
            nid = st.text_input("아이디"); npw = st.text_input("비밀번호", type="password")
            npw2 = st.text_input("비밀번호 확인", type="password"); nm = st.text_input("닉네임")
            if st.form_submit_button("회원가입"):
                if npw != npw2: st.error("비밀번호 불일치")
                elif len(nid) < 3: st.error("3자 이상")
                elif register_user(nid, npw, nm): st.success("완료! 로그인 탭에서 로그인")
                else: st.error("중복 아이디")
    st.stop()

# ── 로그인 후 ──
user_id = st.session_state.user
user_data = st.session_state.user_data
current_day = user_data.get("current_day", 1)
day_titles = {1:"당신의 지도를 그리다",2:"에너지의 발견",3:"갈등과 선택의 순간",4:"타인의 시선, 내면의 목소리",5:"진짜 내가 원하는 것",6:"가능성의 지도",7:"당신의 무기와 작전 지도"}

with st.sidebar:
    st.markdown(f"### 👋 {user_data.get('name', user_id)}님")
    st.markdown(f"**Day {current_day}/7**")
    st.progress(current_day/7)
    for i in range(1,8):
        if i < current_day: st.markdown(f"✅ Day {i}")
        elif i == current_day: st.markdown(f"🔵 **Day {i} - 오늘**")
        else: st.markdown(f"⏳ Day {i}")
    st.divider()
    if current_day > 1:
        past = st.selectbox("📖 과거 대화 보기", list(range(1, current_day)), index=None, placeholder="Day 선택")
        if past:
            st.session_state.viewing_past_day = past
            st.session_state.past_messages = load_messages(user_id, past)
            st.rerun()
        if st.session_state.viewing_past_day and st.button("현재로 돌아가기"):
            st.session_state.viewing_past_day = None
            st.session_state.messages = load_messages(user_id, current_day)
            st.rerun()
    if st.button("🔄 오늘 대화 다시하기"):
        delete_messages_by_day(user_id, current_day)
        st.session_state.messages = []
        st.rerun()
    st.divider()
    if current_day < 7:
        if st.button("⏩ 오늘 건너뛰기"):
            set_current_day(user_id, current_day+1)
            st.session_state.user_data["current_day"] = current_day+1
            st.session_state.messages = load_messages(user_id, current_day+1)
            st.rerun()
    elif current_day == 7: st.info("마지막 날!")
    if st.button("로그아웃"):
        st.session_state.authenticated = False; st.session_state.user = None
        st.session_state.messages = []; st.rerun()
    with st.expander("회원 탈퇴"):
        with st.form("delete"):
            dpw = st.text_input("비밀번호 확인", type="password")
            if st.form_submit_button("탈퇴"):
                s, m = delete_user(user_id, dpw)
                if s: st.success(m); st.session_state.authenticated = False; st.rerun()
                else: st.error(m)

# ── 메인 ──
st.markdown(f'<div class="main-header">☀️ Sunpple</div>', unsafe_allow_html=True)

if st.session_state.viewing_past_day:
    pd = st.session_state.viewing_past_day
    st.markdown(f"## 📖 Day {pd} 대화 기록")
    for msg in st.session_state.past_messages:
        cls = "user-msg" if msg["role"]=="user" else "coach-msg"
        st.markdown(f'<div class="{cls}">{msg["content"]}</div>', unsafe_allow_html=True)
    st.stop()

day_number = current_day
st.markdown(f'<div class="day-badge">☀️ Day {day_number} - {day_titles[day_number]}</div>', unsafe_allow_html=True)

for msg in st.session_state.messages:
    cls = "user-msg" if msg["role"]=="user" else "coach-msg"
    st.markdown(f'<div class="{cls}">{msg["content"]}</div>', unsafe_allow_html=True)

coach = st.session_state.coach
if len(st.session_state.messages) == 0:
    opening = coach.get_opening(day_number, user_data)
    st.session_state.messages.append({"role":"assistant","content":opening,"day_number":day_number})
    save_messages(user_id, st.session_state.messages)
    st.markdown(f'<div class="coach-msg">☀️ {opening}</div>', unsafe_allow_html=True)

if current_day == day_number and current_day <= 7:
    with st.form("chat", clear_on_submit=True):
        ui = st.text_input("이야기를 들려주세요...", placeholder="편안하게 답변해주세요.")
        if st.form_submit_button("답변하기") and ui:
            st.session_state.messages.append({"role":"user","content":ui,"day_number":day_number})
            # ★ 모든 과거 메시지를 불러와서 합친 뒤 전송
            all_history = []
            for d in range(1, day_number+1):
                all_history.extend(load_messages(user_id, d))
            # 중복 방지 (현재 세션에 이미 있는 메시지는 제외)
            seen = {(m["role"], m["content"]) for m in st.session_state.messages}
            pure = []
            for m in all_history:
                if (m["role"], m["content"]) not in seen:
                    pure.append({"role":m["role"],"content":m["content"]})
            pure.extend([{"role":m["role"],"content":m["content"]} for m in st.session_state.messages])
            with st.spinner("생각 중..."):
                resp = coach.get_response(day_number, pure, user_data)
            st.session_state.messages.append({"role":"assistant","content":resp,"day_number":day_number})
            save_messages(user_id, st.session_state.messages)
            st.rerun()
    if len(st.session_state.messages) > 1:
        st.divider()
        if st.button("✅ 오늘의 대화 마치기"):
            if current_day < 7:
                set_current_day(user_id, current_day+1)
                st.session_state.user_data["current_day"] = current_day+1
                st.session_state.messages = load_messages(user_id, current_day+1)
                st.rerun()
            else:
                set_current_day(user_id, 8)
                st.session_state.user_data["current_day"] = 8
                st.balloons()
                st.success("🎉 7일 완료! 최종 리포트를 생성합니다...")
                all_msgs = []
                for d in range(1,8): all_msgs.extend(load_messages(user_id, d))
                pure_all = [{"role":m["role"],"content":m["content"]} for m in all_msgs]
                report_prompt = f"""[최종 리포트 생성]
사용자: {user_data.get('name')}
7일간의 대화 전체를 바탕으로 아래 항목을 포함한 커리어 리포트를 작성하세요:
1. 핵심 강점 요약
2. 추천 커리어 가설 (가장 적합한 1개)
3. 3단계 실행 로드맵 요약
4. "당신의 무기" 한 줄 정의"""
                with st.spinner("리포트 생성 중..."):
                    report = coach._call_gemini([{"role":"system","content":report_prompt}]+pure_all)
                st.markdown("## 📋 최종 커리어 리포트")
                st.markdown(report)
else:
    if current_day <= 7: st.info("오늘의 대화가 완료되었습니다. 내일 또 만나요!")
    else:
        st.success("🎉 7일 여정 완료!")
        st.markdown("## 📋 최종 커리어 리포트")
        all_msgs = []
        for d in range(1,8): all_msgs.extend(load_messages(user_id, d))
        pure_all = [{"role":m["role"],"content":m["content"]} for m in all_msgs]
        with st.spinner("리포트 생성 중..."):
            report = coach._call_gemini([{"role":"system","content":f"사용자:{user_data.get('name')}. 7일 대화 기반 최종 커리어 리포트를 작성하세요."}]+pure_all)
        st.markdown(report)

st.divider()
st.caption("☀️ Sunpple - 7일간의 디스커버리 여정")
