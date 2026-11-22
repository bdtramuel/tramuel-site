"""Puts the old posts' songs back, as Apple Music players, where the Squarespace
audio players used to sit. Songs that aren't on Apple Music get a credit line.

Reads tools/songs.json. Skips a post that already has the song.
Usage (from the site folder): python3 tools/place_songs.py [--dry-run]
"""
import json, os, re, sys

site = '.'
dry = '--dry-run' in sys.argv
songs = json.load(open(os.path.join(site, 'tools', 'songs.json'), encoding='utf-8'))


def squash(text):
    keep, where = [], []
    i = 0
    skip = re.compile(r'\]\([^)]*\)|<[^>]+>|\{\{<[^>]*>\}\}')
    while i < len(text):
        m = skip.match(text, i)
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
        for size in (60, 40, 25, 12):
            probe = clean(prev)[-size:]
            if len(probe) >= 12 and flat.count(probe) == 1:
                end = where[flat.index(probe) + len(probe) - 1] + 1
                brk = body.find('\n\n', end)
                return (len(body) if brk == -1 else brk), 'after'
    if nxt:
        for size in (60, 40, 25, 12):
            probe = clean(nxt)[:size]
            if len(probe) >= 6 and flat.count(probe) == 1:
                start = where[flat.index(probe)]
                brk = body.rfind('\n\n', 0, start)
                return (0 if brk == -1 else brk), 'before'
    return 0, 'top'


def code(s):
    if s['url']:
        return '{{< song "%s" >}}' % s['url']
    attrs = 'title="%s"' % s['title'].replace('"', "'")
    if s['artist']:
        attrs += ' artist="%s"' % s['artist'].replace('"', "'")
    return '{{< song %s >}}' % attrs


placed = skipped = 0
for s in songs:
    page = os.path.join(site, 'content', s['post'].strip('/'), 'index.md')
    if not os.path.exists(page):
        print('NO PAGE', s['post'])
        continue
    text = open(page, encoding='utf-8').read()
    head_end = text.find('\n---', 3) + 4
    head, body = text[:head_end], text[head_end:]
    line = code(s)
    if line in body:
        skipped += 1
        continue
    at, how = place(body, s['prev'], s['next'])
    body = body[:at].rstrip('\n') + '\n\n' + line + '\n\n' + body[at:].lstrip('\n')
    placed += 1
    print(f'{how:7}', s['post'], '|', s['title'])
    if not dry:
        with open(page, 'w', encoding='utf-8') as fh:
            fh.write(head + body.rstrip('\n') + '\n')

print(f'{placed} songs placed, {skipped} already there')
