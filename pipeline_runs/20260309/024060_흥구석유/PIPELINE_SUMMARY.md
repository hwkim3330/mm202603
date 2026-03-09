# Pipeline Summary 흥구석유(024060)

- score: `23`
- reasons: `투자경고 | 투자경고 지정예고`
- latest_date: `2026-03-06`
- event_count: `2`
- output_dir: `/home/kim/mm202603/pipeline_runs/20260309/024060_흥구석유`

## KRX events

| category | reason | act_date | design_date | price | delta |
| --- | --- | --- | --- | ---: | ---: |
| caution | 투자경고 지정예고 | 2026-03-04 | 2026-03-05 | 31,100 | 3,500 |
| warning | 투자경고 | 2026-03-05 | 2026-03-06 | 31,200 | 3,600 |

## Steps

| step | status | output | note |
| --- | --- | --- | --- |
| candidate_json | OK | `/home/kim/mm202603/pipeline_runs/20260309/024060_흥구석유/candidate.json` | ranked candidate snapshot saved |
| naver_board_collect | OK | `/home/kim/mm202603/pipeline_runs/20260309/024060_흥구석유/community_titles` | rows=100, representative_posts=4 |
| post_targets | OK | `/home/kim/mm202603/pipeline_runs/20260309/024060_흥구석유/naver_post_targets.json` | 4 posts selected |
| naver_board_evidence | OK | `/home/kim/mm202603/pipeline_runs/20260309/024060_흥구석유/naver_post_evidence` | count=4 |
| public_archive | OK | `/home/kim/mm202603/pipeline_runs/20260309/024060_흥구석유/archive` | count=5 |
| kiwoom_evidence | ERR | `/home/kim/mm202603/pipeline_runs/20260309/024060_흥구석유/kiwoom_evidence` | no --kiwoom-dotenv provided |

## Next

- 공개자료형 제보는 이 출력물만으로 가능하다.
- 포상금 가능성을 더 올리려면 리딩방 캡처, 반복 홍보 이미지, 선행매매 정황이 추가로 필요하다.
