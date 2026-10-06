"""Coordinate validation and fail-closed frame/input state."""
from collections import OrderedDict
from dataclasses import dataclass
import io
import math
import secrets
import threading
import time
from .messages import text


class SafetyError(ValueError):
    """A refusal people see; `key` names its text in messages.MESSAGES."""
    def __init__(self, key, detail=''):
        self.key, self.detail = key, str(detail)
        super().__init__(text(key, 'en', self.detail))

    def text(self, lang):
        return text(self.key, lang, self.detail)


def check_deadline(deadline, clock):
    if clock() >= deadline:
        raise SafetyError('expired')


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
        raise SafetyError('target_hidden')
    if g.width > 8192 or g.height > 8192 or g.width * g.height > 16_000_000:
        raise SafetyError('target_too_large')


def validate_regions(regions, width, height):
    if not isinstance(regions, list) or not 1 <= len(regions) <= 4:
        raise SafetyError('region_count')
    result = []
    for region in regions:
        if not isinstance(region, (list, tuple)) or len(region) != 4 or not all(integer(v) for v in region):
            raise SafetyError('region_format')
        x, y, w, h = region
        if x < 0 or y < 0 or w <= 0 or h <= 0 or x + w > width or y + h > height:
            raise SafetyError('region_outside')
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
        self.reason = None  # (message key, detail) of the latest pause

    def _pause(self, key, detail=''):
        self.paused = True
        self.control = False
        self.reason = (key, str(detail))
        self.frames.clear()
        raise SafetyError(key, detail)

    def _check(self, point=None):
        if self.paused:
            raise SafetyError(*(self.reason or ('resume_on_pc',)))
        if self.target is None:
            raise SafetyError('not_configured')
        try:
            current = self.backend.snapshot(self.target.hwnd)
            validate_geometry(current)
            if current != self.target:
                self._pause('target_changed')
            if not self.backend.safe(current, point):
                self._pause('target_covered')
            return current
        except SafetyError as error:
            if not self.paused:
                self._pause(error.key, error.detail)
            raise
        except Exception as error:
            self._pause('inspection_failed', error)

    def configure(self, hwnd, regions):
        with self.lock:
            if not integer(hwnd) or hwnd <= 0:
                raise SafetyError('invalid_window')
            g = self.backend.snapshot(hwnd)
            validate_geometry(g)
            selected = validate_regions(regions, g.width, g.height)
            if not self.backend.safe(g):
                raise SafetyError('covered_bring_front')
            self.target, self.regions = g, selected
            self.frames.clear()
            self.control, self.paused, self.reason = False, False, None

    def status(self, lang='en'):
        with self.lock:
            reason = text(self.reason[0], lang, self.reason[1]) if self.reason else ''
            return dict(configured=self.target is not None, paused=self.paused, control=self.control,
                        reason=reason, demo=bool(self.backend.demo), ttl=self.ttl,
                        regions=[list(r) for r in self.regions])

    def capture(self):
        with self.lock:
            g = self._check()
            try:
                image = self.backend.capture(g)
                self._check()
                if image.size != (g.width, g.height):
                    self._pause('capture_size_changed')
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
                self._pause('capture_failed', error)

    def _frame(self, ident, panel):
        if not isinstance(ident, str) or ident not in self.frames:
            raise SafetyError('invalid_frame')
        frame = self.frames[ident]
        check_deadline(frame[0] + self.ttl, self.clock)
        if not integer(panel) or not 0 <= panel < len(frame[3]):
            raise SafetyError('invalid_panel')
        return frame

    def image(self, ident, panel):
        with self.lock:
            self._check()
            return self._frame(ident, panel)[3][panel]

    def click(self, ident, panel, x, y):
        with self.lock:
            if not self.control:
                raise SafetyError('view_only')
            frame = self._frame(ident, panel)
            for v in (x, y):
                if isinstance(v, bool) or not isinstance(v, (int, float)) or not math.isfinite(v) or not 0 <= v < 1:
                    raise SafetyError('invalid_tap')
            if frame[1] != self.target or frame[2] != tuple(self.regions):
                raise SafetyError('config_changed')
            rx, ry, rw, rh = frame[2][panel]
            sx = frame[1].x + rx + math.floor(x * rw)
            sy = frame[1].y + ry + math.floor(y * rh)
            self._check((sx, sy))
            deadline = frame[0] + self.ttl
            check_deadline(deadline, self.clock)
            try:
                self.backend.click(sx, sy, deadline=deadline, clock=self.clock)
            except Exception as error:
                self._pause('input_failed', error)

    def set_control(self, enabled):
        with self.lock:
            if not isinstance(enabled, bool):
                raise SafetyError('control_bool')
            if enabled:
                self._check()
            self.control = enabled

    def stop(self):
        with self.lock:
            self.control, self.paused, self.reason = False, True, ('stopped', '')
            self.frames.clear()

    def resume(self):
        with self.lock:
            if self.target is None:
                raise SafetyError('configure_first')
            g = self.backend.snapshot(self.target.hwnd)
            validate_geometry(g)
            if g.pid != self.target.pid or g.hwnd != self.target.hwnd:
                raise SafetyError('process_changed')
            validate_regions([list(r) for r in self.regions], g.width, g.height)
            if not self.backend.safe(g):
                raise SafetyError('covered')
            self.target = g
            self.frames.clear()
            self.control, self.paused, self.reason = False, False, None

    def preview(self, hwnd):
        with self.lock:
            if not integer(hwnd) or hwnd <= 0:
                raise SafetyError('invalid_window')
            g = self.backend.snapshot(hwnd)
            validate_geometry(g)
            if not self.backend.safe(g):
                raise SafetyError('covered_bring_front')
            image = self.backend.capture(g)
            if self.backend.snapshot(hwnd) != g or not self.backend.safe(g):
                raise SafetyError('changed_during_capture')
            buffer = io.BytesIO()
            image.convert('RGB').save(buffer, 'JPEG', quality=75)
            return g, buffer.getvalue()
