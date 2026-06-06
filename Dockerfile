FROM python:3.11-slim

WORKDIR /app

# 시스템 의존성
RUN apt-get update && apt-get install -y \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Python 패키지 설치
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Playwright 브라우저 설치
RUN playwright install chromium
RUN playwright install-deps chromium

# 소스 복사
COPY . .

# 디렉토리 생성
RUN mkdir -p logs data

ENV TZ=Asia/Seoul
ENV PYTHONUNBUFFERED=1

CMD ["python", "main.py"]
