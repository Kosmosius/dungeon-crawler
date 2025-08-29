import os, sys, select

class KeyPoller:
    """Cross-platform non-blocking key poller with normalized keys."""
    def __init__(self):
        self.is_windows = os.name == 'nt'
        self.fd = None
        self.old = None
        if self.is_windows:
            import msvcrt
            self.msvcrt = msvcrt
        else:
            import termios, tty
            self.termios = termios
            self.tty = tty

    def __enter__(self):
        if not self.is_windows:
            self.fd = sys.stdin.fileno()
            self.old = self.termios.tcgetattr(self.fd)
            self.tty.setcbreak(self.fd)
        return self

    def __exit__(self, t, v, tb):
        if not self.is_windows and self.old is not None:
            self.termios.tcsetattr(self.fd, self.termios.TCSADRAIN, self.old)

    def poll(self):
        keys = set()
        if self.is_windows:
            while self.msvcrt.kbhit():
                ch = self.msvcrt.getwch()
                if ch in ('\x00','\xe0'):
                    k = self.msvcrt.getwch()
                    mapping = {'H':'up','P':'down','K':'left','M':'right'}
                    keys.add(mapping.get(k,''))
                else:
                    keys.add(ch.lower())
        else:
            while select.select([sys.stdin], [], [], 0)[0]:
                ch = sys.stdin.read(1)
                if ch == '\x1b':
                    if select.select([sys.stdin], [], [], 0.001)[0]:
                        nxt = sys.stdin.read(1)
                        if nxt == '[' and select.select([sys.stdin], [], [], 0.001)[0]:
                            k = sys.stdin.read(1)
                            mapping = {'A':'up','B':'down','D':'left','C':'right'}
                            keys.add(mapping.get(k,''))
                        else:
                            keys.add('esc')
                    else:
                        keys.add('esc')
                else:
                    keys.add(ch.lower())
        if '\r' in keys or '\n' in keys:
            keys.add('enter'); keys.discard('\r'); keys.discard('\n')
        return {k for k in keys if k}

