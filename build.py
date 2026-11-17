#!/usr/bin/env python3
"""Static site generator for testmix.infopick.co.kr (GitHub Pages).

Usage:
  python3 build.py                 # production build (site at domain root)
  python3 build.py --base /testmix # preview build under https://<user>.github.io/testmix/

Input : content/posts.json, content/posts/**.html, content/thumbs/*, theme/*
Output: docs/
"""
import argparse
import html
import json
import os
import re
import shutil
from datetime import datetime
from urllib.parse import quote

ROOT = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(ROOT, 'docs')

ap = argparse.ArgumentParser()
ap.add_argument('--base', default='', help='URL path prefix, e.g. /testmix (empty for custom domain)')
args = ap.parse_args()
BASE = args.base.rstrip('/')
PREVIEW = bool(BASE)

site = json.load(open(os.path.join(ROOT, 'theme', 'site.json'), encoding='utf-8'))
ORIGIN = site['origin']
posts = json.load(open(os.path.join(ROOT, 'content', 'posts.json'), encoding='utf-8'))['posts']
posts.sort(key=lambda p: datetime.fromisoformat(p['published']), reverse=True)

# Images copied from Blogger into the repository (see fetch_images.py)
IMG_MAP_FILE = os.path.join(ROOT, 'content', 'image_map.json')
IMG_MAP = json.load(open(IMG_MAP_FILE, encoding='utf-8')) if os.path.exists(IMG_MAP_FILE) else {}
IMG_PAT = re.compile(r'https?://blogger\.googleusercontent\.com/[^\s"\'<>)\\]+')


def local_images(text):
    """Point Blogger image URLs at the copies served from this site (absolute URLs)."""
    return IMG_PAT.sub(lambda m: ORIGIN + '/assets/img/' + IMG_MAP[m.group(0)] if m.group(0) in IMG_MAP else m.group(0), text)


for _p in posts:
    if _p['image'] in IMG_MAP:
        _p['image'] = '/assets/img/' + IMG_MAP[_p['image']]
    _p['ogImage'] = local_images(_p['ogImage'])

esc = lambda s: html.escape(s or '', quote=True)


def read(rel):
    return open(os.path.join(ROOT, rel), encoding='utf-8').read()


def write(rel, text):
    path = os.path.join(OUT, rel.lstrip('/'))
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, 'w', encoding='utf-8', newline='') as f:
        f.write(text)


def url(path):
    """Site-internal URL for links."""
    return BASE + path


def label_url(label):
    return url('/search/label/' + quote(label) + '/')


def img_url(src):
    return url(src) if src.startswith('/') else src


def localize(fragment):
    """Rewrite absolute live-site links in theme fragments to site-internal links."""
    def rep(m):
        attr, path = m.group(1), m.group(2)
        if path.startswith('feeds/'):
            return m.group(0)
        if path.startswith('search/label/'):
            return "%s='%s'" % (attr, label_url(path[len('search/label/'):]))
        if path == 'search':
            return "%s='%s'" % (attr, url('/search/'))
        return "%s='%s'" % (attr, url('/' + path))
    return re.sub(r"(href|action|data-home)='" + re.escape(ORIGIN) + r"/([^']*)'", rep, fragment)


def rebase_body(body):
    """Preview only: root-relative links inside post bodies need the path prefix."""
    if not BASE:
        return body
    return re.sub(r'((?:href|src)=)(["\'])/(?!/)', lambda m: m.group(1) + m.group(2) + BASE + '/', body)


def kdate(iso):
    y, m, d = iso[:10].split('-')
    return '%d월 %s, %s' % (int(m), d, y)


CHROME = localize(read('theme/chrome.html'))
# The reading-list feed loader has no feed on a static host; the list is rendered at build time.
CHROME = re.sub(r" data-feed='[^']*'", '', CHROME)
FOOTER = read('theme/footer.html').replace(
    "<!--Can't find substitution for tag [blog.description]-->", esc(site['description']))

AD_SCRIPT = ('<script async src="https://pagead2.googlesyndication.com/pagead/js/adsbygoogle.js?client=%s" '
             'crossorigin="anonymous"></script>' % site['adClient'])


