"""
legacy/ — GLM5-1 생성 원본 코드 (수정 금지)

모듈 목록:
  main.py             - 메인 진입점 (CLI: --init, --fund, --status, --check, --run, --smart)
  config.py           - 16개 EVM 체인 설정, 스케줄/안티시빌/가스 설정
  wallet_manager.py   - HD 지갑 생성 및 관리 (WalletManager, Wallet)
  activity_engine.py  - 온체인 활동 실행 엔진 (bridge, swap, lend, lp, nft, governance, transfer)
  scheduler.py        - APScheduler 기반 자동 스케줄러 (AirdropScheduler)
  checker.py          - 에어드랍 자격 확인 및 점수화 (EligibilityChecker)
  db.py               - SQLite 데이터베이스 (Database) — activities, balances, airdrops, gas_snapshots
  anti_sybil.py       - 시빌 방지 엔진 (AntiSybilEngine) — 딜레이, 금액 변동, 패턴 셔플
  gas_optimizer.py    - 가스비 최적화 (GasOptimizer) — EIP-1559, 히스토리 추적
  balance_tracker.py  - 멀티체인 잔액 모니터링 (BalanceTracker)
  discovery.py        - 에어드랍 탐색 (AirdropDiscovery) — airdrops.io 스크래핑
  listing_checker.py  - CoinGecko 상장 여부 확인
  telegram_bot.py     - 텔레그램 제어 봇 (AirdropTelegramBot) — 15개 명령어
  distribute_funds.py - Monad 체인 자금 배포 유틸리티 (1회성)
"""
