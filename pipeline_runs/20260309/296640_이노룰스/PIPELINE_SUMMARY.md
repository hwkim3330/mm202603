# Pipeline Summary 이노룰스(296640)

- score: `27`
- reasons: `단일계좌 거래량 상위 | 소수지점/계좌 | 특정계좌(군) 매매관여 과다`
- latest_date: `2026-03-09`
- event_count: `4`
- output_dir: `/home/kim/mm202603/pipeline_runs/20260309/296640_이노룰스`

## KRX events

| category | reason | act_date | design_date | price | delta |
| --- | --- | --- | --- | ---: | ---: |
| caution | 특정계좌(군) 매매관여 과다 | 2026-03-06 | 2026-03-09 | 7,250 | 190 |
| caution | 소수지점/계좌 | 2026-03-05 | 2026-03-06 | 7,250 | 190 |
| caution | 소수지점/계좌 | 2026-03-03 | 2026-03-04 | 7,250 | 190 |
| caution | 단일계좌 거래량 상위 | 2026-03-03 | 2026-03-04 | 7,250 | 190 |

## Steps

| step | status | output | note |
| --- | --- | --- | --- |
| candidate_json | OK | `/home/kim/mm202603/pipeline_runs/20260309/296640_이노룰스/candidate.json` | ranked candidate snapshot saved |
| naver_board_collect | OK | `/home/kim/mm202603/pipeline_runs/20260309/296640_이노룰스/community_titles` | rows=60, representative_posts=3 |
| post_targets | OK | `/home/kim/mm202603/pipeline_runs/20260309/296640_이노룰스/naver_post_targets.json` | 3 posts selected |
| naver_board_evidence | OK | `/home/kim/mm202603/pipeline_runs/20260309/296640_이노룰스/naver_post_evidence` | {"count": 3, "output_dir": "/home/kim/mm202603/pipeline_runs/20260309/296640_이노룰스/naver_post_evidence"} |
| public_archive | OK | `/home/kim/mm202603/pipeline_runs/20260309/296640_이노룰스/archive` | count=4 |
| kiwoom_evidence | ERR | `/home/kim/mm202603/pipeline_runs/20260309/296640_이노룰스/kiwoom_evidence` | no --kiwoom-dotenv provided |

## Next

- 공개자료형 제보는 이 출력물만으로 가능하다.
- 포상금 가능성을 더 올리려면 리딩방 캡처, 반복 홍보 이미지, 선행매매 정황이 추가로 필요하다.
