"""After copy-photos.command runs: points every post at its own copy of each photo
instead of the Squarespace URL. Reads tools/image-results.txt.

Usage (from the site folder): python3 tools/localize_images.py
"""
import collections, os, sys

site = sys.argv[1] if len(sys.argv) > 1 else '.'
results = os.path.join(site, 'tools', 'image-results.txt')
by_folder = collections.defaultdict(dict)   # content folder -> {url: filename}
failed = 0
for line in open(results, encoding='utf-8'):
    parts = line.split()
    if len(parts) != 3:
        continue
    status, url, path = parts
    if status != 'ok':
        failed += 1
        continue
    folder, name = os.path.split(path)
    by_folder[folder][url] = name

changed = replaced = 0
for folder, mapping in by_folder.items():
    page = os.path.join(site, folder, 'index.md')
    if not os.path.exists(page):
        continue
    text = original = open(page, encoding='utf-8').read()
    # Longest URLs first so one URL that starts with another isn't half-replaced.
    for url in sorted(mapping, key=len, reverse=True):
        name = mapping[url]
        for variant in (url + '?format=1500w', url):
            if variant in text:
                replaced += text.count(variant)
                text = text.replace(variant, name)
    if text != original:
        with open(page, 'w', encoding='utf-8') as fh:   # write in place
            fh.write(text)
        changed += 1

print(f'{changed} pages updated, {replaced} references now local, {failed} photos could not be copied')
