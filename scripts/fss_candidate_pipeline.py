#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import json
import subprocess
import sys
from dataclasses import asdict, dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

KST = timezone(timedelta(hours=9))
DEFAULT_KEYWORDS = '유가,상한가,상장폐지,청산,호르무즈,전쟁,쩜상,주포,매집,작전,세력,급등'


@dataclass
class StepResult:
    name: str
    ok: bool
    output: str
    note: str


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description='Run KRX -> Naver -> archive -> Kiwoom evidence pipeline for top warning candidates.'
    )
    p.add_argument('--screen-json', help='ranked_candidates.json path. Defaults to latest dated output under manipulation_screening/output/')
    p.add_argument('--codes', help='Comma-separated stock codes to run. Defaults to top-ranked candidates.')
    p.add_argument('--top', type=int, default=3, help='How many top candidates to process when --codes is not provided')
    p.add_argument('--output-root', default='pipeline_runs', help='Root directory for pipeline outputs')
    p.add_argument('--pages', type=int, default=12, help='How many Naver board pages to collect per stock')
    p.add_argument('--keywords', default=DEFAULT_KEYWORDS, help='Comma-separated Naver title keywords')
    p.add_argument('--kiwoom-dotenv', help='Optional dotenv file with KIWOOM_APP_KEY / KIWOOM_APP_SECRET')
    p.add_argument('--kiwoom-start-date', help='YYYYMMDD for Kiwoom query start')
    p.add_argument('--kiwoom-end-date', help='YYYYMMDD for Kiwoom query end')
    p.add_argument('--max-posts', type=int, default=5, help='Max representative Naver posts to fetch bodies for')
    return p.parse_args()


def repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def find_latest_screen_json(root: Path) -> Path:
    base = root / 'manipulation_screening' / 'output'
    candidates = sorted(base.glob('*/ranked_candidates.json'))
    if not candidates:
        raise FileNotFoundError('No ranked_candidates.json found under manipulation_screening/output/')
    return candidates[-1]


def load_screen_candidates(path: Path) -> dict[str, dict]:
    payload = json.loads(path.read_text(encoding='utf-8'))
    return {item['code']: item for item in payload['candidates']}


def latest_run_stamp() -> str:
    return datetime.now(KST).strftime('%Y%m%d')


def stock_dir_name(code: str, name: str) -> str:
    safe_name = ''.join(ch for ch in name if ch.isalnum() or ch in ('_', '-'))
    return f'{code}_{safe_name or "stock"}'


def run_cmd(cmd: list[str], cwd: Path) -> tuple[bool, str]:
    proc = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True)
    output = (proc.stdout or '') + ('\n' + proc.stderr if proc.stderr else '')
    return proc.returncode == 0, output.strip()


def summarize_output(output: str, max_len: int = 200) -> str:
    try:
        payload = json.loads(output)
        if isinstance(payload, dict):
            if 'meta' in payload and isinstance(payload['meta'], dict):
                meta = payload['meta']
                row_count = meta.get('row_count')
                reps = len(payload.get('representative_posts', []))
                if row_count is not None:
                    return f'rows={row_count}, representative_posts={reps}'
            if 'count' in payload:
                return f"count={payload['count']}"
    except Exception:
        pass
    lines = [line.strip() for line in output.splitlines() if line.strip()]
    lines = [
        line for line in lines
        if not line.startswith('/usr/')
        and not line.startswith('from pandas')
        and line not in {'{', '}', '[', ']'}
    ]
    for line in lines:
        if line.startswith('{') and line.endswith('}'):
            try:
                payload = json.loads(line)
                if isinstance(payload, dict) and 'count' in payload:
                    return f"count={payload['count']}"
            except Exception:
                pass
    if not lines:
        return 'no output'
    summary = lines[-1]
    if len(summary) > max_len:
        summary = summary[: max_len - 3] + '...'
    return summary


def write_json(path: Path, payload: Any) -> None:
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding='utf-8')


