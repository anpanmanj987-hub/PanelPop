"""Coordinate validation and fail-closed frame/input state."""
from collections import OrderedDict
from dataclasses import dataclass
import io
import math
import secrets
import threading
import time


class SafetyError(ValueError):
    pass


def check_deadline(deadline, clock):
    if clock() >= deadline:
        raise SafetyError('表示期限が切れました。表示を更新してください。')


@dataclass(frozen=True)
class Geometry:
    hwnd: int
    pid: int
    x: int
    y: int
    width: int
    height: int
    visible: bool
    minimized: bool


def integer(value):
    return isinstance(value, int) and not isinstance(value, bool)


def validate_geometry(g):
    if not g.visible or g.minimized or g.width <= 0 or g.height <= 0:
        raise SafetyError('対象は非表示・最小化、または無効です。PCで確認してください。')
    if g.width > 8192 or g.height > 8192 or g.width * g.height > 16_000_000:
        raise SafetyError('対象が大きすぎます（最大1600万画素）。')


def validate_regions(regions, width, height):
    if not isinstance(regions, list) or not 1 <= len(regions) <= 4:
        raise SafetyError('領域は1〜4個必要です。')
    result = []
    for region in regions:
        if not isinstance(region, (list, tuple)) or len(region) != 4 or not all(integer(v) for v in region):
            raise SafetyError('領域は整数の x, y, 幅, 高さで指定してください。')
        x, y, w, h = region
        if x < 0 or y < 0 or w <= 0 or h <= 0 or x + w > width or y + h > height:
            raise SafetyError('領域がクライアント画面外です。')
        result.append((x, y, w, h))
    return result


