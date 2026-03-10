#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import json
import re
from collections import Counter, defaultdict
from pathlib import Path

PROMO_KEYWORDS = [
    '상한가', '쩜상', '급등', '폭등', '주포', '매집', '세력', '유출', '100배', '시총',
    '확정', '직행', '가야', '간다', '터진다', '오픈채팅', '방', '리딩', '추천',
]


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description='Summarize suspicious Naver board patterns from title/body/OCR.')
    p.add_argument('--board-csv', required=True)
    p.add_argument('--post-evidence-dir', required=True)
    p.add_argument('--output-file', required=True)
    p.add_argument('--stock-name', default='')
    p.add_argument('--stock-code', default='')
    p.add_argument('--start-date', default='', help='Inclusive YYYY.MM.DD filter for title/written_at')
    p.add_argument('--end-date', default='', help='Inclusive YYYY.MM.DD filter for title/written_at')
    return p.parse_args()


def normalize(text: str) -> str:
    return re.sub(r'\s+', ' ', (text or '')).strip()


def hit_keywords(text: str) -> list[str]:
    hits = []
    norm = normalize(text)
    for kw in PROMO_KEYWORDS:
        if kw in norm:
            hits.append(kw)
    return hits


def load_board_rows(path: Path) -> list[dict]:
    with path.open(newline='', encoding='utf-8') as fp:
        return list(csv.DictReader(fp))


def load_manifest(path: Path) -> list[dict]:
    return json.loads(path.read_text())


def in_range(date_text: str, start_date: str, end_date: str) -> bool:
    if not date_text:
        return False
    if 'T' in date_text:
        base = date_text[:10].replace('-', '.')
    else:
        base = date_text.split()[0]
    if start_date and base < start_date:
        return False
    if end_date and base > end_date:
        return False
    return True


def main() -> int:
    args = parse_args()
    board_rows = load_board_rows(Path(args.board_csv))
    board_rows = [r for r in board_rows if in_range(r.get('date', ''), args.start_date, args.end_date)]
    ev_dir = Path(args.post_evidence_dir)
    manifest = load_manifest(ev_dir / 'manifest.json')
    raw_dir = ev_dir / 'raw'

    title_hits = [row for row in board_rows if hit_keywords(row.get('title', ''))]
    author_counter = Counter(row.get('author', '') for row in title_hits if row.get('author'))
    keyword_counter = Counter()
    author_keywords: dict[str, Counter] = defaultdict(Counter)
    for row in title_hits:
        kws = hit_keywords(row.get('title', ''))
        keyword_counter.update(kws)
        if row.get('author'):
            author_keywords[row['author']].update(kws)

    body_rows = []
    for item in manifest:
        text_parts = []
        text_file = raw_dir / item['text_filename']
        if text_file.exists():
            text_parts.append(text_file.read_text(encoding='utf-8'))
        stem = Path(item['text_filename']).stem.split('.content')[0]
        for ocr_file in sorted(raw_dir.glob(f'{stem}_img*.ocr.txt')):
            text_parts.append(ocr_file.read_text(encoding='utf-8'))
        full_text = '\n'.join(text_parts)
        if not in_range(item.get('written_at', ''), args.start_date, args.end_date):
            continue
        kws = hit_keywords(full_text)
        if kws:
            body_rows.append({
                'label': item['label'],
                'title': item['title'],
                'written_at': item['written_at'],
                'author': item['author'],
                'hits': kws,
                'sample': normalize(full_text)[:220],
            })

    lines: list[str] = []
    if args.stock_name and args.stock_code:
        lines.append(f'# Naver Board Redflag Summary {args.stock_name}({args.stock_code})')
    elif args.stock_name:
        lines.append(f'# Naver Board Redflag Summary {args.stock_name}')
    else:
        lines.append('# Naver Board Redflag Summary')
    lines.append('')
    lines.append(f'- 전체 제목 수집 건수: `{len(board_rows)}`')
    lines.append(f'- 과장/홍보형 키워드 제목 건수: `{len(title_hits)}`')
    lines.append(f'- 본문/OCR에서 과장 문구가 확인된 대표 게시글 수: `{len(body_rows)}`')
    lines.append('')

    lines.append('## Title Keyword Frequency')
    lines.append('')
    for kw, count in keyword_counter.most_common(15):
        lines.append(f'- `{kw}` `{count}`건')
    lines.append('')

    lines.append('## Repeated Authors in Title Hits')
    lines.append('')
    for author, count in author_counter.most_common(10):
        lines.append(f'- `{author}` `{count}`건 / 키워드 `{dict(author_keywords[author])}`')
    if not author_counter:
        lines.append('- 반복 작성자 패턴 미미')
    lines.append('')

    lines.append('## Body / OCR Samples')
    lines.append('')
    for row in body_rows[:8]:
        lines.append(f"- `{row['written_at']}` `{row['author']}` / hits `{row['hits']}`")
        lines.append(f"  - 제목: {row['title']}")
        lines.append(f"  - 샘플: {row['sample']}")
    if not body_rows:
        lines.append('- 본문/OCR에서 직접적인 과장 문구 미확인')
    lines.append('')

    lines.append('## Filing Use')
    lines.append('')
    lines.append('- 본 문서는 KRX 경보와 별도로 온라인 기대 과열 패턴을 보조 입증하는 용도다.')
    lines.append('- 단순 질문형/의견형 글은 제외하고, 반복 작성자와 과장 문구가 섞인 경우를 우선 본다.')
    lines.append('')

    Path(args.output_file).write_text('\n'.join(lines), encoding='utf-8')
    print(Path(args.output_file))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
