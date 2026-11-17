#!/usr/bin/env python3
"""Download Blogger-hosted images referenced by posts into content/images/.

Idempotent: only URLs missing from content/image_map.json are fetched.
Run by the pages workflow before build.py (needs open internet access).
"""
import concurrent.futures
import glob
import hashlib
import json
import os
import re
import sys
import urllib.request

ROOT = os.path.dirname(os.path.abspath(__file__))
IMG_DIR = os.path.join(ROOT, 'content', 'images')
MAP_FILE = os.path.join(ROOT, 'content', 'image_map.json')
PAT = re.compile(r'https?://blogger\.googleusercontent\.com/[^\s"\'<>)\\]+')
EXT = {'image/png': 'png', 'image/jpeg': 'jpg', 'image/webp': 'webp', 'image/gif': 'gif', 'image/svg+xml': 'svg'}


def collect():
    urls = set()
    for f in glob.glob(os.path.join(ROOT, 'content', 'posts', '**', '*.html'), recursive=True):
        urls.update(PAT.findall(open(f, encoding='utf-8').read()))
    urls.update(PAT.findall(open(os.path.join(ROOT, 'content', 'posts.json'), encoding='utf-8').read()))
    return sorted(urls)


def fetch(url):
    last = None
    for _ in range(3):
        try:
            req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0', 'Accept': 'image/png,image/jpeg,image/gif,*/*;q=0.5'})
            with urllib.request.urlopen(req, timeout=40) as r:
                ctype = r.headers.get('Content-Type', '').split(';')[0].strip().lower()
                data = r.read()
            if ctype not in EXT or len(data) < 50:
                raise ValueError('unexpected response %s (%d bytes)' % (ctype, len(data)))
            base = url.rsplit('/', 1)[-1].split('=')[0]
            base = re.sub(r'\.(png|jpe?g|webp|gif)$', '', base, flags=re.I)
            base = base if re.fullmatch(r'[A-Za-z0-9_-]{3,60}', base) and not base.startswith('AVvX') else ''
            h = hashlib.sha1(url.encode()).hexdigest()[:10]
            name = ('%s-%s' % (base.lower(), h) if base else h) + '.' + EXT[ctype]
            return url, name, data, None
        except Exception as e:  # noqa
            last = e
    return url, None, None, last


def main():
    os.makedirs(IMG_DIR, exist_ok=True)
    mapping = json.load(open(MAP_FILE, encoding='utf-8')) if os.path.exists(MAP_FILE) else {}
    mapping = {u: n for u, n in mapping.items() if os.path.exists(os.path.join(IMG_DIR, n))}
    todo = [u for u in collect() if u not in mapping]
    print('images: %d known, %d to fetch' % (len(mapping), len(todo)))
    failed = 0
    with concurrent.futures.ThreadPoolExecutor(8) as ex:
        for url, name, data, err in ex.map(fetch, todo):
            if err:
                failed += 1
                print('FAILED', url[:110], err, file=sys.stderr)
                continue
            with open(os.path.join(IMG_DIR, name), 'wb') as f:
                f.write(data)
            mapping[url] = name
    json.dump(dict(sorted(mapping.items())), open(MAP_FILE, 'w', encoding='utf-8'), ensure_ascii=False, indent=0)
    total = sum(os.path.getsize(os.path.join(IMG_DIR, n)) for n in set(mapping.values()))
    print('images: %d stored (%.1f MB), %d failed' % (len(mapping), total / 1e6, failed))


if __name__ == '__main__':
    main()
