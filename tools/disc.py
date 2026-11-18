"""Read known files from a local PSP ISO9660 disc or CISO v1 image.
Standard library only; bounded reads, no mount, no temporary full-size ISO.
Only the fixed allowlist below is ever written to the host filesystem.
"""
from array import array
from pathlib import Path
import hashlib, struct, sys, zlib
from prx import BOOT_HASH, BOOT_SIZE

SECTOR=2048
MODULES={
    'kmodule/sc_sascore.prx':'e8bb9918c2fc7cf8a68166dd48bc517236cf9b6839d1b2a8f158e6ab904042b3',
    'kmodule/audiocodec.prx':'97904138ebbb4679b8ee68b88992cec3cc00678eec9416e8d2d50b061eaff27e',
    'kmodule/mpegbase.prx':'e8708b87b583f68f9bfc6c212d7ba489679a0acefda43713581780f03f6c4ec1',
    'kmodule/videocodec.prx':'e5907c626cc32700d0bba42856c59aa6b2aaf8e69df73a747d9e71f513ac21c0',
    'module/libatrac3plus.prx':'e3f05887507d61c36b150154621c625066bb73c20ac80e1f448a86300a1f0284',
    'module/mpeg.prx':'babe9aa19ed767ba75f945a23e4a91b64255e46da7b315b791ee5c17e0535a01',
}

def num(buf,at,n=4): return int.from_bytes(buf[at:at+n],'little')

