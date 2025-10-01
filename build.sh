#!/bin/bash

# 최소 필요 공간 설정 (단위: GB)
# PyTorch (torch) 같은 대용량 라이브러리 설치를 고려하여 8GB로 상향 조정합니다.
MIN_SPACE_GB=8 

# 루트 파일 시스템('/')의 사용 가능한 공간(KB)을 가져옵니다.
AVAILABLE_KB=$(df -k / | awk 'NR==2 {print $4}')

# KB를 GB로 변환합니다.
AVAILABLE_GB=$((AVAILABLE_KB / 1024 / 1024))

echo "========================================"
echo "         🚀 Docker 빌드 전 검사"
echo "========================================"
echo "현재 사용 가능 디스크 공간: ${AVAILABLE_GB} GB"
echo "최소 필요 공간: ${MIN_SPACE_GB} GB (torch 포함 시 권장)"
echo "----------------------------------------"

if [ "$AVAILABLE_GB" -lt "$MIN_SPACE_GB" ]; then
    echo "❌ 에러: 사용 가능 공간(${AVAILABLE_GB} GB)이 ${MIN_SPACE_GB} GB보다 작습니다."
    echo "도커 빌드를 시작할 수 없습니다. 'docker system prune -a' 등으로 공간을 확보하세요."
    echo "========================================"
    exit 1
else
    echo "✅ 디스크 공간 충분. 빌드를 시작합니다..."
    echo "========================================"

    # 1. 기존 컨테이너 중지 및 삭제 (선택 사항)
    docker stop dotodo-api > /dev/null 2>&1
    docker rm dotodo-api > /dev/null 2>&1
    
    # 2. Docker 이미지 빌드 (캐시 자동 사용)
    docker build -t dotodo-api:latest .
    
    # 3. 새로운 컨테이너 실행 (성공적인 빌드 후)
    if [ $? -eq 0 ]; then
        echo "✅ 빌드 성공! 새로운 컨테이너를 실행합니다."
        # 포트는 예시입니다. 실제 사용 포트에 맞게 조정하세요.
        docker run -d --name dotodo-api -p 8000:5000 dotodo-api:latest
    else
        echo "❌ 도커 빌드 실패. 로그를 확인하세요."
    fi
fi
