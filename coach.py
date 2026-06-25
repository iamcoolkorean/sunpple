import google.generativeai as genai
import streamlit as st
import time
import random
from datetime import datetime, timedelta

class SunppleCoach:
    def __init__(self):
        self.api_keys = []
        for i in range(1, 9):
            key = st.secrets.get(f"GEMINI_API_KEY_{i}")
            if key:
                self.api_keys.append(key)
        if not self.api_keys:
            raise ValueError("GEMINI_API_KEY_1 ~ 8 중 최소 하나는 설정해야 합니다.")
        
        self.key_status = {i: {'cooldown_until': datetime.min, 'fail_count': 0} for i in range(len(self.api_keys))}
        self.system_prompt = """당신은 '선플(Sunpple)'입니다. 7일간의 커리어 디스커버리 여정을 함께하는 AI 커리어 동반자입니다.

[말투와 태도]
- 따뜻하고 비판 없는 호기심을 보여주세요.
- "~군요", "~네요", "~셨군요" 같은 부드러운 종결어미를 사용하세요.
- 사용자의 답변을 절대 평가하거나 판단하지 마세요.
- 답변이 짧으면 구체적 경험으로 자연스럽게 유도하세요.
- 모든 질문은 한 번에 하나씩만 하세요.
- 이모지는 가끔만 사용하세요 (☀️, 🌱, 💡 등).

[중요 규칙]
- 하루에 3~5개 정도의 질문을 자연스럽게 나누어 대화하세요.
- 사용자의 이전 답변을 참조하여 연결된 대화를 이어가세요.
- 오늘의 주제에 맞게 대화를 이끌어가되, 사용자의 페이스를 존중하세요.
- 각 대화의 마지막에는 따뜻하게 마무리하고 "내일 또 만나요"라는 느낌을 주세요.
- 당신은 사용자의 성격보다 '직무 역량'과 '산업 적합도'를 분석하는 커리어 코치입니다.  
  단, 업무 성향(work style)은 중요한 데이터이므로 반드시 수집하세요.
- 모든 질문은 가능한 한 보기(선택지)를 제공하여 사용자가 쉽게 답할 수 있도록 하세요.
- 응답은 항상 완전한 문장으로 마무리하세요. 중간에 끝내지 마세요."""

    # ────────────── API 키 순환 / 호출 로직 (기존과 동일) ──────────────
    def _get_available_key(self):
        now = datetime.now()
        available = [i for i, status in self.key_status.items() if now >= status['cooldown_until']]
        if not available:
            min_cooldown = min(status['cooldown_until'] for status in self.key_status.values())
            wait_time = max(0, (min_cooldown - now).total_seconds())
            st.warning(f"모든 API 키가 일시적 제한 상태입니다. {wait_time:.1f}초 후 자동 재시도됩니다.")
            time.sleep(wait_time + 1)
            return self._get_available_key()
        return random.choice(available)

    def _handle_rate_limit(self, key_index):
        fail_count = self.key_status[key_index]['fail_count'] + 1
        cooldown_seconds = min(2 ** fail_count, 60)
        self.key_status[key_index]['fail_count'] = fail_count
        self.key_status[key_index]['cooldown_until'] = datetime.now() + timedelta(seconds=cooldown_seconds)
        st.info(f"API 요청이 일시적으로 많아 {cooldown_seconds}초 후 다시 시도합니다. (키 {key_index+1})")

    def _truncate_conversation(self, conversation, max_turns=8):
        if len(conversation) > max_turns:
            system_msgs = [msg for msg in conversation if msg["role"] == "system"]
            other_msgs = [msg for msg in conversation if msg["role"] != "system"]
            return system_msgs + other_msgs[-(max_turns):]
        return conversation

    def _call_gemini(self, conversation, max_retries=5):
        last_error = None
        conversation = self._truncate_conversation(conversation)
        for attempt in range(max_retries):
            key_index = self._get_available_key()
            key = self.api_keys[key_index]
            try:
                genai.configure(api_key=key)
                model = genai.GenerativeModel(
                    model_name="gemini-2.5-flash",
                    generation_config={"temperature": 0.7, "max_output_tokens": 2048}
                )
                safety_settings = [
                    {"category": "HARM_CATEGORY_HARASSMENT", "threshold": "BLOCK_NONE"},
                    {"category": "HARM_CATEGORY_HATE_SPEECH", "threshold": "BLOCK_NONE"},
                    {"category": "HARM_CATEGORY_SEXUALLY_EXPLICIT", "threshold": "BLOCK_NONE"},
                    {"category": "HARM_CATEGORY_DANGEROUS_CONTENT", "threshold": "BLOCK_NONE"},
                ]
                gemini_messages = []
                system_content = None
                for msg in conversation:
                    if msg["role"] == "system":
                        system_content = msg["content"]
                    elif msg["role"] == "user":
                        content = msg["content"]
                        if system_content:
                            content = f"[지침]\n{system_content}\n\n---\n\n{content}"
                            system_content = None
                        gemini_messages.append({"role": "user", "parts": [content]})
                    elif msg["role"] == "assistant":
                        gemini_messages.append({"role": "model", "parts": [msg["content"]]})
                if system_content and gemini_messages:
                    gemini_messages[0]["parts"][0] = f"[지침]\n{system_content}\n\n---\n\n{gemini_messages[0]['parts'][0]}"
                elif system_content and not gemini_messages:
                    gemini_messages.append({"role": "user", "parts": [f"[지침]\n{system_content}"]})
                if gemini_messages and gemini_messages[0]["role"] == "model":
                    gemini_messages.insert(0, {"role": "user", "parts": ["(시작)"]})
                if gemini_messages and gemini_messages[-1]["role"] == "model":
                    gemini_messages.pop()
                if len(gemini_messages) == 1:
                    chat = model.start_chat(history=[])
                    response = chat.send_message(gemini_messages[0]["parts"][0], safety_settings=safety_settings)
                else:
                    chat = model.start_chat(history=gemini_messages[:-1])
                    response = chat.send_message(gemini_messages[-1]["parts"][0], safety_settings=safety_settings)
                full_response = response.text
                while response.candidates and response.candidates[0].finish_reason.name == 'MAX_TOKENS':
                    response = chat.send_message("계속해서 이어서 작성해 주세요. 완전한 문장으로 마무리해 주세요.", safety_settings=safety_settings)
                    full_response += response.text
                self.key_status[key_index]['fail_count'] = 0
                return full_response.strip()
            except Exception as e:
                last_error = e
                if "429" in str(e) or "quota" in str(e).lower() or "rate" in str(e).lower():
                    self._handle_rate_limit(key_index)
                    continue
                else:
                    break
        return f"죄송해요, 잠시 응답을 생성하기 어렵네요. 다시 시도해 주시겠어요? ☀️\n\n(오류: {str(last_error)[:100]})"

    # ────────────── 오프닝 / 응답 / 지침 ──────────────
    def get_opening(self, day_number, user_data):
        name = user_data.get("name", "사용자")
        openings = {
            1: f"""안녕하세요, {name}님! ☀️
저는 당신의 커리어 동반자 **선플(Sunpple)**이라고 해요.
앞으로 7일 동안 매일 저녁 짧은 대화를 통해 당신의 하루를 돌아보고, 결국엔 "당신만의 무기"를 찾는 여정을 함께하려고 합니다.
오늘은 첫날이니까, 당신이 어떤 길을 걸어왔는지 가볍게 이야기해볼게요.
정답도 없고, 잘못된 답변도 없어요. 그냥 당신의 이야기를 들려주세요.
먼저, 현재(혹은 마지막) 학교와 전공을 알려주실래요?""",
            2: f"""{name}님, 오늘 하루는 어떠셨나요? ☀️
오늘은 당신이 실제로 몰입했던 경험을 통해 당신의 숨은 재능을 발견해볼 거예요.
최근 1주일 안에 **시간 가는 줄 모르고 몰입했던 일**이 있다면 하나만 떠올려 주세요.""",
            3: f"""{name}님, 오늘 하루도 수고 많으셨어요. 🌱
오늘은 당신이 예상치 못한 문제를 어떻게 해결하는지, 어떤 방식으로 결정을 내리는지 살펴볼게요.
먼저, 팀 프로젝트나 아르바이트 중 예상치 못한 문제가 생겼을 때, 당신은 주로 어떤 방식으로 해결했나요?""",
            4: f"""{name}님, 오늘은 다른 사람들과의 협업 속에서 당신의 자연스러운 모습을 알아볼게요. 💡
팀으로 일할 때 당신이 가장 자주 맡는 역할은 무엇인가요?""",
            5: f"""{name}님, 벌써 5일째네요. 오늘은 당신의 관심 산업과 어떤 환경에서 가장 에너지가 생기는지 탐색해볼게요.
먼저, 다음 중 가장 관심이 가는 산업군을 2개만 골라주세요.
- IT/테크, 콘텐츠/미디어, 교육/에듀테크, 이커머스/리테일, 금융/핀테크, 헬스케어/바이오, 게임, 엔터테인먼트/공연, 사회적 기업/NGO/공공, 제조/하드웨어""",
            6: f"""{name}님, 오늘은 제가 지난 5일간의 대화를 종합해서, 당신만을 위한 커리어 가설을 준비해왔어요! 🎯
먼저, 제가 발견한 당신의 핵심 강점과 업무 성향을 요약해드릴게요.
그런 다음, **3가지 커리어 방향을 '산업 → 역할 → 전망' 목록**으로 먼저 보여드릴게요.
그중에서 가장 관심 가는 것을 선택하시면, 그에 대해 자세히 설명해드리겠습니다.""",
            7: f"""{name}님, 드디어 마지막 날이네요! 🎉
오늘은 어제 가장 마음에 들어하셨던 커리어 가설을 실제로 **테스트할 계획**을 함께 만들어볼게요.
Phase 1(탐색), Phase 2(경험), Phase 3(진입) 순서로 **실제 해커톤, 공모전, 채용 공고**를 찾아서 구체적인 링크와 함께 안내해드릴게요."""
        }
        return openings.get(day_number, f"{name}님, 오늘 하루는 어떠셨나요?")

    def get_response(self, day_number, messages, user_data):
        day_instructions = self._get_day_instructions(day_number, user_data, messages)
        conversation = [{"role": "system", "content": self.system_prompt + "\n\n" + day_instructions}]
        conversation.extend(messages)
        return self._call_gemini(conversation)

    def _get_day_instructions(self, day_number, user_data, messages):
        name = user_data.get("name", "사용자")
        instructions = {
            1: f"""[Day 1 지침 - 배경 수집]
{name}님의 전공, 경험, 잘하는 일, 흥미를 수집하세요.
질문: 전공, 몰입 과제와 실제 행동, 잘하는 유형(보기), 무보수 활동, 배운 기술.""",
            2: f"""[Day 2 지침 - 몰입]
최근 몰입 경험, 유형(보기), 사용 도구, 잘한다는 피드백을 수집하세요.""",
            3: f"""[Day 3 지침 - 문제 해결]
문제 해결 방식(보기), 의사 결정 방식(보기), 자주 사용하는 도구를 수집하세요.""",
            4: f"""[Day 4 지침 - 협업 성향]
팀 역할(보기), 갈등 반응(보기), 피드백 반응(보기), 셀프 피드백(보기)을 수집하세요.""",
            5: f"""[Day 5 지침 - 산업/환경]
관심 산업(보기), 해결하고 싶은 문제 유형(보기), 선호 업무 환경(보기), 마감 반응(보기), 롤모델을 수집하세요.""",
            6: f"""[Day 6 지침 - 커리어 가설 (3단계 추천)]
1. 지난 5일간의 데이터를 요약하여 사용자의 학과, 재능, 강점, 관심 산업을 먼저 보여주세요.
2. **3가지 커리어 방향을 아래 형식으로 목록화**하여 제시하세요:
   - 산업: (예: 콘텐츠/미디어)
   - 역할: (예: UX 라이터/콘텐츠 디자이너)
   - 전망: (예: AI 시대에 더 중요해지는 직무, 연봉 성장 가능성 등)
   반드시 3개의 목록을 한 번에 보여주고, 사용자가 하나를 선택하도록 유도하세요.
3. 사용자가 선택하면, 그 직무에 대해 **왜 {name}님에게 맞는지 구체적인 데이터 근거(학과, 재능, 성향)**와 함께 상세히 설명하세요.
4. 나머지 2개도 궁금하면 추가로 설명해줄 수 있다고 알려주세요.""",
            7: f"""[Day 7 지침 - 검증 로드맵 (실제 정보 검색)]
선택된 가설을 바탕으로 3단계 로드맵을 제공하세요.
**중요: 아래 정보는 실제로 존재하는 최신 해커톤, 공모전, 채용 공고여야 합니다.**
- Phase 1 탐색: {name}님의 관심 산업 관련 뉴스레터, 유튜브, 링크드인 검색 키워드
- Phase 2 경험: {name}님의 강점(피그마, 애펙 등)을 활용할 실제 해커톤/공모전 (2025~2026년 기준, 접수 링크나 검색 키워드 포함)
- Phase 3 진입: 관련 기업 유형, 실제 채용 플랫폼(원티드, 로켓펀치 등)과 검색 키워드
마지막으로 7일 여정을 마무리하는 **최종 리포트**를 생성하세요:
- 사용자의 핵심 강점 요약
- 추천 커리어 가설
- 3단계 실행 로드맵 요약
- "당신의 무기" 한 줄 정의"""
        }
        return instructions.get(day_number, f"{name}님과의 대화를 이어가세요.")