def ad_unit(slot):
    return ('<div class="widget AdSense"><div class="widget-content">'
            '<ins class="adsbygoogle" style="display:block" data-ad-client="%s" data-ad-slot="%s" '
            'data-ad-format="auto" data-full-width-responsive="true"></ins>'
            '<script>(adsbygoogle = window.adsbygoogle || []).push({});</script></div></div>'
            % (site['adClient'], slot))


ADS_COLUMN = "<div><div class='vertical-ad-container section' id='ads'>%s</div>" % ''.join(
    ad_unit(s) for s in site['adSlots'])


def reading_links():
    items = [p for p in posts if site['readingLabel'] in p['labels']][:4]
    out = []
    for p in items:
        t = re.sub(r'\s+', ' ', p['title']).strip()
        short = t[:24] + '…' if len(t) > 24 else t
        out.append("<a href='%s' title='%s'>%s</a>" % (url(p['path']), esc(t), esc(short)))
    return ''.join(out)


CHROME = CHROME.replace("id='pm-drawer-reading-posts'></div>",
                        "id='pm-drawer-reading-posts'>%s</div>" % reading_links())


def page(*, body_class, title, description, canonical, main, og_image='', og_type='website', extra_head=''):
    robots = '<meta name="robots" content="noindex">\n' if PREVIEW else ''
    og_img = '<meta property="og:image" content="%s">\n' % esc(og_image) if og_image else ''
    return '''<!DOCTYPE html>
<html dir="ltr" lang="ko">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>%(title)s</title>
<meta name="description" content="%(desc)s">
%(robots)s<link rel="canonical" href="%(canonical)s">
<meta property="og:type" content="%(og_type)s">
<meta property="og:site_name" content="%(site)s">
<meta property="og:url" content="%(canonical)s">
<meta property="og:title" content="%(title)s">
<meta property="og:description" content="%(desc)s">
%(og_img)s<meta name="twitter:card" content="summary_large_image">
<meta name="theme-color" content="#eeeeee">
<link rel="icon" href="%(base)s/favicon.svg" type="image/svg+xml">
<link rel="alternate" type="application/rss+xml" title="%(site)s" href="%(base)s/rss.xml">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Jua&amp;display=swap">
<link rel="stylesheet" href="%(base)s/assets/site.css">
%(ad)s
%(extra)s</head>
<body class="%(cls)s version-1-3-3">
<a class="skip-navigation" href="#main" tabindex="0">기본 콘텐츠로 건너뛰기</a>
%(chrome)s
%(main)s
%(footer)s
<script src="%(base)s/assets/site.js"></script>
</body>
</html>
''' % dict(title=esc(title), desc=esc(description), robots=robots, canonical=esc(canonical), og_type=og_type,
           site=esc(site['title']), og_img=og_img, base=BASE, ad=AD_SCRIPT, extra=extra_head, cls=body_class,
           chrome=CHROME, main=main, footer=FOOTER)


def card(p, badge=''):
    img = ("<img loading='lazy' alt='' src='%s'/>" % esc(img_url(p['image']))) if p['image'] \
        else "<div class='pm-card-placeholder'>&#10022;</div>"
    b = "<span class='pm-card-badge'>%s</span>" % badge if badge else ''
    return ("<article class='pm-card'><a class='pm-card-link' href='%s'><div class='pm-card-thumb'>%s%s</div>"
            "<h3 class='pm-card-title'>%s</h3><div class='pm-card-meta'>%s</div></a></article>"
            % (url(p['path']), img, b, esc(p['title']), esc(p['labels'][0] if p['labels'] else '새 콘텐츠')))


def editorial_card(p):
    img = ("<img loading='lazy' alt='' src='%s'/>" % esc(img_url(p['image']))) if p['image'] \
        else "<div class='pm-editorial-placeholder'>읽</div>"
    topic = ([l for l in p['labels'] if l != site['readingLabel']] or [site['readingLabel']])[0]
    return ("<article class='pm-editorial-card'><a class='pm-editorial-link' href='%s'><div class='pm-editorial-thumb'>%s</div>"
            "<div class='pm-editorial-copy'><span class='pm-editorial-kicker'>%s</span><h3 class='pm-editorial-title'>%s</h3>"
            "<p class='pm-editorial-desc'>%s</p></div></a></article>"
            % (url(p['path']), img, esc(topic), esc(p['title']),
               esc(p['description'] or p['snippet'] or '성향과 심리에 관한 이야기를 읽어보세요.')))


