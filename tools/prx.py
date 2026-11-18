"""Prepare the known ULUS10128 v1.02 PRX for *static*, fixed-address emission.
No cryptography and no title bytes in this file. The hash is the revision gate.
"""
from collections import Counter, defaultdict
import hashlib
import struct as S

BOOT_HASH = '3db80280dbfcac7bba87160c00e7bcc94686a96e804d00cdd4ad6cbcd0ca5fc8'
BOOT_SIZE = 1870572
BASE = 0x08804000

def u16(b, at): return S.unpack_from('<H', b, at)[0]
def u32(b, at): return S.unpack_from('<I', b, at)[0]
def set32(b, at, x): S.pack_into('<I', b, at, x & 0xFFFFFFFF)
def signed16(x): return ((x & 0xffff) ^ 0x8000) - 0x8000

def prepare(original):
    sha = hashlib.sha256(original).hexdigest()
    if len(original) != BOOT_SIZE or sha != BOOT_HASH:
        raise ValueError('Unsupported BOOT.BIN revision. Expected ULUS10128 v1.02, SHA-256 ' + BOOT_HASH + '; got ' + sha)
    b = bytearray(original)
    ph, sh = u32(b, 28), u32(b, 32)
    phn, shn = u16(b, 44), u16(b, 48)
    phs, shs = u16(b, 42), u16(b, 46)
    seg = [list(S.unpack_from('<8I', b, ph + i*phs)) for i in range(phn)]
    sec = [list(S.unpack_from('<10I', b, sh + i*shs)) for i in range(shn)]
    names = bytes(b[sec[u16(b, 50)][4]:][:sec[u16(b, 50)][5]])
    name = lambda s: names[s[0]:].split(b'\0')[0].decode('ascii')
    if phn != 2 or any(s[0] != 1 for s in seg): raise ValueError('Unknown segment layout')
    # Make the file-to-load-address bias identical in both segments: the
    # toolkit uses a single bias to read pointer-seed sites during discovery.
    cut = seg[1][1]
    gap = seg[0][1] + (seg[1][2] - seg[0][2]) - cut
    if not 0 <= gap <= 16: raise ValueError('Unexpected segment alignment')
    b[cut:cut] = bytes(gap)
    sh += gap
    set32(b, 32, sh)
    seg[1][1] += gap
    for s in sec:
        if s[4] >= cut: s[4] += gap
    base = [BASE + p[2] for p in seg]
    counts = Counter()
    for s in sec:
        if s[1] != 0x700000A0: continue
        pending = defaultdict(list)
        for j in range(s[4], s[4] + s[5], 8):
            off, inf = S.unpack_from('<II', b, j)
            typ, loc, ref = inf & 255, (inf >> 8) & 255, (inf >> 16) & 255
            if loc >= phn or ref >= phn or off + 4 > seg[loc][4]: raise ValueError('Invalid PRX relocation')
            p = seg[loc][1] + off; v = u32(b, p); add = base[ref]
            if typ == 2: set32(b, p, v + add)                         # R_MIPS_32
            elif typ == 4: set32(b, p, (v & 0xFC000000) | (((v & 0x03ffffff) + (add >> 2)) & 0x03ffffff))
            elif typ == 5: pending[ref].append((p, v))                 # HI16 may share a LO16
            elif typ == 6:
                for hp, hv in pending.pop(ref, []):
                    h = (((hv & 65535) << 16) + signed16(v) + add + 0x8000) >> 16
                    set32(b, hp, (hv & 0xffff0000) | (h & 65535))
                set32(b, p, (v & 0xffff0000) | ((v + add) & 65535))
            else: raise ValueError('Unexpected relocation type ' + str(typ))
            counts[typ] += 1
            # Already-applied relocations are retained as discovery hints only.
            S.pack_into('<II', b, j, base[loc] + off, typ)
        if any(pending.values()): raise ValueError('Unpaired HI16 at end of section')
        s[1] = 9    # SHT_REL; absolute offset, not a PSP segment-relative site
    for i, p in enumerate(seg):
        p[2] = p[3] = base[i]; S.pack_into('<8I', b, ph+i*phs, *p)
    for i, s in enumerate(sec):
        if s[2] & 2: s[3] += BASE
        S.pack_into('<10I', b, sh+i*shs, *s)
    entry = u32(b, 24) + BASE
    set32(b, 24, entry); S.pack_into('<H', b, 16, 2)  # ET_EXEC: do not relocate at runtime
    mi = next(s[4] for s in sec if name(s) == '.rodata.sceModuleInfo')
    bias = seg[0][1] - base[0]
    gp = u32(b, mi+32)
    start, end = S.unpack_from('<II', b, mi+44); imports = []
    a = start
    while a < end:
        p = a + bias; lib = u32(b, p) + bias
        libname = bytes(b[lib:lib+32]).split(b'\0')[0].decode('ascii')
        stride = b[p+8]*4
        if stride < 20: raise ValueError('Bad library descriptor')
        n = u16(b, p+10); nids = u32(b,p+12) + bias; stubs = u32(b,p+16)
        imports += [(stubs+8*i, u32(b, nids+4*i), libname) for i in range(n)]
        a += stride
    if a != end or len(imports) != 226: raise ValueError('Import table mismatch')
    return bytes(b), entry, gp, imports, dict(sorted(counts.items()))
