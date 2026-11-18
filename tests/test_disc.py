#!/usr/bin/env python3
"""Synthetic reader regression tests; run with python3 tests/test_disc.py."""
import io, struct, sys, unittest, zlib
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
from disc import Disc,read_sfo
from prx import prepare,signed16
S=2048

def rec(name,lba,data_len,directory=False):
    ln=33+len(name);b=bytearray(ln+ln%2);b[0]=len(b);struct.pack_into('<I',b,2,lba);struct.pack_into('>I',b,6,lba);struct.pack_into('<I',b,10,data_len);struct.pack_into('>I',b,14,data_len);b[25]=2 if directory else 0;b[28]=b[31]=1;b[32]=len(name);b[33:33+len(name)]=name;return b

def tinyiso():
    b=bytearray(23*S);p=16*S;b[p:p+7]=b'\x01CD001\x01';b[p+128:p+132]=b'\x00\x08\x08\x00';r=rec(b'\0',18,S,True);b[p+156:p+156+len(r)]=r
    files=rec(b'\0',18,S,True)+rec(b'\1',18,S,True)+rec(b'TEST.BIN;1',20,3000);b[18*S:18*S+len(files)]=files
    payload=bytes((i%239 for i in range(3000)));b[20*S:20*S+3000]=payload;return bytes(b),payload

def csov1(iso):
    blocks=len(iso)//S;head=struct.pack('<4sIQIBB2x',b'CISO',0,len(iso),S,1,1);start=24+4*(blocks+1);buf=bytearray();index=[]
    for i in range(blocks):
        sect=iso[i*S:(i+1)*S];stored=i in (16,20);index.append(((start+len(buf))>>1)|(0x80000000 if stored else 0));c=zlib.compressobj(6,zlib.DEFLATED,-15);buf+=sect if stored else c.compress(sect)+c.flush();buf+=b'\0'*(len(buf)%2)
    index.append((start+len(buf))>>1);return head+struct.pack('<'+'I'*len(index),*index)+buf

class Tests(unittest.TestCase):
    def test_iso(self):
        iso,p=tinyiso();self.assertEqual(Disc(io.BytesIO(iso)).file('test.bin',4000),p)
    def test_compressed_raw_and_padded(self):
        iso,p=tinyiso();d=Disc(io.BytesIO(csov1(iso)));self.assertEqual(d.file('TEST.BIN',3000),p)
    def test_truncated(self):
        iso,_=tinyiso()
        with self.assertRaises(ValueError):Disc(io.BytesIO(csov1(iso)[:-20]))
    def test_wrong_format(self):
        with self.assertRaises(ValueError):Disc(io.BytesIO(b'not a game'))
    def test_entry_limits(self):
        d=Disc(io.BytesIO(tinyiso()[0]));
        with self.assertRaises(ValueError):d.file('MISSING.BIN',5000)
        with self.assertRaises(ValueError):d.file('TEST.BIN',1)
    def test_sfo(self):
        k=b'DISC_ID\0';v=b'SYNTH0001\0';b=b'\0PSF'+struct.pack('<4I',0x101,36,36+len(k),1)+struct.pack('<HHIII',0,0x204,len(v),len(v),0)+k+v
        self.assertEqual(read_sfo(b),{'DISC_ID':'SYNTH0001'})
        with self.assertRaises(ValueError):read_sfo(b[:-1])
    def test_revision_gate(self):
        with self.assertRaises(ValueError):prepare(b'\x7fELF-not-the-matching-module')
    def test_hi16_carry(self):self.assertEqual([signed16(v) for v in (0x7fff,0x8000,0xffff,0x12345678)],[32767,-32768,-1,0x5678])

if __name__=='__main__':unittest.main(verbosity=2)
