"""Visible-desktop capture and conservative, non-atomic Windows input checks."""
import ctypes
from ctypes import wintypes
import sys
from PIL import ImageGrab
from .core import Geometry, SafetyError, check_deadline


class POINT(ctypes.Structure):
    _fields_ = [('x', ctypes.c_int32), ('y', ctypes.c_int32)]


class RECT(ctypes.Structure):
    _fields_ = [('left', ctypes.c_int32), ('top', ctypes.c_int32), ('right', ctypes.c_int32), ('bottom', ctypes.c_int32)]


class MOUSEINPUT(ctypes.Structure):
    _fields_ = [('dx', ctypes.c_int32), ('dy', ctypes.c_int32), ('mouseData', ctypes.c_uint32),
                ('dwFlags', ctypes.c_uint32), ('time', ctypes.c_uint32), ('dwExtraInfo', ctypes.c_size_t)]


class KEYBDINPUT(ctypes.Structure):
    _fields_ = [('wVk', ctypes.c_uint16), ('wScan', ctypes.c_uint16), ('dwFlags', ctypes.c_uint32),
                ('time', ctypes.c_uint32), ('dwExtraInfo', ctypes.c_size_t)]


class HARDWAREINPUT(ctypes.Structure):
    _fields_ = [('uMsg', ctypes.c_uint32), ('wParamL', ctypes.c_uint16), ('wParamH', ctypes.c_uint16)]


class INPUTUNION(ctypes.Union):
    _fields_ = [('mi', MOUSEINPUT), ('ki', KEYBDINPUT), ('hi', HARDWAREINPUT)]


class INPUT(ctypes.Structure):
    _anonymous_ = ('data',)
    _fields_ = [('type', ctypes.c_uint32), ('data', INPUTUNION)]


def load_api():
    if sys.platform != 'win32':
        raise SafetyError('windows_required')
    api = ctypes.WinDLL('user32', use_last_error=True)
    hwnd, boolean, uint = wintypes.HWND, wintypes.BOOL, wintypes.UINT
    signatures = {
        'SetProcessDpiAwarenessContext': ([wintypes.HANDLE], boolean),
        'GetThreadDpiAwarenessContext': ([], wintypes.HANDLE),
        'GetAwarenessFromDpiAwarenessContext': ([wintypes.HANDLE], ctypes.c_int),
        'IsWindow': ([hwnd], boolean), 'IsWindowVisible': ([hwnd], boolean), 'IsIconic': ([hwnd], boolean),
        'GetWindowThreadProcessId': ([hwnd, ctypes.POINTER(ctypes.c_uint32)], ctypes.c_uint32),
        'GetClientRect': ([hwnd, ctypes.POINTER(RECT)], boolean),
        'ClientToScreen': ([hwnd, ctypes.POINTER(POINT)], boolean),
        'GetWindowRect': ([hwnd, ctypes.POINTER(RECT)], boolean),
        'GetTopWindow': ([hwnd], hwnd), 'GetWindow': ([hwnd, uint], hwnd),
        'GetAncestor': ([hwnd, uint], hwnd), 'WindowFromPoint': ([POINT], hwnd),
        'GetWindowTextLengthW': ([hwnd], ctypes.c_int),
        'GetWindowTextW': ([hwnd, wintypes.LPWSTR, ctypes.c_int], ctypes.c_int),
        'SetCursorPos': ([ctypes.c_int, ctypes.c_int], boolean),
        'GetCursorPos': ([ctypes.POINTER(POINT)], boolean),
        'SendInput': ([uint, ctypes.POINTER(INPUT), ctypes.c_int], uint),
    }
    for name, (args, result) in signatures.items():
        function = getattr(api, name)
        function.argtypes, function.restype = args, result
    return api


def load_dwm():
    dwm = ctypes.WinDLL('dwmapi')
    dwm.DwmGetWindowAttribute.argtypes = [wintypes.HWND, wintypes.DWORD, ctypes.c_void_p, wintypes.DWORD]
    dwm.DwmGetWindowAttribute.restype = ctypes.c_long  # HRESULT
    return dwm


def enable_dpi(api):
    # Must execute before capture, window enumeration, or opening any UI.
    if not api.SetProcessDpiAwarenessContext(ctypes.c_void_p(-4)):
        context = api.GetThreadDpiAwarenessContext()
        if api.GetAwarenessFromDpiAwarenessContext(context) != 2:
            raise SafetyError('dpi_failed')


