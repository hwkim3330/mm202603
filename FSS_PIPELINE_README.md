# FSS Candidate Pipeline

`fss_candidate_pipeline.py`는 이미 만들어둔 수집기들을 한 번에 묶어서 `포상금용 조사 후보` 패키지를 자동 생성한다.

## 흐름

1. `KRX` 공개 경보 랭킹 결과 로드
2. 상위 후보 또는 지정 종목 선택
3. 네이버 종토방 제목 수집
4. 대표 게시글 본문 / 이미지 / OCR 수집
5. 공개 URL 원문 HTML과 해시 보존
6. 선택적으로 `Kiwoom REST` 원시데이터 수집
7. 종목별 `PIPELINE_SUMMARY.md`와 실행 결과 `run_manifest.json` 생성

## 기본 실행

```bash
cd /home/kim/mm202603
python3 scripts/fss_candidate_pipeline.py --top 3
```

## 특정 종목만 실행

```bash
python3 scripts/fss_candidate_pipeline.py --codes 238090,296640
```

## 키움 REST까지 포함

```bash
python3 scripts/fss_candidate_pipeline.py \
  --codes 238090 \
  --kiwoom-dotenv /home/kim/mm202603/.kiwoom.env \
  --kiwoom-start-date 20260226 \
  --kiwoom-end-date 20260309
```

## 출력

- `pipeline_runs/YYYYMMDD/README.md`: 실행 요약
- `pipeline_runs/YYYYMMDD/run_manifest.json`: 전체 실행 메타데이터
- `pipeline_runs/YYYYMMDD/<code>_<name>/candidate.json`: 스크리너 원본 후보
- `pipeline_runs/YYYYMMDD/<code>_<name>/community_titles/`: 네이버 제목 스냅샷
- `pipeline_runs/YYYYMMDD/<code>_<name>/naver_post_evidence/`: 게시글 본문 / OCR
- `pipeline_runs/YYYYMMDD/<code>_<name>/archive/`: 공개 원문 HTML + 해시
- `pipeline_runs/YYYYMMDD/<code>_<name>/kiwoom_evidence/`: 키움 원시데이터

## 한계

- 공개자료 자동화이지 `포상금 보장 시스템`은 아니다.
- `리딩방 캡처`, `회원비`, `선행매매 정황`, `실계좌 단서`는 별도 수집이 필요하다.
