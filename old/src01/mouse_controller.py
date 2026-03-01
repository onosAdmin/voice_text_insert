import subprocess
import time

try:
    import pyatspi

    HAS_ATSPI = True
except ImportError:
    HAS_ATSPI = False
    pyatspi = None


class MouseController:
    def __init__(self):
        self._initialize_atspi()

    def _initialize_atspi(self):
        if not HAS_ATSPI:
            return
        try:
            pyatspi.setCacheLevel(pyatspi.CacheMode.NONE)
        except Exception:
            pass

    def get_cursor_position(self) -> tuple:
        result = subprocess.run(
            ["xdotool", "getmouselocation", "--shell"], capture_output=True, text=True
        )
        x, y = 0, 0
        for line in result.stdout.splitlines():
            if line.startswith("X="):
                x = int(line[2:])
            elif line.startswith("Y="):
                y = int(line[2:])
        return (x, y)

    def click_at_current_position(self):
        subprocess.run(["xdotool", "click", "1"], check=True)

    def type_text(self, text: str):
        text = text.replace("'", "'\\''")
        subprocess.run(f"xdotool type -- '{text}'", shell=True, check=True)

    def click_and_type(self, text: str):
        self.click_at_current_position()
        time.sleep(0.1)
        self.type_text(text)
