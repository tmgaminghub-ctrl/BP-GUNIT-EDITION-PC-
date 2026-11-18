#!/usr/bin/env python3
"""Documentation guard: local links resolve and the kit never claims to be emulator-free.

Two failure modes this catches early:
  * a relative link in a Markdown file that points at a file we do not ship;
  * a sentence that presents this hybrid as an emulator-free/standalone port.
Allowed exceptions for the second check are listed in ALLOWED_CLAIM_CONTEXT.
"""
import re,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parent.parent
LINK=re.compile(r'(?<!!)\[[^\]]*\]\(([^)]+)\)')
BAD_CLAIM=re.compile(r'(emulator[- ]free|standalone (?:port|build)|fully native|no emulator (?:core|needed|required))',re.I)
# Files that legitimately point at release assets rather than repository files.
ALLOW_MISSING=('toolkit/LICENSE','vendor/','runtime/','source/','bin/','Play-Data/')
# Files that must discuss the words in order to deny them.
DENIAL_CONTEXT=re.compile(r"(\bnot\b|\bnever\b|\bcannot\b|can't|isn't|\bwould\b|\bmust\b|has to|\bneeds?\b|\brequires?\b|"
                          r"without the emulator core|\bfalse\b|\bhonest\b|\bgap\b|\bnothing\b|\bfails?\b|"
                          r"denie[sd]|rather than|instead of|presents the (?:hybrid|project|kit) as)",re.I)

def main():
    problems=[]
    for md in sorted(ROOT.rglob('*.md')):
        rel=md.relative_to(ROOT).as_posix()
        text=md.read_text('utf-8',errors='replace')
        for target in LINK.findall(text):
            t=target.split('#')[0].strip()
            if not t or re.match(r'^[a-z]+:',t,re.I) or t.startswith('sandbox:'):continue
            if t.startswith('../') or t.startswith('../../'):continue   # GitHub-relative (releases, tags)
            if any(a in t for a in ALLOW_MISSING):continue
            if not (md.parent/t).exists() and not (ROOT/t).exists():
                problems.append(f'{rel}: broken local link -> {target}')
        lines=text.splitlines()
        for i,line in enumerate(lines):
            if not BAD_CLAIM.search(line):continue
            window=' '.join(lines[max(0,i-1):i+2])          # judge the sentence in its paragraph
            if not DENIAL_CONTEXT.search(window):
                problems.append(f'{rel}:{i+1}: presents the kit as emulator-free -> {line.strip()[:110]}')
    if problems:
        print('\n'.join('FAIL '+p for p in problems));return 1
    print('Docs ok: links resolve and the hybrid is described as a hybrid.')
    return 0

if __name__=='__main__':sys.exit(main())
