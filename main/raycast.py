import math
def clamp(x,a,b): return a if x<a else b if x>b else x

class Raycaster:
    def __init__(self, game):
        self.game=game
        self.fov = math.radians(80)
        self.depth = 30.0

    def raycast(self, sx, sy, ang, maxd):
        x,y=sx,sy; dx=math.cos(ang); dy=math.sin(ang)
        mapX,mapY=int(x),int(y)
        deltaX=abs(1.0/(dx+1e-9)); deltaY=abs(1.0/(dy+1e-9))
        if dx<0: stepX=-1; sideX=(x-mapX)*deltaX
        else: stepX=1; sideX=(mapX+1.0-x)*deltaX
        if dy<0: stepY=-1; sideY=(y-mapY)*deltaY
        else: stepY=1; sideY=(mapY+1.0-y)*deltaY
        dist=0; tile='#'
        while dist<maxd:
            if sideX<sideY: sideX+=deltaX; mapX+=stepX; side=0
            else: sideY+=deltaY; mapY+=stepY; side=1
            if not (0<=mapX<self.game.map.W and 0<=mapY<self.game.map.H):
                dist=maxd; break
            t=self.game.map.grid[mapY][mapX]
            if t in ('#','D'):
                dist=(mapX - x + (1 - stepX)/2)/(dx+1e-9) if side==0 else (mapY - y + (1 - stepY)/2)/(dy+1e-9)
                tile=t; break
        if dist<=0: dist=0.001
        return dist,tile

    def render(self, W, H, show_minimap=False, show_legend=False, minimap_size=(18,10)):
        g=self.game; p=g.player; px,py,pa=p.x,p.y,p.ang
        halfH = H//2
        fov=self.fov
        lines = [ [' '] * W for _ in range(H) ]
        z=[float('inf')]*W
        shade = ' .:-=+*#%@'
        for x in range(W):
            ray = pa - fov/2 + fov*(x/(W-1))
            dist,tile = self.raycast(px,py,ray,self.depth)
            dist *= math.cos(ray - pa)
            z[x]=dist
            ceiling = int(halfH - H/(dist+1e-6))
            floor = H - ceiling
            idx = clamp(int((10.0/(dist+0.1))), 0, len(shade)-1)
            wall_char = '+' if tile=='D' else shade[idx]
            for y in range(H):
                if y < max(0,ceiling):
                    ch = ' '
                elif y >= min(H,floor):
                    t = (y - halfH) / halfH
                    fshade = ' ..,,--=='
                    fi = clamp(int(t*len(fshade)), 0, len(fshade)-1)
                    ch = fshade[fi]
                else:
                    ch = wall_char
                lines[y][x]=ch

        sprites=[]
        for y in range(g.map.H):
            for x in range(g.map.W):
                ch=g.map.grid[y][x]
                if ch in ('T','t'):
                    sprites.append({'x':x+0.5,'y':y+0.5,'ch':ch})
        for guard in g.guards:
            if guard.ko: continue
            sprites.append({'x':guard.x,'y':guard.y,'ch':'G'})
        if g.map.idol and not p.has_idol: sprites.append({'x':g.map.idol[0],'y':g.map.idol[1],'ch':'I'})
        if g.map.exit: sprites.append({'x':g.map.exit[0],'y':g.map.exit[1],'ch':'E'})

        for s in sprites:
            dx,dy = s['x']-px, s['y']-py
            dist = math.hypot(dx,dy)
            angle = math.atan2(dy,dx) - pa
            angle = (angle+math.pi)%(2*math.pi)-math.pi
            if abs(angle) > fov/2 + 0.3: continue
            sx = int((angle+fov/2)/fov * W)
            height = int(H/(dist+1e-6))
            top = max(0, H//2 - height//2)
            bot = min(H-1, H//2 + height//2)
            if 0<=sx<W and dist<z[sx]:
                for y in range(top, bot):
                    lines[y][sx] = s['ch']

        out = [''.join(row) for row in lines]

        if show_minimap:
            mm = self.minimap_text(minimap_size[0], minimap_size[1]).splitlines()
            for i,line in enumerate(mm):
                if i < len(out):
                    s = (line + ' ')[:W]
                    out[i] = s + out[i][len(s):]
        if show_legend and out:
            legend = " @You GGuard T lit t out D door = open I idol E exit # wall "
            out[0] = legend[:W].ljust(W)
        return out

    def minimap_text(self, w, h):
        g=self.game; p=g.player; px=int(p.x); py=int(p.y)
        rx=range(max(0,px-w//2), min(g.map.W, px+w//2))
        ry=range(max(0,py-h//2), min(g.map.H, py+h//2))
        rows=[]
        rows.append("+" + "-"*(len(rx)) + "+")
        for y in ry:
            row=["|"]
            for x in rx:
                ch='.'
                tile=g.map.grid[y][x]
                if int(p.x)==x and int(p.y)==y: ch='@'
                elif tile=='#': ch='#'
                elif tile=='D': ch='D'
                elif tile=='=': ch='='
                elif tile=='T': ch='T'
                elif tile=='t': ch='t'
                elif g.map.idol and int(g.map.idol[0])==x and int(g.map.idol[1])==y and not p.has_idol:
                    ch='I'
                elif g.map.exit and int(g.map.exit[0])==x and int(g.map.exit[1])==y:
                    ch='E'
                else:
                    for guard in g.guards:
                        if guard.ko: continue
                        if int(guard.x)==x and int(guard.y)==y: ch='G'; break
                row.append(ch)
            row.append("|")
            rows.append(''.join(row))
        rows.append("+" + "-"*(len(rx)) + "+")
        return '\n'.join(rows)
