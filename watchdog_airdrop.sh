#!/bin/bash
# 🪂 에어드롭 파밍 봇 Watchdog — 5분마다 프로세스 확인, 죽으면 재시작
DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$DIR"

PID_FILE="logs/airdrop_farmer.pid"
LOG_FILE="logs/airdrop_farmer.log"
WATCHDOG_LOG="logs/watchdog.log"

echo "$(date '+%Y-%m-%d %H:%M:%S') [watchdog] 체크 시작" >> "$WATCHDOG_LOG"

# PID 파일 확인
if [ ! -f "$PID_FILE" ]; then
    echo "$(date '+%Y-%m-%d %H:%M:%S') [watchdog] PID 파일 없음. 봇 시작..." >> "$WATCHDOG_LOG"
    bash start_airdrop.sh
    exit 0
fi

PID=$(cat "$PID_FILE")

# 프로세스 살아있는지 확인
if kill -0 "$PID" 2>/dev/null; then
    echo "$(date '+%Y-%m-%d %H:%M:%S') [watchdog] 정상 가동중 (PID: $PID)" >> "$WATCHDOG_LOG"
else
    echo "$(date '+%Y-%m-%d %H:%M:%S') [watchdog] ⚠️ 프로세스 죽음! 재시작..." >> "$WATCHDOG_LOG"
    bash start_airdrop.sh
    echo "$(date '+%Y-%m-%d %H:%M:%S') [watchdog] 재시작 완료" >> "$WATCHDOG_LOG"
fi

# 로그 파일이 50MB 넘으면 백업하고 새로 생성
if [ -f "$LOG_FILE" ]; then
    SIZE=$(stat -f%z "$LOG_FILE" 2>/dev/null || echo 0)
    if [ "$SIZE" -gt 52428800 ]; then
        mv "$LOG_FILE" "${LOG_FILE}.$(date '+%Y%m%d_%H%M%S')"
        echo "$(date '+%Y-%m-%d %H:%M:%S') [watchdog] 로그 로테이션" >> "$WATCHDOG_LOG"
    fi
fi