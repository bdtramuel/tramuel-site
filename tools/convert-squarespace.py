"""Convert a Squarespace WordPress export into Hugo content for tramuel.com.

Usage: python3 -I convert.py EXPORT.xml SITE_DIR
Writes SITE_DIR/content/... and SITE_DIR/tools/image-manifest.json
"""
import sys, re, os, html, json, collections, datetime
from zoneinfo import ZoneInfo
from lxml import etree
import yaml
from bs4 import BeautifulSoup, Comment
from markdownify import MarkdownConverter

EXPORT, SITE = sys.argv[1], sys.argv[2]
CONTENT = os.path.join(SITE, 'content')
ET = ZoneInfo('America/New_York')
NS = {'wp': 'http://wordpress.org/export/1.2/',
      'content': 'http://purl.org/rss/1.0/modules/content/',
      'excerpt': 'http://wordpress.org/export/1.2/excerpt/'}

tree = etree.parse(EXPORT, etree.XMLParser(huge_tree=True, recover=True))
items = tree.findall('.//item')
def g(it, path):
    e = it.find(path, NS)
    return (e.text or '') if e is not None else ''

# ---------- helpers ----------
def norm_url(u):
    u = html.unescape((u or '').strip())
    if u.startswith('//'): u = 'https:' + u
    if u.startswith('http://'): u = 'https://' + u[7:]
    return u

def is_sqs(u): return 'squarespace' in u

def base(u):  # strip query string from Squarespace image URLs
    return u.split('?')[0] if is_sqs(u) else u

def shown(u, fmt='1500w'):
    return f"{base(u)}?format={fmt}" if is_sqs(u) else u

class MD(MarkdownConverter):
    def convert_img(self, el, text, parent_tags=None, **kw):
        src = norm_url(el.get('src') or '')
        if not src: return ''
        alt = html.unescape(el.get('alt') or '').replace('\u00a0', ' ').replace('[', '').replace(']', '')
        alt = re.sub(r'\s+', ' ', alt).strip()
        # Squarespace sometimes stores the filename as alt text; drop those
        if re.fullmatch(r'[\w\-\+\.]+\.(jpe?g|png|gif|webp|heic)', alt, re.I) or alt.startswith('image-asset'):
            alt = ''
        return f'![{alt}]({shown(src)})'

def to_markdown(raw):
    soup = BeautifulSoup(raw or '', 'html.parser')
    for c in soup.find_all(string=lambda s: isinstance(s, Comment)): c.extract()
    for t in soup.find_all(['script', 'style', 'noscript']): t.decompose()
    for t in soup.find_all(lambda t: ':' in t.name or t.name in ('xml',)): t.unwrap()
    # Old email-forward posts use tables for layout. Flatten those into plain blocks;
    # keep small text grids as Markdown tables.
    def is_layout(tb):
        return (tb.find('table') is not None or tb.find('img') is not None
                or any(len(c.get_text(strip=True)) > 120 for c in tb.find_all(['td', 'th'])))
    while True:
        tb = soup.find(lambda x: x.name == 'table' and is_layout(x))
        if tb is None: break
        for c in tb.find_all(['td', 'th']): c.name = 'div'
        for c in tb.find_all(['tr', 'tbody', 'thead', 'tfoot', 'table']): c.unwrap()
        tb.unwrap()
    embeds = []
    for f in soup.find_all('iframe'):
        src = norm_url(f.get('src') or '')
        m = re.search(r'youtube(?:-nocookie)?\.com/embed/([\w\-]{6,})', src)
        v = re.search(r'player\.vimeo\.com/video/(\d+)', src)
        if m: code = '{{< youtube %s >}}' % m.group(1)
        elif v: code = '{{< vimeo %s >}}' % v.group(1)
        elif src: code = f'<iframe src="{src}" width="100%" height="400" frameborder="0" allowfullscreen loading="lazy"></iframe>'
        else: code = ''
        token = f'EMBEDTOKEN{len(embeds)}X'
        embeds.append(code)
        p = soup.new_tag('p'); p.string = token
        f.replace_with(p)
    md = MD(heading_style='ATX', bullets='-', strip=['span', 'font', 'big', 'u']).convert_soup(soup)
    for i, code in enumerate(embeds):
        md = md.replace(f'EMBEDTOKEN{i}X', code)
    md = md.replace(' ', ' ')
    md = re.sub(r'[ \t]+\n', lambda m: '  \n' if m.group(0).startswith('  ') else '\n', md)
    md = re.sub(r'\n{3,}', '\n\n', md).strip()
    return md + '\n'

