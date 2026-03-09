#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import datetime as dt
import json
import sys
from collections import defaultdict
from pathlib import Path
from typing import Dict, Iterable, List

import requests

BASE_URL = 'https://open.krx.co.kr'
USER_AGENT = 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0 Safari/537.36'
PAGES = {
    'caution': '10020405',
    'warning': '10020406',
    'risk': '10020407',
}
CAUTION_REASON_WEIGHTS = {
    '투자경고 지정예고': 4,
    '종가급변': 1,
    '소수계좌 매수관여 과다': 5,
    '소수계좌 매도관여 과다': 5,
    '소수지점/계좌': 3,
    '단일계좌 거래량 상위': 4,
    '단일계좌 거래량 상위종목': 4,
    '15일간 상승종목의 당일 소수계좌 매수관여 과다': 5,
    '15일간 하락종목의 당일 소수계좌 매도관여 과다': 5,
    '특정계좌(군) 매매관여 과다': 6,
}
CATEGORY_WEIGHTS = {
    'caution': 2,
    'warning': 8,
    'risk': 14,
}
REASON_ALIASES = {
    '단일계좌거래량': '단일계좌 거래량 상위',
    '매매관여과다종목': '특정계좌(군) 매매관여 과다',
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description='Fetch KRX market warning data and rank investigation candidates.')
    parser.add_argument('--start-date', help='YYYYMMDD, defaults to 7 days before end-date')
    parser.add_argument('--end-date', help='YYYYMMDD, defaults to today in Asia/Seoul')
    parser.add_argument('--output-dir', default='manipulation_screening/output', help='Directory to write CSV/Markdown/JSON output')
    parser.add_argument('--top', type=int, default=15, help='How many candidates to show in Markdown output')
    return parser.parse_args()


def today_kst() -> dt.date:
    return dt.datetime.now(dt.timezone(dt.timedelta(hours=9))).date()


def format_ymd(d: dt.date) -> str:
    return d.strftime('%Y%m%d')


def ensure_session() -> requests.Session:
    session = requests.Session()
    session.headers.update({'User-Agent': USER_AGENT})
    return session


def fetch_page_rows(session: requests.Session, page_id: str, start_date: str, end_date: str) -> List[dict]:
    referer = f'{BASE_URL}/contents/MKD/10/1002/{page_id}/MKD{page_id}.jsp'
    bld = f'MKD/10/1002/{page_id}/mkd{page_id}'
    otp = session.post(
        f'{BASE_URL}/contents/COM/GenerateOTP.jspx',
        headers={'Referer': referer},
        data={
            'name': 'form',
            'filetype': 'json',
            'url': bld,
            'bld': bld,
        },
        timeout=20,
    )
    otp.raise_for_status()
    code = otp.text.strip()
    if not code:
        raise RuntimeError(f'OTP generation returned empty body for page {page_id}')

    response = session.post(
        f'{BASE_URL}/contents/OPN/99/OPN99000001.jspx',
        headers={'Referer': referer},
        data={
            'ind_tp': 'ALL',
            'period_strt_dd': start_date,
            'period_end_dd': end_date,
            'pagePath': f'/contents/MKD/10/1002/{page_id}/MKD{page_id}.jsp',
            'code': code,
        },
        timeout=20,
    )
    response.raise_for_status()
    payload = response.json()
    return payload.get('block1', [])


def is_equity_code(code: str) -> bool:
    return code.isdigit() and len(code) == 6


def normalize_row(category: str, row: dict) -> dict | None:
    code = row.get('isu_srt_cd') or row.get('isu_cd') or ''
    name = row.get('isu_nm') or row.get('kor_isu_nm') or ''
    if not code or not name or not is_equity_code(code):
        return None
    date_str = row.get('design_dd') or row.get('act_dd') or ''
    if '/' in date_str:
        date_str = date_str.replace('/', '-')
    elif len(date_str) == 8:
        date_str = f'{date_str[:4]}-{date_str[4:6]}-{date_str[6:]}'
    reason = row.get('gubun', '').strip()
    if not reason:
        reason = {
            'warning': '투자경고',
            'risk': '투자위험',
            'caution': '투자주의',
        }.get(category, category)
    reason = REASON_ALIASES.get(reason, reason)
    return {
        'code': code,
        'name': name,
        'category': category,
        'reason': reason,
        'act_date': (row.get('act_dd') or '').replace('/', '-'),
        'design_date': date_str,
        'price': row.get('isu_cur_pr') or row.get('isu_std_pr') or '',
        'delta': row.get('prv_dd_cmpr') or '',
        'raw': row,
    }


