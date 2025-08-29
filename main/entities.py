import math
def hypot(a,b): return math.hypot(a,b)

class Player:
    def __init__(self, game, x,y):
        self.game=game; self.x=x; self.y=y; self.ang=0.0
        self.mode='WALK'
        self.water=3; self.noise=2
        self.has_idol=False
        self.locking=False; self.lock_t=0.0
        self.max_hp=12; self.hp=12; self.ac=12; self.atk=3; self.dmg=(1,8)

    def speed(self): return {'SNEAK':1.6,'WALK':3.2,'RUN':5.0}[self.mode]
    def noise_radius(self): return {'SNEAK':1,'WALK':3,'RUN':6}[self.mode]

class Guard:
    def __init__(self, game, x,y,facing='LEFT', name='Guard'):
        self.game=game; self.x=x; self.y=y; self.facing=facing
        self.state='PATROL'; self.target=None; self.invest_t=0.0; self.ko=False
        self.patrol=[]; self.pidx=0; self.name=name; self.speed=2.2
        self.max_hp=8; self.hp=8; self.ac=11; self.atk=2; self.dmg=(1,6)

    def sees_player(self):
        p=self.game.player
        if not self.game.map.los(self.x,self.y,p.x,p.y): return False
        L=self.game.map.light[int(p.y)][int(p.x)]
        if L>=1: return True
        if hypot(self.x-p.x,self.y-p.y)<=1.6: return True
        return False

    def _move_towards(self, goal, dt, fast=False):
        gx,gy=goal; dx,dy=gx-self.x, gy-self.y
        d=math.hypot(dx,dy); 
        if d<1e-6: return
        ux,uy=dx/d,dy/d; sp=self.speed*(1.4 if fast else 1.0)
        nx,ny=self.x+ux*sp*dt, self.y+uy*sp*dt
        if not self.game.map.is_block(nx,self.y): self.x=nx
        if not self.game.map.is_block(self.x,ny): self.y=ny
        self.facing = 'LEFT' if abs(ux)>abs(uy) and ux<0 else                       'RIGHT' if abs(ux)>abs(uy) and ux>0 else                       'UP' if uy<0 else 'DOWN'

    def step(self, dt):
        if self.ko: return
        p=self.game.player
        if hypot(self.x-p.x,self.y-p.y)<0.8 and (self.sees_player() or self.state=='CHASE'):
            self.game.start_combat(self); return
        if self.sees_player():
            self.state='CHASE'; self.target=(p.x,p.y)
        else:
            heard=self.game.best_noise((self.x,self.y))
            if heard:
                self.state='INVESTIGATE'; self.target=heard; self.invest_t=4.0
        if self.state=='CHASE':
            self.target=(p.x,p.y); self._move_towards(self.target, dt, fast=True)
        elif self.state=='INVESTIGATE':
            if self.invest_t>0 and self.target:
                self._move_towards(self.target, dt, fast=False); self.invest_t-=dt
            else:
                self.state='PATROL'; self.target=None
        elif self.state=='PATROL':
            if self.patrol:
                goal=self.patrol[self.pidx]
                if hypot(self.x-goal[0],self.y-goal[1])<0.2:
                    self.pidx=(self.pidx+1)%len(self.patrol); goal=self.patrol[self.pidx]
                self._move_towards(goal, dt, fast=False)

    def knock_out(self): self.ko=True; self.state='KO'
