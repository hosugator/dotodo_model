from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, RootModel
from typing import List, Dict, Any

import uvicorn
import sys
import os

from nlp_agent.nlp_agent import NLPAgent
from recommendation.todo_recommendation_system import LangChainTodoRecommendationSystem

# Pydantic 모델을 재정의하여 추천 항목을 포함합니다.
class Recommendation(BaseModel):
    todo: str
    frequency: int

class ProcessedTodoItem(BaseModel):
    user_id: str
    todo: str
    date: str
    time: str
    original_sentence: str
    embedding: List[float]
    category: str
    recommendations: List[Recommendation]

class TodoResponse(BaseModel):
    success: bool
    todos: List[ProcessedTodoItem]

# Pydantic을 사용해 요청 데이터의 형식을 정의합니다.
class TextRequest(BaseModel):
    user_id: str
    text: str


# 새로운 요청 데이터 모델을 정의합니다.
class PastTodoItem(BaseModel):
    todo: str
    completed: bool

# 'CompletedTodos'를 RootModel로 수정
class CompletedTodos(RootModel):
    root: Dict[str, List[PastTodoItem]]

class PastData(BaseModel):
    user_id: str
    date: str
    completed_todos: CompletedTodos

class ScheduledTodoItem(BaseModel):
    todo: str
    completed: bool

# 'ScheduledTodos'를 RootModel로 수정
class ScheduledTodos(RootModel):
    root: Dict[str, List[ScheduledTodoItem]]

class TodayData(BaseModel):
    user_id: str
    date: str
    scheduled_todos: ScheduledTodos

class RecommendationRequest(BaseModel):
    p_data: List[PastData]
    h_data: TodayData


# NLPAgent와 추천 시스템 인스턴스를 초기화합니다.
agent = NLPAgent()
# 추천 시스템 인스턴스를 초기화합니다.
recommendation_system = LangChainTodoRecommendationSystem()


# FastAPI 애플리케이션 인스턴스를 생성합니다.
app = FastAPI(
    title="DoToDo NLP Model Service",
    description="To-do 항목을 자연어 처리하는 마이크로서비스 API",
    version="1.0.0",
)


@app.get("/")
def read_root():
    return {"message": "DoToDo NLP Model Service is running."}


@app.post("/process-text", response_model=TodoResponse)
def process_text_endpoint(request_body: TextRequest):
    """
    사용자의 자연어 텍스트를 받아 TODO 항목을 추출하고 처리하며,
    추천 항목을 함께 반환합니다. 모든 로직은 NLPAgent에서 처리됩니다.
    """
    input_text = request_body.text
    
    # NLPAgent의 process_text 메소드를 호출하여 모든 파이프라인을 실행합니다.
    # 이 메소드는 할 일 저장, 카테고리 할당, 추천 검색까지 모두 포함한 결과를 반환합니다.
    final_todos = agent.process_text(text=input_text, user_id=request_body.user_id)

    # final_todos 리스트의 각 항목에 대해 embedding 값을 반올림하여 간소화합니다.
    for item in final_todos:
        if 'embedding' in item and isinstance(item['embedding'], list):
            item['embedding'] = [round(v, 4) for v in item['embedding']]

    return {"success": True, "todos": final_todos}


@app.post("/api/model/recommendations")
def get_recommendations_endpoint(request_body: RecommendationRequest):
    """
    사용자의 과거 및 현재 데이터를 기반으로 TODO 항목을 추천합니다.
    """
    print("추천 API 엔드포인트 호출됨.")
    try:
        # Pydantic v2 문법에 맞게 'root' 속성으로 데이터에 접근
        p_data = request_body.p_data
        h_data = request_body.h_data

        recommendations = recommendation_system.run_recommendation_process(p_data, h_data)
        return recommendations
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"추천 생성 중 오류 발생: {e}")


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=9000)