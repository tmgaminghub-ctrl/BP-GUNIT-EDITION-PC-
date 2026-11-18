import os,json
from pathlib import Path
p=Path(__file__).resolve().parents[1]; hdr=p/'winsdk/sdk/include'; words=0; roots=[]
for dept in ('um','ucrt','shared','winrt'):
 tree={}; dirs=list((p/'xwincache/unpack').glob('*/include/'+dept))+[hdr/dept]
 for d in dirs:
  for root,_,fs in os.walk(d):
   for f in fs:
    v=Path(root)/f
    if not v.is_file():continue
    tok=(v.relative_to(d)).as_posix().lower().split('/');D=tree
    for part in tok[:-1]:D=D.setdefault(part,{})
    D[tok[-1]]=str(v.resolve());words+=1
 def conv(k,v):
  if isinstance(v,str):return {'type':'file','name':k,'external-contents':v}
  return {'type':'directory','name':k,'contents':[conv(x,y) for x,y in sorted(v.items())]}
 roots.append(conv(str(hdr/dept),tree))
(p/'win-llvm/sdk.json').write_text(json.dumps({'version':0,'case-sensitive':False,'use-external-names':False,'roots':roots},separators=(',',':')));print(words)
