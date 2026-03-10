#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urljoin

import pytesseract
import requests
from bs4 import BeautifulSoup
from PIL import Image
from io import BytesIO

USER_AGENT = 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0 Safari/537.36'
KST = timezone.utc


@dataclass
class PostArtifact:
    label: str
    source_url: str
    mobile_url: str
    title: str
    written_at: str
    author: str
    recommend_count: int
    view_count: int
    image_count: int
    link_count: int
    ocr_chars: int
    text_filename: str
    html_filename: str
    meta_filename: str


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description='Archive Naver board post body/images/OCR.')
    p.add_argument('--input-json', required=True, help='JSON list of {label,url}')
    p.add_argument('--output-dir', required=True)
    return p.parse_args()


def session() -> requests.Session:
    s = requests.Session()
    s.headers.update({'User-Agent': USER_AGENT})
    return s


def fetch_html(s: requests.Session, url: str) -> str:
    return s.get(url, timeout=30).text


def resolve_mobile_url(source_url: str, html: str) -> str:
    soup = BeautifulSoup(html, 'html.parser')
    iframe = soup.select_one('table.view iframe#contents')
    if iframe and iframe.get('src'):
        return iframe['src']
    return source_url


def extract_post_data(mobile_html: str) -> dict:
    m = re.search(r'<script id="__NEXT_DATA__" type="application/json">(.*?)</script>', mobile_html)
    if not m:
        raise RuntimeError('NEXT_DATA not found')
    data = json.loads(m.group(1))
    for q in data.get('props', {}).get('pageProps', {}).get('dehydratedState', {}).get('queries', []):
        result = q.get('state', {}).get('data', {}).get('result')
        if isinstance(result, dict) and 'title' in result and 'contentHtml' in result:
            return result
    raise RuntimeError('post result not found in NEXT_DATA')


def html_to_text(content_html: str) -> str:
    soup = BeautifulSoup(content_html, 'html.parser')
    return soup.get_text('\n', strip=True)


def extract_image_urls(content_html: str) -> list[str]:
    soup = BeautifulSoup(content_html, 'html.parser')
    urls = []
    for img in soup.find_all('img'):
        src = img.get('src')
        if src:
            urls.append(src)
    return urls


def extract_links(content_html: str) -> list[str]:
    soup = BeautifulSoup(content_html, 'html.parser')
    urls = []
    seen = set()
    for a in soup.find_all('a'):
        href = a.get('href')
        if not href or href in seen:
            continue
        seen.add(href)
        urls.append(href)
    return urls


def save_image_and_ocr(s: requests.Session, url: str, raw_dir: Path, label: str, idx: int) -> tuple[str, str]:
    resp = s.get(url, timeout=30)
    resp.raise_for_status()
    img = Image.open(BytesIO(resp.content))
    ext = '.png'
    image_name = f'{label}_img{idx:02d}{ext}'
    image_path = raw_dir / image_name
    img.save(image_path)
    ocr_text = pytesseract.image_to_string(img, lang='kor+eng')
    ocr_name = f'{label}_img{idx:02d}.ocr.txt'
    (raw_dir / ocr_name).write_text(ocr_text, encoding='utf-8')
    return image_name, ocr_name


def main() -> int:
    args = parse_args()
    output_dir = Path(args.output_dir)
    raw_dir = output_dir / 'raw'
    output_dir.mkdir(parents=True, exist_ok=True)
    raw_dir.mkdir(parents=True, exist_ok=True)
    items = json.loads(Path(args.input_json).read_text(encoding='utf-8'))
    s = session()
    manifest: list[PostArtifact] = []
    failures: list[dict] = []

    for item in items:
        label = item['label']
        source_url = item['url']
        try:
            source_html = fetch_html(s, source_url)
            mobile_url = resolve_mobile_url(source_url, source_html)
            mobile_html = fetch_html(s, mobile_url)
            result = extract_post_data(mobile_html)
            content_html = result.get('contentHtml', '')
            text = html_to_text(content_html)
            image_urls = extract_image_urls(content_html)
            extracted_links = extract_links(content_html)
        except Exception as e:
            failures.append({
                'label': label,
                'source_url': source_url,
                'error': str(e),
            })
            continue

        text_filename = f'{label}.content.txt'
        html_filename = f'{label}.content.html'
        meta_filename = f'{label}.meta.json'
        (raw_dir / text_filename).write_text(text, encoding='utf-8')
        (raw_dir / html_filename).write_text(content_html, encoding='utf-8')

        ocr_chars = 0
        saved_images = []
        for idx, img_url in enumerate(image_urls, start=1):
            try:
                image_name, ocr_name = save_image_and_ocr(s, img_url, raw_dir, label, idx)
                ocr_text = (raw_dir / ocr_name).read_text(encoding='utf-8')
                ocr_chars += len(ocr_text.strip())
                saved_images.append({'url': img_url, 'image_file': image_name, 'ocr_file': ocr_name})
            except Exception as e:
                saved_images.append({'url': img_url, 'error': str(e)})

        meta = {
            'label': label,
            'source_url': source_url,
            'mobile_url': mobile_url,
            'title': result.get('title', ''),
            'written_at': result.get('writtenAt', ''),
            'author': result.get('writer', {}).get('nickname', ''),
            'recommend_count': result.get('recommendCount', 0),
            'view_count': result.get('viewCount', 0),
            'image_urls': image_urls,
            'extracted_links': extracted_links,
            'saved_images': saved_images,
            'text_filename': text_filename,
            'html_filename': html_filename,
        }
        (raw_dir / meta_filename).write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding='utf-8')

        manifest.append(PostArtifact(
            label=label,
            source_url=source_url,
            mobile_url=mobile_url,
            title=result.get('title', ''),
            written_at=result.get('writtenAt', ''),
            author=result.get('writer', {}).get('nickname', ''),
            recommend_count=int(result.get('recommendCount', 0) or 0),
            view_count=int(result.get('viewCount', 0) or 0),
            image_count=len(image_urls),
            link_count=len(extracted_links),
            ocr_chars=ocr_chars,
            text_filename=text_filename,
            html_filename=html_filename,
            meta_filename=meta_filename,
        ))

    (output_dir / 'manifest.json').write_text(json.dumps([asdict(x) for x in manifest], ensure_ascii=False, indent=2), encoding='utf-8')
    (output_dir / 'failures.json').write_text(json.dumps(failures, ensure_ascii=False, indent=2), encoding='utf-8')
    lines = ['# Naver Board Evidence Manifest', '', '| label | title | time | 추천 | 조회 | 이미지수 | 링크수 | OCR chars | text | html | meta |', '| --- | --- | --- | ---: | ---: | ---: | ---: | ---: | --- | --- | --- |']
    for x in manifest:
        lines.append(f"| {x.label} | {x.title} | {x.written_at} | {x.recommend_count} | {x.view_count} | {x.image_count} | {x.link_count} | {x.ocr_chars} | `{x.text_filename}` | `{x.html_filename}` | `{x.meta_filename}` |")
    if failures:
        lines.extend(['', '## Failures', '', '| label | url | error |', '| --- | --- | --- |'])
        for x in failures:
            lines.append(f"| {x['label']} | {x['source_url']} | {x['error']} |")
    (output_dir / 'manifest.md').write_text('\n'.join(lines) + '\n', encoding='utf-8')
    print(json.dumps({'count': len(manifest), 'failures': len(failures), 'output_dir': str(output_dir)}, ensure_ascii=False))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
