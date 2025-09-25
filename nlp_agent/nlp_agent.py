import json
from typing import Dict, Any, List

# .parser, .embedder, .matcher 파일을 임포트
from .parser import Parser
from .embedder import TextEmbedder
from .matcher import ToDoMatcher
from .recommender import RecommendationEngine

class NLPAgent:
    def __init__(self):
        # 파서, 임베더, 매처 인스턴스 생성
        self.parser = Parser()
        self.embedder = TextEmbedder()
        self.matcher = ToDoMatcher(self.embedder)
        # ✅ RecommendationEngine 인스턴스 생성
        self.recommender = RecommendationEngine(host="localhost", port=8001)
        print("\nNLPAgent 초기화 완료.")

    # ✅ user_id 매개변수 추가
    def process_text(self, text: str, user_id: str) -> List[Dict[str, Any]]:
        """
        입력 텍스트를 처리하여 TODO 항목들을 추출하고 임베딩 및 카테고리 할당, 그리고 개인화 추천을 수행합니다.
        
        Args:
            text (str): 사용자의 자연어 입력.
            user_id (str): 사용자를 식별하는 고유 ID.
        
        Returns:
            List[Dict[str, Any]]: 처리된 TODO 항목들의 리스트.
        """
        # 1단계: Parser를 통해 문장 분리 및 메타데이터 추출
        parsed_todos = self.parser.parse_multiple_sentences(text)
        
        # 2단계: 각 TODO 항목에 대해 임베딩, 카테고리 할당, 벡터 DB 저장
        for todo_item in parsed_todos:
            todo_text = todo_item.get('todo', '')
            if todo_text:
                # 2-1단계: todo 텍스트를 임베더로 전달하여 임베딩 생성
                embed_result = self.embedder.embed_text(todo_text)
                embedding = embed_result['embedding']
                
                # 2-2단계: 임베딩을 매처로 전달하여 카테고리 할당
                assigned_category = self.matcher.match_category(embedding)
                
                # 변환된 텍스트, 임베딩, 카테고리를 결과에 추가
                todo_item['simplified_text'] = todo_text
                todo_item['embedding'] = embedding.squeeze().tolist()
                todo_item['category'] = assigned_category
                todo_item['user_id'] = user_id # ✅ 사용자 ID 추가
                
                # ✅ 3단계: 벡터 DB에 할 일 항목 저장
                self.recommender.save_todo_item(
                    user_id=user_id,
                    todo_text=todo_text,
                    embedding=todo_item['embedding'],
                    date=todo_item['date']
                )
            else:
                todo_item['simplified_text'] = ''
                todo_item['embedding'] = []
                todo_item['category'] = '기타'

        # ✅ 4단계: 저장 후, 각 할 일에 대한 추천 항목 검색 및 추가
        for todo_item in parsed_todos:
            todo_text = todo_item.get('todo', '')
            if not todo_text:
                continue
            
            recommendations = self.recommender.find_recommendations(
                user_id=user_id,
                todo_text=todo_text,
                embedding=todo_item['embedding'],
                min_frequency=2,     # 최소 2번 이상 함께 수행된 할 일만 추천
                min_similarity=0.8   # 유사도 0.8 이상인 할 일도 추천
            )
            todo_item['recommendations'] = recommendations
        
        return parsed_todos

if __name__ == "__main__":
    agent = NLPAgent()

    input_text = "내일 아침 헬스장에 가야 해. 그리고 오후 8시에 친구와 저녁 약속이 있어. 주말에는 집 근처 마트에서 장을 봐야지."
    
    # 텍스트 처리 파이프라인 실행
    # ✅ 테스트용 user_id 추가
    final_result = agent.process_text(input_text, user_id="test_user_123")

    print("\n\n--- 최종 통합 결과 ---")
    for idx, item in enumerate(final_result):
        print(f"** {idx + 1}. 원본 문장: '{item['original_sentence']}'")
        print(f"   - To-do (변환): '{item['simplified_text']}'")
        print(f"   - 카테고리: '{item['category']}'")
        print(f"   - 날짜: '{item['date']}'")
        print(f"   - 시간: '{item['time']}'")
        print(f"   - 추천 항목: {item.get('recommendations', '없음')}") # ✅ 추천 항목 추가
        print("-" * 20)