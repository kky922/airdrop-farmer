# Airdrop Research Tool

공개 주소의 활동 수치를 사용해 에어드롭 프로젝트를 조사하고 예상 비용과 로컬
자격 기준을 계산하는 읽기 전용 CLI입니다. 거래를 만들거나 전송하지 않습니다.

## 기능

- 검증할 프로젝트 후보 목록 조회
- 예상 활동 횟수와 평균 수수료를 이용한 비용 계산
- 공개 EVM 주소의 거래 횟수·활동 일수 기준 점검
- JSON 형식의 통합 연구 리포트

## 설치

```bash
git clone https://github.com/kky922/airdrop-farmer.git
cd airdrop-farmer
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## 설정

비밀키나 API 키가 필요하지 않습니다. `projects.json`에는 공식 출처로 확인한 공개
프로젝트 정보만 기록하세요.

## 실행

```bash
python main.py scan
python main.py estimate-cost --transactions 12 --fee-usd 0.08
python main.py check-eligibility \
  --address 0x0000000000000000000000000000000000000000 \
  --transactions 12 \
  --unique-days 6
python main.py report \
  --address 0x0000000000000000000000000000000000000000 \
  --transactions 12 \
  --unique-days 6 \
  --fee-usd 0.08
```

## 테스트

```bash
pytest -q
```

## 주의사항

이 도구의 기준은 프로젝트의 실제 보상 조건을 보장하지 않습니다. 공식 문서와 이용
약관을 직접 확인하고, 공개 주소 외의 비밀정보를 입력하지 마세요. 투자 자문이 아닙니다.

## 라이선스

MIT
