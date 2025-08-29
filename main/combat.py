import time, random
from .input import KeyPoller

class Combat:
    def __init__(self, game, guard):
        self.game=game; self.guard=guard
        self.log=["A guard confronts you!", "Actions: [A]ttack  [D]odge  [F]lee"]

    def roll(self, sides): 
        return random.randint(1,sides)

    def attack(self, atk_bonus, target_ac): 
        return self.roll(20)+atk_bonus >= target_ac

    def damage(self, dice):
        n,s=dice; return sum(self.roll(s) for _ in range(n))

    def render(self):
        W,H=self.game.W,self.game.H
        lines=[" "*W for _ in range(H)]
        pw, ph = min(W-8, 100), min(H-8, 20)
        x0,y0 = (W - pw)//2, (H - ph)//2
        top = '+' + '-'*(pw-2) + '+'
        mid = '|' + ' '*(pw-2) + '|'
        panel=[top] + [mid]*(ph-2) + [top]
        title=" COMBAT "
        tpos=(pw-len(title))//2
        panel[0]='+' + '-'*(tpos-1) + title + '-'*(pw-2 - tpos - len(title)) + '+'
        p=self.game.player; g=self.guard
        stats=f"You HP {p.hp}/{p.max_hp} AC {p.ac}   vs   Guard HP {max(g.hp,0)}/{g.max_hp} AC {g.ac}"
        panel[2]='|' + stats.center(pw-2) + '|'
        start=4
        for i,entry in enumerate(self.log[-(ph-8):]):
            panel[start+i]='|' + entry.ljust(pw-2)[:pw-2] + '|'
        panel[-3]='|' + "Press A/D/F. Q/Esc to quit, Enter to continue.".center(pw-2) + '|'
        for i,row in enumerate(panel):
            r=y0+i
            if 0<=r<H:
                lines[r] = lines[r][:x0] + row + lines[r][x0+len(row):]
        info="Old-School D20: d20+Atk ≥ AC hits; damage by weapon dice."
        lines[-1]=info[:W].ljust(W)
        return lines

    def loop(self):
        scr=self.game.screen
        with KeyPoller() as kp:
            while True:
                scr.draw(self.render())
                keys=set()
                while not keys:
                    keys = kp.poll()
                    time.sleep(0.01)
                if 'q' in keys or 'esc' in keys:
                    self.game.end_game("You quit."); return
                if 'a' in keys:
                    p=self.game.player; g=self.guard
                    if self.attack(p.atk, g.ac):
                        dmg=self.damage(p.dmg); g.hp-=dmg
                        self.log.append(f"You hit ({dmg}). Guard {max(g.hp,0)}/{g.max_hp}.")
                    else:
                        self.log.append("You miss.")
                elif 'd' in keys:
                    self.log.append("You ready to dodge (+2 AC this round).")
                    temp=p.ac+2
                elif 'f' in keys:
                    L=self.game.map.light[int(self.game.player.y)][int(self.game.player.x)]
                    base=0.35 + (0.25 if self.game.player.mode=='RUN' else 0.0) + (0.2 if L==0 else 0.0)
                    if random.random()<base:
                        self.log.append("You slip away into the dark!")
                        self.game.state='PLAY'
                        return
                    else:
                        self.log.append("You fail to escape!")
                if self.guard.hp>0 and self.game.state!='PLAY':
                    p=self.game.player; g=self.guard
                    pac = temp if 'temp' in locals() else p.ac
                    if self.attack(g.atk, pac):
                        dmg=self.damage(g.dmg); p.hp-=dmg
                        self.log.append(f"Guard hits ({dmg}). You {max(p.hp,0)}/{p.max_hp}.")
                    else:
                        self.log.append("Guard misses.")
                if 'temp' in locals(): del temp
                if self.game.player.hp<=0:
                    self.game.end_game("You were defeated."); return
                if self.guard.hp<=0:
                    self.log.append("Guard collapses.")
                    self.guard.knock_out()
                    self.game.add_noise((self.game.player.x,self.game.player.y),3,1.0)
                    self.game.state='PLAY'
                    return
                if len(self.log)>20: self.log=self.log[-20:]
