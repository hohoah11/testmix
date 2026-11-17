#!/usr/bin/env python3
"""Add a new post to content/.

  python3 add_post.py body.html --title "..." --labels "연애,심리" --permalink love-type-test \
      --description "..." [--date 2026-11-17T11:00:00+09:00]
"""
import argparse
import html as H
import json
import os
import re
import shutil
from datetime import datetime, timezone, timedelta

ROOT = os.path.dirname(os.path.abspath(__file__))
ap = argparse.ArgumentParser()
ap.add_argument('body')
ap.add_argument('--title', required=True)
ap.add_argument('--labels', required=True)
ap.add_argument('--permalink', required=True)
ap.add_argument('--description', default='')
ap.add_argument('--date', default='')
a = ap.parse_args()

KST = timezone(timedelta(hours=9))
date = a.date or datetime.now(KST).replace(microsecond=0).isoformat()
ym = date[:4] + '/' + date[5:7]
path = '/%s/%s.html' % (ym, a.permalink)
body_rel = 'content/posts' + path
posts_file = os.path.join(ROOT, 'content', 'posts.json')
data = json.load(open(posts_file, encoding='utf-8'))
if any(p['path'] == path for p in data['posts']):
    raise SystemExit('already exists: ' + path)
content = open(a.body, encoding='utf-8').read()
if '{{IMG_' in content:
    raise SystemExit('unfilled image placeholders in ' + a.body)
os.makedirs(os.path.dirname(os.path.join(ROOT, body_rel)), exist_ok=True)
shutil.copy(a.body, os.path.join(ROOT, body_rel))
m = re.search(r'<img[^>]+src=["\']([^"\']+)', content)
image = m.group(1) if m else ''
text = re.sub(r'<(style|script|noscript|template|svg)\b.*?</\1>', ' ', content, flags=re.S | re.I)
text = re.sub(r'\s+', ' ', H.unescape(re.sub(r'<[^>]+>', ' ', text))).strip()
data['posts'].append({
    'title': a.title.strip(), 'path': path, 'published': date, 'updated': date,
    'labels': [l.strip() for l in a.labels.split(',') if l.strip()],
    'description': a.description.strip(), 'ogImage': image, 'image': image,
    'snippet': text[:150], 'body': body_rel,
})
json.dump(data, open(posts_file, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
print('added', path)
