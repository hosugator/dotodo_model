import re
import json
from typing import Dict, Any, List
from mecab import MeCab
from datetime import datetime, timedelta
import os

SENTENCE_SPLITTER = re.compile(r"([.?!,])\s*|\n")


class Parser:
    def __init__(self):
        self.tokenizer = MeCab()
        print("Parser 초기화 완료: Mecab 엔진 사용")

        # 원본 문장에서 찾아야 할 신조어 목록
        self.special_words = [
            "엽떡",
            "짜파구리",
            "맞담",
            "인강",
            "쿠팡",
            "배민",
            "요기요",
            "로제",
            "혼술",
            "혼밥",
            "소확행",
            "퇴근길",
            "출근길",
            "점메추",
            "점메추",
            "아아",
            "아메",
            "아카",
            "아카페라",
            "카페라떼",
            "카페모카",
            "카모",
            "카모카",
        ]

    def _split_sentences(self, text: str) -> List[str]:
        sentences = [
            s.strip()
            for s in SENTENCE_SPLITTER.split(text)
            if s and s not in [".", "?", "!", ","]
        ]
        return sentences

    def _get_absolute_date(self, relative_date: str) -> str:
        """
        '오늘', '내일', '주말' 등의 상대적 날짜를 YYYY-MM-DD 형식으로 변환합니다.
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

        # 1. 원본 문장에서 신조어/줄임말을 먼저 찾습니다.
        for word in self.special_words:
            if word in sentence:
                # 2. Mecab 토큰 결과를 덮어쓰기 위해, 해당 단어를 명사로 간주하고 새로 파싱합니다.
                # 예: '아침에 엽떡먹고' -> '아침' + '엽떡' + '먹고'
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
                # 신조어가 없으면 기존 Mecab 파싱을 사용합니다.
                parsed_tokens = self.tokenizer.pos(sentence)
                print(f"[STEP 2] Mecab 품사 태깅 결과: {parsed_tokens}")

        date = ""
        time = ""
        metadata_tokens = set()

        for i, (token, pos) in enumerate(parsed_tokens):
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

        # 연속된 명사(NNG, NNP)를 결합하여 todo_parts에 추가
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

        todo = " ".join(todo_parts)

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

    input_text = "아침에 엽떡먹고, 그리고 오후 8시에 친구와 강남에서 저녁 약속이 있어. 주말에는 집 근처 마트에서 장을 봐야지."
    parsed_list = parser_instance.parse_multiple_sentences(input_text)

    print("\n\n--- 최종 JSON 출력 ---")
    print(json.dumps(parsed_list, indent=4, ensure_ascii=False))
