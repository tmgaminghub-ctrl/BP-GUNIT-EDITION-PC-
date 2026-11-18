"""Offline campaign library, full-disc verification, checkpoints and backups.
No ROM, player data, downloaded dependencies or pre-unlocked saves are supplied.
"""
import hashlib,json,os,re,struct,sys,tempfile,time,uuid,zipfile
from datetime import datetime
from pathlib import Path
ROOT=Path(__file__).resolve().parent.parent
sys.path.insert(0,str(ROOT/'tools'))
from disc import Disc,SECTOR,read_sfo,read_title
DISC_ID='ULUS10128'; VERSION='1.02'; TOTAL=1686241280
LOGICAL_HASH='8004fc87f627b193b23f51614caa082b0f3c3d8d5ae78e449ed683d34ced7498'
DEFAULTS={'version':4,'mode':'hybrid','auto_backup':True,'disc':None,'display':None}
DISPLAY_DEFAULTS={'mode':'windowed','width':1280,'height':720,'render':'2','vsync':True}
DISPLAY_MODES=('windowed','fullscreen')
RENDER_CHOICES=('auto','1','2','3','4','5')          # 1x = 480x272 PSP native
RESOLUTIONS=((960,544),(1280,720),(1366,768),(1600,900),(1920,1080),(2560,1440),(3840,2160))
GAME_SAVE=re.compile(r'^ULUS10128\d{4}$',re.I)
QUICK_SAVE=re.compile(r'^ULUS10128_1\.02_[0-4]\.ppst$',re.I)
SAVE_FILES={'PARAM.SFO','KEVLAR.BIN','ICON0.PNG','ICON1.PMF','PIC1.PNG','SND0.AT3','PIC0.PNG'}

def atomic(p,b):
    p=Path(p);p.parent.mkdir(parents=True,exist_ok=True);name=None
    try:
        with tempfile.NamedTemporaryFile(dir=p.parent,delete=False) as f:
            name=f.name;f.write(b);f.flush();os.fsync(f.fileno())
        os.replace(name,p)
    finally:
        if name:Path(name).unlink(missing_ok=True)

def read_config(data):
    try:v=json.loads((data/'campaign-launcher.json').read_text('utf8'))
    except (OSError,ValueError):v={}
    if not isinstance(v,dict):v={}
    c=DEFAULTS.copy();c.update({k:v[k] for k in DEFAULTS if k in v});c['mode']='compat' if c['mode']=='compat' else 'hybrid';c['display']=normalize_display(v.get('display'));c.pop('fullscreen',None);return c


def normalize_display(d):
    out=dict(DISPLAY_DEFAULTS)
    if isinstance(d,dict):
        mode=str(d.get('mode','')).lower()
        if mode in DISPLAY_MODES:out['mode']=mode
        for key,lo,hi in (('width',640,7680),('height',360,4320)):
            try:v=int(d.get(key,out[key]))
            except (TypeError,ValueError):continue
            if lo<=v<=hi:out[key]=v+(v&1)      # keep even dimensions
        r=str(d.get('render',out['render'])).lower()
        if r in RENDER_CHOICES:out['render']=r
        if isinstance(d.get('vsync'),bool):out['vsync']=d['vsync']
    return out


def ini_set(text,section,values):
    """Set keys in one INI section, preserving everything else. Unknown keys are
    harmless to the runtime, so this works across PPSSPP point releases."""
    lines=text.splitlines(keepends=True)
    want=re.compile(r'^\s*\['+re.escape(section)+r'\]\s*$',re.I)
    idx=next((i for i,x in enumerate(lines) if want.match(x)),None)
    if idx is None:
        if lines and not lines[-1].endswith('\n'):lines[-1]+='\n'
        lines.append(f'[{section}]\n');idx=len(lines)-1
    end=next((i for i in range(idx+1,len(lines)) if lines[i].lstrip().startswith('[')),len(lines))
    for key,value in values.items():
        pat=re.compile(r'^\s*'+re.escape(key)+r'\s*=',re.I);at=next((i for i in range(idx+1,end) if pat.match(lines[i])),None)
        line=f'{key} = {value}\n'
        if at is None:lines.insert(end,line);end+=1
        else:lines[at]=line
    return ''.join(lines)


def apply_display(ini,display):
    """Write the launcher's display choice into the player's private ppsspp.ini.
    Render scale: 1 = 480x272, 2 = 960x544, 3 = 1440x816, 4 = 1920x1088, 5 = 2400x1360."""
    d=normalize_display(display);values={'FullScreen':'True' if d['mode']=='fullscreen' else 'False',
        'VSyncInterval':'1' if d['vsync'] else '0','WindowWidth':str(d['width']),'WindowHeight':str(d['height'])}
    if d['render']!='auto':values['InternalResolution']=d['render']
    ini=Path(ini);text=ini.read_text(encoding='utf-8-sig') if ini.is_file() else ''
    new=ini_set(text,'Graphics',values)
    if new!=text:atomic(ini,new.encode('utf-8'))
    return {'display':d,'settings':values}


def describe_display(display):
    d=normalize_display(display)
    render={'auto':'runtime default','1':'1x (480x272)','2':'2x (960x544)','3':'3x (1440x816)','4':'4x (1920x1088)','5':'5x (2400x1360)'}[d['render']]
    if d['mode']=='fullscreen':where='Full screen (desktop resolution)'
    else:where=f"Window {d['width']}x{d['height']}"
    return f"{where}, render {render}, vsync {'on' if d['vsync'] else 'off'}"

def save_config(data,c):atomic(data/'campaign-launcher.json',(json.dumps(c,indent=2,ensure_ascii=False)+'\n').encode())

