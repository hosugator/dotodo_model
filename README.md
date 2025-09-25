## ToDo 자연어 처리 모델 서비스

이 프로젝트는 사용자의 자연어 음성 입력으로부터 할 일(To-Do) 항목을 추출하고, 이를 구조화된 데이터로 변환하는 마이크로서비스입니다. NLP(자연어 처리) 기술을 활용하여 텍스트 파싱, 임베딩, 그리고 카테고리 매칭을 수행합니다.

-----

### 주요 기능

1.  **텍스트 파싱 및 정보 추출**: 사용자의 문장에서 할 일 항목(`todo`), 날짜(`date`), 시간(`time`) 등 핵심 정보를 분리합니다.
2.  **의미 기반 카테고리 분류**: 임베딩 모델을 사용하여 텍스트의 의미적 유사도를 측정하고, 미리 정의된 카테고리(예: 운동, 공부, 장보기)로 할 일을 자동 분류합니다.
3.  **API 제공**: FastAPI를 통해 다른 백엔드 서비스와 쉽게 연동될 수 있는 RESTful API 엔드포인트를 제공합니다.

-----

### 기술 스택

  * **FastAPI**: 빠르고 효율적인 API 서버 구축
  * **Mecab**: 한국어 형태소 분석 및 품사 태깅
  * **Hugging Face Transformers**: 의미 기반 텍스트 임베딩
  * **PyTorch**: 임베딩 모델 실행
  * **Docker**: 서비스 컨테이너화 및 배포

-----

### API 규격

#### 요청 (Request)

사용자 ID와 텍스트 입력을 JSON 형태로 받습니다.

  * **URL**: `/process-text`
  * **Method**: `POST`
  * **Body**:
    ```json
    {
      "user_id": "string",
      "text": "string"
    }
    ```

#### 응답 (Response)

처리 결과를 포함하는 JSON을 반환합니다.

  * **Body**:
    ```json
    {
      "success": true,
      "todos": [
        {
          "user_id": "string",
          "todo": "string",
          "date": "string",
          "time": "string",
          "original_sentence": "string",
          "embedding": [
            0.123, -0.456, ...
          ],
          "category": "string"
        }
      ]
    }
    ```

-----

### 개발 및 실행 방법

1.  **환경 설정**:

    ```bash
    # 가상 환경 생성 및 활성화
    python3 -m venv venv
    source venv/bin/activate
    # 의존성 설치
    pip install -r requirements.txt
    ```

2.  **로컬 서버 실행**:

    ```bash
    # 9000번 포트에서 서버 실행 (포트 충돌 방지)
    uvicorn app:app --reload --host 0.0.0.0 --port 9000
    ```

    서버가 실행되면 `http://localhost:9000/docs`에서 API 문서를 확인할 수 있습니다.

3.  **Docker를 사용한 빌드 및 배포**:

    ```bash
    # Docker 이미지 빌드
    docker build -t dotodo-model-service:local .
    # Docker 컨테이너 실행 (예시: 8000번 포트 매핑)
    docker run -d --name local-model-server -p 8000:5000 dotodo-model-service:local
    ```