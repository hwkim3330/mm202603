# Kiwoom Evidence Workflow

## 원칙

1. `AppKey`와 `SecretKey`는 채팅에 붙이지 않는다.
2. 이미 채팅에 올린 키는 `유출된 것`으로 보고 즉시 폐기/재발급한다.
3. 실제 수집은 로컬 `.env` 파일 또는 셸 환경변수로만 수행한다.

## 준비

1. 예시 파일 복사

```bash
cp /home/kim/mm202603/kiwoom_rest.env.example /home/kim/mm202603/.kiwoom.env
```

2. `.kiwoom.env`에 재발급받은 값 입력

```env
KIWOOM_APP_KEY=YOUR_NEW_APP_KEY
KIWOOM_APP_SECRET=YOUR_NEW_APP_SECRET
```

## 실행 예시

앤디포스:

```bash
python3 /home/kim/mm202603/scripts/kiwoom_stock_evidence.py \
  --code 238090 \
  --name 앤디포스 \
  --start-date 20260226 \
  --end-date 20260309 \
  --use-dotenv /home/kim/mm202603/.kiwoom.env \
  --output-dir /home/kim/mm202603/fss_submissions/20260309_andyfos/kiwoom_evidence
```

이노룰스:

```bash
python3 /home/kim/mm202603/scripts/kiwoom_stock_evidence.py \
  --code 296640 \
  --name 이노룰스 \
  --start-date 20260303 \
  --end-date 20260309 \
  --use-dotenv /home/kim/mm202603/.kiwoom.env \
  --output-dir /home/kim/mm202603/fss_submissions/20260309_innorules/kiwoom_evidence
```

## 수집 항목

스크립트는 아래 원시 응답을 각각 JSON으로 저장한다.

1. `ka10001` 기본종목정보
2. `ka10004` 호가
3. `ka10080` 5분봉
4. `ka10079` 틱차트
5. `ka10015` 당일 체결내역
6. `ka10047` 체결강도
7. `ka10002` 회원사 정보
8. `ka10059` 종목별 투자자기관별
9. `ka10060` 종목별 투자자기관 차트
10. `ka10045` 기관/외국인 매매추이
11. `ka10078` 회원사별 종목매매동향
12. `ka10084` 당일전일체결

## 산출물

실행 후 아래 파일이 생성된다.

1. `SUMMARY.md`
2. `collection_manifest.json`
3. `raw/*.json`

## 왜 이게 중요한가

공개 기사와 게시판만으로는 `조사 필요성`은 만들 수 있어도, 포상금의 핵심인 `기여도`는 약하다.
키움 REST 원시 데이터는 적어도 아래를 보강한다.

1. 특정 시점 체결 흐름
2. 장중 호가 불균형
3. 투자자/기관/회원사 관여 흐름
4. 원시 응답 보존

다만 이것만으로도 포상금이 보장되지는 않는다. `리딩방`, `선행매매`, `계좌`, `유인 메시지`가 추가되면 훨씬 강해진다.