class WindowsBackend:
    demo = False
    dwm = None
    def __init__(self):
        self.api = load_api()
        enable_dpi(self.api)
        self.dwm = load_dwm()
        self._input_target = None

    def cloaked(self, hwnd):
        # Windows 10/11 keep suspended UWP apps and shell surfaces (for example
        # "Windows Input Experience") visible but cloaked: DWM never draws them,
        # so they cannot cover the target. A failed query counts as drawn.
        if self.dwm is None:
            return False
        value = ctypes.c_uint32()  # DWORD; wintypes.DWORD is 8 bytes off Windows
        result = self.dwm.DwmGetWindowAttribute(hwnd, 14, ctypes.byref(value), ctypes.sizeof(value))  # DWMWA_CLOAKED
        return result == 0 and value.value != 0

    def snapshot(self, hwnd):
        api = self.api
        if not api.IsWindow(hwnd):
            raise SafetyError('window_gone')
        pid = ctypes.c_uint32()
        if not api.GetWindowThreadProcessId(hwnd, ctypes.byref(pid)):
            raise SafetyError('process_unknown')
        rect, origin = RECT(), POINT()
        if not api.GetClientRect(hwnd, ctypes.byref(rect)) or not api.ClientToScreen(hwnd, ctypes.byref(origin)):
            raise SafetyError('client_rect_failed')
        return Geometry(int(hwnd), pid.value, origin.x, origin.y, rect.right - rect.left,
                        rect.bottom - rect.top, bool(api.IsWindowVisible(hwnd)), bool(api.IsIconic(hwnd)))

    def windows(self):
        result, hwnd, seen = [], self.api.GetTopWindow(None), set()
        while hwnd and int(hwnd) not in seen and len(seen) < 4096:
            seen.add(int(hwnd))
            if self.api.IsWindowVisible(hwnd) and not self.api.IsIconic(hwnd) and not self.cloaked(hwnd):
                length = min(self.api.GetWindowTextLengthW(hwnd), 1024)
                if length:
                    title = ctypes.create_unicode_buffer(length + 1)
                    self.api.GetWindowTextW(hwnd, title, length + 1)
                    try:
                        g = self.snapshot(hwnd)
                        if g.width > 0 and g.height > 0:
                            result.append(dict(hwnd=int(hwnd), pid=g.pid, title=title.value))
                    except SafetyError:
                        pass
            hwnd = self.api.GetWindow(hwnd, 2)  # GW_HWNDNEXT
        return result

    def safe(self, geometry, point=None):
        api = self.api
        hwnd, seen = api.GetTopWindow(None), set()
        # IsWindowVisible alone says nothing about occlusion. Check every higher
        # top-level window, conservatively including transparent/pop-up windows.
        while hwnd and int(hwnd) != geometry.hwnd:
            if int(hwnd) in seen or len(seen) >= 4096:
                return False
            seen.add(int(hwnd))
            if api.IsWindowVisible(hwnd) and not api.IsIconic(hwnd) and not self.cloaked(hwnd):
                rect = RECT()
                if not api.GetWindowRect(hwnd, ctypes.byref(rect)):
                    return False
                if rect.left < geometry.x + geometry.width and rect.right > geometry.x and rect.top < geometry.y + geometry.height and rect.bottom > geometry.y:
                    return False
            hwnd = api.GetWindow(hwnd, 2)
        if not hwnd:
            return False
        if point is not None:
            hit = api.WindowFromPoint(POINT(*point))
            if not hit or int(api.GetAncestor(hit, 2) or 0) != geometry.hwnd:  # GA_ROOT
                return False
            self._input_target = geometry
        return True

    def capture(self, geometry):
        # Captures visible desktop pixels, never a hidden-window rendering API.
        return ImageGrab.grab(bbox=(geometry.x, geometry.y, geometry.x + geometry.width,
                                   geometry.y + geometry.height), all_screens=True)

    def click(self, x, y, *, deadline, clock):
        target = self._input_target
        self._input_target = None
        check_deadline(deadline, clock)
        if target is None or self.snapshot(target.hwnd) != target or not self.safe(target, (x, y)):
            raise SafetyError('changed_before_input')
        check_deadline(deadline, clock)
        if not self.api.SetCursorPos(x, y):
            raise SafetyError('cursor_move_failed')
        # Cursor movement itself can change hover popups: check again immediately.
        if self.snapshot(target.hwnd) != target or not self.safe(target, (x, y)):
            raise SafetyError('changed_after_move')
        events = (INPUT * 2)()
        events[0].type, events[0].mi.dwFlags = 0, 0x0002  # left down
        events[1].type, events[1].mi.dwFlags = 0, 0x0004  # left up
        # SetCursorPos can succeed while ClipCursor clamps the position. Other
        # desktop input may also move it during the safety checks. Fail closed.
        position = POINT()
        if not self.api.GetCursorPos(ctypes.byref(position)) or (position.x, position.y) != (x, y):
            raise SafetyError('cursor_mismatch')
        check_deadline(deadline, clock)
        sent = self.api.SendInput(2, events, ctypes.sizeof(INPUT))
        self._input_target = None
        if sent != 2:
            # Try to release a potentially accepted button down. Report failure.
            release = (INPUT * 1)()
            release[0].mi.dwFlags = 0x0004
            self.api.SendInput(1, release, ctypes.sizeof(INPUT))
            raise SafetyError('sendinput_failed')
