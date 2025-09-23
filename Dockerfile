# 파이썬 3.11 버전을 기반으로 컨테이너 이미지를 생성합니다.
FROM python:3.11-slim

# 컨테이너 내 작업 디렉터리를 /app으로 설정합니다.
WORKDIR /app

# 애플리케이션의 의존성(requirements.txt) 파일을 컨테이너에 복사합니다.
COPY requirements.txt .

# requirements.txt에 명시된 파이썬 라이브러리들을 설치합니다.
RUN pip install --no-cache-dir -r requirements.txt

# 한국어 자연어 처리를 위한 MeCab과 관련 사전을 설치합니다.
RUN pip install python-mecab-ko

# 'nlp_agent' 폴더와 'app.py'를 포함한 나머지 모든 파일을 컨테이너의 /app 디렉터리로 복사합니다.
COPY . .

# FastAPI 서버가 사용하는 포트 5000을 외부에 노출합니다.
EXPOSE 5000

# 컨테이너가 시작될 때 uvicorn 서버를 실행합니다.
# "app:app"은 app.py 파일의 app 인스턴스를 의미합니다.
CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "5000"]