def list_card(p):
    img = ("<img loading='lazy' alt='' src='%s'/>" % esc(img_url(p['image']))) if p['image'] \
        else "<span class='pm-list-placeholder'>&#10022;</span>"
    search = esc((p['title'] + ' ' + p['description'] + ' ' + ' '.join(p['labels'])).lower())
    return ("<div class='post-outer-container pm-list-card pm-generated-card' data-search='%s'><div class='post-outer'>"
            "<a class='pm-list-thumb' href='%s' aria-label='%s'>%s</a>"
            "<div class='post-content container'><div class='post-title-container'><h3 class='post-title'>"
            "<a href='%s'>%s</a></h3></div></div></div></div>"
            % (search, url(p['path']), esc(p['title']), img, url(p['path']), esc(p['title'])))


# ---------------------------------------------------------------- home
def build_home():
    main = localize(read('theme/home_main.html'))
    slides, dots = [], []
    for i, p in enumerate(posts[:5]):
        media = ("<img alt='' loading='%s' src='%s'/>" % ('eager' if i == 0 else 'lazy', esc(img_url(p['image'])))) \
            if p['image'] else "<div class='pm-hero-placeholder'></div>"
        slides.append(
            "<a class='pm-hero-slide%s' href='%s' aria-hidden='%s' tabindex='%s'><div class='pm-hero-copy'>"
            "<span class='pm-hero-eyebrow'>%s</span><h2 class='pm-hero-title'>%s</h2><p class='pm-hero-desc'>%s</p>"
            "<span class='pm-hero-cta'>바로 보기 &#8594;</span></div><div class='pm-hero-media'>%s</div></a>"
            % (' pm-active' if i == 0 else '', url(p['path']), 'false' if i == 0 else 'true', '0' if i == 0 else '-1',
               esc(p['labels'][0] if p['labels'] else '추천 콘텐츠'), esc(p['title']),
               esc(p['snippet'] or '지금 가장 먼저 확인해 보세요.'), media))
        dots.append("<button type='button' class='pm-hero-dot%s' aria-label='%d번 슬라이드'%s></button>"
                    % (' pm-active' if i == 0 else '', i + 1, " aria-current='true'" if i == 0 else ''))
    main = main.replace("<div class='pm-loading'>콘텐츠를 불러오는 중입니다.</div>", ''.join(slides))
    main = main.replace("id='pm-hero-dots' role='group'></div>", "id='pm-hero-dots' role='group'>%s</div>" % ''.join(dots))
    main = main.replace("id='pm-new-content'></div>",
                        "id='pm-new-content'>%s</div>" % ''.join(card(p, 'NEW') for p in posts[:12]))
    reading = [p for p in posts if site['readingLabel'] in p['labels']][:3]
    if reading:
        main = main.replace("id='pm-popular-content'></div>",
                            "id='pm-popular-content'>%s</div>" % ''.join(editorial_card(p) for p in reading))
    else:
        main = main.replace("<section class='pm-content-section pm-editorial-section' id='pm-popular-section'>",
                            "<section class='pm-content-section pm-editorial-section' id='pm-popular-section' hidden='hidden'>")

    def fill(m):
        label = m.group(2)
        items = [p for p in posts if label in p['labels']][:8]
        return m.group(1) + ''.join(card(p) for p in items) + '</div>', bool(items)

    def section(m):
        block = m.group(0)
        t = re.search(r"(<div class='pm-card-grid pm-category-target' data-label='([^']+)' id='[^']+'>)</div>", block)
        if not t:
            return block
        filled, ok = fill(t)
        block = block.replace(t.group(0), filled)
        if not ok:
            block = block.replace("<section class='pm-content-section pm-label-collection'>",
                                  "<section class='pm-content-section pm-label-collection' hidden='hidden'>")
        return block
    main = re.sub(r"<section class='pm-content-section pm-label-collection'>.*?</section>", section, main, flags=re.S)
    ld = json.dumps({'@context': 'https://schema.org', '@type': 'WebSite', 'name': site['title'],
                     'url': ORIGIN + '/', 'description': site['description']}, ensure_ascii=False)
    write('/index.html', page(body_class='pm-home-view', title=site['title'], description=site['description'],
                              canonical=ORIGIN + '/', main=main, og_image=posts[0]['ogImage'],
                              extra_head="<script type='application/ld+json'>%s</script>\n" % ld))


