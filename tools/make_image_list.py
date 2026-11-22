"""Builds tools/image-list.txt from tools/image-manifest.json.
Each line: <folder>/<name without extension> <Squarespace URL>."""
import json, os, re, sys, urllib.parse
site = sys.argv[1] if len(sys.argv) > 1 else '.'
manifest = json.load(open(os.path.join(site, 'tools', 'image-manifest.json')))
lines = []
for bundle, urls in manifest.items():
    if bundle == 'about':          # About now uses a local photo
        continue
    used = set()
    for url in urls:
        stem = urllib.parse.unquote(url.rstrip('/').split('/')[-1]).replace('+', '-')
        stem = re.sub(r'\.(jpe?g|png|gif|webp|heic|bmp)$', '', stem, flags=re.I)
        stem = re.sub(r'[^A-Za-z0-9._-]+', '-', stem).strip('-.') or 'image'
        name, n = stem, 2
        while name.lower() in used:
            name, n = f'{stem}-{n}', n + 1
        used.add(name.lower())
        lines.append(f'content/{bundle}/{name} {url}')
open(os.path.join(site, 'tools', 'image-list.txt'), 'w').write('\n'.join(lines) + '\n')
print(len(lines), 'images')
