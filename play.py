#!/usr/bin/env python3
"""Build local Engine AOT code and play ULUS10128 v1.02. Your CSO/ISO is opened read-only.
Run without arguments (or from the campaign launcher) to use the remembered disc."""
import argparse,hashlib,json,os,platform,re,shutil,subprocess,sys,tempfile,time,zlib
from pathlib import Path
ROOT=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT/'tools'));sys.path.insert(0,str(ROOT/'launcher'))
from disc import read_title
from prx import prepare, BOOT_HASH
from leaves import emit_local
import campaign_store as cs
WIN=os.name=='nt'
ARCH='windows-x64' if WIN else 'linux-x64'
PLUGIN='engine-leaves.dll' if WIN else 'engine-leaves.so'
DEFAULT_INI='''[General]
FirstRun = False
CheckForNewVersion = False
EnableDiscordPresence = False
[CPU]
CPUCore = 3
[Graphics]
GraphicsBackend = 0 (OPENGL)
InternalResolution = 2
VSyncInterval = 1
[Control]
ShowTouchControls = False
[Network]
EnableWlan = False
'''

def set_hybrid_cpu(ini):
    # Keep the normal settings/saves path. The upstream -J CLI option prevents
    # future preference changes from being saved, which is wrong for a game kit.
    s=ini.read_text(encoding='utf-8-sig'); lines=s.splitlines(keepends=True); idx=next((i for i,x in enumerate(lines) if x.strip().casefold()=='[cpu]'),None)
    if idx is None:s=s.rstrip()+'\n[CPU]\nCPUCore = 3\n'
    else:
        end=next((i for i in range(idx+1,len(lines)) if lines[i].lstrip().startswith('[')),len(lines))
        at=next((i for i in range(idx+1,end) if re.match(r'^\s*CPUCore\s*=',lines[i],re.I)),None)
        if at is not None and lines[at].split('=',1)[1].strip()=='3':return
        if at is None:lines.insert(idx+1,'CPUCore = 3\n')
        else:lines[at]='CPUCore = 3\n'
        s=''.join(lines)
    with tempfile.NamedTemporaryFile(mode='w',encoding='utf-8',dir=ini.parent,delete=False) as f:f.write(s);name=f.name
    os.replace(name,ini)

def prepare_display(ini,cfg,args):
    """Resolve the launcher's display choice plus per-run overrides, then write it
    into this kit's private ppsspp.ini. Returns the effective display dict."""
    display=dict(cfg['display'])
    if getattr(args,'display_mode',None):display['mode']=args.display_mode
    if getattr(args,'fullscreen',False):display['mode']='fullscreen'
    if getattr(args,'windowed',False):display['mode']='windowed'
    if getattr(args,'width',None):display['width']=args.width
    if getattr(args,'height',None):display['height']=args.height
    if getattr(args,'render',None):display['render']=args.render
    if getattr(args,'vsync',None) is not None:display['vsync']=args.vsync
    display=cs.normalize_display(display)
    cs.apply_display(ini,display)
    return display


def sha(p):
    with Path(p).open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()

def pick():
    try:
        import tkinter as tk
        from tkinter import filedialog
        root=tk.Tk();root.withdraw(); result=filedialog.askopenfilename(title='Select your Bulletproof USA v1.02 disc',filetypes=[('PSP disc images','*.iso *.cso *.ISO *.CSO'),('All files','*')]);root.destroy();return result
    except Exception:
        if shutil.which('zenity'):
            p=subprocess.run(['zenity','--file-selection','--title=Select your Bulletproof USA v1.02 disc'],capture_output=True,text=True);return p.stdout.rstrip('\n') if not p.returncode else ''
        raise ValueError('Supply the path to your own USA v1.02 ISO/CSO on the command line.')