def write_markdown_summary(path: Path, candidate: dict, steps: list[StepResult], stock_output_dir: Path) -> None:
    lines = []
    lines.append(f"# Pipeline Summary {candidate['name']}({candidate['code']})")
    lines.append('')
    lines.append(f"- score: `{candidate['score']}`")
    lines.append(f"- reasons: `{candidate['reasons']}`")
    lines.append(f"- latest_date: `{candidate['latest_date']}`")
    lines.append(f"- event_count: `{candidate['event_count']}`")
    lines.append(f"- output_dir: `{stock_output_dir}`")
    lines.append('')
    lines.append('## KRX events')
    lines.append('')
    lines.append('| category | reason | act_date | design_date | price | delta |')
    lines.append('| --- | --- | --- | --- | ---: | ---: |')
    for event in candidate.get('events', []):
        lines.append(
            f"| {event['category']} | {event['reason']} | {event['act_date']} | {event['design_date']} | {event['price']} | {event['delta']} |"
        )
    lines.append('')
    lines.append('## Steps')
    lines.append('')
    lines.append('| step | status | output | note |')
    lines.append('| --- | --- | --- | --- |')
    for step in steps:
        lines.append(f"| {step.name} | {'OK' if step.ok else 'ERR'} | `{step.output}` | {step.note} |")
    lines.append('')
    lines.append('## Next')
    lines.append('')
    lines.append('- 공개자료형 제보는 이 출력물만으로 가능하다.')
    lines.append('- 포상금 가능성을 더 올리려면 리딩방 캡처, 반복 홍보 이미지, 선행매매 정황이 추가로 필요하다.')
    path.write_text('\n'.join(lines) + '\n', encoding='utf-8')


def build_post_targets(board_summary_path: Path, board_csv_path: Path, output_path: Path, max_posts: int) -> list[dict]:
    summary = json.loads(board_summary_path.read_text(encoding='utf-8'))
    urls: list[dict] = []
    seen = set()
    for idx, row in enumerate(summary.get('representative_posts', []), start=1):
        href = row['href']
        if href in seen:
            continue
        seen.add(href)
        urls.append({'label': f'post_{idx:02d}', 'url': href})
        if len(urls) >= max_posts:
            break
    if len(urls) < max_posts:
        with board_csv_path.open(encoding='utf-8') as fp:
            reader = csv.DictReader(fp)
            rows = sorted(reader, key=lambda r: (-int(r['up']), -int(r['view'])))
        for row in rows:
            href = row['href']
            if href in seen:
                continue
            seen.add(href)
            urls.append({'label': f'post_{len(urls)+1:02d}', 'url': href})
            if len(urls) >= max_posts:
                break
    write_json(output_path, urls)
    return urls


def build_archive_targets(code: str, stock_name: str, board_targets: list[dict], output_path: Path) -> list[dict]:
    items = [
        {
            'label': f'{stock_name}_naver_board_main',
            'url': f'https://finance.naver.com/item/board.naver?code={code}',
        }
    ]
    for item in board_targets:
        items.append({'label': f'{stock_name}_{item["label"]}', 'url': item['url']})
    write_json(output_path, items)
    return items


