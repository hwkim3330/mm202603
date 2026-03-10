#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import json
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description='Create a direct-evidence summary from Naver board evidence and Kiwoom minute data.')
    p.add_argument('--board-csv', required=True)
    p.add_argument('--post-evidence-dir', required=True)
    p.add_argument('--minute-json', required=True)
    p.add_argument('--output-md', required=True)
    p.add_argument('--output-json', required=True)
    p.add_argument('--stock-name', default='')
    p.add_argument('--stock-code', default='')
    return p.parse_args()


def as_int(text: str | int | None) -> int:
    if text is None:
        return 0
    return int(str(text).replace(',', '').strip() or 0)


def as_price(text: str | int | None) -> int:
    return abs(as_int(text))


def parse_board_rows(path: Path) -> dict[str, dict]:
    rows = list(csv.DictReader(path.open(encoding='utf-8')))
    return {row['href']: row for row in rows}


def parse_time(text: str) -> datetime:
    if 'T' in text:
        return datetime.fromisoformat(text)
    return datetime.strptime(text, '%Y.%m.%d %H:%M')


def load_manifest(path: Path) -> list[dict]:
    return json.loads(path.read_text(encoding='utf-8'))


def load_minute_rows(path: Path) -> list[dict]:
    raw = json.loads(path.read_text(encoding='utf-8')).get('stk_min_pole_chart_qry', [])
    rows = []
    for row in raw:
        ts = datetime.strptime(row['cntr_tm'], '%Y%m%d%H%M%S')
        rows.append({
            'ts': ts,
            'price': as_price(row.get('cur_prc')),
            'qty': as_int(row.get('trde_qty')),
            'acc_qty': as_int(row.get('acc_trde_qty')),
        })
    return sorted(rows, key=lambda x: x['ts'])


def nearest_minute_ref(post_dt: datetime, minute_rows: list[dict]) -> dict | None:
    same_day = [r for r in minute_rows if r['ts'].date() == post_dt.date()]
    if not same_day:
        return None
    before = [r for r in same_day if r['ts'] <= post_dt]
    if before:
        ref = before[-1].copy()
        ref['match_type'] = 'prior_or_same'
        return ref
    ref = same_day[0].copy()
    ref['match_type'] = 'next_open'
    return ref


def body_hits(text: str) -> list[str]:
    keywords = ['세력', '주포', '상한가', '쩜상', '시총', '매집', '설거지', '호재', '오픈채팅', '대화방', '리딩방', '리딩', '100배', '목표']
    return [kw for kw in keywords if kw in text]


def first_hit_snippet(text: str) -> str:
    for line in [x.strip() for x in text.splitlines() if x.strip()]:
        if body_hits(line):
            return line[:220]
    return text.replace('\n', ' ')[:220]


def main() -> int:
    args = parse_args()
    board_by_href = parse_board_rows(Path(args.board_csv))
    ev_dir = Path(args.post_evidence_dir)
    manifest = load_manifest(ev_dir / 'manifest.json')
    raw_dir = ev_dir / 'raw'
    minute_rows = load_minute_rows(Path(args.minute_json))

    repeated_authors = Counter(item.get('author', '') for item in manifest if item.get('author'))
    title_kw_counter = Counter()
    body_kw_counter = Counter()
    external_links = Counter()
    report_rows = []

    for item in manifest:
        meta = json.loads((raw_dir / item['meta_filename']).read_text(encoding='utf-8'))
        text = (raw_dir / item['text_filename']).read_text(encoding='utf-8')
        title = item['title']
        title_hits = body_hits(title)
        body_hits_list = body_hits(text)
        title_kw_counter.update(title_hits)
        body_kw_counter.update(body_hits_list)
        for link in meta.get('extracted_links', []):
            external_links[link] += 1
        post_dt = parse_time(item['written_at'])
        minute_ref = nearest_minute_ref(post_dt, minute_rows)
        report_rows.append({
            'label': item['label'],
            'date': item['written_at'],
            'author': item.get('author', ''),
            'title': title,
            'title_hits': title_hits,
            'body_hits': body_hits_list,
            'recommend': item.get('recommend_count', 0),
            'view': item.get('view_count', 0),
            'link_count': len(meta.get('extracted_links', [])),
            'minute_ref': minute_ref,
            'snippet': first_hit_snippet(text),
            'url': item['source_url'],
        })

    report_rows.sort(key=lambda x: (len(x['body_hits']) + len(x['title_hits']), x['recommend'], x['view']), reverse=True)

    payload = {
        'stock_name': args.stock_name,
        'stock_code': args.stock_code,
        'post_count': len(report_rows),
        'repeated_authors': repeated_authors.most_common(20),
        'title_keyword_counts': dict(title_kw_counter),
        'body_keyword_counts': dict(body_kw_counter),
        'external_links': external_links.most_common(20),
        'posts': report_rows,
    }
    Path(args.output_json).write_text(json.dumps(payload, ensure_ascii=False, indent=2, default=str), encoding='utf-8')

    title = f"# Direct Evidence Report {args.stock_name}({args.stock_code})" if args.stock_name and args.stock_code else '# Direct Evidence Report'
    lines = [title, '']
    lines.append(f"- 수집 게시글 수: `{len(report_rows)}`")
    lines.append(f"- 반복 작성자 상위: `{repeated_authors.most_common(10)}`")
    lines.append(f"- 제목 키워드 빈도: `{dict(title_kw_counter)}`")
    lines.append(f"- 본문 키워드 빈도: `{dict(body_kw_counter)}`")
    lines.append('')
    lines.append('## External Links')
    lines.append('')
    if external_links:
        for link, count in external_links.most_common(20):
            lines.append(f'- `{count}`회 `{link}`')
    else:
        lines.append('- 외부 링크 미확인')
    lines.append('')
    lines.append('## Repeated Authors')
    lines.append('')
    for author, count in repeated_authors.most_common(15):
        lines.append(f'- `{author}` `{count}`건')
    lines.append('')
    lines.append('## Post vs Minute Reference')
    lines.append('')
    lines.append('| time | author | title hits | body hits | 추천 | 조회 | minute ref | price | qty | note |')
    lines.append('| --- | --- | --- | --- | ---: | ---: | --- | ---: | ---: | --- |')
    for row in report_rows[:30]:
        ref = row['minute_ref'] or {}
        ref_ts = ref.get('ts').strftime('%Y-%m-%d %H:%M') if ref.get('ts') else '-'
        price = ref.get('price', '-')
        qty = ref.get('qty', '-')
        note = row['snippet'].replace('|', '/')
        lines.append(
            f"| {row['date']} | {row['author']} | {','.join(row['title_hits']) or '-'} | {','.join(row['body_hits']) or '-'} | {row['recommend']} | {row['view']} | {ref_ts} | {price} | {qty} | {note} |"
        )
    lines.append('')
    lines.append('## Filing Use')
    lines.append('')
    lines.append('- 본 문서는 KRX 경보와 키움 원시데이터 신고의 보조증거로 사용한다.')
    lines.append('- 반복 작성자, 과장 표현, 게시 시각과 가격구간 대응을 정리해 공개자료형 신고의 기여도를 높이는 목적이다.')
    Path(args.output_md).write_text('\n'.join(lines) + '\n', encoding='utf-8')
    print(Path(args.output_md))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
