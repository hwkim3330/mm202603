#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Callable

KST = timezone(timedelta(hours=9))


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description='Collect Kiwoom REST evidence bundle for one stock.')
    p.add_argument('--code', required=True, help='6-digit stock code')
    p.add_argument('--name', required=True, help='stock name label')
    p.add_argument('--output-dir', required=True)
    p.add_argument('--start-date', help='YYYYMMDD, default 14 days ago in KST')
    p.add_argument('--end-date', help='YYYYMMDD, default today in KST')
    p.add_argument('--use-dotenv', help='optional dotenv path to load before requests')
    return p.parse_args()


def load_dotenv(path: str | None) -> None:
    if not path:
        return
    p = Path(path)
    if not p.exists():
        raise FileNotFoundError(f'dotenv not found: {p}')
    for line in p.read_text(encoding='utf-8').splitlines():
        line = line.strip()
        if not line or line.startswith('#') or '=' not in line:
            continue
        key, _, value = line.partition('=')
        key = key.strip()
        value = value.strip()
        if key and value and key not in os.environ:
            os.environ[key] = value


def ensure_credentials() -> None:
    app_key = os.environ.get('KIWOOM_APP_KEY') or os.environ.get('KIWOOM_API_KEY')
    app_secret = os.environ.get('KIWOOM_APP_SECRET') or os.environ.get('KIWOOM_API_SECRET')
    if not app_key or not app_secret:
        raise RuntimeError('KIWOOM_APP_KEY / KIWOOM_APP_SECRET not set')
    os.environ['KIWOOM_API_KEY'] = app_key
    os.environ['KIWOOM_API_SECRET'] = app_secret


@dataclass
class SavedArtifact:
    label: str
    filename: str
    ok: bool
    note: str


def save_json(path: Path, payload: Any) -> None:
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding='utf-8')


def validate_payload(payload: Any) -> None:
    if not isinstance(payload, dict):
        return
    if 'error' in payload:
        raise RuntimeError(str(payload['error']))
    return_code = payload.get('return_code')
    if return_code not in (None, 0, '0'):
        msg = payload.get('return_msg') or 'unknown Kiwoom API error'
        raise RuntimeError(f'return_code={return_code}: {msg}')


def safe_call(label: str, fn: Callable[[], Any], out_dir: Path, artifacts: list[SavedArtifact]) -> None:
    filename = f'{label}.json'
    try:
        payload = fn()
        validate_payload(payload)
        save_json(out_dir / filename, payload)
        note = 'ok'
        ok = True
    except Exception as e:
        payload = {'error': str(e), 'label': label}
        save_json(out_dir / filename, payload)
        note = f'error: {e}'
        ok = False
    artifacts.append(SavedArtifact(label=label, filename=filename, ok=ok, note=note))


def build_summary(path: Path, code: str, name: str, start_date: str, end_date: str, artifacts: list[SavedArtifact]) -> None:
    lines = []
    lines.append('# Kiwoom Stock Evidence Summary')
    lines.append('')
    lines.append(f'- 종목: `{name}({code})`')
    lines.append(f'- 조회구간: `{start_date} ~ {end_date}`')
    lines.append(f'- 수집시각(KST): `{datetime.now(KST).strftime("%Y-%m-%d %H:%M:%S %Z")}`')
    lines.append('- 목적: 공개자료 외에 키움 REST 원시 데이터를 보존해 종목별 이상거래 정황을 보강')
    lines.append('')
    lines.append('| 항목 | 파일 | 상태 | 비고 |')
    lines.append('| --- | --- | --- | --- |')
    for item in artifacts:
        lines.append(f'| {item.label} | `{item.filename}` | {"OK" if item.ok else "ERR"} | {item.note} |')
    path.write_text('\n'.join(lines) + '\n', encoding='utf-8')


