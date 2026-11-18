#!/usr/bin/env python3
"""Synthetic checks for the campaign launcher's storage layer; no game data."""
import json,struct,sys,tempfile,unittest,zipfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'launcher'))
import campaign_store as cs
sys.path.insert(0,str(ROOT))
import play

def sfo(entries):
    keytab=b'';datatab=b''
    table=b''
    for k,v in entries.items():
        ko=len(keytab);keytab+=k.encode()+b'\0';do=len(datatab);datatab+=v.encode()+b'\0'
        table+=struct.pack('<HHIII',ko,0x204,len(v)+1,len(v)+1,do)
    kb=20+16*len(entries);db=kb+len(keytab)
    return struct.pack('<4sIIII',b'\0PSF',0x101,kb,db,len(entries))+table+keytab+datatab

def make_save(root,name,title,size=12356):
    d=root/name;d.mkdir(parents=True)
    (d/'PARAM.SFO').write_bytes(sfo({'SAVEDATA_TITLE':title,'SAVEDATA_DIRECTORY':name}))
    (d/'KEVLAR.BIN').write_bytes(bytes(range(256))*(size//256))
    (d/'ICON0.PNG').write_bytes(b'\x89PNG\r\n\x1a\n')

class TestCampaignStore(unittest.TestCase):
    def test_config_roundtrip_and_defaults(self):
        with tempfile.TemporaryDirectory() as d:
            data=Path(d);c=cs.read_config(data);self.assertEqual(c['mode'],'hybrid');c['mode']='compat';c['auto_backup']=False;cs.save_config(data,c)
            again=cs.read_config(data);self.assertEqual(again['mode'],'compat');self.assertFalse(again['auto_backup'])
            (data/'campaign-launcher.json').write_text('not json');self.assertEqual(cs.read_config(data)['mode'],'hybrid')
            cs.save_config(data,{**again,'mode':'nonsense'});self.assertEqual(cs.read_config(data)['mode'],'hybrid')

    def test_checkpoints_titles_and_order(self):
        with tempfile.TemporaryDirectory() as d:
            data=Path(d);root=cs.savedir(data);root.mkdir(parents=True)
            make_save(root,'ULUS101280000','Industrial District');make_save(root,'ULUS101280001','Endgame')
            make_save(root,'OTHER00000','Ignored');(root/'ULUS101280002').mkdir();(root/'ULUS101280002'/'KEVLAR.BIN').write_bytes(b'')
            rows=cs.checkpoints(data);self.assertEqual([r[2] for r in rows],['Endgame','Industrial District']);self.assertTrue(all(r[1].name.startswith('ULUS10128') for r in rows))

    def test_backup_zip_and_dedupe(self):
        with tempfile.TemporaryDirectory() as d:
            data=Path(d);root=cs.savedir(data);root.mkdir(parents=True);make_save(root,'ULUS101280000','Industrial District')
            first=cs.backup(data);self.assertIsNotNone(first);self.assertTrue(first.is_file())
            with zipfile.ZipFile(first) as z:
                names=set(z.namelist());self.assertEqual(names,{'ULUS101280000/PARAM.SFO','ULUS101280000/KEVLAR.BIN','ULUS101280000/ICON0.PNG'})
            second=cs.backup(data);self.assertEqual(first,second)          # unchanged saves: no duplicate archive
            (root/'ULUS101280000'/'KEVLAR.BIN').write_bytes(b'\x01'*12356)
            third=cs.backup(data);self.assertNotEqual(first,third);self.assertTrue(third.is_file())
            forth=cs.backup(data,force=True);self.assertNotEqual(third,forth)
            self.assertEqual(len(list((data/'Backups').glob('*.zip'))),3)
            self.assertEqual(cs.backup(Path(d)/'empty'),None)

    def test_snapshots_and_safe_state(self):
        with tempfile.TemporaryDirectory() as d:
            data=Path(d);sd=cs.state_directory(data);sd.mkdir(parents=True)
            good=sd/'ULUS10128_1.02_0.ppst';good.write_bytes(b'PPST'+b'\0'*200)
            (sd/'ULUS10128_1.02_5.ppst').write_bytes(b'PPST'+b'\0'*200)   # out of range slot
            (sd/'ULUS10128_1.02_1.ppst').write_bytes(b'short')            # implausible
            (sd/'other_1.02_1.ppst').write_bytes(b'PPST'+b'\0'*200)
            self.assertEqual([p.name for p in cs.snapshots(data)],['ULUS10128_1.02_0.ppst'])
            self.assertEqual(cs.safe_state(data,good).name,'ULUS10128_1.02_0.ppst')
            with self.assertRaises(ValueError):cs.safe_state(data,sd/'ULUS10128_1.02_5.ppst')
            with self.assertRaises(ValueError):cs.safe_state(data,sd/'other_1.02_1.ppst')

    def test_stamp_and_verified_record(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'image.cso';p.write_bytes(bytes(100000))
            rec={'stamp':cs.stamp(p),'sha256':cs.LOGICAL_HASH,'verified_at':0}
            self.assertTrue(cs.cached_ok(rec))
            p.write_bytes(bytes(99999));self.assertFalse(cs.cached_ok(rec))  # changed file invalidates
            self.assertFalse(cs.cached_ok({'stamp':cs.stamp(p),'sha256':'0'*64}))
            self.assertFalse(cs.cached_ok(None));self.assertFalse(cs.cached_ok({'stamp':{'path':'/nonexistent'},'sha256':cs.LOGICAL_HASH}))

    def test_instance_lock(self):
        with tempfile.TemporaryDirectory() as d:
            a=cs.InstanceLock(Path(d)/'.lock');b=cs.InstanceLock(Path(d)/'.lock')
            self.assertTrue(a.acquire());self.assertFalse(b.acquire());a.close();self.assertTrue(b.acquire());b.close()
    def test_display_normalisation(self):
        d=cs.normalize_display(None);self.assertEqual(d,{'mode':'windowed','width':1280,'height':720,'render':'2','vsync':True})
        d=cs.normalize_display({'mode':'FULLSCREEN','width':1920,'height':1080,'render':'3','vsync':False})
        self.assertEqual((d['mode'],d['width'],d['render'],d['vsync']),('fullscreen',1920,'3',False))
        d=cs.normalize_display({'mode':'nope','width':100,'height':99999,'render':'9','vsync':'yes'})
        self.assertEqual((d['mode'],d['width'],d['height'],d['render'],d['vsync']),('windowed',1280,720,'2',True))
        self.assertEqual(cs.normalize_display({'width':1367,'height':769})['width'],1368)   # even dimensions
        self.assertEqual(cs.normalize_display({'render':'auto'})['render'],'auto')

    def test_ini_set_preserves_other_settings(self):
        text='[General]\nFirstRun = False\n[Graphics]\nGraphicsBackend = 0 (OPENGL)\nInternalResolution = 2\n[CPU]\nCPUCore = 3\n'
        out=cs.ini_set(text,'Graphics',{'InternalResolution':'4','FullScreen':'True'})
        self.assertIn('InternalResolution = 4\n',out);self.assertIn('FullScreen = True\n',out)
        self.assertIn('GraphicsBackend = 0 (OPENGL)',out);self.assertIn('CPUCore = 3',out);self.assertIn('FirstRun = False',out)
        self.assertEqual(cs.ini_set(out,'Graphics',{'InternalResolution':'4','FullScreen':'True'}),out)   # idempotent
        self.assertNotIn('FullScreen = True\n[SECTION]',out)
        new=cs.ini_set('[General]\nFirstRun = False\n','Graphics',{'FullScreen':'False'})
        self.assertIn('[Graphics]\n',new);self.assertIn('FullScreen = False',new)

    def test_apply_display_writes_and_describes(self):
        with tempfile.TemporaryDirectory() as d:
            ini=Path(d)/'ppsspp.ini';ini.write_text('[General]\nFirstRun = False\n[Graphics]\nInternalResolution = 2\n[CPU]\nCPUCore = 3\n')
            res=cs.apply_display(ini,{'mode':'fullscreen','width':2560,'height':1440,'render':'auto','vsync':False})
            self.assertEqual(res['settings']['FullScreen'],'True');self.assertEqual(res['settings']['VSyncInterval'],'0')
            self.assertNotIn('InternalResolution',res['settings'])          # auto leaves the runtime's value alone
            text=ini.read_text();self.assertIn('FullScreen = True',text);self.assertIn('InternalResolution = 2',text);self.assertIn('CPUCore = 3',text)
            cs.apply_display(ini,{'mode':'windowed','width':1600,'height':900,'render':'5','vsync':True})
            text=ini.read_text();self.assertIn('FullScreen = False',text);self.assertIn('InternalResolution = 5',text)
            self.assertIn('WindowWidth = 1600',text);self.assertIn('WindowHeight = 900',text)
            self.assertTrue(cs.describe_display({'mode':'windowed','width':1600,'height':900,'render':'5','vsync':True}).startswith('Window 1600x900'))
            self.assertIn('Full screen',cs.describe_display({'mode':'fullscreen'}))

    def test_config_migrates_old_fullscreen_flag(self):
        with tempfile.TemporaryDirectory() as d:
            data=Path(d);(data/'campaign-launcher.json').write_text(json.dumps({'version':3,'mode':'hybrid','fullscreen':True,'auto_backup':True,'disc':None}))
            c=cs.read_config(data);self.assertNotIn('fullscreen',c);self.assertEqual(c['display']['mode'],'windowed')
            c['display']['mode']='fullscreen';cs.save_config(data,c);self.assertEqual(cs.read_config(data)['display']['mode'],'fullscreen')

    def test_prepare_display_writes_runtime_settings(self):
        import types
        with tempfile.TemporaryDirectory() as d:
            ini=Path(d)/'ppsspp.ini';ini.write_text('[General]\nFirstRun = False\n[Graphics]\nInternalResolution = 2\n[CPU]\nCPUCore = 3\n')
            base=dict(display_mode=None,fullscreen=False,windowed=False,width=None,height=None,render=None,vsync=None)
            cfg={'display':{'mode':'windowed','width':1280,'height':720,'render':'2','vsync':True}}
            eff=play.prepare_display(ini,cfg,types.SimpleNamespace(**{**base,'display_mode':'fullscreen','render':'4','vsync':False}))
            self.assertEqual((eff['mode'],eff['render'],eff['vsync']),('fullscreen','4',False))
            text=ini.read_text();self.assertIn('FullScreen = True',text);self.assertIn('InternalResolution = 4',text);self.assertIn('VSyncInterval = 0',text);self.assertIn('CPUCore = 3',text)
            eff=play.prepare_display(ini,cfg,types.SimpleNamespace(**{**base,'display_mode':'windowed','width':1920,'height':1080}))
            self.assertEqual((eff['width'],eff['height'],eff['mode']),('1920','1080','windowed') if False else (1920,1080,'windowed'))
            text=ini.read_text();self.assertIn('FullScreen = False',text);self.assertIn('WindowWidth = 1920',text);self.assertIn('WindowHeight = 1080',text)
            eff=play.prepare_display(ini,cfg,types.SimpleNamespace(**base))       # no overrides: launcher settings win
            self.assertEqual((eff['width'],eff['render'],eff['vsync']),(1280,'2',True))


if __name__=='__main__':unittest.main(verbosity=2)
