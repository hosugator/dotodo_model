# 파이썬 3.11 버전을 기반으로 컨테이너 이미지를 생성합니다.
FROM python:3.11-slim

# 컨테이너 내 작업 디렉터리를 /app으로 설정합니다.
WORKDIR /app

# 1. 의존성 파일 복사 (캐시 레이어 1: requirements.txt 내용이 바뀌지 않으면 아래 단계는 캐시 사용)
COPY requirements.txt .

# 2. 의존성 설치 및 MeCab 설치 (캐시 레이어 2: 가장 느린 단계. 캐시를 최대한 활용)
# 두 개의 pip install을 하나로 합쳐 레이어 수를 줄였습니다.
# 불필요한 캐시를 바로 삭제하여 빌드 이미지 크기를 줄였습니다.
RUN pip install -r requirements.txt && \
    pip install python-mecab-ko && \
    rm -rf /root/.cache/pip
    
# 3. 소스 코드 복사 (캐시 레이어 3: 가장 자주 바뀌는 부분이므로 가장 뒤로 배치)
# app.py나 nlp_agent 폴더의 파일이 바뀌면 여기서부터 캐시가 깨지고 새로 빌드됩니다.
COPY . .

# FastAPI 서버가 사용하는 포트 5000을 외부에 노출합니다.
EXPOSE 5000

# 컨테이너가 시작될 때 uvicorn 서버를 실행합니다.
CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "5000"]