def main() -> int:
    args = parse_args()
    load_dotenv(args.use_dotenv)
    ensure_credentials()

    today = datetime.now(KST).date()
    start_date = args.start_date or (today - timedelta(days=14)).strftime('%Y%m%d')
    end_date = args.end_date or today.strftime('%Y%m%d')

    base = Path(args.output_dir)
    raw_dir = base / 'raw'
    raw_dir.mkdir(parents=True, exist_ok=True)

    from kiwoom_rest_api.auth.token import TokenManager
    from kiwoom_rest_api.koreanstock.chart import Chart
    from kiwoom_rest_api.koreanstock.market_condition import MarketCondition
    from kiwoom_rest_api.koreanstock.stockinfo import StockInfo

    token_mgr = TokenManager()
    base_url = 'https://api.kiwoom.com'
    chart = Chart(base_url=base_url, token_manager=token_mgr)
    market = MarketCondition(base_url=base_url, token_manager=token_mgr)
    stock = StockInfo(base_url=base_url, token_manager=token_mgr)

    artifacts: list[SavedArtifact] = []

    safe_call('basic_stock_information_ka10001', lambda: stock.basic_stock_information_request_ka10001(stock_code=args.code), raw_dir, artifacts)
    safe_call('orderbook_ka10004', lambda: market.stock_quote_request_ka10004(stock_code=args.code), raw_dir, artifacts)
    safe_call('minute_chart_ka10080', lambda: chart.stock_minute_chart_request_ka10080(stk_cd=args.code, tic_scope='5', upd_stkpc_tp='1'), raw_dir, artifacts)
    safe_call('tick_chart_ka10079', lambda: chart.stock_tick_chart_request_ka10079(stk_cd=args.code, tic_scope='1', upd_stkpc_tp='1'), raw_dir, artifacts)
    safe_call('daily_transaction_details_ka10015', lambda: stock.daily_transaction_details_request_ka10015(stock_code=args.code, start_date=end_date), raw_dir, artifacts)
    safe_call('execution_strength_by_day_ka10047', lambda: market.execution_strength_by_day_request_ka10047(stock_code=args.code), raw_dir, artifacts)
    safe_call('stock_trading_agent_ka10002', lambda: stock.stock_trading_agent_request_ka10002(stock_code=args.code), raw_dir, artifacts)
    safe_call('investor_institution_by_stock_ka10059', lambda: stock.stock_data_by_investor_institution_request_ka10059(date=end_date, stock_code=args.code, amount_quantity_type='1', trade_type='0', unit_type='1000'), raw_dir, artifacts)
    safe_call('investor_institution_chart_ka10060', lambda: chart.stockwise_investor_institution_chart_request_ka10060(dt=end_date, stk_cd=args.code, amt_qty_tp='1', trde_tp='0', unit_tp='1000'), raw_dir, artifacts)
    safe_call('institutional_trading_trend_ka10045', lambda: market.stockwise_institutional_trading_trend_request_ka10045(stock_code=args.code, start_date=start_date, end_date=end_date, org_institution_price_type='1', foreign_institution_price_type='1'), raw_dir, artifacts)
    safe_call('broker_trading_trend_ka10078', lambda: market.brokerwise_stock_trading_trend_request_ka10078(member_company_code='000', stock_code=args.code, start_date=start_date, end_date=end_date), raw_dir, artifacts)
    safe_call('execution_today_vs_previous_ka10084', lambda: stock.today_vs_previous_day_execution_request_ka10084(stock_code=args.code, today_or_previous='1', tick_or_minute='1', time='1'), raw_dir, artifacts)

    save_json(base / 'collection_manifest.json', {
        'code': args.code,
        'name': args.name,
        'start_date': start_date,
        'end_date': end_date,
        'generated_at_kst': datetime.now(KST).strftime('%Y-%m-%d %H:%M:%S %Z'),
        'artifacts': [artifact.__dict__ for artifact in artifacts],
    })
    build_summary(base / 'SUMMARY.md', args.code, args.name, start_date, end_date, artifacts)
    error_count = sum(1 for artifact in artifacts if not artifact.ok)
    print(json.dumps({'output_dir': str(base), 'artifact_count': len(artifacts), 'error_count': error_count}, ensure_ascii=False))
    return 1 if error_count else 0


if __name__ == '__main__':
    raise SystemExit(main())
