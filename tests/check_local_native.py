#!/usr/bin/env python3
"""Optional offline native-code differential test. Pass ONLY a module you built yourself.
Runs all admitted entries with synthetic CPU/RAM contexts; does not boot the game.
"""
import ctypes as C, random, sys
from pathlib import Path
U=C.c_uint32;P=C.POINTER(U);F=C.CFUNCTYPE;MASK=0xffffffff
Begin=F(C.c_void_p,U);End=F(C.c_int,U);Read=F(U,U,U);Write=F(None,U,U,U);Run=F(C.c_int)
class Host(C.Structure):_fields_=[('abi',U),('begin',Begin),('end',End),('read',Read),('write',Write)]
class Rec(C.Structure):_fields_=[('off',U),('n',U),('kind',U),('words',P),('run',Run)]

def signed(v,n):return (v^(1<<(n-1)))-(1<<(n-1))
def ref(w,r,read,write):
    op=w>>26;s=w>>21&31;t=w>>16&31;d=w>>11&31;sh=w>>6&31;fn=w&63;a=r[s];b=r[t];im=w&65535;si=signed(im,16)
    if op==0:
        if fn==8:assert w==0x03e00008;return
        if fn in (0,2,3,4,6,7):
            amt=(a&31) if fn in (4,6,7) else sh
            if fn in (0,4):v=b<<amt
            elif fn in (3,7):v=signed(b,32)>>amt
            elif (fn==2 and s==1) or (fn==6 and sh==1):v=(b>>amt)|(b<<((-amt)&31))
            else:v=b>>amt
        elif fn==10:v=a if b==0 else r[d]
        elif fn==11:v=a if b!=0 else r[d]
        elif fn==22:v=32-a.bit_length()
        elif fn==23:v=32-(MASK^a).bit_length()
        elif fn==33:v=a+b
        elif fn==35:v=a-b
        elif fn==36:v=a&b
        elif fn==37:v=a|b
        elif fn==38:v=a^b
        elif fn==39:v=~(a|b)
        elif fn==42:v=signed(a,32)<signed(b,32)
        elif fn==43:v=a<b
        elif fn==44:v=max(signed(a,32),signed(b,32))
        elif fn==45:v=min(signed(a,32),signed(b,32))
        else:raise ValueError(('unknown special',hex(w)))
        reg=d
    elif op==31:
        if fn==32 and sh in (2,3):
            bb=b.to_bytes(4,'little');v=int.from_bytes(bb[::-1] if sh==3 else bytes([bb[1],bb[0],bb[3],bb[2]]),'little');reg=d
        elif fn==0:v=(a>>sh)&((1<<(d+1))-1);reg=t
        elif fn==4:
            mask=((1<<(d-sh+1))-1)<<sh;v=(b&~mask)|((a<<sh)&mask);reg=t
        else:raise ValueError(('unknown special3',hex(w)))
    elif op in (32,33,35,36,37,40,41,43):
        width={32:1,33:2,35:4,36:1,37:2,40:1,41:2,43:4}[op];addr=(a+si)&MASK
        if op in (40,41,43):write(addr,b,width);return
        v=read(addr,width);reg=t
        if op in (32,33):v=signed(v,width*8)
    else:
        reg=t
        if op==9:v=a+si
        elif op==10:v=signed(a,32)<si
        elif op==11:v=a<(si&MASK)
        elif op==12:v=a&im
        elif op==13:v=a|im
        elif op==14:v=a^im
        elif op==15:v=im<<16
        else:raise ValueError(('unknown opcode',hex(w)))
    if reg:r[reg]=int(v)&MASK

def memory():
    mem={}
    def read(a,n):
        return sum(mem.get((a+j)&MASK,(((a+j)*0x45d9f3b)>>15)&255)<<(8*j) for j in range(n))
    def write(a,v,n):
        for j in range(n):mem[(a+j)&MASK]=v>>(8*j)&255
    return mem,read,write

def check(path):
    lib=C.CDLL(str(Path(path).resolve())); reg=(U*32)();native,r1,w1=memory();oracle,r2,w2=memory();track=[-1,-1]
    def begin(i):track[0]=i;return C.addressof(reg)
    def end(i):track[1]=i;return 0
    host=Host(0x42500202,Begin(begin),End(end),Read(r1),Write(w1));n=U();link=lib.bp_link_v2;link.argtypes=[C.POINTER(Host),P];link.restype=C.POINTER(Rec);table=link(C.byref(host),C.byref(n));assert table and 0<n.value<=65536
    rand=random.Random(0xb011e7);total=0;cases=0
    for i in range(n.value):
        e=table[i];assert e.kind in (0,1) and 1<=e.n<=64;ops=list(e.words[:e.n]);total+=e.n
        for mode in range(3):
            # Distinct random values, alias-heavy pointers, then signed/unsigned boundaries.
            if mode==0:rr=[rand.getrandbits(32) for _ in range(32)]
            elif mode==1:rr=[0x08870000+4*rand.randrange(3) for _ in range(32)]
            else:rr=[rand.choice([0,1,0x7fffffff,0x80000000,MASK]) for _ in range(32)]
            rr[0]=0;reg[:]=rr;native.clear();oracle.clear();track[:]=[-1,-1]
            for w in ops:ref(w,rr,r2,w2)
            e.run();cases+=1
            if list(reg)!=rr or native!=oracle or track!=[i,i]:raise AssertionError(f'difference at +0x{e.off:06x}, context {mode}')
    print(f'PASS: {n.value:,} entries; {total:,} instruction positions; {cases:,} register/memory comparisons; no differences.')
if __name__=='__main__':check(sys.argv[1])
