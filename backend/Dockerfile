# ============================================================
# FastAPI 백엔드 Dockerfile
# Python 3.11 기반, 비동기 처리에 최적화된 경량 이미지
# ============================================================

FROM python:3.11-slim

# ─── 시스템 의존성 설치 ───
# PostgreSQL 클라이언트 라이브러리 + 빌드 도구
RUN apt-get update && apt-get install -y \
    gcc \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# ─── 작업 디렉토리 설정 ───
WORKDIR /app

# ─── Python 의존성 설치 (캐시 레이어 활용) ───
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# ─── 소스 코드 복사 ───
COPY . .

# ─── 포트 노출 ───
EXPOSE 8000

# ─── 기본 실행 명령 (docker-compose에서 오버라이드 가능) ───
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
