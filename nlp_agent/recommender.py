import chromadb
from chromadb.utils import embedding_functions
from typing import List, Dict, Any
from datetime import datetime


class RecommendationEngine:
    def __init__(self, host: str = "localhost", port: int = 8000):
        self.client = chromadb.HttpClient(host=host, port=port)
        self.collection_name = "user_todos"
        self.ef = embedding_functions.DefaultEmbeddingFunction()
        self.collection = self.client.get_or_create_collection(
            name=self.collection_name, embedding_function=self.ef
        )

    def save_todo_item(
        self, user_id: str, todo_text: str, embedding: List[float], date: str
    ):
        try:
            self.collection.add(
                embeddings=[embedding],
                documents=[todo_text],
                metadatas=[{"user_id": user_id, "date": date}],
                ids=[f"{user_id}_{todo_text}_{date}_{datetime.now().timestamp()}"],
            )
            print("✅ 할 일 항목이 성공적으로 저장되었습니다.")
        except Exception as e:
            print(f"❌ 데이터 저장 오류: {e}")

    def find_recommendations(
        self,
        user_id: str,
        todo_text: str,
        embedding: List[float],
        limit: int = 5,
        min_frequency: int = 2,
        min_similarity: float = 0.8,
    ):
        all_recommendations = {}

        # 1. 빈도수 기반 추천 검색 (같은 날 수행된 할 일)
        try:
            # 먼저 현재 사용자와 가장 유사한 문서들을 찾습니다.
            results = self.collection.query(
                query_embeddings=[embedding],
                n_results=limit,
                where={"user_id": user_id},
            )

            # 검색된 문서의 날짜를 기반으로 동일 날짜에 포함된 모든 할 일들의 빈도를 계산합니다.
            for metadata in results.get("metadatas", [[]])[0]:
                similar_day_todos = self.collection.get(
                    where={
                        "$and": [
                            {"user_id": {"$eq": user_id}},
                            {"date": {"$eq": metadata["date"]}},
                        ]
                    }
                )

                for day_doc in similar_day_todos["documents"]:
                    # ✅ 현재 입력된 할 일은 추천하지 않습니다.
                    if day_doc != todo_text:
                        all_recommendations[day_doc] = (
                            all_recommendations.get(day_doc, 0) + 1
                        )
        except Exception as e:
            print(f"❌ 빈도수 기반 추천 검색 오류: {e}")

        # 2. 유사도 기반 추천 검색 (유사한 텍스트를 가진 할 일)
        try:
            similarity_results = self.collection.query(
                query_embeddings=[embedding],
                n_results=limit,
                where={"user_id": user_id},
            )

            for i, doc in enumerate(similarity_results.get("documents", [[]])[0]):
                similarity_score = similarity_results.get("distances", [[]])[0][i]

                # ✅ 현재 입력된 할 일은 추천하지 않으며, 유사도 기준을 충족하는 항목만 추가합니다.
                if doc != todo_text and similarity_score >= min_similarity:
                    all_recommendations[doc] = all_recommendations.get(doc, 0) + 1
        except Exception as e:
            print(f"❌ 유사도 기반 추천 검색 오류: {e}")

        # 3. 빈도수 임계값 적용 및 결과 정렬
        final_recs = {
            todo: count
            for todo, count in all_recommendations.items()
            if count >= min_frequency
        }

        sorted_recs = sorted(final_recs.items(), key=lambda item: item[1], reverse=True)

        # ✅ 4. 최종 추천 목록을 상위 3개로 제한
        limited_recs = sorted_recs[:3]

        return [{"todo": item[0], "frequency": item[1]} for item in limited_recs]