def split_for_cc(path):
    # TinyCC can handle a single TU instantly; split it for conventional compilers.
    s=path.read_text(); a=s.index('static void psp_body_'); b=s.index('static const BP_Leaf leaves[]='); pre=s[:a]
    pre=pre.replace('static const BP_Host *host;', 'const BP_Host *host;').replace('static uint32_t *bp_regs;', 'uint32_t *bp_regs;')
    extern=pre.replace('const BP_Host *host;', 'extern const BP_Host *host;').replace('uint32_t *bp_regs;', 'extern uint32_t *bp_regs;')
    decl=[]; units=[];start=a
    for m in re.finditer(r'^static const uint32_t code_(\d+)\[\]=\{[^\n]+;\n',s[a:b],re.M):
        i=int(m[1]);end=a+m.end();decl.append(f'extern int wrap_{i}(void); extern const uint32_t code_{i}[];')
        if end-start>=102400 or end==b:
            body=s[start:end].replace('static int wrap_', 'int wrap_').replace('static const uint32_t code_', 'const uint32_t code_'); f=path.with_name('unit'+str(len(units))+'.c');f.write_text(extern+body);units.append(f);start=end
    if start!=b or not units:raise ValueError('Cannot partition generated code')
    tail=path.with_name('dispatch.c');tail.write_text(pre+'\n'.join(decl)+'\n'+s[b:]);return [*units,tail]

def ensure_native(boot,cache,rebuild):
    tool=ROOT/'bin'/ARCH/('allegrexrecomp.exe' if WIN else 'allegrexrecomp'); plugin=cache/PLUGIN; meta=cache/'build.json'; cache.mkdir(parents=True,exist_ok=True)
    if not tool.is_file():raise ValueError('Recompiler missing. Extract the entire kit.')
    sig=hashlib.sha256(('bridge-2.3/'+BOOT_HASH+'/'+ARCH+'/'+sha(tool)+'/'+sha(ROOT/'tools/leaves.py')+'/'+sha(ROOT/'bridge/bp_abi.h')).encode()).hexdigest()
    if not rebuild and plugin.is_file() and meta.is_file():
        try:m=json.loads(meta.read_text());valid=m['signature']==sig and m['binary_sha256']==sha(plugin)
        except (KeyError,ValueError):valid=False
        if valid:
            print(f"Using verified local module: {m['leaves']} complete routines + {m['spans']} AOT instruction sequences.",flush=True);return plugin
    cc=str(ROOT/'vendor/tinycc-win64/tcc.exe') if WIN else ((shutil.which('tcc') if shutil.which('ld') else None) or shutil.which('cc'))
    if not cc:raise ValueError('Install a C compiler (e.g. sudo apt install gcc) then retry.')
    if not WIN and not os.access(tool,os.X_OK):tool.chmod(tool.stat().st_mode|0o100)
    with tempfile.TemporaryDirectory(prefix='build-',dir=cache) as t:
        d=Path(t); fixed,*_=prepare(boot);elf=d/'Engine.elf';elf.write_bytes(fixed)
        env=dict(os.environ,PSPRECOMP_TEXT_ONLY='1'); print('Generating C with allegrexrecomp...',flush=True)
        proc=subprocess.run([str(tool),'emit',str(elf),str(d),'bulletproof'],env=env,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,check=False)
        (cache/'emitter.txt').write_bytes(proc.stdout)
        if proc.returncode:raise RuntimeError('Recompiler failed: '+str(cache/'emitter.txt'))
        source=d/'local.c'; n,ins,sp,sw=emit_local((d/'bulletproof_funcs.c').read_text(),(d/'bulletproof_funcs.h').read_text(),fixed,source)
        print(f'Compiling {n} whole routines and {sp} additional straight-line code sequences...',flush=True)
        flags=['-shared'] if WIN else ['-shared','-fPIC','-O0','-fvisibility=hidden'] if Path(cc).name!='tcc' else ['-shared','-fPIC']
        # TinyCC's -shared emits a normal PE DLL; it also honors __declspec(dllexport).
        units=[source] if WIN or Path(cc).name=='tcc' else split_for_cc(source)
        inc=['-I'+str(ROOT/'bridge'),'-I'+str(ROOT/'toolkit/include')]
        if not WIN and Path(cc).name=='tcc':
            # Link the freestanding object with a non-executable stack. Some TinyCC
            # versions omit the modern ELF stack note on shared-library output.
            commands=[[cc,'-c','-fPIC',*inc,str(source),'-o',str(d/'local.o')],
                      [shutil.which('ld'),'-shared','-z','noexecstack','-z','relro','-z','now','-o',str(d/PLUGIN),str(d/'local.o')]]
        else:commands=[[cc,*flags,*inc,*map(str,units),'-o',str(d/PLUGIN)]]
        with (cache/'compile.txt').open('wb') as log:
            for cmd in commands:
                proc=subprocess.run(cmd,stdout=log,stderr=subprocess.STDOUT)
                if proc.returncode:break
        if proc.returncode or not (d/PLUGIN).exists():raise RuntimeError('Native compilation failed: '+str(cache/'compile.txt')+'\n'+(cache/'compile.txt').read_text(errors='replace')[-1200:])
        m={'signature':sig,'boot_sha256':BOOT_HASH,'leaves':n,'spans':sp,'guest_instructions_in_leaves':ins,'guest_instructions_in_spans':sw,'binary_sha256':sha(d/PLUGIN),'target':ARCH}
        os.replace(d/PLUGIN,plugin);(d/'receipt.json').write_text(json.dumps(m,indent=2)+'\n');os.replace(d/'receipt.json',meta)
    return plugin

