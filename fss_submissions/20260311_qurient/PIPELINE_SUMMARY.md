# Pipeline Summary 큐리언트(115180)

- score: `11`
- reasons: `특정계좌(군) 매매관여 과다`
- latest_date: `2026-03-10`
- event_count: `1`
- output_dir: `/home/kim/mm202603/pipeline_runs/20260311/115180_큐리언트`

## KRX events

| category | reason | act_date | design_date | price | delta |
| --- | --- | --- | --- | ---: | ---: |
| caution | 특정계좌(군) 매매관여 과다 | 2026-03-09 | 2026-03-10 | 50,900 | 10,300 |

## Steps

| step | status | output | note |
| --- | --- | --- | --- |
| candidate_json | OK | `/home/kim/mm202603/pipeline_runs/20260311/115180_큐리언트/candidate.json` | ranked candidate snapshot saved |
| naver_board_collect | OK | `/home/kim/mm202603/pipeline_runs/20260311/115180_큐리언트/community_titles` | rows=240, representative_posts=4 |
| post_targets | OK | `/home/kim/mm202603/pipeline_runs/20260311/115180_큐리언트/naver_post_targets.json` | 5 posts selected |
| naver_board_evidence | OK | `/home/kim/mm202603/pipeline_runs/20260311/115180_큐리언트/naver_post_evidence` | count=5 |
| public_archive | OK | `/home/kim/mm202603/pipeline_runs/20260311/115180_큐리언트/archive` | count=6 |
| kiwoom_evidence | OK | `/home/kim/mm202603/pipeline_runs/20260311/115180_큐리언트/kiwoom_evidence` | {"output_dir": "/home/kim/mm202603/pipeline_runs/20260311/115180_큐리언트/kiwoom_evidence", "artifact_count": 12, "error_count": 0} |

## Next

- 공개자료형 제보는 이 출력물만으로 가능하다.
- 포상금 가능성을 더 올리려면 리딩방 캡처, 반복 홍보 이미지, 선행매매 정황이 추가로 필요하다.
