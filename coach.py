import google.generativeai as genai
import streamlit as st
import time
import random

class SunppleCoach:
    def __init__(self):
        self.api_keys = []
        for i in range(1, 9):
            key = st.secrets.get(f"GEMINI_API_KEY_{i}")
            if key:
                self.api_keys.append(key)
        if not self.api_keys:
            raise ValueError("GEMINI_API_KEY_1 ~ 8 중 최소 하나는 설정해야 합니다.")
        self.key_usage_count = {i: 0 for i in range(len(self.api_keys))}
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
- 응답은 항상 완전한 문장으로 마무리하세요. 중간에 끝내지 마세요.
- 사용자가 추가 질문을 해야만 이어지는 듯한 느낌을 주지 마세요. """

    def _get_next_key(self):
        min_usage = min(self.key_usage_count.values())
        available_keys = [i for i, count in self.key_usage_count.items() if count == min_usage]
        selected_index = random.choice(available_keys)
        self.key_usage_count[selected_index] += 1
        return self.api_keys[selected_index]

    def _call_gemini(self, conversation, max_retries=3):
        last_error = None
        for attempt in range(max_retries):
            key = self._get_next_key()
            try:
                genai.configure(api_key=key)
                model = genai.GenerativeModel(
                    model_name="gemini-2.5-flash",
                    generation_config={
                        "temperature": 0.7,
                        "max_output_tokens": 1024,
                    }
                )
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
                    response = model.generate_content(
                        gemini_messages[0]["parts"][0],
                        safety_settings=[
                            {"category": "HARM_CATEGORY_HARASSMENT", "threshold": "BLOCK_NONE"},
                            {"category": "HARM_CATEGORY_HATE_SPEECH", "threshold": "BLOCK_NONE"},
                            {"category": "HARM_CATEGORY_SEXUALLY_EXPLICIT", "threshold": "BLOCK_NONE"},
                            {"category": "HARM_CATEGORY_DANGEROUS_CONTENT", "threshold": "BLOCK_NONE"},
                        ]
                    )
                else:
                    chat = model.start_chat(history=gemini_messages[:-1])
                    response = chat.send_message(gemini_messages[-1]["parts"][0])
                return response.text
            except Exception as e:
                last_error = e
                error_str = str(e)
                if "429" in error_str or "quota" in error_str.lower() or "rate" in error_str.lower():
                    time.sleep(0.5)
                    continue
                else:
                    break
        return f"죄송해요, 잠시 생각이 꼬였어요. 다시 한 번 말씀해주실래요? ☀️\n\n(오류: {str(last_error)[:100]})"

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
오늘은 당신의 하루를 에너지 그래프로 그려보는 시간이에요.

가볍게, 오늘 하루를 하나의 그래프로 그려본다면 아침부터 지금까지, 에너지가 올랐던 순간과 내려갔던 순간이 언제였을까요?""",

            3: f"""{name}님, 오늘 하루도 수고 많으셨어요. 🌱
오늘은 특별히, 하루 중 **무언가 선택하거나 결정해야 했던 순간**을 떠올려볼게요.

아주 작은 결정도 좋아요. 오늘 당신이 내린 결정 중, 가장 고민했거나 가장 큰 영향을 미친 결정은 무엇이었나요?""",

            4: f"""{name}님, 오늘은 다른 사람들과의 관계 속에서 당신을 바라볼게요. 💡

오늘 누군가에게 칭찬이나 긍정적인 피드백을 받은 적이 있나요? 사소한 것도 좋아요.""" ,

            5: f"""{name}님, 벌써 5일째네요. 지난 4일간 정말 소중한 이야기를 들려주셨어요.
오늘은 조금 더 깊이 들어가서, 당신이 진짜 원하는 것이 무엇인지 함께 탐색해볼게요.

먼저, 지난 4일간의 패턴을 간단히 요약해드릴게요.
(이전 대화를 바탕으로 요약할게요)

이 요약을 들으니 어떤 느낌이 드시나요?""",

            6: f"""{name}님, 오늘은 제가 지난 5일간의 대화를 종합해서, 당신만을 위한 커리어 가설을 준비해왔어요! 🎯

먼저, 제가 발견한 당신의 패턴을 한 문장으로 정리해볼게요.
(이전 모든 대화를 분석하여 사용자 패턴 요약 및 강점 정의)

이걸 바탕으로, 세 가지 커리어 가설을 제안해드릴게요. 하나씩 살펴보시겠어요?""",

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
오늘의 목표: {name}님의 학교/전공/가정환경/현재 목표를 자연스럽게 수집하고, 선택의 순간들을 어떻게 해석하는지 관찰하세요.
필수 질문들 (순서대로, 하나씩):
1. 현재 학교/전공 → 
2. 전공 선택 이유 (결정적 순간) → 
3. 가장 재미있었던 수업/활동 → 
4. 그 안에서 맡은 역할 → 
5. 본인이 생각하는 강점 → 
6. 가정환경 분위기 → 
7. 가족이 자주 했던 말 중 기억에 남는 것 → 
8. 현재 가장 이루고 싶은 목표 → 
9. 목표를 꿈꾸게 된 계기 → 
10. 목표에 대한 자신 있는 부분/불안한 부분
마지막에는 따뜻하게 마무리하고 "내일 저녁에 만나요 :)"라고 인사하세요.""",

            2: f"""[Day 2 지침 - 에너지 발견]
