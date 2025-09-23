import json
from typing import Dict, Any, List

# parser.py, embedder.py, matcher.py 파일을 임포트
from parser import Parser
from embedder import TextEmbedder
from matcher import ToDoMatcher

class NLPAgent:
    def __init__(self):
        # 파서, 임베더, 매처 인스턴스 생성
        self.parser = Parser()
        self.embedder = TextEmbedder()
        self.matcher = ToDoMatcher(self.embedder)
        print("\nNLPAgent 초기화 완료.")

    def process_text(self, text: str) -> List[Dict[str, Any]]:
        """
        입력 텍스트를 처리하여 TODO 항목들을 추출하고 임베딩 및 카테고리 할당을 수행합니다.
        
        Args:
            text (str): 사용자의 자연어 입력.
        
        Returns:
            List[Dict[str, Any]]: 처리된 TODO 항목들의 리스트.
        """
        # 1단계: Parser를 통해 문장 분리 및 메타데이터 추출
        parsed_todos = self.parser.parse_multiple_sentences(text)
        
        # 2단계: 각 TODO 항목에 대해 Embedder 및 Matcher 실행
        for todo_item in parsed_todos:
            todo_text = todo_item.get('todo', '')
            if todo_text:
                # 2-1단계: todo 텍스트를 임베더로 전달하여 임베딩만 생성
                embed_result = self.embedder.embed_text(todo_text)
                embedding = embed_result['embedding']
                
                # 2-2단계: 임베딩을 매처로 전달하여 카테고리 할당
                assigned_category = self.matcher.match_category(embedding)
                
                # 변환된 텍스트, 임베딩, 카테고리를 결과에 추가
                todo_item['simplified_text'] = todo_text # 파서의 결과를 그대로 사용
                todo_item['embedding'] = embedding.squeeze().tolist()
                todo_item['category'] = assigned_category
            else:
                todo_item['simplified_text'] = ''
                todo_item['embedding'] = []
                todo_item['category'] = '기타'

        return parsed_todos

if __name__ == "__main__":
    agent = NLPAgent()

    input_text = "내일 아침 헬스장에 가야 해. 그리고 오후 8시에 친구와 저녁 약속이 있어. 주말에는 집 근처 마트에서 장을 봐야지."
    
    # 텍스트 처리 파이프라인 실행
    final_result = agent.process_text(input_text)

    print("\n\n--- 최종 통합 결과 ---")
    for idx, item in enumerate(final_result):
        print(f"** {idx + 1}. 원본 문장: '{item['original_sentence']}'")
        print(f"   - To-do (변환): '{item['simplified_text']}'")
        print(f"   - 카테고리: '{item['category']}'")
        print(f"   - 날짜: '{item['date']}'")
        print(f"   - 시간: '{item['time']}'")
        print("-" * 20)