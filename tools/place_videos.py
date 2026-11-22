"""Puts each restored Squarespace video back into its post, where it sat on the old site.

Reads tools/videos.json (post path, video id, the text just before and after the
video on the old page) and tools/video-results.txt (which videos were converted).
Adds {{< video src="video.mp4" >}} to each post's index.md at the matching spot.
Skips any post that already has that video.

Usage (from the site folder): python3 tools/place_videos.py [--dry-run]
"""
import json, os, re, sys

site = '.'
dry = '--dry-run' in sys.argv
videos = json.load(open(os.path.join(site, 'tools', 'videos.json'), encoding='utf-8'))

ready = None
results = os.path.join(site, 'tools', 'video-results.txt')
if os.path.exists(results):
    ready = {}
    for line in open(results, encoding='utf-8'):
        parts = line.split()
        if len(parts) >= 3 and parts[0] == 'ok':
            ready[parts[1]] = parts[2]          # video id -> file name


def squash(text):
    """Text with markdown, links and whitespace removed, plus where each kept
    character sits in the original."""
    keep, where = [], []
    i = 0
    link = re.compile(r'\]\([^)]*\)')
    tag = re.compile(r'<[^>]+>|\{\{<[^>]*>\}\}')
    while i < len(text):
        m = link.match(text, i) or tag.match(text, i)
        if m:
            i = m.end()
            continue
        ch = text[i]
        if not ch.isspace() and ch not in '*_#>`\\[]':
            keep.append(ch)
            where.append(i)
        i += 1
    return ''.join(keep), where


def clean(anchor):
    return re.sub(r'[\s*_#>`\\\[\]]', '', anchor)


def place(body, prev, nxt):
    flat, where = squash(body)
    if prev:
        for size in (60, 40, 25):
            probe = clean(prev)[-size:]
            if len(probe) >= 12 and flat.count(probe) == 1:
                end = where[flat.index(probe) + len(probe) - 1] + 1
                brk = body.find('\n\n', end)
                return len(body) if brk == -1 else brk, 'after'
    if nxt:
        for size in (60, 40, 25, 12):
            probe = clean(nxt)[:size]
            if len(probe) >= 4 and flat.count(probe) == 1:
                start = where[flat.index(probe)]
                brk = body.rfind('\n\n', 0, start)
                return (0 if brk == -1 else brk), 'before'
    return None, None


by_post = {}
for v in videos:
    by_post.setdefault(v['post'], []).append(v)

placed = missing = skipped = 0
for post, items in by_post.items():
    page = os.path.join(site, 'content', post.strip('/'), 'index.md')
    if not os.path.exists(page):
        print('NO PAGE  ', post)
        missing += len(items)
        continue
    text = open(page, encoding='utf-8').read()
    head_end = text.find('\n---', 3) + 4             # end of front matter
    head, body = text[:head_end], text[head_end:]
    changed = False
    for n, v in enumerate(items, 1):
        name = 'video.mp4' if n == 1 else f'video-{n}.mp4'
        if ready is not None:
            if v['id'] not in ready:
                print('NOT READY', post, v['id'])
                missing += 1
                continue
            name = ready[v['id']]
        if f'src="{name}"' in body:
            skipped += 1
            continue
        prev = v['prev'][2:] if v['prev'].startswith('T:') else ''
        nxt = v['next'][2:] if v['next'].startswith('T:') else ''
        at, how = place(body, prev, nxt)
        if at is None:
            at, how = (len(body.rstrip()), 'end') if prev else (0, 'start')
        code = f'{{{{< video src="{name}" >}}}}'
        body = body[:at].rstrip('\n') + '\n\n' + code + '\n\n' + body[at:].lstrip('\n')
        changed = True
        placed += 1
        print(f'{how:7}', post, name)
    if changed and not dry:
        with open(page, 'w', encoding='utf-8') as fh:
            fh.write(head + body.rstrip('\n') + '\n')

print(f'{placed} videos placed, {skipped} already there, {missing} missing')
