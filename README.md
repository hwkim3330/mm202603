# mm202603

Investigation materials for a suspected financial regulator impersonation / investment inducement site.

## Contents
- `investigations/k-stable-20260308/REPORT.md`: main passive investigation report
- `investigations/k-stable-20260308/POLICE_COMPLAINT_TEMPLATE.txt`: complaint draft
- `investigations/k-stable-20260308/FSC_TIP_TEMPLATE.txt`: capital-markets tip draft
- `investigations/k-stable-20260308/REWARD_ASSESSMENT.md`: reward feasibility assessment
- `investigations/k-stable-20260308/OFFICIAL_REFERENCES.md`: official / media source list used in the report
- `investigations/k-stable-20260308/raw/`: preserved HTML and related raw captures
- `investigations/k-stable-20260308/SHA256SUMS.txt`: integrity hashes for preserved files

## Scope
This repository only contains passive evidence collected from public web pages and public registry / DNS / TLS metadata.
No active exploitation, credential testing, or login attempts were performed.

## Pipeline

- `FSS_PIPELINE_README.md`: KRX 경보 -> 네이버 게시판 -> 원문 보존 -> 키움 원시데이터까지 묶는 자동 발굴 파이프라인 설명
- `scripts/fss_candidate_pipeline.py`: 후보 선별과 증거 수집 오케스트레이터