def run_stock_pipeline(
    candidate: dict,
    root: Path,
    output_root: Path,
    pages: int,
    keywords: str,
    max_posts: int,
    kiwoom_dotenv: str | None,
    kiwoom_start_date: str | None,
    kiwoom_end_date: str | None,
) -> dict[str, Any]:
    stock_output_dir = output_root / stock_dir_name(candidate['code'], candidate['name'])
    stock_output_dir.mkdir(parents=True, exist_ok=True)
    logs_dir = stock_output_dir / 'logs'
    logs_dir.mkdir(parents=True, exist_ok=True)
    steps: list[StepResult] = []

    candidate_path = stock_output_dir / 'candidate.json'
    write_json(candidate_path, candidate)
    steps.append(StepResult('candidate_json', True, str(candidate_path), 'ranked candidate snapshot saved'))

    board_dir = stock_output_dir / 'community_titles'
    ok, note = run_cmd(
        [
            sys.executable,
            str(root / 'scripts' / 'naver_board_collect.py'),
            '--code',
            candidate['code'],
            '--pages',
            str(pages),
            '--keywords',
            keywords,
            '--output-dir',
            str(board_dir),
        ],
        cwd=root,
    )
    (logs_dir / 'naver_board_collect.log').write_text(note + '\n', encoding='utf-8')
    steps.append(StepResult('naver_board_collect', ok, str(board_dir), summarize_output(note)))

    board_summary = board_dir / f'naver_board_{candidate["code"]}_summary.json'
    board_csv = board_dir / f'naver_board_{candidate["code"]}.csv'
    board_targets_json = stock_output_dir / 'naver_post_targets.json'
    if ok and board_summary.exists() and board_csv.exists():
        board_targets = build_post_targets(board_summary, board_csv, board_targets_json, max_posts)
        steps.append(StepResult('post_targets', True, str(board_targets_json), f'{len(board_targets)} posts selected'))
    else:
        board_targets = []
        steps.append(StepResult('post_targets', False, str(board_targets_json), 'board summary missing'))

    naver_evidence_dir = stock_output_dir / 'naver_post_evidence'
    if board_targets:
        ok, note = run_cmd(
            [
                sys.executable,
                str(root / 'scripts' / 'naver_board_evidence.py'),
                '--input-json',
                str(board_targets_json),
                '--output-dir',
                str(naver_evidence_dir),
            ],
            cwd=root,
        )
        (logs_dir / 'naver_board_evidence.log').write_text(note + '\n', encoding='utf-8')
        steps.append(StepResult('naver_board_evidence', ok, str(naver_evidence_dir), summarize_output(note)))
    else:
        steps.append(StepResult('naver_board_evidence', False, str(naver_evidence_dir), 'no representative posts'))

    archive_targets_json = stock_output_dir / 'archive_targets.json'
    archive_targets = build_archive_targets(candidate['code'], candidate['name'], board_targets, archive_targets_json)
    archive_dir = stock_output_dir / 'archive'
    ok, note = run_cmd(
        [
            sys.executable,
            str(root / 'scripts' / 'public_evidence_archive.py'),
            '--input-json',
            str(archive_targets_json),
            '--output-dir',
            str(archive_dir),
        ],
        cwd=root,
    )
    (logs_dir / 'public_archive.log').write_text(note + '\n', encoding='utf-8')
    steps.append(StepResult('public_archive', ok, str(archive_dir), summarize_output(note)))

    kiwoom_dir = stock_output_dir / 'kiwoom_evidence'
    if kiwoom_dotenv:
        kiwoom_cmd = [
            sys.executable,
            str(root / 'scripts' / 'kiwoom_stock_evidence.py'),
            '--code',
            candidate['code'],
            '--name',
            candidate['name'],
            '--output-dir',
            str(kiwoom_dir),
            '--use-dotenv',
            kiwoom_dotenv,
        ]
        if kiwoom_start_date:
            kiwoom_cmd += ['--start-date', kiwoom_start_date]
        if kiwoom_end_date:
            kiwoom_cmd += ['--end-date', kiwoom_end_date]
        ok, note = run_cmd(kiwoom_cmd, cwd=root)
        (logs_dir / 'kiwoom_evidence.log').write_text(note + '\n', encoding='utf-8')
        steps.append(StepResult('kiwoom_evidence', ok, str(kiwoom_dir), summarize_output(note)))
    else:
        steps.append(StepResult('kiwoom_evidence', False, str(kiwoom_dir), 'no --kiwoom-dotenv provided'))

    write_markdown_summary(stock_output_dir / 'PIPELINE_SUMMARY.md', candidate, steps, stock_output_dir)

    return {
        'code': candidate['code'],
        'name': candidate['name'],
        'score': candidate['score'],
        'output_dir': str(stock_output_dir),
        'steps': [asdict(step) for step in steps],
    }


def main() -> int:
    args = parse_args()
    root = repo_root()
    screen_json = Path(args.screen_json) if args.screen_json else find_latest_screen_json(root)
    candidates_by_code = load_screen_candidates(screen_json)

    if args.codes:
        codes = [code.strip() for code in args.codes.split(',') if code.strip()]
        candidates = [candidates_by_code[code] for code in codes if code in candidates_by_code]
    else:
        candidates = list(candidates_by_code.values())[:args.top]

    if not candidates:
        raise SystemExit('No candidates selected')

    run_root = root / args.output_root / latest_run_stamp()
    run_root.mkdir(parents=True, exist_ok=True)

    results = []
    for candidate in candidates:
        results.append(
            run_stock_pipeline(
                candidate=candidate,
                root=root,
                output_root=run_root,
                pages=args.pages,
                keywords=args.keywords,
                max_posts=args.max_posts,
                kiwoom_dotenv=args.kiwoom_dotenv,
                kiwoom_start_date=args.kiwoom_start_date,
                kiwoom_end_date=args.kiwoom_end_date,
            )
        )

    manifest = {
        'generated_at_utc': datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ'),
        'screen_json': str(screen_json),
        'run_root': str(run_root),
        'selected_codes': [candidate['code'] for candidate in candidates],
        'results': results,
    }
    write_json(run_root / 'run_manifest.json', manifest)
    lines = ['# FSS Candidate Pipeline Run', '']
    lines.append(f"- screen_json: `{screen_json}`")
    lines.append(f"- run_root: `{run_root}`")
    lines.append(f"- selected_codes: `{', '.join(manifest['selected_codes'])}`")
    lines.append('')
    lines.append('| code | name | score | output_dir |')
    lines.append('| --- | --- | ---: | --- |')
    for item in results:
        lines.append(f"| {item['code']} | {item['name']} | {item['score']} | `{item['output_dir']}` |")
    (run_root / 'README.md').write_text('\n'.join(lines) + '\n', encoding='utf-8')
    print(json.dumps({'run_root': str(run_root), 'count': len(results)}, ensure_ascii=False))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
