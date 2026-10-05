"""Explicit synthetic demo; never captures desktop or sends OS input."""
import time
from PIL import Image, ImageDraw
from .core import Geometry, SafetyError, check_deadline


class DemoBackend:
    demo = True
    def __init__(self):
        self.last_click = None
    def windows(self):
        return [dict(hwnd=1, pid=1, title='SYNTHETIC DEMO / 合成デモ')]
    def snapshot(self, hwnd):
        if hwnd != 1:
            raise SafetyError('デモ対象は1だけです。')
        return Geometry(1, 1, 0, 0, 960, 540, True, False)
    def safe(self, geometry, point=None):
        return True
    def capture(self, geometry):
        image = Image.new('RGB', (960, 540), '#172539')
        draw = ImageDraw.Draw(image)
        draw.text((30, 25), 'PanelPop SYNTHETIC DEMO - no desktop / no OS input', fill='white')
        draw.text((30, 55), time.strftime('%H:%M:%S'), fill='#84e5ff')
        for index in range(4):
            x, y = 30 + (index % 2) * 470, 100 + (index // 2) * 200
            draw.rounded_rectangle((x, y, x + 430, y + 170), radius=20, fill=('#215b78', '#4f4076', '#216956', '#744538')[index])
            draw.text((x + 20, y + 20), 'Panel ' + str(index + 1), fill='white')
            progress = int(time.monotonic() * 40) % 350
            draw.rectangle((x + 20, y + 80, x + 20 + progress, y + 110), fill='#a6e5eb')
        if self.last_click:
            x, y = self.last_click
            draw.ellipse((x - 12, y - 12, x + 12, y + 12), fill='#ffdd70')
        return image
    def click(self, x, y, *, deadline, clock):
        check_deadline(deadline, clock)
        self.last_click = (x, y)