class Disc:
    def __init__(self,file):
        self.f=file;self.size=file.seek(0,2);file.seek(0)
        h=file.read(24);self.index=None;self.dirs={}
        if len(h)<24:raise ValueError('File is too short to be a PSP disc')
        if h[:4]==b'CISO':
            _,hs,total,block,ver,align=struct.unpack('<4sIQIBB2x',h);hs=hs or 24
            if ver!=1 or block!=SECTOR or align>15 or not 24<=hs<=4096:
                raise ValueError('Only CISO v1 with 2,048-byte sectors is supported')
            if not 17*SECTOR<=total<=2**31 or total%SECTOR: raise ValueError('Invalid CISO disc size')
            self.length=total;self.align=align;self.kind='CISO v1';n=total//SECTOR+1
            raw=self.get(hs,n*4);idx=array('I');idx.frombytes(raw)
            if sys.byteorder!='little':idx.byteswap()
            if idx.itemsize!=4:raise ValueError('Unsupported integer format')
            self.index=idx
            if self.pos(0)<hs+n*4 or self.pos(n-1)>self.size:raise ValueError('Invalid CISO index bounds')
        else:
            self.length=self.size;self.kind='ISO9660'
            if self.length%SECTOR or self.length>2**31:raise ValueError('Not a supported PSP ISO or CISO v1 disc')
        pvd=self.read(16,SECTOR)
        if pvd[:7]!=b'\x01CD001\x01' or num(pvd,128,2)!=SECTOR:raise ValueError('No supported ISO9660 primary volume descriptor')
        _,self.root=self.record(pvd,156)
    def get(self,at,n):
        if at<0 or n<0 or at+n>self.size:raise ValueError('Invalid or truncated disc extent')
        self.f.seek(at);b=self.f.read(n)
        if len(b)!=n:raise ValueError('Short read from disc')
        return b
    def pos(self,i):return (self.index[i]&0x7fffffff)<<self.align
    def read(self,lba,n):
        if n<0 or n>16*1024*1024 or lba<0 or lba*SECTOR+n>self.length:raise ValueError('Disc extent outside allowed range')
        if not n:return b''
        if self.index is None:return self.get(lba*SECTOR,n)
        end=lba+(n+SECTOR-1)//SECTOR;lo=self.pos(lba);hi=self.pos(end)
        if hi<lo or hi-lo>(end-lba)*(SECTOR+(1<<self.align)+64) or hi-lo>32*1024*1024:raise ValueError('Invalid compressed extent size')
        src=self.get(lo,hi-lo);out=bytearray()
        for i in range(lba,end):
            a=self.pos(i)-lo;b=self.pos(i+1)-lo
            if a<0 or b<=a or b>len(src):raise ValueError('Corrupt CISO index')
            block=src[a:b]
            if self.index[i]&0x80000000:plain=block[:SECTOR]
            else:
                dec=zlib.decompressobj(-15);plain=dec.decompress(block,SECTOR+1)
                if not dec.eof:raise ValueError('Incomplete or oversized CISO sector')
            if len(plain)!=SECTOR:raise ValueError('Bad CISO sector length')
            out.extend(plain)
        return bytes(out[:n])
    def record(self,b,i):
        if i+34>len(b) or b[i]<34 or i+b[i]>len(b) or 33+b[i+32]>b[i]:raise ValueError('Bad ISO directory record')
        name=b[i+33:i+33+b[i+32]].split(b';')[0].decode('ascii')
        # No multi-extent or interleaved boot files on the supported revision.
        node=(num(b,i+2),num(b,i+10),b[i+25]);return name,node
    def directory(self,node):
        if node in self.dirs:return self.dirs[node]
        lba,n,flags=node
        if not flags&2 or n>2*1024*1024:raise ValueError('Invalid ISO directory')
        b=self.read(lba,n);d={};i=0
        while i<n:
            if not b[i]:i=(i//SECTOR+1)*SECTOR;continue
            name,ent=self.record(b,i);i+=b[i]
            if name not in ('\x00','\x01'):d[name.casefold()]=ent
        self.dirs[node]=d;return d
    def file(self,path,limit):
        f=self.root
        for segment in path.split('/'):
            d=self.directory(f);f=d.get(segment.casefold())
            if f is None:raise ValueError('Missing disc file: '+path)
        if f[2] & (2|128) or not 0<f[1]<=limit:raise ValueError('Unexpected file type or size: '+path)
        return self.read(f[0],f[1])

def read_sfo(b):
    if len(b)<20 or b[:4]!=b'\0PSF':raise ValueError('Invalid PARAM.SFO')
    kb,db,n=struct.unpack_from('<III',b,8)
    if 20+16*n>kb or kb>db or db>len(b):raise ValueError('Invalid SFO tables')
    r={}
    for i in range(n):
        ko,fmt,ln,cap,do=struct.unpack_from('<HHIII',b,20+i*16)
        end=b.find(b'\0',kb+ko,db)
        if end<0 or ln>cap or db+do+ln>len(b):raise ValueError('Invalid SFO entry')
        if fmt==0x204:r[b[kb+ko:end].decode('ascii')]=b[db+do:db+do+ln].rstrip(b'\0').decode('utf-8')
    return r

def read_title(path):
    with Path(path).open('rb') as f:
        disc=Disc(f);sfo=disc.file('PSP_GAME/PARAM.SFO',16384);id=read_sfo(sfo)
        if id.get('DISC_ID')!='ULUS10128' or id.get('DISC_VERSION')!='1.02':
            raise ValueError('Expected ULUS10128 v1.02; found '+str(id.get('DISC_ID'))+' v'+str(id.get('DISC_VERSION')))
        boot=disc.file('PSP_GAME/SYSDIR/BOOT.BIN',BOOT_SIZE)
        if hashlib.sha256(boot).hexdigest()!=BOOT_HASH:
            raise ValueError('This disc does not contain the matching plain BOOT.BIN (wrong revision, modified, or zero-filled).')
        files={'PSP_GAME/PARAM.SFO':sfo}
        for name,h in MODULES.items():
            p='PSP_GAME/USRDIR/'+name;data=disc.file(p,128*1024)
            if hashlib.sha256(data).hexdigest()!=h:raise ValueError('Unsupported module revision: '+p)
            files[p]=data
        return boot,files,{'format':disc.kind,'physical_bytes':disc.size,'logical_bytes':disc.length,'disc_id':id['DISC_ID'],'revision':id['DISC_VERSION'],'title':id.get('TITLE','')}
