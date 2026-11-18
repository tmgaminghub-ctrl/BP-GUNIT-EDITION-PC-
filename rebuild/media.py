#!/usr/bin/env python3
"""Optional developer convenience: fetch PPSSPP's matching prebuilt FFmpeg archives.
Not invoked by the player. Alternatively build them from the included FFmpeg source.
"""
import argparse,hashlib,json,os,tempfile,urllib.request
from pathlib import Path
PIN='1e3b4965632f60b1d85360261d1b9dd45444bc71'
BASE='https://raw.githubusercontent.com/hrydgard/ppsspp-ffmpeg/'+PIN+'/'
if __name__=='__main__':
 ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('runtime_source',type=Path);ap.add_argument('platform',choices=['linux','windows']);a=ap.parse_args()
 root=a.runtime_source.resolve()/'ffmpeg'
 if not (root/'configure').is_file():ap.error('Pass the extracted PPSSPP source root')
 for name,digest in json.loads(Path(__file__).with_name('media-hashes.json').read_text()).items():
    if name.split('/')[0].lower()!=a.platform:continue
    p=root/name;p.parent.mkdir(parents=True,exist_ok=True)
    if p.exists() and hashlib.sha256(p.read_bytes()).hexdigest()==digest:continue
    print('Fetching verified build input:',name,flush=True)
    with urllib.request.urlopen(BASE+name,timeout=120) as response:data=response.read(64*1024*1024+1)
    if len(data)>64*1024*1024 or hashlib.sha256(data).hexdigest()!=digest:raise SystemExit('Digest mismatch for '+name)
    with tempfile.NamedTemporaryFile(dir=p.parent,delete=False) as f:f.write(data);n=f.name
    os.replace(n,p)
