import re
import json
from typing import Dict, Any, List
from mecab import MeCab
from datetime import datetime, timedelta
import os

class Parser:
    def __init__(self):
        self.tokenizer = MeCab()
        print("Parser 초기화 완료: Mecab 엔진 사용")

        self.special_words = [
            "엽떡", "짜파구리", "맞담", "인강", "쿠팡", "배민", "요기요", "로제", "혼술",
            "혼밥", "소확행", "퇴근길", "출근길", "점메추", "아아", "아메", "아카",
            "아카페라", "카페라떼", "카페모카", "카모", "카모카", "헬스장", "교촌치킨", 
            "포트폴리오", "채용공고", "경찰서" # 복합 명사 추가 유지
        ]

        # 문장 분리 기준 품사/토큰 목록
        self.SPLIT_TOKENS = {
            "EC",  # 연결 어미: -고, -으며 등
            "MAJ",  # 접속 부사: 그리고, 그러나 등
            "SF"   # 마침표
        }
        # 토큰 텍스트 기준 (강제 분리 및 필터링)
        # 🚨 FIX 2: '되', '고'를 삭제하여 문장 분리 기준을 완화하고, 불필요한 과분리 방지
        self.SPLIT_TEXTS = [
            "그리고", "그러고", "해야지", "해야겠다", "해야돼", "해야만", "하고", "이고", 
            "되니", "되서", "되고", "돼" 
        ]

    # --- 유틸리티 메서드 추가 ---
    def _get_verb_root(self, token: str) -> str:
        """ 동사 토큰에서 어미를 제거하고 원형을 추출하는 휴리스틱 """
        
        # '되' 계열은 최종 동사 원형으로 사용하지 않음
        if token in ["되", "돼", "되고", "되서", "되어"]:
             return ""

        # 1. 일반적인 어미 제거 휴리스틱 (종결/연결 어미)
        root = re.sub(r'(아|어|이|야|지|다|고|네|니|야지|어야지|아야지|ㄹ까|ㄹ게|ㅂ니다|습니다|요)$', '', token, flags=re.IGNORECASE)
        
        # 2. '해' -> '하' 처리
        if root == "해":
            return "하"
        
        # 3. 후처리: 제거 후 빈 문자열이 되는 경우 (예: '가' + '고' -> '가')
        if not root and len(token) > 1 and token[-1] in ['고', '서', '니', '야']:
            return token[:-1]
            
        return root if root else ""

    def _split_sentences(self, text: str) -> List[str]:
        """ 
        입력 텍스트를 띄어쓰기를 최대한 보존하며 문장 분리 기준에 따라 나눕니다.
        """
        
        split_tokens_pattern = '|'.join(map(re.escape, self.SPLIT_TEXTS))
        split_pattern_regex = r'(' + split_tokens_pattern + r'|\s*[.,?!]\s*)'

        sentences_and_splitters = re.split(split_pattern_regex, text)
        
        cleaned_sentences = []
        current_sentence = ""

        for part in sentences_and_splitters:
            if part is None or not part.strip():
                continue
            
            is_splitter = any(part.strip() == t for t in self.SPLIT_TEXTS) or re.match(r'^\s*[.,?!]\s*$', part.strip())
            
            if is_splitter:
                if current_sentence.strip():
                    cleaned_sentences.append(current_sentence.strip())
                current_sentence = ""
            else:
                if current_sentence and not current_sentence.endswith(' ') and not part.startswith(' '):
                     current_sentence += ' ' 
                current_sentence += part

        if current_sentence.strip():
            cleaned_sentences.append(current_sentence.strip())
            
        return [s for s in cleaned_sentences if s]


    def _get_absolute_date(self, relative_date: str) -> str:
        """ 상대적 날짜를 절대 날짜로 변환 """
        today = datetime.today()
        if relative_date == "오늘" or relative_date == "":
            return today.strftime("%Y-%m-%d")
        elif relative_date == "내일":
            tomorrow = today + timedelta(days=1)
            return tomorrow.strftime("%Y-%m-%d")
        elif relative_date == "주말":
            days_until_saturday = (5 - today.weekday() + 7) % 7
            if days_until_saturday == 0:
                days_until_saturday = 7
            weekend_saturday = today + timedelta(days=days_until_saturday)
            return weekend_saturday.strftime("%Y-%m-%d")
        elif relative_date == "이번주":
            days_until_monday = today.weekday()
            this_monday = today - timedelta(days=days_until_monday)
            return this_monday.strftime("%Y-%m-%d")
        elif relative_date == "다음주":
            days_until_monday = (0 - today.weekday() + 7) % 7
            next_monday = today + timedelta(days=days_until_monday)
            return next_monday.strftime("%Y-%m-%d")
        else:
            return relative_date

    def _parse_single_sentence(self, sentence: str) -> Dict[str, Any]:
        print(f"\n[STEP 1] 원본 문장: '{sentence}'")

        # 1. 신조어 처리 후 Mecab 품사 태깅 
        parsed_tokens = self.tokenizer.pos(sentence)
        for word in self.special_words:
            if word in sentence:
                processed_tokens = []
                current_text = sentence
                while word in current_text:
                    pre_word_text, post_word_text = current_text.split(word, 1)
                    
                    processed_tokens.extend(self.tokenizer.pos(pre_word_text))
                    processed_tokens.append((word, "NNG"))
                    current_text = post_word_text
                
                processed_tokens.extend(self.tokenizer.pos(current_text))
                
                parsed_tokens = [(t, p) for t, p in processed_tokens if t.strip()]
                break # 첫 번째 특수 단어만 처리

        print(f"[STEP 2] Mecab 품사 태깅 결과: {parsed_tokens}")

        date = ""
        time = ""
        metadata_tokens = set()
        final_verb_root = ""
        action_verbs = []
        object_nouns = set() # 🚨 FIX: 핵심 목적물(을/를, 이/가) 식별용

        # 2. 메타데이터, 동사, 핵심 목적어/주어 추출
        for i, (token, pos) in enumerate(parsed_tokens):
            
            # 핵심 목적어/주어 식별 (JKO, JKS)
            if pos.startswith("NN") or pos.startswith("NP"):
                if i + 1 < len(parsed_tokens) and parsed_tokens[i+1][1].startswith("JKO"): # 목적격 (을/를)
                    object_nouns.add(token)
                if i + 1 < len(parsed_tokens) and parsed_tokens[i+1][1].startswith("JKS"): # 주격 (이/가)
                    object_nouns.add(token)
            
            # 메타데이터 추출 (날짜/시간)
            if token in ["내일", "오늘", "이번주", "다음주", "주말"]:
                date = self._get_absolute_date(token)
                metadata_tokens.add((token, pos))
            elif token in ["아침", "점심", "저녁", "오전", "오후", "새벽", "밤", "낮"]:
                time = token
                metadata_tokens.add((token, pos))
            elif pos == "SN":
                if i + 1 < len(parsed_tokens) and parsed_tokens[i + 1][0] == "시":
                    time = f"{token}시"
                    metadata_tokens.add((token, pos))
                    metadata_tokens.add(parsed_tokens[i + 1])
                elif "시" in sentence:
                    time = f"{token}시"
                    metadata_tokens.add((token, pos))
                else:
                    metadata_tokens.add((token, pos))
            elif token == "시" and pos == "NNBC":
                metadata_tokens.add((token, pos))
                
            # 모든 액션 동사(VV, XSV) 수집
            is_action_verb = pos.startswith("VV") or pos.startswith("XSV")
            
            if is_action_verb: 
                if not (token.startswith("있") or token.startswith("없")):
                    action_verbs.append((token, pos))
                metadata_tokens.add((token, pos))
            elif pos == "VA": 
                metadata_tokens.add((token, pos))

            elif token == "자야" and pos == "NNG" and '잠' in sentence:
                action_verbs.append(("자", "VV"))
                metadata_tokens.add((token, pos))
        
        # 2-1. 추출된 동사 목록에서 최종 동사 결정: 
        # 🚨 FIX 5: 메인 동사(보조 동사가 아닌)를 우선 선택하여 '집 쉬기' 문제 해결
        for token, pos in reversed(action_verbs):
            if token == "되": continue 
            
            root = self._get_verb_root(token)

            # '쉬어야 해'처럼 마지막에 '하' 계열(보조 동사)이 오면 건너뛰고 이전 동사 찾기
            # '해'가 유일한 동사이면 '하'가 선택됨
            if root == "하" and token in ["해", "해야", "합니다", "봐야", "봐"]: 
                if len(action_verbs) == 1:
                    final_verb_root = root
                    break
                else:
                    continue # 다음 (메인) 동사를 찾음
            
            if root:
                final_verb_root = root
                break

        # 3. todo_parts에 유효한 명사만 추출 
        todo_parts = []
        is_jam_in_sentence = '잠' in sentence
            
        for i, (token, pos) in enumerate(parsed_tokens): # 인덱스 사용을 위해 enumerate 재사용
            
            # 3-1. 필터링: 기능어, 동사, 형용사, 메타데이터 토큰 제외
            is_functional_or_verb = (
                pos.startswith("J") or pos.startswith("E") or pos.startswith("M") or 
                pos.startswith("X") or pos.startswith("S") or 
                pos.startswith("VV") or pos.startswith("VA") or 
                (token, pos) in metadata_tokens 
            )
            if is_functional_or_verb:
                continue
            
            # 3-2. 명사 필터링 강화: 대명사(NP) 및 Mecab 오분류 필터링
            if pos == "NP" and token in ["나", "너", "우리", "저"]: 
                continue

            if pos.startswith("NN") or pos.startswith("XSN") or pos.startswith("SL"): 
                
                # 🚨 NEW FIX: JKB 명사 필터링 (맥락 명사 제거)
                is_followed_by_jkb = False
                if i + 1 < len(parsed_tokens) and parsed_tokens[i+1][1].startswith("JKB"):
                    is_followed_by_jkb = True

                # 핵심 목적어/주어가 존재하고(object_nouns), 현재 명사가 JKB와 함께 쓰인 경우, 목적물이 아니면 제거
                # 이 로직으로 '집 길 두부 사기'에서 '집', '길'이 제거됨
                if object_nouns and is_followed_by_jkb and token not in object_nouns:
                    continue 
                
                # (기존: '잠 자기' 케이스 필터링 유지)
                if token == "자야" and pos == "NNG" and is_jam_in_sentence:
                    continue
                
                todo_parts.append(token)
            
        # 4. 최종 할 일 문장 생성: 명사구 + [동사원형]기
        
        # 🚨 FIX 3: special_words에 있는 단어는 붙여서 나오도록 처리
        temp_noun_phrase = " ".join(todo_parts)
        for word in self.special_words:
            # Mecab이 쪼갠 명사를 다시 붙인다 (예: "점 메추" -> "점메추")
            if ' ' in word: 
                 continue
                 
            split_word = " ".join(self.tokenizer.morphs(word))
            temp_noun_phrase = temp_noun_phrase.replace(split_word, word)

        todo_parts = [p for p in temp_noun_phrase.split(" ") if p]
        todo_noun_phrase = " ".join(todo_parts).strip()
        final_todo = ""
        last_noun = todo_parts[-1] if todo_parts else ""

        if final_verb_root:
            verb_noun = final_verb_root + "기"
            
            # 🚨 FIX 1: 동사성 명사 ('작성', '검색', '운동' 등) + '하기'는 붙여쓰기
            if final_verb_root == '하' and last_noun in ["작성", "검색", "운동", "준비", "정리"]:
                rest_of_nouns = " ".join(todo_parts[:-1]).strip()
                
                if rest_of_nouns:
                    final_todo = rest_of_nouns + " " + last_noun + verb_noun
                else:
                    final_todo = last_noun + verb_noun
            
            # 그 외의 일반적인 명사구 + 동사 조합 ('두부 사기', '집 쉬기', '잠 자기')
            elif todo_noun_phrase:
                final_todo = todo_noun_phrase + " " + verb_noun
            else:
                final_todo = verb_noun 
        
        # 5. Todo가 비어있으면 문장 전체를 다시 사용 (예외 처리)
        if not final_todo.strip():
            final_todo = sentence

        print("\n--- 파싱 결과 최종 확인 ---")
        print(f"Todo: '{final_todo}'")
        print(f"Date: '{date}'")
        print(f"Time: '{time}'")
        print("----------------------------\n")

        return {"todo": final_todo, "date": date, "time": time, "original_sentence": sentence}

    def parse_multiple_sentences(self, text: str) -> List[Dict[str, Any]]:
        print(f"전체 입력 텍스트: '{text}'")
        sentences = self._split_sentences(text) 

        parsed_results = []
        last_known_date = datetime.today().strftime("%Y-%m-%d")

        for sentence in sentences:
            if not sentence:
                continue

            result = self._parse_single_sentence(sentence)

            if result["todo"] in self.SPLIT_TEXTS or result["todo"] in ["고", "그리고"]:
                 print(f"⚠️ 분리 토큰 필터링: {result['todo']}")
                 continue

            NOISE_TOKENS = ["나", "고", "그리고", "되", "돼"] 
            if not result['todo'].strip() or (len(result['todo'].split()) == 1 and result['todo'].strip() in NOISE_TOKENS):
                 print(f"⚠️ 단일 토큰 필터링: {result['todo']}")
                 continue


            if result["date"]:
                last_known_date = result["date"]
            elif last_known_date:
                result["date"] = last_known_date

            parsed_results.append(result)

        return parsed_results


