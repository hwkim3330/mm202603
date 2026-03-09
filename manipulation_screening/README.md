# Manipulation Screening

이 디렉터리는 `포상금용 조사 후보`를 임의 추정이 아니라 한국거래소 공개 경보 데이터로 선별하기 위한 패키지다.

원칙은 두 가지다.

1. `조작 회사`라고 단정하지 않는다.
2. `투자주의/경고/위험`과 `소수계좌/특정계좌군/투자경고 지정예고` 같은 공식 경보를 먼저 모은 뒤, 추가 증거가 붙는 종목만 신고 후보로 올린다.

## 포함 내용

- `SCREENING_METHOD.md`: 점수화 기준과 제보용 해석 기준
- `OFFICIAL_RED_FLAGS.md`: KRX 공식 이상징후 문구 정리
- `output/YYYYMMDD/`: 실행 결과물
- `../scripts/krx_warning_screener.py`: 수집 및 랭킹 스크립트

## 실행

```bash
cd /home/kim/mm202603
python3 scripts/krx_warning_screener.py
```

특정 기간으로 돌리려면:

```bash
python3 scripts/krx_warning_screener.py --start-date 20260303 --end-date 20260309
```

## 출력

- `ranked_candidates.csv`
- `ranked_candidates.json`
- `ranked_candidates.md`
- `raw_payloads.json`

## 해석 주의

점수는 `조사 우선순위`다. 포상금 가능성은 여기에 더해 아래가 붙어야 올라간다.

- 종목 유인 캡처
- 허위 재료 유포 흔적
- 선행매매 또는 사후매도 정황
- 송금, 예치, 회원비 구조