def recency_bonus(date_text: str, end_date: dt.date) -> int:
    if not date_text:
        return 0
    try:
        design_date = dt.date.fromisoformat(date_text)
    except ValueError:
        return 0
    gap = (end_date - design_date).days
    if gap <= 1:
        return 3
    if gap <= 3:
        return 2
    if gap <= 7:
        return 1
    return 0


def score_candidate(events: Iterable[dict], end_date: dt.date) -> dict:
    events = list(events)
    categories = sorted({event['category'] for event in events})
    reasons = sorted({event['reason'] for event in events})
    score = 0
    explanation: List[str] = []

    for category in categories:
        weight = CATEGORY_WEIGHTS.get(category, 0)
        score += weight
        explanation.append(f'{category}+{weight}')

    for event in events:
        reason_weight = CAUTION_REASON_WEIGHTS.get(event['reason'], 0)
        if reason_weight:
            score += reason_weight
            explanation.append(f"{event['reason']}+{reason_weight}")
        bonus = recency_bonus(event['design_date'], end_date)
        if bonus:
            score += bonus
            explanation.append(f"recent({event['design_date']})+{bonus}")

    if len(categories) >= 2:
        score += 4
        explanation.append('multi_category+4')
    if len(reasons) >= 2:
        score += 2
        explanation.append('multi_reason+2')

    latest_date = max((event['design_date'] for event in events if event['design_date']), default='')
    return {
        'score': score,
        'categories': ', '.join(categories),
        'reasons': ' | '.join(reasons),
        'latest_date': latest_date,
        'event_count': len(events),
        'events': events,
        'explanation': ' / '.join(explanation),
    }


def build_candidates(rows: Iterable[dict], end_date: dt.date) -> List[dict]:
    grouped: Dict[tuple, List[dict]] = defaultdict(list)
    for row in rows:
        grouped[(row['code'], row['name'])].append(row)

    candidates = []
    for (code, name), events in grouped.items():
        scored = score_candidate(events, end_date)
        candidates.append({
            'code': code,
            'name': name,
            **scored,
        })

    candidates.sort(key=lambda item: (-item['score'], -item['event_count'], item['latest_date'], item['code']))
    return candidates


def write_csv(path: Path, candidates: List[dict]) -> None:
    with path.open('w', newline='', encoding='utf-8') as fp:
        writer = csv.DictWriter(
            fp,
            fieldnames=['rank', 'score', 'code', 'name', 'categories', 'reasons', 'event_count', 'latest_date', 'explanation'],
        )
        writer.writeheader()
        for rank, candidate in enumerate(candidates, start=1):
            writer.writerow({
                'rank': rank,
                'score': candidate['score'],
                'code': candidate['code'],
                'name': candidate['name'],
                'categories': candidate['categories'],
                'reasons': candidate['reasons'],
                'event_count': candidate['event_count'],
                'latest_date': candidate['latest_date'],
                'explanation': candidate['explanation'],
            })


def write_json(path: Path, candidates: List[dict], meta: dict) -> None:
    path.write_text(json.dumps({'meta': meta, 'candidates': candidates}, ensure_ascii=False, indent=2), encoding='utf-8')


def write_raw_payloads(path: Path, raw_payloads: dict, meta: dict) -> None:
    path.write_text(json.dumps({'meta': meta, 'raw_payloads': raw_payloads}, ensure_ascii=False, indent=2), encoding='utf-8')