def verify_disc(image,data):
    print('Reading every sector of your disc image (read only; this may take a few minutes)...',flush=True)
    last=[0]
    def progress(n,total):
        if n-last[0]>=total//10 or n==total:last[0]=n;print(f'  {100*n//total:3d}%  {n*2048:,} / {total*2048:,} bytes',flush=True)
    rec=cs.verify(image,progress)
    cfg=cs.read_config(data);cfg['disc']=rec;cs.save_config(data,cfg)
    print('Complete disc verified. All data matches the USA v1.02 image.',flush=True);return rec

def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('image',nargs='?',help='USA revision 1.02 .cso/.iso (default: the disc remembered by the launcher)')
    ap.add_argument('--state',help='resume a PPSSPP save-state snapshot (advanced; snapshots are not game saves)')
    ap.add_argument('--compat',action='store_true',help='explicitly disable AOT for this run')
    ap.add_argument('--native',action='store_true',help='force the native hybrid even if the launcher is set to compatibility')
    ap.add_argument('--audit',action='store_true',help='compare the first live call of each native routine/sequence to the interpreter')
    ap.add_argument('--verify-full',action='store_true',help='verify every sector of the disc image, then remember it')
    ap.add_argument('--fullscreen',action='store_true',help='start full screen for this run (desktop resolution)')
    ap.add_argument('--windowed',action='store_true',help='start in a window for this run')
    ap.add_argument('--display-mode',choices=cs.DISPLAY_MODES,dest='display_mode',help='windowed or fullscreen (set by the launcher)')
    ap.add_argument('--width',type=int,help='window width in pixels (windowed mode)')
    ap.add_argument('--height',type=int,help='window height in pixels (windowed mode)')
    ap.add_argument('--render',choices=cs.RENDER_CHOICES,help='render scale: auto, or 1..5 (1 = 480x272)')
    ap.add_argument('--vsync',dest='vsync',action='store_true',default=None,help='force vsync on')
    ap.add_argument('--no-vsync',dest='vsync',action='store_false',help='force vsync off')
    ap.add_argument('--no-backup',action='store_true',help='skip the automatic save backup for this session')
    ap.add_argument('--build-only',action='store_true',help='check the disc and compile, without starting the player')
    ap.add_argument('--rebuild',action='store_true',help='discard the cached native library and recompile')
    ap.add_argument('--data',type=Path,default=ROOT/'Play-Data',help='user-owned build cache, saves, settings and logs')
    a=ap.parse_args()
    if platform.machine().lower() not in ('x86_64','amd64') or (not WIN and not sys.platform.startswith('linux')):raise ValueError('This packaged player targets x86-64 Windows and Linux.')
    if sys.version_info < (3,11):raise ValueError('Use Python 3.11 or newer, or the bundled Windows launcher.')
    data=a.data.expanduser().resolve();cfg=cs.read_config(data)
    if a.image:image=Path(a.image)
    elif cfg.get('disc') and Path(cfg['disc']['path']).is_file():image=Path(cfg['disc']['path'])
    else:image=Path(pick()) if not (a.verify_full and not sys.stdin.isatty()) else None
    if not image:return 0
    image=image.expanduser().resolve()
    if a.verify_full:verify_disc(image,data)
    print('Checking your original disc image (read only)...',flush=True)
    boot,_,disc=read_title(image);print(f"{disc['title']} | {disc['disc_id']} v{disc['revision']}",flush=True)
    rec=cfg.get('disc')
    if cs.cached_ok(rec) and Path(rec['path'])==image:print('This image is the fully verified USA v1.02 disc (all sectors match).',flush=True)
    else:
        if rec and rec.get('sha256')==cs.LOGICAL_HASH:print('Note: this image is a verified copy, but the file has changed since verification. The boot program still matches.',flush=True)
        else:print('Boot program matches. Use "Verify entire disc" in the launcher once to confirm every sector.',flush=True)
    state=None
    if a.state:
        state=cs.safe_state(data,a.state);print('Resuming save-state snapshot: '+state.name+'\n(This is a runtime snapshot, not an in-game save.)',flush=True)
    mode='compat' if a.compat or (cfg.get('mode')=='compat' and not a.native) else 'hybrid'
    native=None if mode=='compat' else ensure_native(boot,data/'native'/ARCH,a.rebuild)
    if a.build_only:return 0
    exe=runtime/('PPSSPPWindows64.exe' if WIN else 'PPSSPPSDL');(data/'logs').mkdir(parents=True,exist_ok=True)
    if not exe.is_file():raise ValueError('Missing hybrid runtime. Extract the entire ZIP, or see the runtime build instructions.')
    if not WIN and not os.access(exe,os.X_OK):exe.chmod(exe.stat().st_mode|0o100)
    controls=settings/'controls.ini'
    if not controls.exists():controls.write_text('; No mapping section: use the platform defaults on first launch.\n',encoding='utf-8')
    if native:set_hybrid_cpu(ini)
    if cfg.get('auto_backup',True) and not a.no_backup:
        try:
            b=cs.backup(data)
            if b:print('Save backup: '+str(b),flush=True)
        except (OSError,ValueError) as e:print('Could not update the automatic save backup: '+str(e),flush=True)
    log=data/'logs'/('session-'+time.strftime('%Y%m%d-%H%M%S')+'-'+str(os.getpid())+'.txt')
    env={k:v for k,v in os.environ.items() if k not in ('BP_AOT_PATH','BP_AOT_LOG','BP_AOT_AUDIT')}
    if native:env.update(BP_AOT_PATH=str(native),BP_AOT_LOG=str(log),BP_AOT_AUDIT='1' if a.audit else '0')
    env['XDG_CONFIG_HOME']=str(data/'config')
    if WIN:
        # This runtime and its settings are private to the kit, not any system install.
        (runtime/'installed.txt').write_text(str(stick)+'\n',encoding='utf-8')
    print(('Playing in hybrid mode (local AOT + PPSSPP).\nNative counters: '+str(log)) if native else 'Playing in compatibility-only mode (no local AOT).',flush=True)
    print('In-game saves: '+str(stick/'PSP/SAVEDATA')+'\nControls: Z accept / X back, I J K L move, Space pause menu, Esc runtime menu.',flush=True)
    cmd=[str(exe),'--pause-menu-exit']
    if display['mode']=='windowed':cmd.append('--windowed')
    if state:cmd.append('--state='+str(state))
    cmd.append(str(image))
    rc=subprocess.run(cmd,env=env,cwd=runtime).returncode
    if rc:raise RuntimeError(f'Runtime exited with status {rc}. See README.md > Troubleshooting.')
    if native:
        rows=log.read_text(errors='replace').splitlines() if log.is_file() else []
        counters=next((dict(re.findall(r'(\w+)=(\d+)',s)) for s in reversed(rows) if s.startswith(('sample ','stop '))),{})
        if not any('exact=' in s for s in rows) or not int(counters.get('calls',0)):
            raise RuntimeError('No native execution recorded. Was the player closed before boot? Check '+str(log)+'; --compat is emulation only.')
        print(f"Native execution recorded: {int(counters['calls']):,} calls, {int(counters['distinct']):,} distinct entries.",flush=True)
        if int(counters.get('mismatches',0)) or int(counters.get('invalid_accesses',0)):
            print('The native bridge reported a discrepancy. Keep the session log; try --compat to compare.',file=sys.stderr)
    rows=cs.checkpoints(data)
    if rows:print('Latest in-game save: '+rows[0][2]+'  ('+rows[0][1].name+')',flush=True)
    return 0

if __name__=='__main__':
    try:sys.exit(main())
    except (OSError,ValueError,RuntimeError,subprocess.SubprocessError,zlib.error,InterruptedError) as e:print('Play error:',e,file=sys.stderr);sys.exit(2)
