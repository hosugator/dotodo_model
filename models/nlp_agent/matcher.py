import torch
import torch.nn.functional as F
from typing import Dict, Any, List, Tuple
from embedder import TextEmbedder


class ToDoMatcher:
    def __init__(self, embedder: TextEmbedder, similarity_threshold: float = 0.5):
        """
        카테고리 매칭 클래스를 초기화하고, 카테고리 임베딩을 미리 계산합니다.

        Args:
            embedder (TextEmbedder): 텍스트 임베딩을 담당하는 인스턴스.
            similarity_threshold (float): 유사도 임계값. 이 값보다 낮으면 카테고리를 할당하지 않습니다.
        """
        self.embedder = embedder
        self.similarity_threshold = similarity_threshold

        # 미리 정의된 카테고리와 대표 문구
        self.categories: Dict[str, str] = {
            "운동": "헬스장 가기, 운동하기, 산책하기",
            "공부": "공부하기, 책 읽기, 강의 듣기",
            "장보기": "마트 가기, 장보기, 식료품 사기",
            "업무": "업무하기, 보고서 쓰기, 회의 참여",
            "일상": "친구 만나기, 부모님 댁 방문, 약속",
        }

        # 카테고리 임베딩 미리 계산 및 저장
        self.category_embeddings: Dict[str, torch.Tensor] = (
            self._precompute_category_embeddings()
        )
        print("\n카테고리 임베딩 사전 계산 완료.")

    def _precompute_category_embeddings(self) -> Dict[str, torch.Tensor]:
        """
        정의된 각 카테고리의 대표 문구를 임베딩하여 딕셔너리에 저장합니다.
        """
        embeddings = {}
        print("카테고리 임베딩 계산 중...")
        for category, phrase in self.categories.items():
            # 임베더의 메서드를 활용하여 임베딩만 가져옴
            embed_result = self.embedder.embed_text(phrase)
            embeddings[category] = embed_result["embedding"]
        return embeddings

    def match_category(self, todo_embedding: torch.Tensor) -> str:
        """
        새로운 투두 임베딩과 카테고리 임베딩을 비교하여 가장 유사한 카테고리를 반환합니다.

        Args:
            todo_embedding (torch.Tensor): 새로운 투두 항목의 임베딩 벡터.

        Returns:
            str: 가장 유사한 카테고리 이름. 임계값 이하일 경우 '기타'를 반환.
        """
        max_similarity = -1
        best_match = "기타"

        # 새로운 투두 임베딩과 모든 카테고리 임베딩 간의 유사도 계산
        for category, category_embed in self.category_embeddings.items():
            # 코사인 유사도 계산
            similarity = F.cosine_similarity(
                todo_embedding, category_embed, dim=1
            ).item()

            if similarity > max_similarity and similarity >= self.similarity_threshold:
                max_similarity = similarity
                best_match = category

        print(f"최고 유사도: {max_similarity:.4f}, 할당된 카테고리: '{best_match}'")
        return best_match


if __name__ == "__main__":
    # 임베더 인스턴스 생성 (테스트용)
    embedder = TextEmbedder()

    # 매처 인스턴스 생성
    matcher = ToDoMatcher(embedder)

    # 테스트용 투두 텍스트와 임베딩 생성
    test_todo_text = "헬스장에 가기"
    test_todo_embedding = embedder.embed_text(test_todo_text)["embedding"]

    # 카테고리 매칭 실행
    assigned_category = matcher.match_category(test_todo_embedding)

    print(f"\n테스트 투두: '{test_todo_text}'")
    print(f"할당된 카테고리: '{assigned_category}'")

    print("-" * 50)

    # 또 다른 테스트
    test_todo_text_2 = "수학 공부하기"
    test_todo_embedding_2 = embedder.embed_text(test_todo_text_2)["embedding"]

    assigned_category_2 = matcher.match_category(test_todo_embedding_2)

    print(f"\n테스트 투두: '{test_todo_text_2}'")
    print(f"할당된 카테고리: '{assigned_category_2}'")