# ---------------------------------------------------------------- post
def build_post(p):
    body = local_images(rebase_body(read(p['body'])))
    canonical = ORIGIN + p['path']
    desc = p['description'] or p['snippet']
    ld = {'@context': 'https://schema.org', '@type': 'BlogPosting',
          'mainEntityOfPage': {'@type': 'WebPage', '@id': canonical},
          'headline': p['title'], 'description': desc,
          'datePublished': p['published'], 'dateModified': p['updated'],
          'author': {'@type': 'Organization', 'name': site['title']},
          'publisher': {'@type': 'Organization', 'name': site['title']}}
    if p['ogImage']:
        ld['image'] = {'@type': 'ImageObject', 'url': p['ogImage'], 'width': 1200, 'height': 630}
    labels = ''.join("<a href='%s' rel='tag'>%s</a>\n" % (label_url(l), esc(l)) for l in p['labels'])
    related = [q for q in posts if q is not p and set(q['labels']) & set(p['labels'])][:4]
    if len(related) < 4:
        related += [q for q in posts if q is not p and q not in related][:4 - len(related)]
    main = '''<div class='page'>
<div class='page_body has-vertical-ads'>
<div class='centered'>
%(ads)s
<main class='centered-bottom' id='main' role='main' tabindex='-1'>
<div class='main section' id='page_body'>
<div class='widget Blog' data-version='2' id='Blog1'>
<div class='blog-posts hfeed container'>
<article class='post-outer-container'>
<div class='post-outer'>
<div class='post'>
<script type='application/ld+json'>%(ld)s</script>
<h3 class='post-title entry-title'>
%(title)s
</h3>
<div class='post-header'>
<div class='post-header-line-1'>
<span class='byline post-timestamp'>
-
<a class='timestamp-link' href='%(self)s' rel='bookmark' title='permanent link'>
<time class='published' datetime='%(pub)s' title='%(pub)s'>
%(date)s
</time>
</a>
</span>
</div>
</div>
<div class='post-body entry-content float-container' id='post-body'>
%(body)s
</div>
<div class='post-bottom'>
<div class='post-footer float-container'>
<div class='post-footer-line post-footer-line-2'>
<span class='byline post-labels'>
<span class='byline-label'>
</span>
%(labels)s</span>
</div>
</div>
</div>
</div>
</div>
</article>
</div>
</div>
<section class='pm-content-section tm-related'>
<div class='pm-section-head'><div><h2 class='pm-section-title'>다른 테스트도 해 보세요</h2></div><a class='pm-section-more' href='%(all)s'>전체 보기 &#8594;</a></div>
<div class='pm-card-grid'>%(related)s</div>
</section>
</div>
</main>
</div>
</div>
</div>
</div>''' % dict(ads=ADS_COLUMN, ld=json.dumps(ld, ensure_ascii=False).replace('</', '<\\/'), title=esc(p['title']),
                 self=url(p['path']), pub=p['published'], date=kdate(p['published']), body=body, labels=labels,
                 all=url('/search/'), related=''.join(card(q) for q in related))
    write(p['path'], page(body_class='item-view', title=p['title'], description=desc, canonical=canonical,
                          main=main, og_image=p['ogImage'], og_type='article'))


