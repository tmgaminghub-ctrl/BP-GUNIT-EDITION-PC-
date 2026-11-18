#!/usr/bin/env python3
"""Verify the original kit files; user saves and generated modules are never scanned."""
import hashlib,sys
from pathlib import Path
root=Path(__file__).resolve().parents[1]

def digest(p):
    h=hashlib.sha256()
    with p.open('rb') as f:
        for block in iter(lambda:f.read(1024*1024),b''):h.update(block)
    return h.hexdigest()

def main():
    errors=[];count=0
    for line in (root/'SHA256SUMS.txt').read_text(encoding='utf8').splitlines():
        expected,name=line.split('  ',1);p=(root/name).resolve()
        if root not in p.parents:raise ValueError('Invalid manifest path')
        if not p.is_file():errors.append('MISSING  '+name)
        elif digest(p)!=expected:errors.append('CHANGED  '+name)
        count+=1
    if errors:print('\n'.join(errors),file=sys.stderr);return 1
    print(f'OK: {count} packaged files match SHA256SUMS.txt.');return 0
if __name__=='__main__':
    try:sys.exit(main())
    except (OSError,ValueError) as e:print('Verification failed:',e,file=sys.stderr);sys.exit(2)
