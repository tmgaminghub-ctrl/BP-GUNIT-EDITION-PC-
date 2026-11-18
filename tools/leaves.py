"""Select bounded, single-exit integer leaves from andyst-dev/allegrexrecomp's emitted C.
Not a disassembler/translator. The bodies are copied from the emitter verbatim.
Only CPU/register aliases, memory access and the entry/return convention are adapted.
"""
import re, struct
from pathlib import Path
from prx import BASE

ALLOWED=set(('nop addu subu and or xor nor slt sltu max min movz movn addiu slti sltiu '
             'andi ori xori lui sll srl sra rotr sllv srlv srav rotrv clz clo seb seh wsbh '
             'wsbw bitrev ext ins lb lbu lh lhu lw sb sh sw').split())
BODY=re.compile(r'^static void psp_body_([0-9A-F]{8})\(uint32_t _entry\) \{\n(.*?)^\}',re.M|re.S)
INS=re.compile(r'/\* ([0-9A-F]{8})  (\S+)\s*(.*?)\s*\*/')

def admissible(addr,body):
    op=INS.findall(body)
    if not 2<=len(op)<=64 or [int(x[0],16) for x in op]!=list(range(addr,addr+4*len(op),4)):
        return False
    if op[-2][1:]!=('jr','$ra') or any(x[1] not in ALLOWED for x in op[:-2]+op[-1:]):return False
    if all(x[1] in ('nop','jr') for x in op):return False
    # No alternate entry, tail/indirect call, trap, write to RA or hidden state.
    if any(x in body for x in ('switch (','goto ','psp_func_','psp_at_','psp_dispatch','psp_unimplemented','psp_cpu.','psp_syscall','r_ra =')):return False
    if body.count('return;')!=1 or not body.rstrip().endswith('return;'):return False
    return True

# Extract only a single whitelist-matched, straight-line emitter statement per opcode.
# Do not swallow branch/delay control which can follow the statement on later lines.
SIMPLE=re.compile(r'/\* ([0-9A-F]{8})  (\S+)[^\n]*?\*/\n[ \t]*([^\n]*)')
STMT=re.compile(r'(?:;|(?:if \(r_\w+ [!=]= 0\) )?r_\w+ = [\w\s,()+<>&|~^=\-]+;|psp_write(?:8|16|32)\([\w\s,()+\-]+\);)')

def span_groups(source,covered,heads):
    lines={}; heads=set(heads)
    for m in SIMPLE.finditer(source):
        addr=int(m[1],16);op=m[2];line=m[3].strip()
        if op.startswith(('b','j')) and op not in ('bitrev','break'):heads.add(addr+8)
        if addr in covered or op not in ALLOWED or not STMT.fullmatch(line):continue
        if addr in lines and lines[addr]!=line:raise ValueError('Inconsistent emitter output at '+hex(addr))
        lines[addr]=line
    buf=[]
    for addr in sorted(lines):
        if buf and (addr!=buf[-1]+4 or addr in heads or len(buf)>=24):
            if len(buf)>=4:yield buf[0],[lines[i] for i in buf]
            buf=[]
        buf.append(addr)
    if len(buf)>=4:yield buf[0],[lines[i] for i in buf]

def emit_local(source,header,fixed,out):
    # Read file bias from the fixed ELF instead of assuming a constant header length.
    ph=struct.unpack_from('<I',fixed,28)[0];typ,offset,vaddr,_,filesz=struct.unpack_from('<IIIII',fixed,ph)
    if typ!=1 or vaddr!=BASE:raise ValueError('Unrecognized fixed engine layout')
    aliases=re.findall(r'^#define (r_\w+)\s+psp_cpu\.r\[(\d+)\]$',header,re.M)
    if len(aliases)!=32:raise ValueError('Unsupported emitter/register layout')
    h=['#include "bp_abi.h"','#include <psprecomp/recomp_rt.h>',
       'static const BP_Host *host;', 'static uint32_t *bp_regs;',
       '#define PSP_ENTER(a) ((void)0)','#define PSP_MARK(a) ((void)0)',
       '#define PSP_SP_CHECK(a) ((void)0)','#define PSP_SP_ENTER() ((void)0)']
    h += [f'#define {r} bp_regs[{n}]' for r,n in aliases]
    for bits in (8,16,32):
        h += [f'#define psp_read{bits}(a) ((uint{bits}_t)host->read((a),{bits//8}))',
              f'#define psp_write{bits}(a,v) host->write((a),(uint{bits}_t)(v),{bits//8})']
    rows=[];code=[];count=0;covered=set(); heads=set()
    for m in BODY.finditer(source):
        addr=int(m[1],16);heads.add(addr);body=m[2]
        if not admissible(addr,body):continue
        n=len(INS.findall(body));off=addr-BASE
        if off<0 or off+n*4>filesz:raise ValueError('Body outside ELF text segment')
        words=struct.unpack_from('<'+'I'*n,fixed,offset+off)
        if words[-2]!=0x03e00008:raise ValueError('Return/delay slot disagreement')
        i=len(rows);count+=n
        code += [m[0],f'static int wrap_{i}(void) {{ bp_regs=host->begin({i}); psp_body_{m[1]}(0x{addr:08X}u); return host->finish({i}); }}',
                 f'static const uint32_t code_{i}[]={{'+','.join(f'0x{w:08x}u' for w in words)+'};']
        rows.append(f'{{ {off}u, {n}u, 0u, code_{i}, wrap_{i} }},')
        covered.update(range(addr,addr+4*n,4))
    leaf_count=len(rows);leaf_words=count
    for addr,stmts in span_groups(source,covered,heads):
        n=len(stmts);off=addr-BASE;i=len(rows)
        if off<0 or off+4*n>filesz:raise ValueError('Span outside text')
        words=struct.unpack_from('<'+'I'*n,fixed,offset+off)
        code += [f'static int wrap_{i}(void) {{ bp_regs=host->begin({i});',*stmts,f'return host->finish({i}); }}',
                 f'static const uint32_t code_{i}[]={{'+','.join(f'0x{w:08x}u' for w in words)+'};']
        rows.append(f'{{ {off}u, {n}u, 1u, code_{i}, wrap_{i} }},');count+=n
    if not rows or len(rows)>65536:raise ValueError('Invalid AOT count')
    h+=code+['static const BP_Leaf leaves[]={',*rows,'};',
              'BP_EXPORT const BP_Leaf *bp_link_v2(const BP_Host *h, uint32_t *n) {',
              ' if (!h || !n || h->abi!=BP_ABI) return 0; host=h; *n=sizeof(leaves)/sizeof(leaves[0]); return leaves; }']
    Path(out).write_text('\n'.join(h)+'\n',encoding='utf-8');return leaf_count,leaf_words,len(rows)-leaf_count,count-leaf_words