오늘의 목표: {name}님이 언제 에너지가 충전되고 소진되는지 관찰하세요.
필수 질문들:
1. 오늘 하루 에너지 그래프 (오른 순간/내려간 순간)
2. 가장 몰입한 특정 순간 자세히 (무엇을, 누구와, 어떤 생각)
3. 그 경험이 준 감정 (유능감/관계감/성취감 등)
4. 가장 에너지 빠진 순간
5. 그때의 감정 (답답함/무력감/불안 등)
6. 오늘 에너지를 좌우한 핵심 요인
발견된 패턴을 간단히 요약해주고 마무리하세요.""",

            3: f"""[Day 3 지침 - 의사결정]
오늘의 목표: {name}님이 난관에 부딪혔을 때 어떤 방식으로 생각하고 행동하는지 관찰하세요.
필수 질문들:
1. 오늘 내린 결정 중 가장 고민한 것
2. 선택 기준 (효율/재미/관계/안전)
3. 결정 직전 사고 (불안 숙고/추진/비교)
4. 다른 선택을 했다면 어땠을지 상상하는지
5. 결정 패턴 요약 후 마무리""",

            4: f"""[Day 4 지침 - 피드백]
오늘의 목표: {name}님이 외부 평가와 내부 기준 사이에서 어떻게 균형을 잡는지 관찰하세요.
필수 질문들:
1. 오늘 받은 긍정적 피드백
2. 그 피드백에 대한 솔직한 반응
3. 부정적 피드백이나 실수 인지 순간
4. 그런 순간의 대응 방식
5. 스스로에게 자주 하는 셀프 피드백
6. 피드백 패턴 요약 후 마무리""",

            5: f"""[Day 5 지침 - 가치관]
오늘의 목표: 지난 4일간의 패턴을 바탕으로 {name}님의 근본적인 가치관과 동기 원천을 탐색하세요.
필수 질문들:
1. 지난 4일간 패턴 요약 제시 후 반응 묻기
2. 절대 포기할 수 없는 가치 한 가지
3. 그 가치가 비롯된 과거 경험
4. 10년 후 성공 장면 구체적으로 상상
5. 그 길에서 자신이 생각하는 가장 큰 장애물
[중요] 이전 대화를 실제로 분석하여 패턴을 요약하세요. 내일 구체적 커리어 가설을 제시할 것이라고 예고하세요.""",

            6: f"""[Day 6 지침 - 커리어 가설 제시]
오늘의 목표: 지금까지의 모든 데이터를 종합하여 {name}님에게 맞는 3가지 커리어 가설을 제시하세요.
진행 방식:
1. 먼저 5일간의 데이터를 종합한 사용자 프로필을 한 문장으로 제시
2. 가설 1 (직관적 방향): 전공/경험과 연결되면서 강점이 살아나는 포지션
   - 직무명 + 차별화 포인트 + 구체적 상황 예시
3. 가설 2 (숨은 가능성): 의외의 직무, 전공 외 강점 활용
   - 직무명 + 숨은 강점 + 유사 사례
4. 가설 3 (도전적 방향): 핵심 가치에 가장 부합하는 방향
   - 직무명 + 가치 연결 + 장애물 극복 시 얻는 것
5. 세 가설에 대한 선호도와 이유 묻기
[중요] 실제 한국의 직무명과 스타트업/대기업 트렌드를 반영하세요. "마케터" 같은 일반론이 아닌 구체적인 포지션을 제시하세요. 내일 검증 계획을 세울 것이라고 예고하세요.""",

            7: f"""[Day 7 지침 - 검증 로드맵]
오늘의 목표: {name}님이 선택한 커리어 가설을 검증할 3페이즈 로드맵을 제공하세요.
진행 방식:
1. Phase 1 탐색 (0~1개월): 무료로 바로 시작할 수 있는 것들 (뉴스레터, 팟캐스트, 링크드인 검색 팁)
2. Phase 2 경험 (1~3개월): 작은 실험들 (해커톤/공모전, 미니 포트폴리오 프로젝트, 정보 인터뷰)
3. Phase 3 진입 (3~6개월): 추천 기업 유형, 실제 채용 플랫폼, 지원 시 강조할 포인트
마지막으로 7일 여정 소회를 묻고, "당신의 무기"를 한 줄로 정의해주세요.
[중요] 실제 존재하는 한국의 해커톤, 채용 플랫폼을 언급하세요. 감동적인 마무리 메시지로 여정을 마무리하세요. ☀️"""
        }
        return instructions.get(day_number, f"{name}님과의 대화를 이어가세요.")