# ---------------------------------------------------------------- lists
def list_page(rel, *, body_class, title, description, canonical, items, message, searchable=False):
    grid = ''.join(list_card(p) for p in items) or "<div class='no-posts-message'>게시물이 없습니다.</div>"
    msg = ('''<div class='post-filter-message'%s>
<div>%s</div>
<div><a class='flat-button ripple' href='%s'>전체 보기</a></div>
</div>''' % (" id='tm-filter-message'" if searchable else '', message, url('/'))) if (message or searchable) else ''
    if searchable and not message:
        msg = msg.replace("<div class='post-filter-message'", "<div class='post-filter-message' hidden='hidden'")
    main = '''<div class='page'>
<div class='page_body has-vertical-ads'>
<div class='centered'>
%s
<main class='centered-bottom' id='main' role='main' tabindex='-1'>
<h2 class='main-heading'>글</h2>
%s
<div class='main section' id='page_body'>
<div class='widget Blog' data-version='2' id='Blog1'>
<div class='blog-posts hfeed container pm-list-grid'%s>
%s
</div>
</div>
</div>
</main>
</div>
</div>
</div>
</div>''' % (ADS_COLUMN, msg, " id='tm-search-grid'" if searchable else '', grid)
    write(rel, page(body_class=body_class, title=title, description=description, canonical=canonical, main=main))


def build_lists():
    labels = list(site['menuLabels']) + [site['readingLabel']]
    for p in posts:
        for l in p['labels']:
            if l not in labels:
                labels.append(l)
    for l in labels:
        list_page('/search/label/%s/index.html' % l, body_class='label-view', title='%s - %s' % (l, site['title']),
                  description='%s 테스트 모음 - %s' % (l, site['title']),
                  canonical=ORIGIN + '/search/label/' + quote(l),
                  items=[p for p in posts if l in p['labels']],
                  message="라벨이 <span class='search-label'>%s</span>인 게시물 표시" % esc(l))
    list_page('/search/index.html', body_class='search-view', title='전체 콘텐츠 - ' + site['title'],
              description=site['description'], canonical=ORIGIN + '/search', items=posts, message='', searchable=True)
    months = {}
    for p in posts:
        months.setdefault(p['path'][1:8], []).append(p)
    for ym, items in months.items():
        y, m = ym.split('/')
        list_page('/%s/index.html' % ym, body_class='archive-view', title='%s년 %d월 - %s' % (y, int(m), site['title']),
                  description=site['description'], canonical='%s/%s/' % (ORIGIN, ym), items=items,
                  message='%s년 %d월 게시물 표시' % (y, int(m)))
    years = {}
    for p in posts:
        years.setdefault(p['path'][1:5], []).append(p)
    for y, items in years.items():
        list_page('/%s/index.html' % y, body_class='archive-view', title='%s년 - %s' % (y, site['title']),
                  description=site['description'], canonical='%s/%s/' % (ORIGIN, y), items=items,
                  message='%s년 게시물 표시' % y)