def plain(raw):
    t = BeautifulSoup(raw or '', 'html.parser').get_text(' ')
    return re.sub(r'\s+', ' ', html.unescape(t)).strip()

def clip(text, n=300):
    if len(text) <= n: return text
    cut = text[:n].rsplit(' ', 1)[0]
    return cut.rstrip(',;:') + '…'

def et_date(s):
    d = datetime.datetime.strptime(s.strip(), '%Y-%m-%d %H:%M:%S').replace(tzinfo=datetime.timezone.utc)
    return d.astimezone(ET).isoformat()

def front(fm, body):
    y = yaml.safe_dump(fm, allow_unicode=True, sort_keys=False, width=1000)
    return f'---\n{y}---\n\n{body}'

def write(path, text):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, 'w', encoding='utf-8') as fh: fh.write(text)

def imgs_in(raw):
    return [norm_url(m) for m in re.findall(r'<img[^>]+src="([^"]+)"', raw or '')]

# ---------- attachments (Squarespace thumbnails) ----------
attachments = {g(it, 'wp:post_id'): norm_url(g(it, 'wp:attachment_url'))
               for it in items if g(it, 'wp:post_type') == 'attachment'}

manifest = collections.OrderedDict()   # content-relative bundle dir -> [image urls]
stats = collections.Counter()
seen_dirs = {}

# ---------- posts ----------
for it in items:
    if g(it, 'wp:post_type') != 'post': continue
    link = g(it, 'link').strip()
    path = link.strip('/')
    aliases = []
    if ' ' in path:                       # one Squarespace URL has a space in it
        aliases.append('/' + path + '/')
        path = path.replace(' ', '-')
    key = path.lower()
    if key in seen_dirs:
        raise SystemExit(f'URL collision: {link} vs {seen_dirs[key]}')
    seen_dirs[key] = link
    section = path.split('/')[0]
    raw = g(it, 'content:encoded')
    title = html.unescape(g(it, 'title')).strip()
    body = to_markdown(raw)
    if not title:
        title = clip(plain(raw), 60) or 'Untitled'
        stats['untitled'] += 1

    cats, tags = [], []
    for c in it.findall('category'):
        name = html.unescape(c.text or '').strip()
        if not name: continue
        if c.get('domain') == 'category':
            name = name.rstrip('-').strip()        # Squarespace artifact: "Quotes-", "Books-"
            if name not in cats: cats.append(name)
        elif name not in tags: tags.append(name)

    fm = {'title': title, 'date': et_date(g(it, 'wp:post_date'))}
    if g(it, 'wp:status') != 'publish': fm['draft'] = True; stats['drafts'] += 1
    if cats: fm['categories'] = cats
    if tags: fm['tags'] = tags
    exc = plain(g(it, 'excerpt:encoded'))
    if exc: fm['description'] = clip(exc)

    thumb = None
    for m in it.findall('wp:postmeta', NS):
        if m.findtext('wp:meta_key', namespaces=NS) == '_thumbnail_id':
            thumb = attachments.get(m.findtext('wp:meta_value', namespaces=NS))
    body_imgs = imgs_in(raw)
    if not thumb:
        thumb = next((u for u in body_imgs if is_sqs(u)), None)
    if thumb:
        fm['thumbnail'] = base(thumb)
        fm['images'] = [shown(thumb)]
        stats['with_thumbnail'] += 1
    if aliases: fm['aliases'] = aliases

    rel = path
    write(os.path.join(CONTENT, rel, 'index.md'), front(fm, body))
    comments = []
    for c in it.findall('wp:comment', NS):
        if c.findtext('wp:comment_approved', namespaces=NS) != '1': continue
        text = to_markdown(html.unescape(c.findtext('wp:comment_content', namespaces=NS) or '')).strip()
        if not text: continue
        comments.append({
            'id': (c.findtext('wp:comment_id', namespaces=NS) or '').strip(),
            'parent': (c.findtext('wp:comment_parent', namespaces=NS) or '0').strip() or '0',
            'author': html.unescape(c.findtext('wp:comment_author', namespaces=NS) or '').strip() or 'Anonymous',
            'date': et_date(c.findtext('wp:comment_date_gmt', namespaces=NS) or c.findtext('wp:comment_date', namespaces=NS)),
            'content': text,
        })
    if comments:
        comments.sort(key=lambda c: c['date'])
        ids = {c['id'] for c in comments}
        for c in comments:                      # replies to removed comments go to the top level
            if c['parent'] not in ids: c['parent'] = '0'
        write(os.path.join(CONTENT, rel, 'comments.yaml'),
              yaml.safe_dump(comments, allow_unicode=True, sort_keys=False, width=1000))
        stats['posts_with_comments'] += 1
        stats['comments'] += len(comments)
    urls = [base(u) for u in ([thumb] if thumb else []) + body_imgs if is_sqs(u)]
    if urls: manifest[rel] = list(dict.fromkeys(urls))
    stats['posts'] += 1
    stats['section:' + section] += 1

