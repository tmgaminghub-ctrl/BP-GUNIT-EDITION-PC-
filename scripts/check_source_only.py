#!/usr/bin/env python3
"""Fail if a commit would contain game data, generated modules or vendored binaries.

The repository is source-only. The distributable player (runtime binaries,
vendored Python/TinyCC, modified PPSSPP corresponding source) is published as a
release asset and is rebuilt with rebuild/package.py, never committed.

Usage:  python3 scripts/check_source_only.py [path ...]     (default: repository root)
"""
import subprocess,sys
from pathlib import Path

ROOT=Path(__file__).resolve().parent.parent
BAD_SUFFIX={'.cso','.iso','.pmf','.at3','.ppst','.elf','.o','.obj','.so','.dll','.exe','.pyc','.zip','.xz','.7z'}
BAD_NAMES={'engine-leaves.so','engine-leaves.dll','installed.txt','kevlar.bin','boot.bin','eboot.bin',
           'build.json','campaign-launcher.json','ppsspp.ini','controls.ini','sha256sums.txt'}
BAD_PARTS={'play-data','native','vendor','runtime','source','__pycache__','node_modules','.venv'}
ALLOW={'docs/screenshots/launcher.png','launcher/art/yard.png','launcher/art/bulletproof.ico',
       'launcher/art/mark.png','rebuild/media-hashes.json','tests/test_campaign.py'}

def tracked():
    try:
        out=subprocess.run(['git','-C',str(ROOT),'ls-files','-z'],capture_output=True,check=True).stdout
        return [Path(p) for p in out.decode().split('\0') if p]
    except (OSError,subprocess.CalledProcessError):
        base=Path(sys.argv[1]) if len(sys.argv)>1 else ROOT
        skip={'.git','__pycache__','Play-Data','node_modules','.venv'}
        return [p.relative_to(base) for p in base.rglob('*')
                if p.is_file() and not (set(p.parts)&skip)]

def why(rel):
    rel=Path(rel);low=rel.as_posix().lower()
    if rel.as_posix() in ALLOW:return None
    if any(part in BAD_PARTS for part in rel.parts[:-1]):return 'generated/user/vendored directory'
    if rel.suffix.lower() in BAD_SUFFIX:return 'binary or generated file type'
    if rel.name.lower() in BAD_NAMES:return 'generated artifact'
    if (ROOT/rel).stat().st_size>2*1024*1024 and rel.suffix.lower() not in ('.mp4',):return 'unexpectedly large file'
    return None

def main():
    bad=[]
    for rel in tracked():
        p=ROOT/rel
        if not p.is_file():bad.append((rel,'missing file'));continue
        reason=why(rel)
        if reason:bad.append((rel,reason))
    if bad:
        print('Source-only check FAILED:')
        for rel,reason in bad:print(f'  {rel}  ({reason})')
        return 1
    print(f'Source-only check passed: {len(tracked())} files, no game data or generated binaries.')
    return 0

if __name__=='__main__':sys.exit(main())