# ---------------------------------------------------------------- misc files
SITE_JS = r'''(function(){
'use strict';
var body=document.body;
var menuToggle=document.querySelector('.pm-menu-toggle');
var menuClose=document.querySelector('.pm-menu-close');
var drawer=document.querySelector('.pm-mobile-drawer');
var backdrop=document.querySelector('.pm-drawer-backdrop');
var searchToggle=document.querySelector('.pm-search-toggle');
var searchLayer=document.querySelector('.pm-search-layer');
var searchInput=document.querySelector('.pm-search-input');
function openMenu(){body.classList.add('pm-menu-open');if(menuToggle)menuToggle.setAttribute('aria-expanded','true');if(drawer){drawer.removeAttribute('inert');drawer.setAttribute('aria-hidden','false');}setTimeout(function(){if(menuClose)menuClose.focus();},50);}
function closeMenu(){body.classList.remove('pm-menu-open');if(menuToggle)menuToggle.setAttribute('aria-expanded','false');if(drawer){drawer.setAttribute('aria-hidden','true');drawer.setAttribute('inert','inert');}}
function openSearch(){if(!searchLayer)return;searchLayer.hidden=false;searchLayer.classList.add('pm-open');if(searchToggle)searchToggle.setAttribute('aria-expanded','true');setTimeout(function(){if(searchInput)searchInput.focus();},80);}
function closeSearch(){if(!searchLayer)return;searchLayer.classList.remove('pm-open');searchLayer.hidden=true;if(searchToggle)searchToggle.setAttribute('aria-expanded','false');}
if(menuToggle)menuToggle.addEventListener('click',openMenu);
if(menuClose)menuClose.addEventListener('click',closeMenu);
if(backdrop)backdrop.addEventListener('click',closeMenu);
Array.prototype.forEach.call(document.querySelectorAll('.pm-drawer-nav a'),function(a){a.addEventListener('click',closeMenu);});
if(searchToggle)searchToggle.addEventListener('click',openSearch);
if(searchLayer)searchLayer.addEventListener('click',function(e){if(e.target===searchLayer)closeSearch();});
document.addEventListener('keydown',function(e){if(e.key==='Escape'){closeMenu();closeSearch();}});
var year=document.getElementById('pm-copy-year');if(year)year.textContent=new Date().getFullYear();

/* hero slider (slides are rendered at build time) */
var slider=document.getElementById('pm-hero-slider');
if(slider){
  var slides=Array.prototype.slice.call(slider.querySelectorAll('.pm-hero-slide'));
  var buttons=Array.prototype.slice.call(document.querySelectorAll('#pm-hero-dots .pm-hero-dot'));
  var current=0,timer=null;
  var show=function(index,reset){
    slides[current].classList.remove('pm-active');slides[current].setAttribute('aria-hidden','true');slides[current].tabIndex=-1;
    if(buttons[current]){buttons[current].classList.remove('pm-active');buttons[current].removeAttribute('aria-current');}
    current=index;
    slides[current].classList.add('pm-active');slides[current].setAttribute('aria-hidden','false');slides[current].tabIndex=0;
    if(buttons[current]){buttons[current].classList.add('pm-active');buttons[current].setAttribute('aria-current','true');}
    if(reset)start();
  };
  var start=function(){if(timer)clearInterval(timer);if(slides.length<2||window.matchMedia('(prefers-reduced-motion: reduce)').matches)return;timer=setInterval(function(){show((current+1)%slides.length,false);},5200);};
  buttons.forEach(function(dot,index){dot.addEventListener('click',function(){show(index,true);});});
  slider.addEventListener('mouseenter',function(){if(timer)clearInterval(timer);});
  slider.addEventListener('mouseleave',start);
  if(slides.length)start();
}

/* search page: filter cards by ?q= */
var grid=document.getElementById('tm-search-grid');
if(grid){
  var q=(new URLSearchParams(location.search).get('q')||'').trim();
  if(q){
    var words=q.toLowerCase().split(/\s+/);var shown=0;
    Array.prototype.forEach.call(grid.querySelectorAll('.pm-list-card'),function(card){
      var text=card.getAttribute('data-search')||'';
      var ok=words.every(function(w){return text.indexOf(w)!==-1;});
      card.hidden=!ok;if(ok)shown++;
    });
    var msg=document.getElementById('tm-filter-message');
    if(msg){msg.hidden=false;var first=msg.querySelector('div');if(first){first.textContent='';var s=document.createElement('span');s.className='search-query';s.textContent=q;first.appendChild(document.createTextNode('검색어 '));first.appendChild(s);first.appendChild(document.createTextNode('와 일치하는 게시물 표시'));}}
    if(!shown){var none=document.createElement('div');none.className='no-posts-message';none.textContent='검색 결과가 없습니다.';grid.appendChild(none);}
    if(searchInput)searchInput.value=q;
  }
}
}());
'''

EXTRA_CSS = '''
/* ---- static site additions ---- */
.pm-list-card[hidden]{display:none!important}
ins.adsbygoogle[data-ad-status="unfilled"]{display:none!important}
.tm-related{margin-top:44px}
@media(max-width:1100px){
.vertical-ad-container{display:none}
.page_body.has-vertical-ads .centered .centered-bottom{display:block;width:100%}
}
'''

