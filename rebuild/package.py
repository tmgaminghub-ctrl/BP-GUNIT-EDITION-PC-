#!/usr/bin/env python3
"""Package a built kit without ever walking user saves, build caches or a disc.
Usage: python3 rebuild/package.py STAGED-KIT /path/to/release.zip
"""
import hashlib,shutil,sys,zipfile
from pathlib import Path
ROOT_FILES=['START HERE.txt','README.md','THIRD-PARTY.md','LICENSE.txt','Play Bulletproof.exe','Play on Linux.sh','play.py']
TREES=['bin','bridge','guide','launcher','rebuild','tests','toolkit','tools','vendor','runtime/assets']
REQUIRED=['runtime/PPSSPPWindows64.exe','runtime/PPSSPPSDL','source/runtime-source.tar.xz']

def sha(p):
    with p.open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()

def files(root):
    fs={root/p for p in ROOT_FILES+REQUIRED}
    for directory in TREES:
        for p in (root/directory).rglob('*'):
            if not p.is_file() or any(x in ('.git','__pycache__') for x in p.parts) or p.suffix=='.pyc' or p.name.endswith('~'):continue
            name=p.name.lower()
            if name in ('installed.txt','engine-leaves.dll','engine-leaves.so','kevlar.bin','eboot.bin','boot.bin','engine.elf','build.json') or p.suffix.lower() in ('.cso','.iso','.pmf'):
                raise ValueError('Unexpected test or disc artifact in packaged tree: '+str(p))
            fs.add(p)
    for p in fs:
        if not p.is_file() or p.is_symlink():raise ValueError('Missing file or unsupported link: '+str(p))
    return sorted(fs,key=lambda p:p.relative_to(root).as_posix())

def main(root,output):
    root=root.resolve();fs=files(root);manifest=root/'SHA256SUMS.txt';manifest.write_bytes(''.join(sha(p)+'  '+p.relative_to(root).as_posix()+'\n' for p in fs).encode('utf-8'))
    with zipfile.ZipFile(output,'w',compression=zipfile.ZIP_DEFLATED,compresslevel=7) as z:
        for p in sorted([*fs,manifest],key=lambda p:p.relative_to(root).as_posix()):
            name=p.relative_to(root).as_posix();info=zipfile.ZipInfo('Bulletproof PC/'+name,(2000,1,1,0,0,0));info.create_system=3;info.external_attr=((0o100755 if p.stat().st_mode&0o111 else 0o100644)<<16);info.compress_type=zipfile.ZIP_STORED if p.suffix.lower() in ('.xz','.bz2','.png','.zip','.jpg','.mp4') else zipfile.ZIP_DEFLATED
            with z.open(info,'w') as out,p.open('rb') as f:shutil.copyfileobj(f,out,1024*1024)
    with zipfile.ZipFile(output) as z:
        bad=z.testzip()
        if bad:raise ValueError('ZIP integrity failure: '+bad)
        print(f'{len(z.infolist())} files, {output.stat().st_size:,} bytes, SHA-256 {sha(output)}',flush=True)
if __name__=='__main__':main(Path(sys.argv[1]),Path(sys.argv[2]))
