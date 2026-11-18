#!/usr/bin/env python3
"""Add a source-level optional AOT provider to a clean PPSSPP v1.20.4 checkout/tarball."""
import argparse,shutil
from pathlib import Path

def once(s,old,new):
    if s.count(old)!=1:raise ValueError('Not a clean PPSSPP v1.20.4 tree: '+repr(old[:90]))
    return s.replace(old,new)

def patch(root):
    d=Path(root)/'Core/HLE'; base=Path(__file__).resolve().parent
    r=d/'ReplaceTables.cpp'; h=d/'ReplaceTables.h'; k=d/'sceKernelModule.cpp'
    s=r.read_text(); t=k.read_text(); u=h.read_text()
    if '#include "bp_local_host.inc"' not in s:
        s=once(s,'void Replacement_Init() {','#include "bp_local_host.inc"\n\nvoid Replacement_Init() {')
        s=once(s,'void Replacement_Shutdown() {','void Replacement_Shutdown() {\n\tBPAot::closeSession();')
        s=once(s,'if (i >= ARRAY_SIZE(entries)) {\n\t\treturn nullptr;','if (i >= ARRAY_SIZE(entries)) {\n\t\treturn BPAot::lookup(i-ARRAY_SIZE(entries));')
        t=once(t,'Reporting::NotifyExecModule(moduleName, moduleVersion, module->crc);','Reporting::NotifyExecModule(moduleName, moduleVersion, module->crc);\n\tBPInstallAOT(module->nm.entry_addr, moduleName);')
        t=once(t,'\t\t\tif (module && module->libstub != 0) {','\t\t\tif (module && !module->isFake) BPInstallAOT(module->nm.entry_addr, module->nm.name);\n\t\t\tif (module && module->libstub != 0) {')
        u+='\n// Optional, revision-checked game-local native leaves.\nvoid BPInstallAOT(u32 entry, const char *moduleName);\n'
        r.write_text(s);k.write_text(t);h.write_text(u)
    ir=Path(root)/'Core/MIPS/IR/IRFrontend.cpp'; v=ir.read_text()
    if 'BPFindSpan(GetCompilerPC()' not in v:
        v=once(v,'\t\tMIPSOpcode inst = Memory::Read_Opcode_JIT(GetCompilerPC());',
        """		int nAot=0, aotCost=0;
		int aot=(!g_breakpoints.HasBreakPoints() && !g_breakpoints.HasMemChecks()) ? BPFindSpan(GetCompilerPC(),nAot,aotCost) : -1;
		if(aot>=0) {
			FlushAll();
			ir.Write(IROp::SetPCConst, 0, ir.AddConstant(GetCompilerPC()));
			ir.Write(IROp::CallReplacement, IRTEMP_0, ir.AddConstant(aot));
			js.compilerPC+=4*nAot; js.numInstructions+=nAot; js.downcountAmount+=aotCost;
			continue;
		}
		MIPSOpcode inst = Memory::Read_Opcode_JIT(GetCompilerPC());""")
        ir.write_text(v)
    if 'int BPFindSpan(' not in h.read_text():
        with h.open('a') as f:f.write('\nint BPFindSpan(u32 pc, int &size, int &cycles);\n')
    shutil.copyfile(base/'host.inc',d/'bp_local_host.inc');shutil.copyfile(base/'bp_abi.h',d/'bp_abi.h')

if __name__=='__main__':
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('source');patch(ap.parse_args().source)