FAVICON = '''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 64 64"><defs><linearGradient id="g" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="#5746e8"/><stop offset=".5" stop-color="#8e4edb"/><stop offset="1" stop-color="#e35b9a"/></linearGradient></defs><rect width="64" height="64" rx="16" fill="url(#g)"/><path fill="#fff" d="M32 10c2.4 12.2 7.8 17.6 20 20-12.2 2.4-17.6 7.8-20 20-2.4-12.2-7.8-17.6-20-20 12.2-2.4 17.6-7.8 20-20z"/></svg>
'''


def build_misc():
    write('/assets/site.css', read('theme/site.css') + EXTRA_CSS)
    write('/assets/site.js', SITE_JS)
    write('/favicon.svg', FAVICON)
    write('/.nojekyll', '')
    tdir = os.path.join(ROOT, 'content', 'thumbs')
    os.makedirs(os.path.join(OUT, 'assets', 'thumbs'), exist_ok=True)
    for f in os.listdir(tdir):
        shutil.copy(os.path.join(tdir, f), os.path.join(OUT, 'assets', 'thumbs', f))
    idir = os.path.join(ROOT, 'content', 'images')
    os.makedirs(os.path.join(OUT, 'assets', 'img'), exist_ok=True)
    for f in set(IMG_MAP.values()):
        if os.path.exists(os.path.join(idir, f)):
            shutil.copy(os.path.join(idir, f), os.path.join(OUT, 'assets', 'img', f))
    write('/ads.txt', 'google.com, %s, DIRECT, f08c47fec0942fa0\n' % site['adClient'].replace('ca-', ''))
    if PREVIEW:
        write('/robots.txt', 'User-agent: *\nDisallow: /\n')
    else:
        write('/robots.txt', 'User-agent: Mediapartners-Google\nDisallow: \n\nUser-agent: *\nDisallow: /search\nAllow: /\n\n'
                             'Sitemap: %s/sitemap.xml\n' % ORIGIN)
        write('/CNAME', ORIGIN.split('//')[1] + '\n')
    urls = ['<url><loc>%s/</loc></url>' % ORIGIN]
    urls += ['<url><loc>%s%s</loc><lastmod>%s</lastmod></url>' % (ORIGIN, p['path'], p['updated']) for p in posts]
    write('/sitemap.xml', "<?xml version='1.0' encoding='UTF-8'?>\n<urlset xmlns=\"http://www.sitemaps.org/schemas/sitemap/0.9\">\n%s\n</urlset>\n"
          % '\n'.join(urls))
    items = ''.join('<item><title>%s</title><link>%s%s</link><guid>%s%s</guid><pubDate>%s</pubDate><description>%s</description></item>\n'
                    % (esc(p['title']), ORIGIN, p['path'], ORIGIN, p['path'], rfc822(p['published']),
                       esc(p['description'] or p['snippet'])) for p in posts)
    write('/rss.xml', '<?xml version="1.0" encoding="UTF-8"?>\n<rss version="2.0"><channel><title>%s</title><link>%s/</link>'
                      '<description>%s</description><language>ko</language>\n%s</channel></rss>\n'
          % (esc(site['title']), ORIGIN, esc(site['description']), items))
    nf = '''<div class='page'><div class='page_body'><div class='centered'>
<main class='centered-bottom' id='main' role='main' tabindex='-1'>
<div class='post-filter-message'><div>찾으시는 페이지가 없습니다.</div><div><a class='flat-button ripple' href='%s'>홈으로</a></div></div>
</main></div></div></div>''' % url('/')
    write('/404.html', page(body_class='error-view', title='페이지를 찾을 수 없습니다 - ' + site['title'],
                            description=site['description'], canonical=ORIGIN + '/', main=nf))


def rfc822(iso):
    return datetime.fromisoformat(iso).strftime('%a, %d %b %Y %H:%M:%S %z')


if os.path.isdir(OUT):
    shutil.rmtree(OUT)
os.makedirs(OUT)
build_home()
for p in posts:
    build_post(p)
build_lists()
build_misc()
n = sum(len(f) for _, _, f in os.walk(OUT))
print('built %d posts, %d files -> docs/ (base=%r)' % (len(posts), n, BASE))
