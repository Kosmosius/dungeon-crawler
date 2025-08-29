from collections import deque
import math

FACING_TO_DIR = {'^':'UP','v':'DOWN','<':'LEFT','>':'RIGHT'}

MAP_STR = """
########################################
#...........T......######.............E#
#..#######..####...#.....####..T..######
#..#.....#....##...#.....##....#.......#
#..#..T..#.^..##...#..I..##....#..T.^..#
#..#.....#....##...#.....##....#.......#
#..#######..#####..###D##..#######..####
#.....S....T....D.................T....#
##############D##..########..#########.#
#..............##..#......#..#.........#
#..##########..##..#..I...#..#..^....#.#
#..#........#..##..#......#..#.......#.#
#..#..T..I..#..##..########..######..#.#
#..#........#..##....................#.#
#..#####D####..############D##########.#
#......................................#
########################################
""".strip("\n")

class Map:
    def __init__(self, s=MAP_STR):
        self.grid=[list(line) for line in s.splitlines()]
        self.H=len(self.grid); self.W=max(len(r) for r in self.grid)
        for r in self.grid:
            if len(r)<self.W: r += [' '] * (self.W-len(r))
        self.start=None; self.idol=None; self.exit=None; self.guard_spawns=[]
        for y in range(self.H):
            for x in range(self.W):
                ch=self.grid[y][x]
                if ch=='S': self.start=(x+0.5,y+0.5); self.grid[y][x]='.'
                if ch=='I': self.idol=(x+0.5,y+0.5); self.grid[y][x]='.'
                if ch=='E': self.exit=(x+0.5,y+0.5); self.grid[y][x]='.'
                if ch in FACING_TO_DIR:
                    self.guard_spawns.append((x+0.5,y+0.5, FACING_TO_DIR[ch]))
                    self.grid[y][x]='.'
        self.light=[[0 for _ in range(self.W)] for _ in range(self.H)]
        self.recompute_light()

    def inb(self,x,y):
        xi,yi=int(x),int(y)
        return 0<=xi<self.W and 0<=yi<self.H
    def tile(self,x,y):
        xi,yi=int(x),int(y)
        if not self.inb(xi,yi): return '#'
        return self.grid[yi][xi]
    def is_block(self,x,y):
        t=self.tile(x,y); return t in ('#','D')
    def los(self,x1,y1,x2,y2):
        dx=x2-x1; dy=y2-y1
        steps=int(max(1,math.hypot(dx,dy)*3))
        for i in range(1,steps+1):
            t=i/steps; x=x1+dx*t; y=y1+dy*t
            if self.is_block(x,y): return False
        return True
    def open_door(self,tx,ty):
        if self.grid[ty][tx]=='D': self.grid[ty][tx]='='
    def torch_positions(self):
        out=[]
        for y in range(self.H):
            for x in range(self.W):
                if self.grid[y][x]=='T': out.append((x,y))
        return out
    def recompute_light(self):
        self.light=[[0 for _ in range(self.W)] for _ in range(self.H)]
        rad=6
        for (tx,ty) in self.torch_positions():
            self._bfs(tx,ty,rad)
    def _bfs(self,sx,sy,rad):
        q=deque([(sx,sy,0)]); seen=set()
        while q:
            x,y,d=q.popleft()
            if (x,y) in seen: continue
            seen.add((x,y))
            if not (0<=x<self.W and 0<=y<self.H): continue
            if self.grid[y][x]=='#': continue
            val=max(0,rad-d)
            if val>self.light[y][x]: self.light[y][x]=val
            if d<rad:
                for dx,dy in [(1,0),(-1,0),(0,1),(0,-1)]:
                    nx,ny=x+dx,y+dy
                    if 0<=nx<self.W and 0<=ny<self.H and self.grid[ny][nx]!='#':
                        q.append((nx,ny,d+1))
