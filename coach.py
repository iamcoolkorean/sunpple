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
        
        # API 키 상태 관리: {인덱스: {'cooldown_until': datetime, 'fail_count': int}}
        self.key_status = {i: {'cooldown_until': datetime.min, 'fail_count': 0} for i in range(len(self.api_keys))}

        self.system_prompt = """당신은 '선플(Sunpple)'입니다. 7일간의 커리어 디스커버리 여정을 함께하는 AI 커리어 동반자입니다.

[말투와 태도]
- 따뜻하고 비판 없는 호기심을 보여주세요.
- "~군요", "~네요", "~셨군요" 같은 부드러운 종결어미를 사용하세요.
- 사용자의 답변을 절대 평가하거나 판단하지 마세요.
- 답변이 짧으면 구체적 경험으로 자연스럽게 유도하세요.
- 모든 질문은 한 번에 하나씩만 하세요.
- 이모지는 가끔만 사용하세요 (☀️, 🌱, 💡 등).
- 긴 응답은 한 번에 보내지 말고, 반드시 여러 메시지로 나누어 전달하세요. 
  예를 들어 커리어 가설은 하나씩 제시하고 사용자의 반응을 확인한 후 다음 가설로 넘어가세요.

[중요 규칙]
- 하루에 3~5개 정도의 질문을 자연스럽게 나누어 대화하세요.
- 사용자의 이전 답변을 참조하여 연결된 대화를 이어가세요.
- 오늘의 주제에 맞게 대화를 이끌어가되, 사용자의 페이스를 존중하세요.
- 각 대화의 마지막에는 따뜻하게 마무리하고 "내일 또 만나요"라는 느낌을 주세요.
- 당신은 사용자의 성격보다 ‘직무 역량’과 ‘산업 적합도’를 분석하는 커리어 코치입니다.  
  단, 업무 성향(work style)은 중요한 데이터이므로 반드시 수집하세요.
- 모든 질문은 가능한 한 보기(선택지)를 제공하여 사용자가 쉽게 답할 수 있도록 하세요.
- 응답은 항상 완전한 문장으로 마무리하세요. 중간에 끝내지 마세요."""

    def _get_available_key(self):
        """사용 가능한 키 중 랜덤 선택 (쿨다운 상태면 제외)"""
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
        """429 오류 발생 시 해당 키의 쿨다운 시간 증가 (지수 백오프)"""
        fail_count = self.key_status[key_index]['fail_count'] + 1
        cooldown_seconds = min(2 ** fail_count, 60)
        self.key_status[key_index]['fail_count'] = fail_count
        self.key_status[key_index]['cooldown_until'] = datetime.now() + timedelta(seconds=cooldown_seconds)
        st.info(f"API 요청이 일시적으로 많아 {cooldown_seconds}초 후 다시 시도합니다. (키 {key_index+1})")

    def _truncate_conversation(self, conversation, max_turns=8):
        """대화가 너무 길면 최근 max_turns만 남깁니다."""
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
                    generation_config={
                        "temperature": 0.7,
                        "max_output_tokens": 2048,
                    }
                )
                safety_settings = [
                    {"category": "HARM_CATEGORY_HARASSMENT", "threshold": "BLOCK_NONE"},
                    {"category": "HARM_CATEGORY_HATE_SPEECH", "threshold": "BLOCK_NONE"},
                    {"category": "HARM_CATEGORY_SEXUALLY_EXPLICIT", "threshold": "BLOCK_NONE"},
                    {"category": "HARM_CATEGORY_DANGEROUS_CONTENT", "threshold": "BLOCK_NONE"},
                ]
                
                # Gemini 포맷으로 변환
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
                
                # 일관된 채팅 세션 시작
                if len(gemini_messages) == 1:
                    chat = model.start_chat(history=[])
                    response = chat.send_message(gemini_messages[0]["parts"][0], safety_settings=safety_settings)
                else:
                    chat = model.start_chat(history=gemini_messages[:-1])
                    response = chat.send_message(gemini_messages[-1]["parts"][0], safety_settings=safety_settings)
                
                full_response = response.text
                
                # MAX_TOKENS로 인해 잘린 경우 자동으로 이어쓰기
                while response.candidates and response.candidates[0].finish_reason.name == 'MAX_TOKENS':
                    response = chat.send_message(
                        "계속해서 이어서 작성해 주세요. 완전한 문장으로 마무리해 주세요.",
                        safety_settings=safety_settings
                    )
                    full_response += response.text
                
                self.key_status[key_index]['fail_count'] = 0
                return full_response.strip()
                
            except Exception as e:
                last_error = e
                error_str = str(e)
                if "429" in error_str or "quota" in error_str.lower() or "rate" in error_str.lower():
                    self._handle_rate_limit(key_index)
                    continue
                else:
                    break
        
        return f"죄송해요, 잠시 응답을 생성하기 어려네요. 다시 시도해 주시겠어요? ☀️\n\n(오류: {str(last_error)[:100]})"

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

