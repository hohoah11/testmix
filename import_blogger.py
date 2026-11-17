#!/usr/bin/env python3
"""One-time import: blogger-export.json -> content/ and theme/ (run once at migration)."""
import json, re, os, sys, base64, hashlib

ROOT = os.path.dirname(os.path.abspath(__file__))
SRC = sys.argv[1] if len(sys.argv) > 1 else os.path.join(ROOT, 'blogger-export.json')
ORIGIN = 'https://testmix.infopick.co.kr'

d = json.load(open(SRC, encoding='utf-8'))
os.makedirs(os.path.join(ROOT, 'content', 'thumbs'), exist_ok=True)
os.makedirs(os.path.join(ROOT, 'theme'), exist_ok=True)


def upgrade(url):
    if not url or url.startswith('data:'):
        return url
    url = re.sub(r'/s\d+(-c)?/', '/s900/', url, count=1)
    url = re.sub(r'=s\d+(-c)?$', '=s900', url)
    return url


def image_from_html(html):
    m = re.search(r'<img[^>]+(?:src|data-src)=["\']([^"\']+)', html)
    if m and m.group(1).strip():
        return m.group(1).split()[0]
    m = re.search(r'url\(\s*(["\']?)(data:image/[^"\')\s]+|https?://[^"\')\s]+)\1\s*\)', html)
    if m:
        return m.group(2)
    m = re.search(r'data:image/(?:webp|png|jpe?g|gif);base64,[A-Za-z0-9+/=]+', html)
    if m:
        return m.group(0)
    m = re.search(r'https?://[^"\'<>\s]+\.(?:webp|png|jpe?g|gif)(?:\?[^"\'<>\s]*)?', html)
    return m.group(0) if m else ''


def text_only(html):
    html = re.sub(r'<(style|script|noscript|template|svg)\b.*?</\1>', ' ', html, flags=re.S | re.I)
    html = re.sub(r'<[^>]+>', ' ', html)
    import html as H
    return re.sub(r'\s+', ' ', H.unescape(html)).strip()


posts = []
for p in d['posts']:
    path = p['path']
    slug = path.strip('/').replace('/', '-').replace('.html', '')
    body_rel = 'content/posts' + path
    os.makedirs(os.path.dirname(os.path.join(ROOT, body_rel)), exist_ok=True)
    open(os.path.join(ROOT, body_rel), 'w', encoding='utf-8', newline='').write(p['content'])
    img = upgrade(p.get('thumb') or '') or image_from_html(p['content'])
    if img.startswith('data:'):
        m = re.match(r'data:image/(\w+);base64,(.*)', img, flags=re.S)
        ext = {'jpeg': 'jpg'}.get(m.group(1), m.group(1))
        raw = base64.b64decode(m.group(2))
        name = slug + '.' + ext
        open(os.path.join(ROOT, 'content', 'thumbs', name), 'wb').write(raw)
        img = '/assets/thumbs/' + name
    meta = p.get('meta') or {}
    posts.append({
        'title': p['title'].strip(),
        'path': path,
        'published': p['published'],
        'updated': p['updated'],
        'labels': p['labels'],
        'description': (meta.get('desc') or '').strip(),
        'ogImage': meta.get('ogImage') or '',
        'image': img,
        'snippet': text_only(p['content'])[:150],
        'body': body_rel,
    })

json.dump({'posts': posts}, open(os.path.join(ROOT, 'content', 'posts.json'), 'w', encoding='utf-8'),
          ensure_ascii=False, indent=1)

# ---- theme pieces from the live Blogger theme ----
home = d['home']['body']
styles = re.findall(r'<style[^>]*>(.*?)</style>', home, flags=re.S)
fonts_css = styles[0]
skin = styles[1].strip()
skin = re.sub(r'^<!--', '', skin)
skin = re.sub(r'-->$', '', skin)
open(os.path.join(ROOT, 'theme', 'site.css'), 'w', encoding='utf-8').write(fonts_css.strip() + '\n' + skin.strip() + '\n')

a = home.find("<header class='pm-site-header'>")
b = home.find("<main class='pm-home-main'")
open(os.path.join(ROOT, 'theme', 'chrome.html'), 'w', encoding='utf-8').write(home[a:b])
a = home.find("<main class='pm-home-main'")
b = home.find('</main>', a) + len('</main>')
open(os.path.join(ROOT, 'theme', 'home_main.html'), 'w', encoding='utf-8').write(home[a:b])
a = home.find("<footer class='pm-site-footer'>")
b = home.find('</footer>', a) + len('</footer>')
open(os.path.join(ROOT, 'theme', 'footer.html'), 'w', encoding='utf-8').write(home[a:b])
m = re.search(r"<meta content='([^']*)' name='description'/>", home)
json.dump({'title': '테스트믹스', 'description': m.group(1) if m else '', 'origin': ORIGIN,
           'adClient': 'ca-pub-2087628123837294', 'adSlots': ['4528552263', '2409550185'],
           'menuLabels': ['성격', '연애', '심리', '사회성향', '운세', '게임'], 'readingLabel': '읽을거리'},
          open(os.path.join(ROOT, 'theme', 'site.json'), 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
print('imported', len(posts), 'posts')
