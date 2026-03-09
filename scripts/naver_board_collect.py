#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import json
from collections import Counter, defaultdict
from pathlib import Path
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup

BASE = 'https://finance.naver.com'
USER_AGENT = 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0 Safari/537.36'
KEYWORDS = ['유가', '상한가', '상장폐지', '청산', '호르무즈', '전쟁', '200달러', '유조선', '쩜상', '사이드카', '서킷']


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description='Collect public Naver stock board titles and keyword patterns.')
    p.add_argument('--code', required=True, help='6-digit stock code')
    p.add_argument('--pages', type=int, default=20)
    p.add_argument('--output-dir', required=True)
    return p.parse_args()


def fetch_rows(code: str, pages: int) -> list[dict]:
    session = requests.Session()
    session.headers.update({'User-Agent': USER_AGENT})
    rows = []
    for page in range(1, pages + 1):
        html = session.get(f'{BASE}/item/board.naver?code={code}&page={page}', timeout=20).text
        soup = BeautifulSoup(html, 'html.parser')
        page_rows = 0
        for tr in soup.select('table.type2 tr'):
            tds = tr.find_all('td')
            if len(tds) != 6:
                continue
            if tds[1].get('class') != ['title']:
                continue
            a = tds[1].find('a')
            if not a:
                continue
            page_rows += 1
            rows.append({
                'date': tds[0].get_text(' ', strip=True),
                'title': a.get_text(' ', strip=True),
                'href': urljoin(BASE, a.get('href')),
                'author': tds[2].get_text(' ', strip=True),
                'view': int(tds[3].get_text(' ', strip=True) or 0),
                'up': int(tds[4].get_text(' ', strip=True) or 0),
                'down': int(tds[5].get_text(' ', strip=True) or 0),
                'page': page,
            })
        if page_rows == 0:
            break
    return rows


def keyword_stats(rows: list[dict]) -> dict[str, Counter]:
    by_date: dict[str, Counter] = defaultdict(Counter)
    for row in rows:
        day = row['date'].split()[0]
        for keyword in KEYWORDS:
            if keyword in row['title']:
                by_date[day][keyword] += 1
    return by_date


def representative_posts(rows: list[dict]) -> list[dict]:
    reps = []
    for keyword in KEYWORDS:
        candidates = [row for row in rows if keyword in row['title']]
        candidates.sort(key=lambda row: (-row['up'], -row['view'], row['date']))
        if candidates:
            reps.append({'keyword': keyword, **candidates[0]})
    return reps


def write_csv(path: Path, rows: list[dict]) -> None:
    with path.open('w', newline='', encoding='utf-8') as fp:
        writer = csv.DictWriter(fp, fieldnames=['date', 'title', 'href', 'author', 'view', 'up', 'down', 'page'])
        writer.writeheader()
        writer.writerows(rows)


def write_json(path: Path, meta: dict, by_date: dict[str, Counter], reps: list[dict]) -> None:
    payload = {
        'meta': meta,
        'keyword_counts_by_date': {day: dict(counter) for day, counter in sorted(by_date.items())},
        'representative_posts': reps,
    }
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding='utf-8')


def write_markdown(path: Path, code: str, meta: dict, by_date: dict[str, Counter], reps: list[dict]) -> None:
    lines = []
    lines.append(f'# Naver Community Snapshot {code}')
    lines.append('')
    lines.append(f"- 수집 페이지 수: `{meta['pages_fetched']}`")
    lines.append(f"- 수집 게시글 수: `{meta['row_count']}`")
    lines.append('- 출처: `https://finance.naver.com/item/board.naver` 공개 게시판 제목')
    lines.append('- 주의: 게시판 글은 사용자 작성물로, 진위는 별도 검증 필요하다.')
    lines.append('')
    lines.append('## 날짜별 키워드 빈도')
    lines.append('')
    lines.append('| 날짜 | 키워드 빈도 |')
    lines.append('| --- | --- |')
    for day, counter in sorted(by_date.items()):
        summary = ', '.join(f'{keyword}:{count}' for keyword, count in counter.items()) or '-'
        lines.append(f'| {day} | {summary} |')
    lines.append('')
    lines.append('## 대표 게시글 제목')
    lines.append('')
    lines.append('| 키워드 | 시각 | 추천 | 조회 | 제목 | 링크 |')
    lines.append('| --- | --- | ---: | ---: | --- | --- |')
    for row in reps:
        title = row['title'].replace('|', '/')
        lines.append(f"| {row['keyword']} | {row['date']} | {row['up']} | {row['view']} | {title} | {row['href']} |")
    path.write_text('\n'.join(lines) + '\n', encoding='utf-8')


def main() -> int:
    args = parse_args()
    rows = fetch_rows(args.code, args.pages)
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    meta = {
        'code': args.code,
        'pages_fetched': max((row['page'] for row in rows), default=0),
        'row_count': len(rows),
        'source': f'{BASE}/item/board.naver?code={args.code}',
    }
    by_date = keyword_stats(rows)
    reps = representative_posts(rows)
    write_csv(output_dir / f'naver_board_{args.code}.csv', rows)
    write_json(output_dir / f'naver_board_{args.code}_summary.json', meta, by_date, reps)
    write_markdown(output_dir / f'naver_board_{args.code}_snapshot.md', args.code, meta, by_date, reps)
    print(json.dumps({'meta': meta, 'representative_posts': reps[:5]}, ensure_ascii=False, indent=2))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