class PanelState:
    """One lock covers stop, modes, geometry, capture, frames and OS input."""
    ttl = 2.0
    def __init__(self, backend, clock=time.monotonic):
        self.backend = backend
        self.clock = clock
        self.lock = threading.RLock()
        self.target = None
        self.regions = []
        self.frames = OrderedDict()
        self.control = False
        self.paused = False
        self.reason = ''

    def _pause(self, reason):
        self.paused = True
        self.control = False
        self.reason = str(reason)
        self.frames.clear()
        raise SafetyError(self.reason)

    def _check(self, point=None):
        if self.paused:
            raise SafetyError(self.reason or 'PCで再開してください。')
        if self.target is None:
            raise SafetyError('PCで対象と領域を設定してください。')
        try:
            current = self.backend.snapshot(self.target.hwnd)
            validate_geometry(current)
            if current != self.target:
                self._pause('対象の位置・サイズ・状態が変わりました。PCで再開してください。')
            if not self.backend.safe(current, point):
                self._pause('対象が他のウィンドウに遮られています。PCで確認して再開してください。')
            return current
        except SafetyError as error:
            if not self.paused:
                self._pause(error)
            raise
        except Exception as error:
            self._pause('対象の検査に失敗しました: ' + str(error))

    def configure(self, hwnd, regions):
        with self.lock:
            if not integer(hwnd) or hwnd <= 0:
                raise SafetyError('対象ウィンドウが無効です。')
            g = self.backend.snapshot(hwnd)
            validate_geometry(g)
            selected = validate_regions(regions, g.width, g.height)
            if not self.backend.safe(g):
                raise SafetyError('対象が遮られています。前面に表示してください。')
            self.target, self.regions = g, selected
            self.frames.clear()
            self.control, self.paused, self.reason = False, False, ''

    def status(self):
        with self.lock:
            return dict(configured=self.target is not None, paused=self.paused, control=self.control,
                        reason=self.reason, demo=bool(self.backend.demo), ttl=self.ttl,
                        regions=[list(r) for r in self.regions])

    def capture(self):
        with self.lock:
            g = self._check()
            try:
                image = self.backend.capture(g)
                self._check()
                if image.size != (g.width, g.height):
                    self._pause('撮影サイズが変わりました。')
                blobs = []
                for x, y, w, h in self.regions:
                    buffer = io.BytesIO()
                    image.crop((x, y, x + w, y + h)).convert('RGB').save(buffer, 'JPEG', quality=75)
                    blobs.append(buffer.getvalue())
                ident = secrets.token_urlsafe(18)
                self.frames[ident] = (self.clock(), g, tuple(self.regions), blobs)
                while len(self.frames) > 8:
                    self.frames.popitem(last=False)
                return dict(id=ident, expires_in=self.ttl,
                            panels=[dict(width=r[2], height=r[3]) for r in self.regions])
            except SafetyError:
                raise
            except Exception as error:
                self._pause('撮影に失敗しました: ' + str(error))

    def _frame(self, ident, panel):
        if not isinstance(ident, str) or ident not in self.frames:
            raise SafetyError('フレームが無効です。表示を更新してください。')
        frame = self.frames[ident]
        check_deadline(frame[0] + self.ttl, self.clock)
        if not integer(panel) or not 0 <= panel < len(frame[3]):
            raise SafetyError('領域番号が無効です。')
        return frame

    def image(self, ident, panel):
        with self.lock:
            self._check()
            return self._frame(ident, panel)[3][panel]

    def click(self, ident, panel, x, y):
        with self.lock:
            if not self.control:
                raise SafetyError('閲覧専用です。操作許可はPC側で設定します。')
            frame = self._frame(ident, panel)
            for v in (x, y):
                if isinstance(v, bool) or not isinstance(v, (int, float)) or not math.isfinite(v) or not 0 <= v < 1:
                    raise SafetyError('タップが領域外、または無効です。')
            if frame[1] != self.target or frame[2] != tuple(self.regions):
                raise SafetyError('設定が変わりました。表示を更新してください。')
            rx, ry, rw, rh = frame[2][panel]
            sx = frame[1].x + rx + math.floor(x * rw)
            sy = frame[1].y + ry + math.floor(y * rh)
            self._check((sx, sy))
            deadline = frame[0] + self.ttl
            check_deadline(deadline, self.clock)
            try:
                self.backend.click(sx, sy, deadline=deadline, clock=self.clock)
            except Exception as error:
                self._pause('入力に失敗しました: ' + str(error))

    def set_control(self, enabled):
        with self.lock:
            if not isinstance(enabled, bool):
                raise SafetyError('操作許可はtrue/falseが必要です。')
            if enabled:
                self._check()
            self.control = enabled

    def stop(self):
        with self.lock:
            self.control, self.paused, self.reason = False, True, 'PCで停止しました。再開もPCで行います。'
            self.frames.clear()

    def resume(self):
        with self.lock:
            if self.target is None:
                raise SafetyError('先に対象を設定してください。')
            g = self.backend.snapshot(self.target.hwnd)
            validate_geometry(g)
            if g.pid != self.target.pid or g.hwnd != self.target.hwnd:
                raise SafetyError('対象のプロセスが変わりました。選び直してください。')
            validate_regions([list(r) for r in self.regions], g.width, g.height)
            if not self.backend.safe(g):
                raise SafetyError('対象が遮られています。')
            self.target = g
            self.frames.clear()
            self.control, self.paused, self.reason = False, False, ''

    def preview(self, hwnd):
        with self.lock:
            if not integer(hwnd) or hwnd <= 0:
                raise SafetyError('対象が無効です。')
            g = self.backend.snapshot(hwnd)
            validate_geometry(g)
            if not self.backend.safe(g):
                raise SafetyError('対象が遮られています。前面に表示してください。')
            image = self.backend.capture(g)
            if self.backend.snapshot(hwnd) != g or not self.backend.safe(g):
                raise SafetyError('撮影中に対象が変わりました。')
            buffer = io.BytesIO()
            image.convert('RGB').save(buffer, 'JPEG', quality=75)
            return g, buffer.getvalue()
