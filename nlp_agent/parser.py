import re
import json
from typing import Dict, Any, List
from mecab import MeCab
from datetime import datetime, timedelta
import os

# 기존 구두점 기반의 SENTENCE_SPLITTER는 사용하지 않습니다.

class Parser:
    def __init__(self):
        self.tokenizer = MeCab()
        print("Parser 초기화 완료: Mecab 엔진 사용")

        # 원본 문장에서 찾아야 할 신조어 목록
        self.special_words = [
            "엽떡", "짜파구리", "맞담", "인강", "쿠팡", "배민", "요기요", "로제", "혼술",
            "혼밥", "소확행", "퇴근길", "출근길", "점메추", "아아", "아메", "아카",
            "아카페라", "카페라떼", "카페모카", "카모", "카모카", "헬스장", "교촌치킨"
        ]
        
        # 새로운 문장 분리 기준 토큰/품사 목록
        self.SPLIT_TOKENS = {
            "EC", # 연결 어미: -고, -으며 등
            "JC", # 접속 조사: -와/과, -랑 등
            "MAJ" # 접속 부사: 그리고, 그러나 등
        }
        # 토큰 텍스트 기준:
        self.SPLIT_TEXTS = ["그리고", "그러고", "해야지", "해야겠다", "해야돼", "해야만", "하고", "이고"]

    def _split_sentences(self, text: str) -> List[str]:
        # Mecab으로 전체 텍스트를 형태소 분석합니다.
        tokens = self.tokenizer.pos(text)
        
        sentences = []
        current_sentence_tokens = []
        
        for i, (token, pos) in enumerate(tokens):
            current_sentence_tokens.append(token)
            
            is_pos_split = pos in self.SPLIT_TOKENS
            is_text_split = token in self.SPLIT_TEXTS
            
            should_split = False
            
            if is_pos_split or is_text_split:
                 should_split = True
            
            if should_split or i == len(tokens) - 1:
                sentence = "".join(current_sentence_tokens).strip()
                if sentence:
                    sentences.append(sentence)
                current_sentence_tokens = []
        
        # 후처리: 분리 기준 토큰 처리 ('그리고', '해야지' 등이 분리된 채로 남은 것 처리)
        final_sentences = []
        for s in sentences:
            found_split = False
            for text in self.SPLIT_TEXTS:
                if s.endswith(text):
                    final_sentences.append(s[:-len(text)].strip())
                    final_sentences.append(text)
                    found_split = True
                    break
            if not found_split:
                 final_sentences.append(s)
        
        
        coalesced_sentences = []
        i = 0
        while i < len(final_sentences):
            current = final_sentences[i]
            if current in self.SPLIT_TEXTS and i > 0:
                coalesced_sentences[-1] += " " + current # 이전 문장에 합치기
                if i + 1 < len(final_sentences) and final_sentences[i+1] not in self.SPLIT_TEXTS:
                     coalesced_sentences[-1] += " " + final_sentences[i+1]
                     i += 1
            else:
                 coalesced_sentences.append(current)
            i += 1

        return [s for s in coalesced_sentences if s.strip()]


    def _get_absolute_date(self, relative_date: str) -> str:
        """
        '오늘', '내일', '주말' 등의 상대적 날짜를 YYYY-MM-DD 형식으로 변환합니다. (동일)
        """
        today = datetime.today()

        if relative_date == "오늘" or relative_date == "":
            return today.strftime("%Y-%m-%d")
        elif relative_date == "내일":
            tomorrow = today + timedelta(days=1)
            return tomorrow.strftime("%Y-%m-%d")
        elif relative_date == "주말":
            # 다음 주말(토요일)을 계산 (월요일이 한 주의 시작)
            days_until_saturday = (5 - today.weekday() + 7) % 7
            if days_until_saturday == 0:
                days_until_saturday = 7
            weekend_saturday = today + timedelta(days=days_until_saturday)
            return weekend_saturday.strftime("%Y-%m-%d")
        elif relative_date == "이번주":
            # 이번 주 월요일을 계산
            days_until_monday = today.weekday()
            this_monday = today - timedelta(days=days_until_monday)
            return this_monday.strftime("%Y-%m-%d")
        elif relative_date == "다음주":
            # 다음 주 월요일을 계산
            days_until_monday = (0 - today.weekday() + 7) % 7
            next_monday = today + timedelta(days=days_until_monday)
            return next_monday.strftime("%Y-%m-%d")
        else:
            return relative_date

    def _parse_single_sentence(self, sentence: str) -> Dict[str, Any]:
        print(f"\n[STEP 1] 원본 문장: '{sentence}'")

        # 1. 원본 문장에서 신조어/줄임말을 먼저 찾습니다. (동일)
        # ... (이 부분의 코드는 위에서 수정한 형태소 분리를 제외하고 동일하게 유지됩니다.)
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
                print(f"[STEP 2] 신조어 처리 후 Mecab 품사 태깅 결과: {parsed_tokens}")
                break
            else:
                parsed_tokens = self.tokenizer.pos(sentence)
                print(f"[STEP 2] Mecab 품사 태깅 결과: {parsed_tokens}")

        date = ""
        time = ""
        metadata_tokens = set()
        verb_parts = [] # 동사 원형을 저장할 리스트

        for i, (token, pos) in enumerate(parsed_tokens):
            # 메타데이터 추출 (동일)
            if token in ["내일", "오늘", "이번주", "다음주", "주말"]:
                date = self._get_absolute_date(token)
                metadata_tokens.add((token, pos))
            elif token in ["아침", "점심", "저녁", "오전", "오후", "새벽"]:
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
                    time = f"{token}"
                    metadata_tokens.add((token, pos))
            
            # TODO: 동사/형용사 원형 추출 및 필터링
            elif pos in ["VV", "VA"]: # VV: 동사, VA: 형용사
                # '있-'이나 '없-'으로 시작하는 경우는 제외 (상태 표현이지 할 일이 아님)
                if not (token.startswith("있") or token.startswith("없")):
                    verb_parts.append(token)
                metadata_tokens.add((token, pos))


        # 연속된 명사(NNG, NNP)를 결합하여 todo_parts에 추가 (동일)
        todo_parts = []
        i = 0
        while i < len(parsed_tokens):
            token, pos = parsed_tokens[i]
            if (token, pos) in metadata_tokens:
                i += 1
                continue

            if pos.startswith("NN"):
                combined_token = token
                j = i + 1
                while j < len(parsed_tokens) and parsed_tokens[j][1].startswith("NN"):
                    if (
                        parsed_tokens[j][0],
                        parsed_tokens[j][1],
                    ) not in metadata_tokens:
                        combined_token += parsed_tokens[j][0]
                    j += 1
                todo_parts.append(combined_token)
                i = j
            else:
                i += 1
        
        # 3. todo_parts와 verb_parts를 결합하고, 동사에 '-기'를 붙여 명사화합니다.
        
        # 명사 부분에 동사 원형을 추가
        if verb_parts:
            # 동사 원형에 '-기'를 붙인 명사구를 생성합니다. (예: 먹다 -> 먹기)
            verb_noun = verb_parts[-1] + "기"
            todo_parts.append(verb_noun)
            
            # 동사/형용사의 원형 부분만 명사구로 만들고, 나머지 명사는 그대로 둠
            # 동사 부분이 중복되지 않게 마지막 동사만 사용하거나, 명사 리스트 뒤에 붙이는 방식을 선택합니다.
            # 여기서는 명사 뒤에 최종 명사형 동사를 붙이는 방식을 사용합니다.
            
            # 최종 todo 문장 생성: 명사구 + '동사원형기'
            todo = " ".join(todo_parts)
            
        else:
            # 동사가 없으면 명사구만 사용
            todo = " ".join(todo_parts)
        
        # todo가 비어있으면 문장 전체를 다시 사용 (예외 처리)
        if not todo.strip():
            todo = sentence

        print("\n--- 파싱 결과 최종 확인 ---")
        print(f"Todo: '{todo}'")
        print(f"Date: '{date}'")
        print(f"Time: '{time}'")
        print("----------------------------\n")

        return {"todo": todo, "date": date, "time": time, "original_sentence": sentence}

    def parse_multiple_sentences(self, text: str) -> List[Dict[str, Any]]:
        print(f"전체 입력 텍스트: '{text}'")
        sentences = self._split_sentences(text)

        parsed_results = []
        last_known_date = datetime.today().strftime("%Y-%m-%d")

        for sentence in sentences:
            if not sentence:
                continue

            result = self._parse_single_sentence(sentence)

            if result["date"]:
                last_known_date = result["date"]
            elif last_known_date:
                result["date"] = last_known_date

            parsed_results.append(result)

        return parsed_results


if __name__ == "__main__":
    parser_instance = Parser()

    # 테스트 케이스
    input_text = "아침에 엽떡 먹고 그리고 오후 8시에 친구와 강남에서 저녁 약속이 있어 주말에는 집 근처 마트에서 장을 봐야지"
    
    # 1. 동사 명사화 테스트
    # "엽떡 먹고 그리고" -> "엽떡 먹기"
    # "저녁 약속이 있어" -> 동사('있어') 제외, 명사구만 추출
    # "장을 봐야지" -> "장 보기"
    parsed_list = parser_instance.parse_multiple_sentences(input_text)

    print("\n\n--- 최종 JSON 출력 ---")
    print(json.dumps(parsed_list, indent=4, ensure_ascii=False))