def write_markdown(path: Path, candidates: List[dict], meta: dict, top_n: int) -> None:
    lines = []
    lines.append('# KRX 이상징후 기반 조사 후보')
    lines.append('')
    lines.append(f"- 기준일: `{meta['end_date']}`")
    lines.append(f"- 조회구간: `{meta['start_date']} ~ {meta['end_date']}`")
    lines.append('- 데이터: 한국거래소 `투자주의/투자경고/투자위험` 공개 조회')
    lines.append('- 주의: 아래 목록은 `조사 후보`이며, 불공정거래 확정 판단이 아니다.')
    lines.append('')
    lines.append('| 순위 | 종목 | 코드 | 점수 | 분류 | 최근 지정일 | 근거 |')
    lines.append('| --- | --- | --- | ---: | --- | --- | --- |')
    for idx, candidate in enumerate(candidates[:top_n], start=1):
        reasons = candidate['reasons'].replace(' | ', ' / ')
        lines.append(
            f"| {idx} | {candidate['name']} | {candidate['code']} | {candidate['score']} | {candidate['categories']} | {candidate['latest_date']} | {reasons} |"
        )
    lines.append('')
    lines.append('## 해석 기준')
    lines.append('')
    lines.append('- `risk`: 투자위험 지정 종목이라 기본 점수를 가장 높게 부여했다.')
    lines.append('- `warning`: 투자경고 지정 종목은 강한 경보로 봤다.')
    lines.append('- `caution`: 투자주의 사유 중에서도 `특정계좌(군)`, `소수계좌 매수관여 과다`, `투자경고 지정예고`를 더 높게 봤다.')
    lines.append('- 동일 종목이 여러 범주에 동시에 걸리면 우선순위를 높였다.')
    lines.append('')
    lines.append('## 상위 후보 상세')
    lines.append('')
    for idx, candidate in enumerate(candidates[:top_n], start=1):
        lines.append(f"### {idx}. {candidate['name']} ({candidate['code']})")
        lines.append('')
        lines.append(f"- 점수: `{candidate['score']}`")
        lines.append(f"- 분류: `{candidate['categories']}`")
        lines.append(f"- 사유: `{candidate['reasons']}`")
        lines.append(f"- 이벤트 수: `{candidate['event_count']}`")
        lines.append(f"- 상세: `{candidate['explanation']}`")
        lines.append('')
    path.write_text('\n'.join(lines) + '\n', encoding='utf-8')


def main() -> int:
    args = parse_args()
    end_date_obj = today_kst()
    if args.end_date:
        end_date_obj = dt.datetime.strptime(args.end_date, '%Y%m%d').date()
    start_date_obj = end_date_obj - dt.timedelta(days=6)
    if args.start_date:
        start_date_obj = dt.datetime.strptime(args.start_date, '%Y%m%d').date()

    start_date = format_ymd(start_date_obj)
    end_date = format_ymd(end_date_obj)
    session = ensure_session()

    normalized_rows: List[dict] = []
    raw_payloads: Dict[str, List[dict]] = {}
    for category, page_id in PAGES.items():
        rows = fetch_page_rows(session, page_id, start_date, end_date)
        raw_payloads[category] = rows
        for row in rows:
            normalized = normalize_row(category, row)
            if normalized:
                normalized_rows.append(normalized)

    candidates = build_candidates(normalized_rows, end_date_obj)
    output_root = Path(args.output_dir) / end_date
    output_root.mkdir(parents=True, exist_ok=True)

    meta = {
        'generated_at_kst': dt.datetime.now(dt.timezone(dt.timedelta(hours=9))).isoformat(),
        'start_date': start_date,
        'end_date': end_date,
        'source_pages': {category: f'{BASE_URL}/contents/MKD/10/1002/{page_id}/MKD{page_id}.jsp' for category, page_id in PAGES.items()},
        'row_count': len(normalized_rows),
        'candidate_count': len(candidates),
    }

    write_csv(output_root / 'ranked_candidates.csv', candidates)
    write_json(output_root / 'ranked_candidates.json', candidates, meta)
    write_raw_payloads(output_root / 'raw_payloads.json', raw_payloads, meta)
    write_markdown(output_root / 'ranked_candidates.md', candidates, meta, args.top)

    print(json.dumps({
        'output_dir': str(output_root),
        'candidate_count': len(candidates),
        'top_candidates': [
            {
                'name': candidate['name'],
                'code': candidate['code'],
                'score': candidate['score'],
                'categories': candidate['categories'],
                'reasons': candidate['reasons'],
            }
            for candidate in candidates[: min(args.top, 10)]
        ],
    }, ensure_ascii=False, indent=2))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