최근 1주일 안에 **시간 가는 줄 모르고 몰입했던 일**이 있다면 하나만 떠올려 주세요.""" ,

            3: f"""{name}님, 오늘 하루도 수고 많으셨어요. 🌱
오늘은 당신이 예상치 못한 문제를 어떻게 해결하는지, 어떤 방식으로 결정을 내리는지 살펴볼게요.

먼저, 팀 프로젝트나 아르바이트 중 예상치 못한 문제가 생겼을 때, 당신은 주로 어떤 방식으로 해결했나요?""" ,

            4: f"""{name}님, 오늘은 다른 사람들과의 협업 속에서 당신의 자연스러운 모습을 알아볼게요. 💡

팀으로 일할 때 당신이 가장 자주 맡는 역할은 무엇인가요?""" ,

            5: f"""{name}님, 벌써 5일째네요. 오늘은 당신의 관심 산업과 어떤 환경에서 가장 에너지가 생기는지 탐색해볼게요.

먼저, 다음 중 가장 관심이 가는 산업군을 2개만 골라주세요.
- IT/테크 (앱, SaaS, AI, 플랫폼)
- 콘텐츠/미디어 (유튜브, 출판, 방송, 뉴스레터)
- 교육/에듀테크
- 이커머스/리테일 (온라인 쇼핑몰, 브랜드)
- 금융/핀테크
- 헬스케어/바이오
- 게임
- 엔터테인먼트/공연
- 사회적 기업/NGO/공공
- 제조/하드웨어""",

            6: f"""{name}님, 오늘은 제가 지난 5일간의 대화를 종합해서, 당신만을 위한 커리어 가설을 준비해왔어요! 🎯

먼저, 제가 발견한 당신의 핵심 강점과 업무 성향을 한 문장으로 정리해볼게요.
(이전 모든 대화를 분석하여 사용자 패턴 요약 및 강점 정의)

이걸 바탕으로, 세 가지 커리어 가설을 **하나씩** 제안해드릴게요. 먼저 첫 번째 가설부터 살펴보시겠어요?""",

            7: f"""{name}님, 드디어 마지막 날이네요! 🎉
오늘은 어제 가장 마음에 들어하셨던 커리어 가설을 실제로 **테스트할 계획**을 함께 만들어볼게요.

이건 확정된 커리어가 아니라 "검증할 가설"입니다. 앞으로 3~6개월 동안 작은 실험들을 통해 이 가설이 정말 당신에게 맞는지 확인해보는 거예요.