def stamp(path):
    path=Path(path).resolve(strict=True);s=path.stat();h=hashlib.sha256()
    with path.open('rb') as f:
        for i in (0,max(0,(s.st_size>>1)-8192),max(0,s.st_size-16384)):
            f.seek(i);h.update(f.read(16384))
    return {'path':str(path),'bytes':s.st_size,'mtime_ns':s.st_mtime_ns,'sample':h.hexdigest()}

def cached_ok(rec):
    try:return rec['sha256']==LOGICAL_HASH and rec['stamp']==stamp(rec['stamp']['path'])
    except (TypeError,KeyError,ValueError,OSError):return False

def logical_hash(d,progress=lambda n,t:None,cancel=lambda:False):
    h=hashlib.sha256();n=d.length//SECTOR
    for i in range(0,n,1024):
        if cancel():raise InterruptedError('Verification cancelled.')
        count=min(1024,n-i);h.update(d.read(i,count*SECTOR));progress(i+count,n)
    return h.hexdigest()

def verify(path,progress=lambda n,t:None,cancel=lambda:False):
    path=Path(path).resolve(strict=True);before=stamp(path);_,_,desc=read_title(path)
    with path.open('rb') as f:
        d=Disc(f)
        if d.length!=TOTAL:raise ValueError('This is not the complete USA v1.02 disc. Its logical size differs.')
        digest=logical_hash(d,progress,cancel)
    if before!=stamp(path):raise ValueError('The image changed while it was being read. Please verify again.')
    if digest!=LOGICAL_HASH:raise ValueError('Full-disc verification failed. The boot program matches, but some disc content differs. Use a complete, unmodified USA v1.02 dump.')
    return {'path':str(path),'stamp':before,'sha256':digest,'format':desc['format'],'logical_bytes':TOTAL,'verified_at':int(time.time()*1_000_000_000)}

def stick(data):return Path(data)/'config/ppsspp/PSP'
def savedir(data):return stick(data)/'SAVEDATA'
def state_directory(data):return stick(data)/'PPSSPP_STATE'

def checkpoints(data):
    root=savedir(data);out=[]
    if not root.is_dir():return out
    for p in root.iterdir():
        if p.is_symlink() or not p.is_dir() or not GAME_SAVE.fullmatch(p.name):continue
        try:
            f=p/'PARAM.SFO';payload=p/'KEVLAR.BIN'
            if f.is_symlink() or payload.is_symlink() or f.stat().st_size>32768 or not 0<payload.stat().st_size<2**20:continue
            s=read_sfo(f.read_bytes());title=s.get('SAVEDATA_TITLE') or 'Campaign checkpoint';out.append((payload.stat().st_mtime_ns,p,title.strip()[:100]))
        except (OSError,ValueError,struct.error):continue
    return sorted(out,key=lambda item:item[0],reverse=True)

def snapshots(data):
    root=state_directory(data)
    if not root.is_dir():return []
    out=[]
    for p in root.iterdir():
        if QUICK_SAVE.fullmatch(p.name) and p.is_file() and not p.is_symlink() and p.stat().st_size>=128:out.append(p)
    return sorted(out,key=lambda p:p.stat().st_mtime_ns,reverse=True)

def safe_state(data,path):
    p=Path(path).resolve(strict=True)
    if p not in (q.resolve() for q in snapshots(data)):raise ValueError('Choose a snapshot for this title and version in this profile’s PPSSPP_STATE folder.')
    return p

def backup(data,force=False):
    rows=checkpoints(data);files=[]
    for _,d,_ in rows:
        for p in sorted(d.iterdir()):
            if p.name.upper() in SAVE_FILES and p.is_file() and not p.is_symlink() and p.stat().st_size<=4*1024*1024:files.append((d.name+'/'+p.name,p))
    if not files:return None
    dest=Path(data)/'Backups';dest.mkdir(parents=True,exist_ok=True);chunks=[];h=hashlib.sha256()
    for n,p in sorted(files):
        b=p.read_bytes();h.update(n.encode()+b'\0'+hashlib.sha256(b).digest());chunks.append((n,b))
    key=h.hexdigest();receipt=dest/'last-automatic.json'
    if not force:
        try:
            info=json.loads(receipt.read_text('utf8'))
            if info['sha256']==key and Path(info['name']).name==info['name'] and (dest/info['name']).is_file():return dest/info['name']
        except (KeyError,ValueError,OSError,TypeError):pass
    tag=datetime.now().strftime('%Y%m%d-%H%M%S');p=dest/(tag+'-'+uuid.uuid4().hex[:6]+'.zip');tmp=p.with_suffix('.partial')
    try:
        with zipfile.ZipFile(tmp,'x',zipfile.ZIP_DEFLATED) as z:
            for n,b in chunks:z.writestr(n,b)
        os.replace(tmp,p)
    finally:tmp.unlink(missing_ok=True)
    atomic(receipt,json.dumps({'sha256':key,'name':p.name}).encode());return p

class InstanceLock:
    def __init__(self,path):self.path=Path(path);self.f=None
    def acquire(self):
        self.path.parent.mkdir(parents=True,exist_ok=True);f=self.path.open('a+b');f.seek(0,2)
        if not f.tell():f.write(b'0');f.flush()
        f.seek(0)
        try:
            if os.name=='nt':
                import msvcrt;msvcrt.locking(f.fileno(),msvcrt.LK_NBLCK,1)
            else:
                import fcntl;fcntl.flock(f,fcntl.LOCK_EX|fcntl.LOCK_NB)
        except OSError:f.close();return False
        self.f=f;return True
    def close(self):
        if self.f:self.f.close();self.f=None
