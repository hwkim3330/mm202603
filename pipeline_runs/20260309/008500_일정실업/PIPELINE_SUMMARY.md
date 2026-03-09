# Pipeline Summary 일정실업(008500)

- score: `20`
- reasons: `소수지점/계좌 | 종가급변 | 특정계좌(군) 매매관여 과다`
- latest_date: `2026-03-06`
- event_count: `3`
- output_dir: `/home/kim/mm202603/pipeline_runs/20260309/008500_일정실업`

## KRX events

| category | reason | act_date | design_date | price | delta |
| --- | --- | --- | --- | ---: | ---: |
| caution | 특정계좌(군) 매매관여 과다 | 2026-03-05 | 2026-03-06 | 2,945 | 165 |
| caution | 종가급변 | 2026-03-05 | 2026-03-06 | 2,945 | 165 |
| caution | 소수지점/계좌 | 2026-03-05 | 2026-03-06 | 2,945 | 165 |

## Steps

| step | status | output | note |
| --- | --- | --- | --- |
| candidate_json | OK | `/home/kim/mm202603/pipeline_runs/20260309/008500_일정실업/candidate.json` | ranked candidate snapshot saved |
| naver_board_collect | OK | `/home/kim/mm202603/pipeline_runs/20260309/008500_일정실업/community_titles` | rows=100, representative_posts=2 |
| post_targets | OK | `/home/kim/mm202603/pipeline_runs/20260309/008500_일정실업/naver_post_targets.json` | 4 posts selected |
| naver_board_evidence | OK | `/home/kim/mm202603/pipeline_runs/20260309/008500_일정실업/naver_post_evidence` | count=4 |
| public_archive | OK | `/home/kim/mm202603/pipeline_runs/20260309/008500_일정실업/archive` | count=5 |
| kiwoom_evidence | ERR | `/home/kim/mm202603/pipeline_runs/20260309/008500_일정실업/kiwoom_evidence` | no --kiwoom-dotenv provided |

## Next

- 공개자료형 제보는 이 출력물만으로 가능하다.
- 포상금 가능성을 더 올리려면 리딩방 캡처, 반복 홍보 이미지, 선행매매 정황이 추가로 필요하다.
