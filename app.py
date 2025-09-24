# app.py
from fastapi import FastAPI
from pydantic import BaseModel
from typing import List, Dict, Any
import uvicorn
import sys
import os

# nlp_agent 패키지 내의 nlp_agent 모듈에서 NLPAgent 클래스를 임포트합니다.
# 이렇게 하면 파이썬이 정확한 경로를 찾아갈 수 있습니다.
from nlp_agent.nlp_agent import NLPAgent


# Pydantic을 사용해 요청 데이터의 형식을 정의합니다.
class TextRequest(BaseModel):
    user_id: str
    voice_text: str


# NLPAgent 인스턴스를 초기화합니다.
agent = NLPAgent()

# FastAPI 애플리케이션 인스턴스를 생성합니다.
app = FastAPI(
    title="DoToDo NLP Model Service",
    description="To-do 항목을 자연어 처리하는 마이크로서비스 API",
    version="1.0.0",
)


@app.get("/")
def read_root():
    return {"message": "DoToDo NLP Model Service is running."}


@app.post("/process-text", response_model=List[Dict[str, Any]])
def process_text_endpoint(request_body: TextRequest):
    """
    사용자의 자연어 텍스트를 받아 TODO 항목을 추출하고 처리합니다.
    """
    input_text = request_body.voice_text
    processed_todos = agent.process_text(input_text)
    final_response = []
    for item in processed_todos:
        # 응답 순서를 재정렬
        # 'embedding' 값을 반올림하여 간소화
        embedding_list = [round(v, 4) for v in item["embedding"]]

        ordered_item = {
            "user_id": request_body.user_id,
            "category": item["category"],
            "todo": item["todo"],
            "simplified_text": item["simplified_text"],
            "date": item["date"],
            "time": item["time"],
            "original_sentence": item["original_sentence"],
            "embedding": embedding_list,
        }
        final_response.append(ordered_item)

    return final_response


if __name__ == "__main__":
    # uvicorn으로 FastAPI 앱을 실행합니다.
    uvicorn.run(app, host="0.0.0.0", port=5000)
