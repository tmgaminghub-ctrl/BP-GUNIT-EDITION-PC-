#!/usr/bin/env python3
"""Bulletproof PC campaign launcher: drive, checkpoints, verification, backups.
Unofficial offline player. It never downloads a game or a save file, and it
opens the disc image read-only."""
import os,sys,subprocess,threading,time
from pathlib import Path
ROOT=Path(__file__).resolve().parent.parent
sys.path.insert(0,str(ROOT/'launcher'));sys.path.insert(0,str(ROOT/'tools'))
import campaign_store as cs
import tkinter as tk
from tkinter import filedialog,messagebox
from tkinter import ttk
WIN=os.name=='nt'
DATA=ROOT/'Play-Data'
ART=Path(__file__).resolve().parent/'art'
BG='#131510';CARD='#1c1f19';INK='#efece0';DIM='#a3a598';ACC='#f0b23f';LINE='#3b3e33';OK='#8fd08a';WARN='#f0b23f'

def short(p,n=72):
    p=str(p)
    return p if len(p)<=n else p[:18]+' ... '+p[-(n-21):]

def when(ns):
    try:
        if ns<10**12:ns=int(ns)*10**9   # tolerate older records stored in seconds
        return time.strftime('%Y-%m-%d %H:%M',time.localtime(ns/1e9))
    except (OverflowError,OSError,ValueError):return ''

