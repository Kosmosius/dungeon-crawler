import sys, shutil, time

CSI = "\x1b["
ALT_SCR_ON  = "\x1b[?1049h"
ALT_SCR_OFF = "\x1b[?1049l"
HIDE = "\x1b[?25l"
SHOW = "\x1b[?25h"
HOME = "\x1b[H"
CLEAR = "\x1b[2J"

class Screen:
    """Alternate-screen full-frame renderer. Clears and draws full buffer each frame to avoid artifacts."""
    def __init__(self):
        self.refresh_size()

    def refresh_size(self):
        sz = shutil.get_terminal_size((120, 38))
        self.w = max(60, sz.columns)
        self.h = max(24, sz.lines)

    def enter(self):
        sys.stdout.write(ALT_SCR_ON + HIDE)
        sys.stdout.flush()

    def exit(self):
        sys.stdout.write(SHOW + ALT_SCR_OFF)
        sys.stdout.flush()

    def draw(self, lines):
        self.refresh_size()
        w,h = self.w, self.h
        buf = [ (line[:w]).ljust(w) for line in lines[:h] ]
        if len(buf) < h:
            buf += [" " * w for _ in range(h - len(buf))]
        sys.stdout.write(HOME + CLEAR + "\n".join(buf))
        sys.stdout.flush()