# ---------- pages ----------
pages = {g(it, 'link').strip(): it for it in items if g(it, 'wp:post_type') == 'page'}

about = pages['/about-1']
write(os.path.join(CONTENT, 'about', 'index.md'), front(
    {'title': 'About', 'aliases': ['/about-1/'], 'displayInList': False}, to_markdown(g(about, 'content:encoded'))))
manifest['about'] = [base(u) for u in imgs_in(g(about, 'content:encoded')) if is_sqs(u)]

blm = pages['/blm']
write(os.path.join(CONTENT, 'blm', 'index.md'), front(
    {'title': 'Black Lives Matter', 'displayInList': False}, to_markdown(g(blm, 'content:encoded'))))
manifest['blm'] = [base(u) for u in imgs_in(g(blm, 'content:encoded')) if is_sqs(u)]

gallery = [base(u) for u in imgs_in(g(pages['/eyetramuel'], 'content:encoded'))]
gallery = list(dict.fromkeys(gallery))
write(os.path.join(CONTENT, 'eyetramuel', 'index.md'), front(
    {'title': 'Eyetramuel', 'layout': 'eyetramuel', 'displayInList': False,
     'gallery': gallery}, ''))
manifest['eyetramuel'] = gallery

# ---------- section and home pages ----------
sections = {
    'iam': {'title': 'Blog', 'layout': 'archive',
            'description': 'Everything, newest first.'},
    'eye-tramuel': {'title': 'Eye TramueL'},
    'recipes': {'title': 'Recipes', 'description': 'Eat food, not too much, mostly plants.'},
    'bibliophile': {'title': 'Bibliophile', 'description': 'Reading is FUNdamental.'},
}
for sec, fm in sections.items():
    write(os.path.join(CONTENT, sec, '_index.md'), front(fm, ''))

write(os.path.join(CONTENT, '_index.md'), front({
    'title': 'Notes From Here',
    'params': {'eyebrow': 'Since 2008', 'writingTitle': 'Recent Posts', 'coverImage': 'cover.jpg',
               'coverAlt': 'Notes From Here cover art'},
}, ''))

os.makedirs(os.path.join(SITE, 'tools'), exist_ok=True)
with open(os.path.join(SITE, 'tools', 'image-manifest.json'), 'w') as fh:
    json.dump(manifest, fh, indent=1)
stats['manifest_bundles'] = len(manifest)
stats['manifest_images'] = sum(len(v) for v in manifest.values())
for k, v in sorted(stats.items()): print(f'{k}: {v}')
