#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import json
from collections import Counter
from pathlib import Path

DEFAULT_KEYWORDS = [
    '세력', '주포', '상한가', '쩜상', '시총', '오픈채팅', '대화방', '리딩방', '리딩', '매집',
    '유출', '급등', '폭등', '확정', '직행', '100배', '물량', '설거지', '작전',
    '호재', '텐버거', '입성',
]


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description='Select suspicious Naver board posts for evidence collection.')
    p.add_argument('--board-csv', required=True)
    p.add_argument('--output-json', required=True)
    p.add_argument('--summary-md', required=True)
    p.add_argument('--start-date', default='')
    p.add_argument('--end-date', default='')
    p.add_argument('--keywords', default=','.join(DEFAULT_KEYWORDS))
    p.add_argument('--top-n', type=int, default=40)
    return p.parse_args()


def in_range(date_text: str, start_date: str, end_date: str) -> bool:
    base = (date_text or '').split()[0]
    if not base:
        return False
    if start_date and base < start_date:
        return False
    if end_date and base > end_date:
        return False
    return True


def main() -> int:
    args = parse_args()
    keywords = [x.strip() for x in args.keywords.split(',') if x.strip()]
    rows = list(csv.DictReader(Path(args.board_csv).open(encoding='utf-8')))
    rows = [r for r in rows if in_range(r.get('date', ''), args.start_date, args.end_date)]

    author_hit_counts = Counter()
    scored_rows = []
    for row in rows:
        hits = [kw for kw in keywords if kw in row.get('title', '')]
        if hits:
            author_hit_counts[row.get('author', '')] += 1
            scored_rows.append((row, hits))

    ranked = []
    for idx, (row, hits) in enumerate(scored_rows, start=1):
        author_count = author_hit_counts[row.get('author', '')]
        score = len(hits) * 10 + min(int(row.get('up', 0)), 20) + min(int(row.get('view', 0)) // 40, 15)
        if author_count >= 2:
            score += author_count * 3
        ranked.append({
            'label': f'post_{idx:02d}',
            'url': row['href'],
            'date': row['date'],
            'title': row['title'],
            'author': row['author'],
            'view': int(row.get('view', 0) or 0),
            'up': int(row.get('up', 0) or 0),
            'page': int(row.get('page', 0) or 0),
            'hits': hits,
            'score': score,
            'author_hit_count': author_count,
        })

    ranked.sort(key=lambda x: (-x['score'], -x['up'], -x['view'], x['date']))
    top = ranked[: args.top_n]

    Path(args.output_json).write_text(
        json.dumps([{'label': x['label'], 'url': x['url']} for x in top], ensure_ascii=False, indent=2),
        encoding='utf-8',
    )

    lines = ['# Suspicious Naver Board Targets', '']
    lines.append(f'- 전체 게시글: `{len(rows)}`')
    lines.append(f'- 키워드 hit 게시글: `{len(ranked)}`')
    lines.append(f'- 본문 수집 대상: `{len(top)}`')
    lines.append('')
    lines.append('## Repeated Authors')
    lines.append('')
    for author, count in author_hit_counts.most_common(15):
        if author:
            lines.append(f'- `{author}` `{count}`건')
    lines.append('')
    lines.append('## Selected Targets')
    lines.append('')
    lines.append('| label | date | author | hits | 추천 | 조회 | score | title |')
    lines.append('| --- | --- | --- | --- | ---: | ---: | ---: | --- |')
    for x in top:
        title = x['title'].replace('|', '/')
        lines.append(f"| {x['label']} | {x['date']} | {x['author']} | {','.join(x['hits'])} | {x['up']} | {x['view']} | {x['score']} | {title} |")
    Path(args.summary_md).write_text('\n'.join(lines) + '\n', encoding='utf-8')
    print(json.dumps({'selected': len(top), 'output_json': args.output_json}, ensure_ascii=False))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
