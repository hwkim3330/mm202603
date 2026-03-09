#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import re
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlparse

import requests

USER_AGENT = 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0 Safari/537.36'


@dataclass
class ArchiveItem:
    label: str
    url: str
    status_code: int
    content_type: str
    fetched_at_utc: str
    bytes: int
    sha256: str
    filename: str


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description='Archive public evidence URLs with hash manifest.')
    p.add_argument('--output-dir', required=True)
    p.add_argument('--input-json', required=True, help='JSON file: list of {label,url}')
    return p.parse_args()


def slugify(text: str) -> str:
    text = text.strip().lower()
    text = re.sub(r'[^a-z0-9]+', '_', text)
    return text.strip('_') or 'item'


def choose_ext(content_type: str, url: str) -> str:
    if 'html' in content_type:
        return '.html'
    if 'json' in content_type:
        return '.json'
    path = urlparse(url).path
    suffix = Path(path).suffix
    return suffix if suffix else '.bin'


def fetch(session: requests.Session, label: str, url: str, raw_dir: Path) -> ArchiveItem:
    resp = session.get(url, timeout=30)
    data = resp.content
    sha = hashlib.sha256(data).hexdigest()
    content_type = resp.headers.get('content-type', '')
    ext = choose_ext(content_type, url)
    stamp = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')
    filename = f'{stamp}_{slugify(label)}{ext}'
    (raw_dir / filename).write_bytes(data)
    return ArchiveItem(
        label=label,
        url=url,
        status_code=resp.status_code,
        content_type=content_type,
        fetched_at_utc=stamp,
        bytes=len(data),
        sha256=sha,
        filename=filename,
    )


def write_csv(path: Path, items: list[ArchiveItem]) -> None:
    with path.open('w', newline='', encoding='utf-8') as fp:
        writer = csv.DictWriter(fp, fieldnames=list(asdict(items[0]).keys()) if items else [
            'label', 'url', 'status_code', 'content_type', 'fetched_at_utc', 'bytes', 'sha256', 'filename'
        ])
        writer.writeheader()
        for item in items:
            writer.writerow(asdict(item))


def write_md(path: Path, items: list[ArchiveItem], raw_dir: Path) -> None:
    lines = []
    lines.append('# Public Evidence Archive Manifest')
    lines.append('')
    lines.append(f'- 수집 파일 수: `{len(items)}`')
    lines.append(f'- 원본 저장 경로: `{raw_dir}`')
    lines.append('')
    lines.append('| label | status | bytes | sha256 | filename | url |')
    lines.append('| --- | ---: | ---: | --- | --- | --- |')
    for item in items:
        lines.append(
            f"| {item.label} | {item.status_code} | {item.bytes} | `{item.sha256}` | `{item.filename}` | {item.url} |"
        )
    path.write_text('\n'.join(lines) + '\n', encoding='utf-8')


def main() -> int:
    args = parse_args()
    output_dir = Path(args.output_dir)
    raw_dir = output_dir / 'raw'
    output_dir.mkdir(parents=True, exist_ok=True)
    raw_dir.mkdir(parents=True, exist_ok=True)
    entries = json.loads(Path(args.input_json).read_text(encoding='utf-8'))
    session = requests.Session()
    session.headers.update({'User-Agent': USER_AGENT})
    items: list[ArchiveItem] = []
    for entry in entries:
        items.append(fetch(session, entry['label'], entry['url'], raw_dir))
    (output_dir / 'archive_manifest.json').write_text(
        json.dumps([asdict(item) for item in items], ensure_ascii=False, indent=2), encoding='utf-8'
    )
    write_csv(output_dir / 'archive_manifest.csv', items)
    write_md(output_dir / 'archive_manifest.md', items, raw_dir)
    print(json.dumps({'count': len(items), 'output_dir': str(output_dir)}, ensure_ascii=False))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
