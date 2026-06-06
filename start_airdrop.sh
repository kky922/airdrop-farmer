#!/bin/bash
# 에어드롭 파밍 봇 시작 스크립트
cd "$(dirname "$0")"

# 기존 프로세스 종료
PID_FILE="logs/airdrop_farmer.pid"
if [ -f "$PID_FILE" ]; then
    OLD_PID=$(cat "$PID_FILE")
    if kill -0 "$OLD_PID" 2>/dev/null; then
        echo "기존 프로세스 종료 중 (PID: $OLD_PID)..."
        kill "$OLD_PID"
        sleep 2
    fi
fi

# 로그 디렉토리 확인
mkdir -p logs

# 봇 시작 (venv Python 강제 지정)
nohup "$(dirname "$0")/.venv/bin/python3" main.py >> logs/airdrop_farmer.log 2>&1 &
echo $! > "$PID_FILE"
echo "🪂 에어드롭 파밍 봇 시작 (PID: $(cat $PID_FILE))"
sleep 3
tail -10 logs/airdrop_farmer.log