if __name__ == "__main__":
    parser_instance = Parser()

    # 테스트 케이스 1: 띄어쓰기 및 오분류, 맥락 필터링 테스트
    # 기대: 포트폴리오 작성하기, 잠 자기, 채용공고 검색하기, 두부 사기 (<- 변경됨)
    input_text_1 = "나는 포트폴리오 작성 해야 하고 밤엔 잠을 잘 자야되고 채용공고를 검색해 봐야 합니다 그리고 집에 가는 길에 두부를 사야 돼"
    print("\n--- 테스트 케이스 1 실행 (띄어쓰기 및 필터링) ---\n")
    parsed_list_1 = parser_instance.parse_multiple_sentences(input_text_1)

    print("\n\n--- 최종 JSON 출력 (테스트 1) ---")
    print(json.dumps(parsed_list_1, indent=4, ensure_ascii=False))

    # 테스트 케이스 2: 기존 테스트 유지 (정상 작동 확인)
    # 기대: 헬스장 가서 운동하기, 점메추 엽떡 먹기
    input_text_2 = "내일 아침 9시에 헬스장 가서 운동 하고 그리고 점메추 받아서 엽떡 먹어야지"
    print("\n--- 테스트 케이스 2 실행 (시간/장소 메타데이터) ---\n")
    parsed_list_2 = parser_instance.parse_multiple_sentences(input_text_2)

    print("\n\n--- 최종 JSON 출력 (테스트 2) ---")
    print(json.dumps(parsed_list_2, indent=4, ensure_ascii=False))

    # 테스트 케이스 3: 사용자 음성 예시
    # 기대: 두부 사기, 경찰서 가기, 집 쉬기
    input_text_3 = "오늘 일단 두부 사야 하고 경찰서 가야 하고 집에서 좀 잘 쉬어야 해"
    print("\n--- 테스트 케이스 3 실행 (간결한 구어체) ---\n")
    parsed_list_3 = parser_instance.parse_multiple_sentences(input_text_3)

    print("\n\n--- 최종 JSON 출력 (테스트 3) ---")
    print(json.dumps(parsed_list_3, indent=4, ensure_ascii=False))