class App:
    def __init__(self,root):
        self.root=root;root.title('Bulletproof PC | Campaign player');root.configure(bg=BG);root.resizable(False,False)
        self.cfg=cs.read_config(DATA);self.busy=False;self.proc=None;self.verify_cancel=False;self.verify_pct=0
        self.disp=cs.normalize_display(self.cfg.get('display'))
        self.lock=cs.InstanceLock(DATA/'.launcher.lock')
        if not self.lock.acquire():
            messagebox.showinfo('Bulletproof PC','The launcher is already open in another window.',parent=root);root.destroy();sys.exit(0)
        self.fam=self.pick_font()
        self.build()
        root.protocol('WM_DELETE_WINDOW',self.close)
        self.refresh()
        if not self.disc_path():
            root.after(350,self.choose_disc)

    def pick_font(self):
        from tkinter import font
        have=set(font.families())
        for n in ('Segoe UI','DejaVu Sans','Liberation Sans','Noto Sans','Arial'):
            if n in have:return n
        return 'TkDefaultFont'

    def F(self,size,weight='normal'):
        return (self.fam,size,weight)

    def card(self,parent,pad=14):
        f=tk.Frame(parent,bg=CARD,highlightbackground=LINE,highlightthickness=1)
        f.pack_propagate(True);return f

    def setup_style(self):
        st=ttk.Style(self.root)
        try:st.theme_use('clam')
        except tk.TclError:pass
        st.configure('BP.TCombobox',fieldbackground='#22261d',background='#2a2d24',foreground=INK,arrowcolor=ACC,bordercolor=LINE,lightcolor=LINE,darkcolor=LINE,selectbackground='#3a3e31',selectforeground=INK,padding=4)
        st.map('BP.TCombobox',fieldbackground=[('readonly','#22261d')],foreground=[('readonly',INK)],background=[('active','#34382c')])
        self.option_font=self.F(9)

    def build(self):
        self.setup_style()
        head=tk.Canvas(self.root,width=928,height=212,bg=BG,highlightthickness=0)
        head.pack(fill='x')
        self.photo=None
        art=ART/'yard.png'
        if art.is_file():
            try:self.photo=tk.PhotoImage(file=str(art));head.create_image(0,0,anchor='nw',image=self.photo)
            except tk.TclError:self.photo=None
        if not self.photo:head.create_rectangle(0,0,928,212,fill='#181b16',outline='')
        head.create_rectangle(20,96,26,158,fill=ACC,outline='')
        head.create_text(40,92,anchor='nw',text='BULLETPROOF',font=self.F(34,'bold'),fill='#f6f1e2')
        head.create_text(42,138,anchor='nw',text='50 CENT: BULLETPROOF - G-UNIT EDITION',font=self.F(11,'bold'),fill='#e6dfc9')
        head.create_text(42,160,anchor='nw',text='PC CAMPAIGN PLAYER  /  native recompiled code + PPSSPP runtime',font=self.F(9),fill='#b8b5a5')
        head.create_text(908,196,anchor='se',text='Unofficial player. Bring your own disc. Nothing is downloaded.',font=self.F(8),fill='#9c9a8c')

        body=tk.Frame(self.root,bg=BG);body.pack(fill='both',expand=True,padx=18,pady=(14,0))

        d=self.card(body);d.pack(fill='x',pady=(0,10))
        row=tk.Frame(d,bg=CARD);row.pack(fill='x',padx=14,pady=(12,4))
        tk.Label(row,text='DISC IMAGE',font=self.F(9,'bold'),bg=CARD,fg=DIM).pack(side='left')
        self.disc_lbl=tk.Label(row,text='',font=self.F(9),bg=CARD,fg=INK,anchor='w',justify='left',wraplength=620)
        self.disc_lbl.pack(side='left',padx=(10,0))
        self.status=tk.Label(d,text='',font=self.F(9),bg=CARD,fg=WARN,anchor='w',justify='left',wraplength=860)
        self.status.pack(fill='x',padx=14)
        btns=tk.Frame(d,bg=CARD);btns.pack(fill='x',padx=14,pady=(6,12))
        self.b_choose=tk.Button(btns,text='Choose disc image...',command=self.choose_disc,bg='#2a2d24',fg=INK,activebackground='#34382c',activeforeground=INK,relief='flat',font=self.F(9,'bold'),padx=12,pady=6,cursor='hand2')
        self.b_choose.pack(side='left')
        self.b_verify=tk.Button(btns,text='Verify entire disc',command=self.verify_disc,bg='#2a2d24',fg=INK,activebackground='#34382c',activeforeground=INK,relief='flat',font=self.F(9),padx=12,pady=6,cursor='hand2')
        self.b_verify.pack(side='left',padx=8)
        self.bar=tk.Canvas(btns,width=280,height=10,bg='#2a2d24',highlightthickness=0)
        self.bar.pack(side='right',pady=8)
        self.fill=self.bar.create_rectangle(0,0,0,10,fill=ACC,outline='')

        v=self.card(body);v.pack(fill='x',pady=(0,10))
        vrow=tk.Frame(v,bg=CARD);vrow.pack(fill='x',padx=14,pady=(11,3))
        tk.Label(vrow,text='DISPLAY',font=self.F(9,'bold'),bg=CARD,fg=DIM).pack(side='left')
        self.dmode=tk.StringVar(value=self.disp['mode'])
        for val,text in (('windowed','Window'),('fullscreen','Full screen')):
            tk.Radiobutton(vrow,text=text,variable=self.dmode,value=val,command=self.display_changed,bg=CARD,fg=INK,selectcolor='#3a3e31',activebackground=CARD,activeforeground=INK,font=self.F(9),highlightthickness=0).pack(side='left',padx=(14,0))
        tk.Label(vrow,text='Window size',font=self.F(9),bg=CARD,fg=DIM).pack(side='left',padx=(22,6))
        self.dsize=tk.StringVar(value=f"{self.disp['width']}x{self.disp['height']}")
        self.sizes=[f'{w}x{h}' for w,h in cs.RESOLUTIONS]
        self.sizebox=ttk.Combobox(vrow,textvariable=self.dsize,values=self.sizes,width=10,state='readonly',style='BP.TCombobox',font=self.F(9))
        self.sizebox.pack(side='left');self.sizebox.bind('<<ComboboxSelected>>',lambda e:self.display_changed())
        tk.Label(vrow,text='Render scale',font=self.F(9),bg=CARD,fg=DIM).pack(side='left',padx=(18,6))
        self.drender=tk.StringVar(value={'auto':'Runtime default','1':'1x · 480x272','2':'2x · 960x544','3':'3x · 1440x816','4':'4x · 1920x1088','5':'5x · 2400x1360'}[self.disp['render']])
        self.renderbox=ttk.Combobox(vrow,textvariable=self.drender,values=['Runtime default','1x · 480x272','2x · 960x544','3x · 1440x816','4x · 1920x1088','5x · 2400x1360'],width=15,state='readonly',style='BP.TCombobox',font=self.F(9))
        self.renderbox.pack(side='left');self.renderbox.bind('<<ComboboxSelected>>',lambda e:self.display_changed())
        self.dvsync=tk.BooleanVar(value=self.disp['vsync'])
        tk.Checkbutton(vrow,text='VSync',variable=self.dvsync,command=self.display_changed,bg=CARD,fg=INK,selectcolor='#3a3e31',activebackground=CARD,activeforeground=INK,font=self.F(9),highlightthickness=0).pack(side='left',padx=(18,0))
        self.dnote=tk.Label(v,text='',font=self.F(8),bg=CARD,fg=DIM,anchor='w',justify='left',wraplength=860)
        self.dnote.pack(fill='x',padx=14,pady=(2,10))

        mid=tk.Frame(body,bg=BG);mid.pack(fill='x')
        p=self.card(mid);p.pack(side='left',fill='both',expand=True)
        tk.Label(p,text='PLAY',font=self.F(9,'bold'),bg=CARD,fg=DIM).pack(anchor='w',padx=14,pady=(12,0))
        self.b_play=tk.Button(p,text='PLAY CAMPAIGN',command=self.play,bg=ACC,fg='#191b15',activebackground='#ffc95c',activeforeground='#191b15',relief='flat',font=self.F(13,'bold'),pady=10,cursor='hand2')
        self.b_play.pack(fill='x',padx=14,pady=(8,6))
        self.mode=tk.StringVar(value='compat' if self.cfg['mode']=='compat' else 'hybrid')
        mrow=tk.Frame(p,bg=CARD);mrow.pack(fill='x',padx=14)
        for val,text in (('hybrid','Hybrid: local recompiled code + runtime (recommended)'),('compat','Runtime only, no local code (comparison)')):
            tk.Radiobutton(mrow,text=text,variable=self.mode,value=val,command=self.save_opts,bg=CARD,fg=INK,selectcolor='#3a3e31',activebackground=CARD,activeforeground=INK,font=self.F(9),highlightthickness=0).pack(anchor='w')
        self.backup=tk.BooleanVar(value=bool(self.cfg['auto_backup']))
        tk.Checkbutton(p,text='Back up game saves automatically on launch',variable=self.backup,command=self.save_opts,bg=CARD,fg=INK,selectcolor='#3a3e31',activebackground=CARD,activeforeground=INK,font=self.F(9),highlightthickness=0).pack(anchor='w',padx=14)
        self.play_status=tk.Label(p,text='',font=self.F(9),bg=CARD,fg=DIM,anchor='w',justify='left',wraplength=420)
        self.play_status.pack(fill='x',padx=14,pady=(6,12))

        c=self.card(mid);c.pack(side='left',fill='both',expand=True,padx=(10,0))
        tk.Label(c,text='CHECKPOINTS  (created by the game)',font=self.F(9,'bold'),bg=CARD,fg=DIM).pack(anchor='w',padx=14,pady=(12,0))
        self.saves=tk.Listbox(c,height=4,bg='#15170f',fg=INK,selectbackground='#4a4b34',selectforeground=INK,relief='flat',font=self.F(9),highlightthickness=1,highlightbackground=LINE,activestyle='none')
        self.saves.pack(fill='x',padx=14,pady=6)
        srow=tk.Frame(c,bg=CARD);srow.pack(fill='x',padx=14,pady=(0,12))
        tk.Button(srow,text='Open save folder',command=self.open_save_folder,bg='#2a2d24',fg=INK,relief='flat',font=self.F(9),padx=10,pady=5,cursor='hand2').pack(side='left')
        tk.Button(srow,text='Back up now',command=self.backup_now,bg='#2a2d24',fg=INK,relief='flat',font=self.F(9),padx=10,pady=5,cursor='hand2').pack(side='left',padx=8)
        self.save_note=tk.Label(c,text='',font=self.F(8),bg=CARD,fg=DIM,anchor='w',justify='left',wraplength=420)
        self.save_note.pack(fill='x',padx=14,pady=(0,12))

        adv=self.card(body);adv.pack(fill='x',pady=(10,0))
        tk.Label(adv,text='RESUME SNAPSHOT  (advanced)',font=self.F(9,'bold'),bg=CARD,fg=DIM).pack(anchor='w',padx=14,pady=(12,0))
        self.states=tk.Listbox(adv,height=3,exportselection=False,bg='#15170f',fg=INK,selectbackground='#4a4b34',selectforeground=INK,relief='flat',font=self.F(9),highlightthickness=1,highlightbackground=LINE,activestyle='none')
        self.states.pack(fill='x',padx=14,pady=6)
        arow=tk.Frame(adv,bg=CARD);arow.pack(fill='x',padx=14,pady=(0,12))
        tk.Button(arow,text='Play selected snapshot',command=self.play_snapshot,bg='#2a2d24',fg=INK,relief='flat',font=self.F(9),padx=10,pady=5,cursor='hand2').pack(side='left')
        tk.Label(arow,text='Runtime captures, not game saves. Use Load Game to continue the story.',font=self.F(8),bg=CARD,fg=DIM).pack(side='left',padx=10)

        foot=tk.Frame(self.root,bg=BG);foot.pack(fill='x',padx=18,pady=10)
        tk.Label(foot,text='Your disc is opened read-only and never modified.  Player data: Play-Data/',font=self.F(8),bg=BG,fg=DIM).pack(side='left')
        tk.Button(foot,text='Player data folder',command=self.open_data_folder,bg=BG,fg=DIM,relief='flat',font=self.F(8,'underline'),cursor='hand2').pack(side='right')

    # --- helpers -------------------------------------------------------
    def disc_path(self):
        p=self.cfg.get('disc')
        try:return Path(p['path']) if p and Path(p['path']).is_file() else None
        except (KeyError,TypeError,OSError):return None

    def save_opts(self):
        self.cfg['mode']=self.mode.get();self.cfg['auto_backup']=bool(self.backup.get());self.cfg['display']=self.display_value()
        cs.save_config(DATA,self.cfg)

    def display_value(self):
        d={'mode':self.dmode.get(),'render':'auto','vsync':bool(self.dvsync.get())}
        try:
            w,h=self.dsize.get().lower().split('x');d['width']=int(w);d['height']=int(h)
        except (AttributeError,ValueError):pass
        label=self.drender.get()
        for value,text in (('1','1x'),('2','2x'),('3','3x'),('4','4x'),('5','5x')):
            if label.startswith(text):d['render']=value
        return cs.normalize_display(d)

    def display_changed(self):
        self.disp=self.display_value();self.save_opts();self.refresh_display()

    def refresh_display(self):
        for widget in (self.sizebox,self.renderbox):
            widget.configure(state='disabled' if self.dmode.get()=='fullscreen' else 'readonly')
        self.dnote.config(text='Applies at the next launch: '+cs.describe_display(self.disp)+'.  In-game: Esc > Settings > Graphics for every other option.')

    def set_status(self,text,color=WARN):self.status.config(text=text,fg=color)

    def open_folder(self,p):
        p=Path(p);p.mkdir(parents=True,exist_ok=True)
        try:
            if WIN:os.startfile(p)
            else:subprocess.Popen(['xdg-open',str(p)],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
        except OSError as e:messagebox.showwarning('Bulletproof PC','Could not open '+str(p)+'\n'+str(e),parent=self.root)

    def open_save_folder(self):self.open_folder(cs.savedir(DATA))
    def open_data_folder(self):self.open_folder(DATA)

    def refresh(self):
        p=self.disc_path()
        self.disc_lbl.config(text=short(p) if p else 'No disc image selected. Choose your complete USA v1.02 .iso or .cso.')
        rec=self.cfg.get('disc')
        if p and rec and cs.cached_ok(rec) and Path(rec['path'])==p:
            self.set_status('Complete disc verified: every sector matches USA v1.02 (ULUS10128).  '+when(rec.get('verified_at',0)),'#8fd08a')
        elif p:self.set_status('Ready. "Verify entire disc" confirms all data once (a few minutes for a full image).',WARN)
        else:self.set_status('Select your own disc image to begin.',WARN)
        if not p:self.bar.coords(self.fill,0,0,0,10)
        self.saves.delete(0,'end');self.rows=cs.checkpoints(DATA)
        if self.rows:
            for ns,d,t in self.rows:self.saves.insert('end',f'{t}    {when(ns)}')
            self.saves.selection_set(0);self.save_note.config(text=f'{len(self.rows)} checkpoint(s) in this profile. Backups: Play-Data/Backups/')
        else:
            self.saves.insert('end','No in-game saves yet. The game creates them in story mode.')
            self.save_note.config(text='Saves live in Play-Data/config/ppsspp/PSP/SAVEDATA/ as normal PSP saves.')
        self.states.delete(0,'end');self.snaps=cs.snapshots(DATA)
        for s in self.snaps:self.states.insert('end',f'{s.name}    {when(s.stat().st_mtime_ns)}')
        if not self.snaps:self.states.insert('end','No snapshots. Save them from the player: Esc > Save state.')
        self.b_play.config(state='normal' if p else 'disabled')
        self.refresh_display()

    # --- disc ----------------------------------------------------------
    def choose_disc(self):
        p=filedialog.askopenfilename(parent=self.root,title='Select your 50 Cent: Bulletproof USA v1.02 disc image',filetypes=[('PSP disc images','*.iso *.cso *.ISO *.CSO'),('All files','*')])
        if not p:return
        try:cs.read_title(p)
        except Exception as e:
            self.set_status('That image cannot be used. It must be the complete USA v1.02 disc (ULUS10128).','#e08a72');return
        self.cfg['disc']={'path':str(Path(p).resolve())};cs.save_config(DATA,self.cfg);self.refresh()
        if messagebox.askyesno('Bulletproof PC','The boot program matches USA v1.02.\n\nCheck every sector now so the launcher can confirm the whole disc? This takes a few minutes for a full image.',parent=self.root):
            self.verify_disc()

    def verify_disc(self):
        p=self.disc_path()
        if not p or self.busy:return
        self.busy=True;self.b_verify.config(state='disabled');self.b_choose.config(state='disabled');self.verify_cancel=False
        self.set_status('Verifying every sector (read only)... 0%',WARN)
        box={'rec':None,'err':None,'pct':0}
        def worker():
            try:box['rec']=cs.verify(p,lambda n,t:box.__setitem__('pct',100*n//t))
            except Exception as e:box['err']=str(e)
        threading.Thread(target=worker,daemon=True).start()
        def poll():
            pct=box['pct'];self.bar.coords(self.fill,0,0,2.8*pct,10)
            if box['rec'] is None and box['err'] is None:
                self.set_status(f'Verifying every sector (read only)... {pct}%',WARN);self.root.after(150,poll);return
            self.busy=False;self.b_verify.config(state='normal');self.b_choose.config(state='normal')
            if box['err']:self.bar.coords(self.fill,0,0,0,10);self.set_status('Verification failed: '+box['err'],'#e08a72');messagebox.showerror('Bulletproof PC',box['err'],parent=self.root)
            else:
                self.cfg['disc']=box['rec'];cs.save_config(DATA,self.cfg);self.bar.coords(self.fill,0,0,280,10);self.refresh()
        poll()

    # --- play ----------------------------------------------------------
    def launch(self,extra=()):
        p=self.disc_path()
        if not p or self.busy:return
        self.save_opts()
        cmd=[sys.executable,'-B',str(ROOT/'play.py'),str(p),'--data',str(DATA),*extra]
        if self.cfg['mode']=='compat':cmd.append('--compat')
        cmd.append('--display-mode='+self.cfg['display']['mode'])
        flags=0x08000000 if WIN else 0   # CREATE_NO_WINDOW: the game has its own window
        try:self.proc=subprocess.Popen(cmd,cwd=str(ROOT),creationflags=flags)
        except OSError as e:messagebox.showerror('Bulletproof PC','Could not start the player: '+str(e),parent=self.root);return
        self.busy=True;self.b_play.config(state='disabled')
        self.play_status.config(text='Playing. The game window opens after the native module is ready.' if self.cfg['mode']=='hybrid' else 'Playing (compatibility mode).')
        self.root.after(500,self.watch)

    def play(self):self.launch()

    def play_snapshot(self):
        sel=self.states.curselection()
        snap=None
        if sel and self.snaps:
            i=sel[0]
            if i<len(self.snaps):snap=self.snaps[i]
        if not snap:messagebox.showinfo('Bulletproof PC','Save a state in the player first (Esc > Save state), or select one in the list.',parent=self.root);return
        self.launch(['--state='+str(snap)])

    def watch(self):
        rc=self.proc.poll() if self.proc else 0
        if rc is None:self.root.after(600,self.watch);return
        self.busy=False;self.proc=None;self.b_play.config(state='normal' if self.disc_path() else 'disabled')
        self.play_status.config(text='Session finished.' if not rc else f'Player exited with code {rc}. See Play-Data/logs/.')
        self.refresh()

    def backup_now(self):
        try:b=cs.backup(DATA,force=True)
        except (OSError,ValueError) as e:messagebox.showerror('Bulletproof PC','Backup failed: '+str(e),parent=self.root);return
        if not b:messagebox.showinfo('Bulletproof PC','There are no in-game saves to back up yet.',parent=self.root);return
        messagebox.showinfo('Bulletproof PC','Saved a copy of your game saves:\n'+str(b),parent=self.root)

    def close(self):
        if self.proc and self.proc.poll() is None:
            if not messagebox.askyesno('Bulletproof PC','The game is still running. Close the launcher anyway? The game keeps running.',parent=self.root):return
        try:self.save_opts()
        except OSError:pass
        self.lock.close();self.root.destroy()

def main():
    root=tk.Tk()
    try:
        dpi=root.winfo_fpixels('1i');root.tk.call('tk','scaling',max(1.0,min(2.0,dpi/72.0)))
    except tk.TclError:pass
    App(root);root.mainloop()

if __name__=='__main__':main()