먼저, 이 분야를 더 깊이 이해하기 위한 Phase 1 탐색부터 시작해볼까요?"""
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
오늘의 목표: {name}님의 전공, 경험, 잘하는 일, 흥미를 자연스럽게 수집하고, 첫 선택의 순간을 관찰하세요.

필수 질문들 (순서대로, 하나씩):
1. 현재 학교/전공 → 
2. 전공 안에서 가장 몰입해서 해결했던 과제나 프로젝트 하나 → 그 안에서 당신이 실제로 한 행동은? (코딩, 보고서, 발표 등)
3. 아래 항목 중 가장 수월하게 해내는 것을 고르게 하세요 (보기 제시):
   - 복잡한 숫자/데이터를 읽고 패턴 찾기
   - 글쓰기 (보고서, 블로그, SNS 카드뉴스 등)
   - 시각자료 만들기 (PPT, 영상, 이미지 편집)
   - 사람들을 설득하거나 분위기를 주도하기
   - 문제를 구조화해서 할 일을 정리하기
   - 새로운 아이디어를 떠올리기
4. 돈을 받지 않아도 계속 했던 취미/활동은?
5. 학과 공부 외에 따로 배워본 기술(예: 프리미어, 파이썬, 피그마 등)

마지막에는 따뜻하게 마무리하고 "내일 저녁에 만나요 :)"라고 인사하세요.

[분석할 점 - 사용자에게 절대 보여주지 말 것]
- 선택의 주체성 (능동/수동)
- 선호하는 작업 유형 (분석/표현/대인/구조화)""",

            2: f"""[Day 2 지침 - 몰입이 증명하는 재능]
오늘의 목표: {name}님이 실제로 몰입한 경험을 통해 직무 역량과 몰입 유형을 관찰하세요.

필수 질문들:
1. 시간 가는 줄 모르고 했던 일을 최근 1주일 안에 하나 떠올리게 하세요.
2. 그 몰입 경험이 어떤 유형에 가까운지 선택하게 하세요:
   - 무언가를 처음부터 끝까지 ‘만드는’ 일 (제작, 코딩, 디자인 등)
   - 정보를 찾아 ‘분석/정리’하는 일 (리서치, 데이터 정리, 요약)
   - 사람을 ‘돕거나 가르치는’ 일 (멘토링, 상담, Q&A 답변)
   - 무언가를 ‘기획/구성’하는 일 (일정표, 이벤트, 프로젝트 설계)
   - 아이디어를 시각화하거나 글로 표현하는 일
3. 그 일을 할 때 주로 사용한 도구/프로그램은?
4. 이 몰입 경험 중 “너 이거 진짜 잘한다”라는 말을 들은 적이 있나요?

발견된 패턴(몰입 유형 + 도구)을 간단히 요약해주고 마무리하세요.""",

            3: f"""[Day 3 지침 - 문제 해결 방식과 성향]
오늘의 목표: {name}님이 예상치 못한 문제를 어떻게 해결하는지, 어떤 의사 결정 성향을 가졌는지 관찰하세요.

필수 질문들:
1. 팀 프로젝트나 아르바이트 중 예상치 못한 문제가 생겼을 때, 주로 어떤 방식으로 해결했나요? (보기 제시):
   - 혼자 조용히 원인을 분석하고 해결책을 찾는다
   - 주변 사람들에게 빠르게 물어보고 도움을 구한다
   - 문제를 작은 단위로 쪼개서 하나씩 처리한다
   - 책/유튜브/검색으로 비슷한 사례를 먼저 찾는다
   - 직감으로 일단 부딪혀보고 고친다
2. 가장 편안하게 생각하는 의사 결정 방식은? (보기 제시):
   - 선택지를 철저히 비교·분석한 후 결정
   - 주변 사람들의 의견을 충분히 들은 후 결정
   - 논리보다 ‘느낌/직관’을 따르는 편
   - 빠르게 결정하고, 문제가 생기면 그때 수정
3. 문제를 해결할 때 가장 자주 사용하는 도구/플랫폼은 무엇인가요? (예: 노션, 엑셀, 파이썬, 미리캔버스, ChatGPT, 트렐로 등)

발견된 패턴(문제 해결 스타일 + 의사 결정 성향)을 요약하고 마무리하세요.""",

            4: f"""[Day 4 지침 - 협업 성향과 피드백]
오늘의 목표: {name}님이 팀에서 어떤 역할을 맡고, 피드백에 어떻게 반응하는지 관찰하세요. **오늘은 성격 탐색의 중심입니다.**

필수 질문들:
1. 팀으로 일할 때 가장 자주 맡는 역할은? (보기 제시):
   - 리더: 방향을 정하고 일을 나누는 역할
   - 실행가: 맡은 일을 묵묵히 끝까지 해내는 역할
   - 분위기 메이커: 팀원들의 사기를 올리고 의견을 조율하는 역할
   - 분석가: 데이터나 자료를 찾아 근거를 제시하는 역할
   - 디자이너/제작자: 결과물을 예쁘고 보기 좋게 만드는 역할
2. 갈등이 생겼을 때 당신의 반응은? (보기 제시):
   - 상대방의 말을 끝까지 듣고 감정을 먼저 이해하려 한다
   - 사실과 논리를 중심으로 차근차근 풀어간다
   - 갈등 자체를 피하고 혼자 해결할 수 있는 방법을 찾는다
   - 다수의 의견을 따르거나 중재자에게 맡긴다
3. 비판/부정적 피드백을 들었을 때 내면의 반응은? (보기 제시):
   - “뭐가 문제였는지 구체적으로 분석하고 바로 고친다”
   - “속으로 오래 생각하지만 겉으로는 잘 받아들인다”
   - “내 방식이 아니라고 느끼며 방어하고 싶다”
   - “일단 감정적으로 흔들렸다가 시간이 지나면 수용한다”
4. 스스로에게 자주 하는 말은? (보기 제시):
   - “수고했어, 괜찮아” (격려형)
   - “여기서 뭘 배웠지?” (분석형)
   - “더 잘할 수 있었는데” (아쉬움/반성형)
   - “그냥 다음엔 다르게 하자” (가벼운 전진형)

피드백 수용 방식과 셀프 대화 패턴을 요약하고 마무리하세요.""",

            5: f"""[Day 5 지침 - 산업 흥미와 업무 환경]
오늘의 목표: {name}님의 관심 산업과 선호하는 업무 환경, 그리고 일의 속도감을 파악하세요.

필수 질문들:
1. 가장 관심이 가는 산업군을 2개만 고르게 하세요 (보기 제시):
   - IT/테크, 콘텐츠/미디어, 교육/에듀테크, 이커머스/리테일, 금융/핀테크, 헬스케어/바이오, 게임, 엔터테인먼트/공연, 사회적 기업/NGO/공공, 제조/하드웨어
2. 그 산업에서 어떤 유형의 문제를 해결하고 싶나요? (보기 제시):
   - 좋은 제품을 더 많은 사람에게 알리는 것 (마케팅, 브랜딩)
   - 사용자 경험을 더 편리하고 아름답게 만드는 것 (UX/UI, 디자인)
   - 데이터를 분석해서 인사이트를 찾아내는 것 (데이터 분석, 리서치)
   - 시스템/프로세스를 효율적으로 만드는 것 (운영, 기획)
   - 사람을 성장시키고 교육하는 것 (교육, 코칭, HR)
3. 어떤 업무 환경에서 더 에너지가 생기나요? (보기 제시):
   - 하루 일정이 명확하고, 해야 할 일이 정리된 구조적인 환경
   - 매일 새로운 과제와 변화가 많은 유연한 환경
   - 혼자 깊게 몰입할 수 있는 조용한 환경
   - 팀원들과 수시로 아이디어를 나누는 협업 중심 환경
4. 마감이 임박했을 때 당신의 반응은? (보기 제시):
   - 평소보다 집중력이 올라간다
   - 스트레스를 받지만 끝까지 해낸다
   - 계획이 틀어져 불안해진다
   - 주변에 도움을 요청하며 팀플레이로 전환한다
5. 가장 존경하는 사람의 유형이나 “이렇게 일하고 싶다”고 생각한 롤모델이 있다면요?

[중요]
- 이전 대화를 실제로 분석하여 패턴을 요약하세요.
- 내일 구체적 커리어 가설을 제시할 것이라고 예고하세요.""",

            6: f"""[Day 6 지침 - 커리어 가설 제시 (분할 전달)]
오늘은 {name}님을 위한 3가지 커리어 가설을 **한 번에 하나씩** 제시합니다.

[진행 순서]
1. 먼저 지난 5일간의 데이터를 요약하여 사용자 프로필을 보여주세요.
2. **가설 1**을 제시하고, 간단한 설명과 함께 “이 방향에 대해 어떻게 생각하시나요?”라고 물어보세요.
3. 사용자의 답변을 받은 후에만 **가설 2**를 제시하세요.
4. 마찬가지로 답변 후 **가설 3**을 제시하세요.
5. 마지막으로 세 가설 중 가장 마음에 드는 것을 선택해 달라고 요청하세요.

[가설 생성 규칙]
- 각 가설에는 직무명, 차별화 포인트, 왜 {name}님에게 맞는지(데이터 근거)를 포함하세요.
- 실제 한국의 구체적인 직무명을 사용하세요.
- 한 메시지에는 하나의 가설만 담으세요. """,

            7: f"""[Day 7 지침 - 검증 로드맵 (분할 전달)]
오늘은 선택된 커리어 가설을 검증할 3단계 로드맵을 **순서대로** 안내합니다.

[진행 순서]
1. **Phase 1 – 탐색**을 먼저 제시하고, 사용자가 어떻게 느끼는지 물어보세요.
2. 사용자의 답변을 받은 후 **Phase 2 – 경험**을 제시하세요.
3. 마지막으로 **Phase 3 – 진입**을 제시하세요.
4. 모든 단계가 끝나면 7일 여정을 마무리하고 “당신의 무기” 한 줄을 선물하세요.

[내용 규칙]
- 각 Phase에는 {name}님의 데이터에 맞춘 실제 뉴스레터, 해커톤, 채용 플랫폼 등을 포함하세요.
- 한 메시지에 하나의 Phase만 설명하세요.
- 마지막에는 감동적인 마무리 메시지를 남기세요. ☀️"""
        }
        return instructions.get(day_number, f"{name}님과의 대화를 이어가세요.")
