# 🪂 에어드롭 파밍 봇 (Airdrop Farmer)

> 직장인을 위한 자동 에어드롭 파밍 시스템  
> 출근 중에도 L2 체인에서 자동으로 활동하여 에어드롭 자격을 획득합니다.

## 💡 수익 모델

| 항목 | 설명 | 예상 수익 |
|------|------|----------|
| 에어드롭 수령 | 체인별 토큰 에어드롭 | $500~$10,000+/체인 |
| 가스 최적화 | 저가스 시간대 자동 실행 | 가스 비용 30~50% 절감 |
| 멀티체인 | Scroll, Berachain, Base 동시 | 기회 다변화 |
| 시빌 방지 | 자연스러운 패턴 시뮬레이션 | 에어드롭 탈락 위험 감소 |

## 🏗️ 아키텍처

```
airdrop_farmer/
├── main.py              # 메인 실행
├── config.py            # 설정
├── wallet_manager.py    # HD 지갑 관리
├── activity_engine.py   # 활동 실행 엔진
├── anti_sybil.py        # 시빌 방지
├── gas_optimizer.py     # 가스 최적화
├── balance_tracker.py   # 잔액 모니터링
├── discovery.py         # 에어드롭 탐지
├── db.py                # SQLite DB
├── scheduler.py         # 자동 스케줄러
├── telegram_bot.py      # 텔레그램 제어
├── chains/
│   ├── base.py          # 체인 베이스
│   ├── scroll.py        # Scroll
│   ├── berachain.py     # Berachain
│   └── base_chain.py    # Base
└── protocols/
    └── __init__.py      # 프로토콜 확장
```

## 🚀 빠른 시작

### 1. 설치

```bash
cd airdrop_farmer
pip install -r requirements.txt
```

### 2. 환경 설정

```bash
cp .env.example .env
# .env 파일 편집 — 니모닉, RPC, 텔레그램 토큰 입력
```

### 3. 지갑 생성

```bash
python main.py --init
```

### 4. 자금 분배

```bash
python main.py --fund
```

### 5. 실행

```bash
python main.py           # 전체 자동 실행
python main.py --status  # 상태 확인
```

## 📱 텔레그램 명령어

| 명령 | 설명 |
|------|------|
| `/start` | 메인 메뉴 |
| `/status` | 시스템 상태 |
| `/balance` | 전체 잔액 |
| `/run [chain]` | 활동 실행 |
| `/stop` | 활동 중지 |
| `/fund [chain]` | 자금 분배 |
| `/airdrop` | 에어드롭 확인 |
| `/discover` | 에어드롭 탐색 |

## 🔒 보안

- **니모닉/개인키는 절대 공유 금지**
- `.env` 파일은 `.gitignore`에 포함
- HD 지갑으로 메인 니모닉 노출 최소화
- 마스터 지갑은 자금 분배용으로만 사용

## ⚠️ 주의사항

- 에어드롭 보장이 아닌 **자격 획득 자동화**입니다
- 가스 비용이 발생합니다 (L2라 저렴)
- 시빌 방지 기능이 있지만 **100% 보장은 아님**
- 투자 원금 손실 가능성을 인지하세요

## 📊 예상 비용/수익

| 항목 | 금액 |
|------|------|
| 지갑당 초기 자금 | ~0.01 ETH ($20~30) |
| 일일 가스 비용 | ~0.001 ETH/지갑 |
| 월 가스 비용 (5지갑) | ~$15~30 |
| 잠재적 에어드롭 | $500~$10,000+ |

## 📄 라이선스

MIT