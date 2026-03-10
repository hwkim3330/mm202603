#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Iterable


def load_json(path: Path) -> Any:
    return json.loads(path.read_text())


def resolve_raw_dir(base: Path) -> Path:
    candidates = [base / 'raw', base / 'attachments', base]
    for cand in candidates:
        if (cand / 'investor_institution_by_stock_ka10059.json').exists() or (cand / 'institutional_trading_trend_ka10045.json').exists():
            return cand
    raise FileNotFoundError(f'Could not find Kiwoom raw json files under {base}')


def as_float(text: str) -> float:
    if text is None:
        return 0.0
    text = str(text).strip().replace(',', '')
    if not text:
        return 0.0
    return float(text)


def as_int(text: str) -> int:
    return int(round(as_float(text)))


def as_rate(text: str) -> float:
    if text is None:
        return 0.0
    raw = str(text).strip().replace(',', '')
    if not raw:
        return 0.0
    value = float(raw)
    if '.' in raw:
        return value
    return value / 100.0


def fmt_date(yyyymmdd: str) -> str:
    s = str(yyyymmdd)
    if len(s) == 8:
        return f'{s[:4]}.{s[4:6]}.{s[6:]}'
    return s


def top_abs(rows: Iterable[dict], key: str, limit: int = 5) -> list[dict]:
    rows = list(rows)
    return sorted(rows, key=lambda r: abs(as_float(r.get(key, 0))), reverse=True)[:limit]


def first_existing(raw_dir: Path, names: list[str]) -> Path | None:
    for name in names:
        p = raw_dir / name
        if p.exists():
            return p
    return None


def summarize(base: Path, stock_name: str | None = None, stock_code: str | None = None) -> str:
    raw_dir = resolve_raw_dir(base)

    p_10059 = first_existing(raw_dir, ['investor_institution_by_stock_ka10059.json'])
    p_10045 = first_existing(raw_dir, ['institutional_trading_trend_ka10045.json'])
    p_10047 = first_existing(raw_dir, ['execution_strength_by_day_ka10047.json'])
    p_10001 = first_existing(raw_dir, ['basic_stock_information_ka10001.json'])

    rows_10059 = load_json(p_10059)['stk_invsr_orgn'] if p_10059 else []
    rows_10045 = load_json(p_10045)['stk_orgn_trde_trnsn'] if p_10045 else []
    rows_10047 = load_json(p_10047)['cntr_str_daly'] if p_10047 else []

    if p_10001:
        obj = load_json(p_10001)
        output = obj.get('stk_prpr', {}) if isinstance(obj, dict) else {}
        stock_name = stock_name or output.get('stk_nm') or stock_name
        stock_code = stock_code or output.get('stk_cd') or stock_code

    lines: list[str] = []
    if stock_name and stock_code:
        title = f'# Kiwoom Redflag Summary {stock_name}({stock_code})'
    elif stock_name:
        title = f'# Kiwoom Redflag Summary {stock_name}'
    else:
        title = '# Kiwoom Redflag Summary'
    lines.append(title)
    lines.append('')
    lines.append(f'- 원천 디렉터리: `{raw_dir}`')
    lines.append('')

    if rows_10059:
        dates = [r.get('dt', '') for r in rows_10059 if r.get('dt')]
        if dates:
            lines.append(f'- 투자자/기관 데이터 구간: `{fmt_date(min(dates))} ~ {fmt_date(max(dates))}`')
        major = [r for r in rows_10059 if abs(as_rate(r.get('flu_rt', 0))) >= 5.0]
        major = sorted(major, key=lambda r: r.get('dt', ''), reverse=True)
        lines.append(f'- 일간 등락률 절대값 5% 이상 일수: `{len(major)}`')
        lines.append('')
        lines.append('## Major Swing Days')
        lines.append('')
        for row in major[:8]:
            dt = fmt_date(row.get('dt', ''))
            flu = as_rate(row.get('flu_rt', 0))
            frg = as_int(row.get('frgnr_invsr', 0))
            org = as_int(row.get('orgn', 0))
            qty = as_int(row.get('acc_trde_qty', 0))
            lines.append(f'- `{dt}` 등락률 `{flu:+.2f}%`, 누적거래량 `{qty}`, 외국인 `{frg}`, 기관 `{org}`')
        lines.append('')

    if rows_10045:
        nonzero = [
            r for r in rows_10045
            if as_int(r.get('for_daly_nettrde_qty', 0)) != 0 or as_int(r.get('orgn_daly_nettrde_qty', 0)) != 0
        ]
        lines.append('## Institution / Foreign Participation')
        lines.append('')
        lines.append(f'- 비제로 기관/외국인 일수: `{len(nonzero)}`')
        if nonzero:
            for row in nonzero[:8]:
                dt = fmt_date(row.get('dt', ''))
                frg = as_int(row.get('for_daly_nettrde_qty', 0))
                org = as_int(row.get('orgn_daly_nettrde_qty', 0))
                flu = as_rate(row.get('flu_rt', 0))
                lines.append(f'- `{dt}` 등락률 `{flu:+.2f}%`, 외국인 `{frg}`, 기관 `{org}`')
        else:
            lines.append('- 주요 구간에서 외국인/기관 순매수 흔적이 사실상 없었음')
        lines.append('')

    if rows_10047:
        strong = top_abs(rows_10047, 'cntr_str', limit=8)
        lines.append('## Execution Strength Extremes')
        lines.append('')
        for row in strong:
            dt = fmt_date(row.get('dt', ''))
            cur = as_rate(row.get('flu_rt', 0))
            cntr = as_float(row.get('cntr_str', 0))
            lines.append(f'- `{dt}` 등락률 `{cur:+.2f}%`, 체결강도 `{cntr:.2f}`')
        lines.append('')

    lines.append('## Filing Use')
    lines.append('')
    lines.append('- 메인 근거는 KRX 경보와 함께 본다.')
    lines.append('- 여기서 중요한 것은 `급등락 반복`, `외국인·기관 참여 빈약`, `체결강도 급변` 3가지다.')
    lines.append('- 포상금 관점에서는 계좌/리딩방 직접 증거가 추가되어야 상한선이 올라간다.')
    lines.append('')
    return '\n'.join(lines)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument('--input-dir', required=True)
    parser.add_argument('--output-file', required=True)
    parser.add_argument('--stock-name', default='')
    parser.add_argument('--stock-code', default='')
    args = parser.parse_args()

    text = summarize(Path(args.input_dir), args.stock_name or None, args.stock_code or None)
    out = Path(args.output_file)
    out.write_text(text)
    print(out)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
