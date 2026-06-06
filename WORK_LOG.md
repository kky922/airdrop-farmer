# Airdrop Farmer v2.0 — 작업 로그

## 2026-04-15 (화) 작업 내용

### 완료된 작업
1. **config.yaml LIVE 모드 전환**
   - `dry_run: false` 설정
   - `active_projects: MegaETH` 단독 활성 (가스비 $0)
   - Unichain/Abstract/MetaMask/Ink 주석 처리

2. **Playwright 브라우저 환경 구축**
   - venv 내부 Playwright 구버전(1.43) → chromium-1117 설치 완료
   - 시스템 Playwright 최신(1.52) → chromium-1208도 설치됨
   - 스텔스 브라우저 생성 성공 확인 (UA 랜덤화, 지갑별 독립 세션)

3. **MegaETH LIVE 파밍 실행 성공**
   - 10개 지갑 모두 스텔스 브라우저 생성 확인
   - 지갑 구성:
     - **Group A (owner=wallet_a)**: #0~#4 (5개 지갑)
     - **Group B (owner=wallet_b)**: #5~#9 (5개 지갑)
   - 전원 MegaETH 파밍 실행 중

4. **텔레그램 알림 테스트 성공**
   - `.env`의 TELEGRAM_BOT_TOKEN / TELEGRAM_CHAT_ID 정상
   - curl 테스트 메시지 전송 성공 확인
   - 알림 유형: 파밍결과, 진행률, 일일요약, 주간스캔, 클레임, 가스, 에러, 프록시, 재시도큐

### 현재 시스템 상태
- **활성 프로젝트**: MegaETH (가스비 $0)
- **지갑**: 10개 (group_a 5 + group_b 5)
- **프록시**: 미설정 (경고만, 기능엔 지장없음)
- **모드**: LIVE (dry_run=false)

### 다음 해야 할 일
1. **[즉시]** 중복 실행 방지 — PID 락 파일 로직 추가
2. **[단기]** 프록시 설정 — 레지덴셜 프록시 4~5개 IP 분배
3. **[단기]** MegaETH 팜 결과 모니터링 — 성공/실패 로그 분석
4. **[중기]** Unichain 활성화 — 가스비 ~$15/월 검토
5. **[중기]** 주간 리포트 자동화 — weekly_airdrop_report.py 스케줄러
6. **[중기]** 대시보드 구축 — port 8080 웹 UI
7. **[장기]** 새 프로젝트 스캐너 — AirdropBuzz/Twitter/CoinGecko
8. **[장기]** AI 엔진 — GLM 기반 프로젝트 자동 평가
9. **[장기]** Claim 자동화 — 토큰 출시 시 자동 클레임

### 프로젝트 구조 (v2.0)
```
airdrop_farmer/
├── main.py                    # 진입점
├── config.yaml                # 메인 설정
├── .env                       # 환경변수
├── core/scheduler.py          # 스케줄러
├── projects/
│   ├── __init__.py            # 프로젝트 레지스트리 + 자동 관리
│   ├── base_project.py        # 기본 프로젝트 클래스
│   ├── megaeth.py             # MegaETH (활성)
│   ├── unichain.py            # Unichain (비활성)
│   ├── abstract.py            # Abstract (비활성)
│   ├── metamask.py            # MetaMask (비활성)
│   └── ink.py                 # Ink (비활성)
├── web3_tools/
│   ├── wallet_manager.py      # 지갑 관리 (암호화)
│   ├── gas_optimizer.py       # 가스 최적화
│   └── claim_manager.py       # 클레임 관리
├── anti_sybil/
│   ├── proxy_manager.py       # 프록시 관리
│   ├── behavior_simulator.py  # 행동 시뮬레이션
│   └── browser_manager.py     # 스텔스 브라우저 (Playwright)
├── ai_engine/
│   ├── risk_assessor.py       # 리스크 평가
│   ├── project_analyzer.py    # 프로젝트 분석
│   └── glm_decision_maker.py  # GLM AI 의사결정
├── scanner/sources/
│   ├── twitter.py             # Twitter 스캔
│   ├── airdropbuzz.py         # AirdropBuzz 스캔
│   └── coingecko.py           # CoinGecko 스캔
├── monitor/telegram_bot.py    # 텔레그램 알림
├── docker-compose.yml         # Docker 배포
└── data/
    └── wallets.json           # 10개 지갑 (암호화)