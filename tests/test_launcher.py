#!/usr/bin/env python3
"""Synthetic regression checks for hybrid settings and compiler partitioning; no game."""
import sys,tempfile,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from play import set_hybrid_cpu,split_for_cc,sha

class TestLauncher(unittest.TestCase):
    def test_merge_cpu(self):
        with tempfile.TemporaryDirectory() as d:
            ini=Path(d)/'ppsspp.ini';ini.write_text('[General]\nFirstRun = False\n[CPU]\nCPUCore = 1\nFastMemoryAccess = True\n[Control]\nShowTouchControls = False\n',encoding='utf-8-sig')
            set_hybrid_cpu(ini);s=ini.read_text(encoding='utf-8-sig');self.assertIn('CPUCore = 3',s);self.assertIn('FastMemoryAccess = True',s);self.assertIn('ShowTouchControls = False',s);before=sha(ini);set_hybrid_cpu(ini);self.assertEqual(before,sha(ini))
    def test_missing_cpu_section(self):
        with tempfile.TemporaryDirectory() as d:
            ini=Path(d)/'cfg';ini.write_text('[Sound]\nVolume = 65\n');set_hybrid_cpu(ini);self.assertEqual(ini.read_text(),'[Sound]\nVolume = 65\n[CPU]\nCPUCore = 3\n')
    def test_missing_cpu_key(self):
        with tempfile.TemporaryDirectory() as d:
            ini=Path(d)/'cfg';ini.write_text('[CPU]\n[Graphics]\nInternalResolution = 4\n');set_hybrid_cpu(ini);self.assertEqual(ini.read_text(),'[CPU]\nCPUCore = 3\n[Graphics]\nInternalResolution = 4\n')
    def test_cc_partition(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'sample.c';p.write_text('static const BP_Host *host;\nstatic uint32_t *bp_regs;\nstatic void psp_body_00000000(void) {}\nstatic int wrap_0(void){return 0;}\nstatic const uint32_t code_0[]={0};\nstatic const BP_Leaf leaves[]={};\n');units=split_for_cc(p);self.assertEqual(len(units),2);self.assertIn('extern const BP_Host *host;',units[0].read_text());self.assertIn('extern int wrap_0',units[-1].read_text());self.assertIn('const BP_Host *host;',units[-1].read_text())
if __name__=='__main__':unittest.main(verbosity=2)
