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
            "아카페라", "카페라떼", "카페모카", "카모", "카모카", "헬스장", "교촌치킨", "포트폴리오"
        ]

        # 문장 분리 기준 품사/토큰 목록
        self.SPLIT_TOKENS = {
            "EC",  # 연결 어미: -고, -으며 등
            "MAJ",  # 접속 부사: 그리고, 그러나 등
            "SF"   # 마침표
        }
        # 토큰 텍스트 기준 (강제 분리 및 필터링)
        self.SPLIT_TEXTS = [
            "그리고", "그러고", "해야지", "해야겠다", "해야돼", "해야만", "하고", "이고", "되", "되니", "되서", "되고", "고", "돼"
        ]

    def _split_sentences(self, text: str) -> List[str]:
        tokens = self.tokenizer.pos(text)
        
        sentences = []
        current_sentence_tokens = []

        for i, (token, pos) in enumerate(tokens):
            current_sentence_tokens.append(token)
            
            is_split_point = pos in self.SPLIT_TOKENS or token in self.SPLIT_TEXTS

            if is_split_point:
                sentence = "".join(current_sentence_tokens).strip()
                if sentence:
                    sentences.append(sentence)
                current_sentence_tokens = []

            if i == len(tokens) - 1 and current_sentence_tokens:
                 sentence = "".join(current_sentence_tokens).strip()
                 if sentence:
                     sentences.append(sentence)

        return [s for s in sentences if s.strip()]

    def _get_absolute_date(self, relative_date: str) -> str:
        """ 상대적 날짜를 절대 날짜로 변환 (기존 로직 유지) """
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

        # 1. 신조어 처리 후 Mecab 품사 태깅 (기존 로직 유지)
        parsed_tokens = self.tokenizer.pos(sentence)
        for word in self.special_words:
            if word in sentence:
                processed_tokens = []
                current_text = sentence
                while word in current_text:
                    pre_word_text, post_word_text = current_text.split(word, 1)
                    processed_tokens.extend(self.tokenizer.pos(pre_word_text.strip()))
                    processed_tokens.append((word, "NNG"))
                    current_text = post_word_text.strip()
                processed_tokens.extend(self.tokenizer.pos(current_text))
                parsed_tokens = processed_tokens
                break
        
        print(f"[STEP 2] Mecab 품사 태깅 결과: {parsed_tokens}")

        date = ""
        time = ""
        metadata_tokens = set()
        final_verb_root = ""
        action_verbs = []

        # 2. 메타데이터 및 모든 액션 동사 추출
        for i, (token, pos) in enumerate(parsed_tokens):
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
            elif pos in ["VV", "XSV"]: 
                if not (token.startswith("있") or token.startswith("없")):
                    action_verbs.append((token, pos))
                metadata_tokens.add((token, pos))
            elif pos == "VA": 
                metadata_tokens.add((token, pos))

            # '잠 자기' 케이스를 위한 오분류 '자야' 처리
            elif token == "자야" and pos == "NNG" and '잠' in sentence:
                action_verbs.append(("자", "VV"))
                metadata_tokens.add((token, pos))
        
        # 2-1. 추출된 동사 목록에서 최종 동사 결정: '되' 필터링 후 가장 마지막 동사 선택
        for token, pos in reversed(action_verbs):
            if token != "되": 
                final_verb_root = token
                break

        # 3. todo_parts에 유효한 명사만 추출 및 불필요한 명사/대명사 필터링
        todo_parts = []
        is_jam_in_sentence = '잠' in sentence
        
        # 🚨 NEW LOGIC: JKB(부사격 조사)가 뒤따르는 명사를 맥락으로 간주하여 필터링
        nouns_to_filter = set()
        for i, (token, pos) in enumerate(parsed_tokens):
            if pos.startswith("NN") or pos.startswith("NP"):
                # Noun/NP가 JKB(부사격 조사)로 곧바로 이어지면 필터링
                if i + 1 < len(parsed_tokens) and parsed_tokens[i+1][1].startswith("JKB"):
                     nouns_to_filter.add((token, pos))
        
        # 필터링된 명사를 metadata_tokens에 추가하여 명사 추출 시 제외되도록 함
        for noun_item in nouns_to_filter:
            metadata_tokens.add(noun_item)
            
        for token, pos in parsed_tokens:
            
            # 3-1. 필터링: 기능어, 동사, 형용사, 메타데이터 토큰(시간, 날짜, JKB 필터링 명사) 제외
            is_functional_or_verb = (
                pos.startswith("J") or pos.startswith("E") or pos.startswith("M") or 
                pos.startswith("X") or pos.startswith("S") or 
                pos in ["VV", "VA", "XSV"] or 
                (token, pos) in metadata_tokens 
            )
            if is_functional_or_verb:
                continue
            
            # 3-2. 명사 필터링 강화: 대명사(NP) 및 Mecab 오분류 필터링
            if pos == "NP" and token in ["나", "너", "우리", "저"]: 
                continue

            if pos.startswith("NN") or pos.startswith("XSN") or pos.startswith("SL"): 
                # '잠 자기' 케이스를 위한 오분류 '자야' 필터링
                if token == "자야" and pos == "NNG" and is_jam_in_sentence:
                    continue
                
                todo_parts.append(token)
            
        # 4. 최종 할 일 문장 생성: 명사구 + [동사원형]기
        
        todo_noun_phrase = " ".join(todo_parts).strip()
        final_todo = todo_noun_phrase

        if final_verb_root:
            verb_noun = final_verb_root + "기"
            
            if final_todo:
                final_todo += " " + verb_noun
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

            # 1. Todo가 단일 분리 토큰인 경우 (e.g., "고", "그리고") 필터링
            if result["todo"] in self.SPLIT_TEXTS or result["todo"] in ["고", "그리고"]:
                 print(f"⚠️ 분리 토큰 필터링: {result['todo']}")
                 continue

            # 2. 결과가 단독 명사/동사/잡토큰이고 할 일이 아닌 경우 필터링 (필터링 목록에 '돼' 추가)
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

    # 테스트 케이스 1: 새로운 입력 테스트
    input_text_1 = "나는 포트폴리오 작성 해야 하고 밤엔 잠을 잘 자야되고 채용공고를 검색해 봐야 합니다 그리고 집에 가는 길에 두부를 사야 돼"
    print("\n--- 테스트 케이스 1 실행 ---\n")
    parsed_list_1 = parser_instance.parse_multiple_sentences(input_text_1)

    print("\n\n--- 최종 JSON 출력 (테스트 1) ---")
    print(json.dumps(parsed_list_1, indent=4, ensure_ascii=False))

    # 테스트 케이스 2: 기존 테스트 유지 (정상 작동 확인)
    input_text_2 = "내일 아침 9시에 헬스장 가서 운동 하고 그리고 점메추 받아서 엽떡 먹어야지"
    print("\n--- 테스트 케이스 2 실행 ---\n")
    parsed_list_2 = parser_instance.parse_multiple_sentences(input_text_2)

    print("\n\n--- 최종 JSON 출력 (테스트 2) ---")
    print(json.dumps(parsed_list_2, indent=4, ensure_ascii=False))