import time, math, random
from .screen import Screen
from .input import KeyPoller
from .map_data import Map
from .entities import Player, Guard
from .raycast import Raycaster
from .combat import Combat

def clamp(x,a,b): return a if x<a else b if x>b else x

class Game:
    def __init__(self):
        self.screen=Screen()
        self.map=Map()
        sx,sy=self.map.start
        self.player=Player(self,sx,sy)
        self.ray=Raycaster(self)
        self.state='MENU'
        self.msg=""
        self.msg_timer=0.0
        self.minimap=False
        self.legend=False
        self.noises=[]
        self.guards=self._spawn_guards(); self._setup_patrols()
        self.time=0.0
        self.menu_idx=0

    @property
    def W(self): return self.screen.w
    @property
    def H(self): return self.screen.h

    def _spawn_guards(self):
        out=[]
        for i,(x,y,fac) in enumerate(self.map.guard_spawns):
            out.append(Guard(self,x,y,fac,name=f"G{i+1}"))
        return out

    def _setup_patrols(self):
        for g in self.guards:
            gx,gy=int(g.x),int(g.y)
            g.patrol=[(gx+0.5,gy+0.5),(gx+4.5,gy+0.5),(gx+4.5,gy+2.5),(gx+0.5,gy+2.5)]

    def add_noise(self, pos, power=5, ttl=1.0):
        self.noises.append({'pos':pos,'power':power,'ttl':ttl})
    def best_noise(self, pos):
        bx,by=pos; best=None; score=-1
        for n in self.noises:
            d=math.hypot(bx-n['pos'][0], by-n['pos'][1])
            if n['ttl']>0 and d<=n['power'] and (n['power']-d)>score:
                score=n['power']-d; best=n['pos']
        return best
    def cleanup_noises(self, dt):
        for n in self.noises: n['ttl']-=dt
        self.noises=[n for n in self.noises if n['ttl']>0]

    def start_combat(self, guard):
        self.state='COMBAT'
        Combat(self, guard).loop()

    def set_msg(self, s, dur=1.6):
        self.msg=s; self.msg_timer=dur

    def shoot_water(self):
        p=self.player
        if p.water<=0: self.set_msg("No water arrows."); return
        x,y=p.x,p.y; ang=p.ang; step=0.05; maxd=12.0
        hit=False
        for _ in range(int(maxd/step)):
            x+=math.cos(ang)*step; y+=math.sin(ang)*step
            if not self.map.inb(x,y): break
            t=self.map.tile(x,y)
            if t in ('#','D'): break
            if t=='T':
                self.map.grid[int(y)][int(x)]='t'; self.map.recompute_light()
                hit=True; self.set_msg("Pffft. Torch out."); break
        if not hit: self.set_msg("Arrow clatters.")
        p.water-=1; self.add_noise((x,y),3,0.6)

    def throw_noise(self):
        p=self.player
        if p.noise<=0: self.set_msg("No noisemakers."); return
        x,y=p.x,p.y; ang=p.ang; step=0.1; dist=6.0
        for _ in range(int(dist/step)):
            nx,ny=x+math.cos(ang)*step, y+math.sin(ang)*step
            if self.map.is_block(nx,ny): break
            x,y=nx,ny
        self.add_noise((x,y),7,2.0); p.noise-=1; self.set_msg("Clink.")

    def pick_lock_tick(self, dt):
        p=self.player
        if not p.locking: return
        if p.mode=='RUN': p.locking=False; self.set_msg("Too loud."); return
        tx,ty=int(p.x+math.cos(p.ang)*0.7), int(p.y+math.sin(p.ang)*0.7)
        if not (0<=tx<self.map.W and 0<=ty<self.map.H) or self.map.grid[ty][tx] != 'D':
            p.locking=False; self.set_msg("No door."); return
        L=self.map.light[int(p.y)][int(p.x)]
        if L>=1: p.locking=False; self.set_msg("Too bright."); return
        p.lock_t += dt; self.add_noise((p.x,p.y),2,0.2)
        if p.lock_t>=1.5:
            self.map.open_door(tx,ty); p.locking=False; p.lock_t=0.0; self.set_msg("Click.")
        else:
            self.set_msg(f"Picking... {p.lock_t:0.1f}/1.5s", dur=0.5)

    def try_blackjack(self):
        p=self.player
        for g in self.guards:
            if g.ko: continue
            if math.hypot(g.x-p.x,g.y-p.y)<1.1:
                vx,vy=p.x-g.x, p.y-g.y; d=math.hypot(vx,vy)+1e-9; ux,uy=vx/d,vy/d
                fx,fy={'UP':(0,-1),'DOWN':(0,1),'LEFT':(-1,0),'RIGHT':(1,0)}[g.facing]
                if ux*fx+uy*fy < -0.3 and not g.sees_player():
                    g.knock_out(); self.set_msg(f"{g.name} down."); self.add_noise((p.x,p.y),1,0.2); return
                else:
                    self.set_msg("They twist away!"); self.add_noise((p.x,p.y),5,1.0); return
        self.set_msg("No target.")

    def interact_pickups(self):
        p=self.player
        if (not p.has_idol) and self.map.idol and math.hypot(p.x-self.map.idol[0], p.y-self.map.idol[1])<1.0:
            p.has_idol=True; self.set_msg("Idol taken."); self.add_noise((p.x,p.y),5,1.0)
        if p.has_idol and self.map.exit and math.hypot(p.x-self.map.exit[0], p.y-self.map.exit[1])<1.2:
            self.state='GAMEOVER'; self.msg="You vanish into the night with the Idol."

    def hud_line(self):
        p=self.player
        stealth = "BRIGHT" if self.map.light[int(p.y)][int(p.x)]>=1 else "DARK"
        hud = f"Mode:{p.mode}  Light:{stealth}  W:{p.water}  N:{p.noise}  Idol:{'Y' if p.has_idol else 'N'}  HP:{p.hp}/{p.max_hp}"
        hint = self.msg if self.msg_timer>0 else "M:Map  ?:Legend  Z/X:Sneak/Run  Q/Esc:Menu"
        return (hud + " | " + hint)[:self.W].ljust(self.W)

    def render_menu(self):
        W,H=self.W,self.H
        lines=[" "*W for _ in range(H)]
        title=" WIZARDRY × THIEF — ASCII "
        sub="Stealthy dungeon heist in first-person ASCII."
        opts=["Start Heist","Controls","Options","Quit"]
        lines[5]=title.center(W); lines[7]=sub.center(W)
        for i,opt in enumerate(opts):
            prefix="➤ " if i==self.menu_idx else "  "
            text=prefix+opt
            lines[10+i*2]=text.center(W)
        lines[-2]="Use Up/Down (or J/K), Enter to select. 'M' minimap toggle. '?' legend.".center(W)
        lines[-1]=("Viewport auto-scales to your terminal. Windows Terminal recommended.").center(W)
        self.screen.draw(lines)

    def render_controls(self):
        W,H=self.W,self.H
        lines=[" "*W for _ in range(H)]
        items=[
            "Controls: W/S forward/back, A/D strafe, J/L or ←/→ turn",
            "Z Sneak  X Run  B Blackjack  F Water Arrow  N Throw Noise",
            "P Pick Lock (face door, hold in darkness)  M Toggle minimap  ? Legend",
            "Q/Esc back to menu  Enter interact/confirm",
            "Goal: Steal Idol (I) and exit (E). Torches (T) light you up.",
            "When seen, combat starts: A attack, D dodge (+2 AC), F flee."
        ]
        for i,t in enumerate(items):
            lines[6+i]=t.center(W)
        lines[-2]="Press Enter or Esc to return".center(W)
        self.screen.draw(lines)

    def render_options(self, idx):
        W,H=self.W,self.H
        lines=[" "*W for _ in range(H)]
        opts=[f"Minimap: {'ON' if self.minimap else 'OFF'}",
              f"Legend overlay (?): {'ON' if self.legend else 'OFF'}",
              "Back"]
        lines[6]=" Options ".center(W)
        for i,opt in enumerate(opts):
            prefix="➤ " if i==idx else "  "
            lines[9+i*2]=(prefix+opt).center(W)
        lines[-2]="Up/Down to move, Enter to toggle/select, Esc to return".center(W)
        self.screen.draw(lines)

    def render_play(self):
        W,H=self.W,self.H
        if W<80 or H<28:
            lines = ["Terminal too small. Enlarge window (≥80x28).".center(W)] + [""]*(H-1)
            self.screen.draw(lines); return
        view_h = H-1
        frame = self.ray.render(W, view_h, show_minimap=self.minimap, show_legend=self.legend, minimap_size=(18,10))
        frame.append(self.hud_line())
        self.screen.draw(frame)

    def render_gameover(self):
        W,H=self.W,self.H
        lines=[" "*W for _ in range(H)]
        lines[H//2-1]=(" GAME OVER " if not self.msg.startswith("You vanish") else " VICTORY ").center(W)
        lines[H//2]=self.msg.center(W)
        lines[H//2+1]="Press any key to return to menu.".center(W)
        self.screen.draw(lines)

    def loop_menu(self):
        with KeyPoller() as kp:
            self.menu_idx=0
            while self.state=='MENU':
                self.render_menu()
                keys=kp.poll()
                time.sleep(0.02)
                if not keys: continue
                if 'esc' in keys or 'q' in keys:
                    self.state='GAMEOVER'; self.msg="Goodbye."; return False
                if 'up' in keys or 'k' in keys: self.menu_idx=(self.menu_idx-1)%4
                if 'down' in keys or 'j' in keys: self.menu_idx=(self.menu_idx+1)%4
                if 'm' in keys: self.minimap = not self.minimap
                if '?' in keys: self.legend = not self.legend
                if 'enter' in keys:
                    if self.menu_idx==0: self.state='PLAY'; return True
                    if self.menu_idx==1:
                        self.render_controls()
                        while True:
                            ks=kp.poll()
                            if 'enter' in ks or 'esc' in ks: break
                            time.sleep(0.02)
                    if self.menu_idx==2:
                        self.loop_options()
                    if self.menu_idx==3:
                        self.state='GAMEOVER'; self.msg="Goodbye."; return False

    def loop_options(self):
        with KeyPoller() as kp:
            idx=0
            while True:
                self.render_options(idx)
                keys=kp.poll()
                time.sleep(0.02)
                if not keys: continue
                if 'esc' in keys: return
                if 'up' in keys or 'k' in keys: idx=(idx-1)%3
                if 'down' in keys or 'j' in keys: idx=(idx+1)%3
                if 'enter' in keys:
                    if idx==0: self.minimap = not self.minimap
                    elif idx==1: self.legend = not self.legend
                    else: return

    def reset_heist(self):
        self.map=Map()
        sx,sy=self.map.start
        self.player=Player(self,sx,sy)
        self.guards=self._spawn_guards(); self._setup_patrols()
        self.noises=[]; self.time=0.0; self.msg=""; self.msg_timer=0.0
        self.state='PLAY'

    def end_game(self, reason):
        self.state='GAMEOVER'; self.msg=reason

    def loop_play(self):
        with KeyPoller() as kp:
            prev=time.time()
            while self.state=='PLAY':
                now=time.time(); dt=min(now-prev, 1/60); prev=now
                keys=kp.poll()
                p=self.player
                if 'z' in keys: p.mode='SNEAK' if p.mode!='SNEAK' else 'WALK'
                if 'x' in keys: p.mode='RUN' if p.mode!='RUN' else 'WALK'
                if 'm' in keys: self.minimap = not self.minimap
                if '?' in keys: self.legend = not self.legend
                if 'b' in keys: self.try_blackjack()
                if 'f' in keys: self.shoot_water()
                if 'n' in keys: self.throw_noise()
                if 'p' in keys and not p.locking: p.locking=True; p.lock_t=0.0
                if 'esc' in keys or 'q' in keys:
                    self.state='MENU'; return

                rot=(1.8 if p.mode=='RUN' else 1.4)*dt
                if 'left' in keys or 'j' in keys: p.ang-=rot
                if 'right' in keys or 'l' in keys: p.ang+=rot

                sp=p.speed()*dt
                if 'w' in keys or 'up' in keys:
                    nx=p.x+math.cos(p.ang)*sp; ny=p.y+math.sin(p.ang)*sp
                    if not self.map.is_block(nx,p.y): p.x=nx
                    if not self.map.is_block(p.x,ny): p.y=ny
                    self.add_noise((p.x,p.y), p.noise_radius(), 0.25); p.locking=False; p.lock_t=0.0
                if 's' in keys or 'down' in keys:
                    nx=p.x-math.cos(p.ang)*sp; ny=p.y-math.sin(p.ang)*sp
                    if not self.map.is_block(nx,p.y): p.x=nx
                    if not self.map.is_block(p.x,ny): p.y=ny
                    self.add_noise((p.x,p.y), p.noise_radius(), 0.25); p.locking=False; p.lock_t=0.0
                if 'a' in keys:
                    nx=p.x+math.cos(p.ang+math.pi/2)*(-sp); ny=p.y+math.sin(p.ang+math.pi/2)*(-sp)
                    if not self.map.is_block(nx,p.y): p.x=nx
                    if not self.map.is_block(p.x,ny): p.y=ny
                    self.add_noise((p.x,p.y), p.noise_radius(), 0.25); p.locking=False; p.lock_t=0.0
                if 'd' in keys:
                    nx=p.x+math.cos(p.ang+math.pi/2)*(sp); ny=p.y+math.sin(p.ang+math.pi/2)*(sp)
                    if not self.map.is_block(nx,p.y): p.x=nx
                    if not self.map.is_block(p.x,ny): p.y=ny
                    self.add_noise((p.x,p.y), p.noise_radius(), 0.25); p.locking=False; p.lock_t=0.0

                self.pick_lock_tick(dt)
                for g in self.guards: g.step(dt)
                self.cleanup_noises(dt)
                self.time+=dt
                if self.msg_timer>0:
                    self.msg_timer -= dt
                    if self.msg_timer < 0: self.msg_timer = 0
                if int(self.time*2)!=int((self.time-dt)*2):
                    self.map.recompute_light()
                self.interact_pickups()

                self.render_play()
                time.sleep(1/120)

    def loop_gameover(self):
        with KeyPoller() as kp:
            self.render_gameover()
            while True:
                k=kp.poll()
                if k: break
                time.sleep(0.02)
        self.state='MENU'

    def run(self):
        self.screen.enter()
        try:
            while True:
                if self.state=='MENU':
                    if not self.loop_menu(): break
                if self.state=='PLAY':
                    self.loop_play()
                if self.state=='COMBAT':
                    pass
                if self.state=='GAMEOVER':
                    self.loop_gameover()
        finally:
            self.screen.exit()
