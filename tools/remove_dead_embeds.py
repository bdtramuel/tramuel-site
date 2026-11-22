"""Takes out YouTube and Vimeo embeds whose videos are gone (deleted, private,
or password-protected as of November 2026).

Two were Red Bull Music Academy lectures; those become a link to the lecture's
page, which still has the full transcript. A post left with nothing at all is
hidden (draft: true) rather than shown as a bare title; delete that line to
bring it back.

Usage (from the site folder): python3 tools/remove_dead_embeds.py [--dry-run]
"""
import os, re, sys

dry = '--dry-run' in sys.argv
dead = {
    'youtube': ['KUG-Uj9gUiw', 'NQPtMC2dKPI', 'fGtRS-JoDAs', 'zVMsgI6RI5M',   # removed
                '2GbfabuCW1g', '5li73Sk4yyQ'],                              # private
    'vimeo': ['252820616', '65215638', '82700156',                          # removed
              '137591399'],                                                 # password-protected
}
instead = {
    '82700156': '[The full lecture and transcript are at Red Bull Music Academy.]'
                '(https://www.redbullmusicacademy.com/lectures/erykah-badu-frother-of-the-month)',
    '65215638': '[The full lecture and transcript are at Red Bull Music Academy.]'
                '(https://www.redbullmusicacademy.com/lectures/rakim-lecture)',
}
pattern = re.compile(r'\n*\{\{< (youtube|vimeo) ([A-Za-z0-9_-]+) >\}\}\n*')

for root, _, files in os.walk('content'):
    if 'index.md' not in files:
        continue
    page = os.path.join(root, 'index.md')
    text = open(page, encoding='utf-8').read()

    def drop(m):
        if m.group(2) in dead[m.group(1)]:
            return '\n\n' + instead[m.group(2)] + '\n\n' if m.group(2) in instead else '\n\n'
        return m.group(0)

    new = pattern.sub(drop, text)
    if new == text:
        continue
    cut = new.find('\n---', 3)
    head, body = new[:cut], new[cut:]
    words = len(re.sub(r'!\[[^\]]*\]\([^)]*\)|\{\{<[^>]*>\}\}', '', body[4:]).split())
    if not words and '\ndraft:' not in head:
        head += '\ndraft: true'
    print(f'{page}: {words} words left' + ('  -> hidden' if not words else ''))
    if not dry:
        with open(page, 'w', encoding='utf-8') as fh:
            fh.write((head + body).rstrip('\n') + '\n')
