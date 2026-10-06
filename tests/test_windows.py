import ctypes
import unittest
from PIL import Image
from panelpop.core import Geometry, PanelState, SafetyError
from panelpop.windows import WindowsBackend, RECT


class FakeAPI:
    def __init__(self):
        self.overlap = True
        self.root = 10
        self.sent = 2
        self.cursor = (0, 0)
        self.clip = None
        self.cursor_ok = True
        self.input_calls = []
        self.after_move = None
    def IsWindow(self, hwnd): return True
    def IsWindowVisible(self, hwnd): return True
    def IsIconic(self, hwnd): return False
    def GetWindowThreadProcessId(self, hwnd, pid): pid._obj.value = 44; return 5
    def GetClientRect(self, hwnd, rect):
        rect._obj.left, rect._obj.top, rect._obj.right, rect._obj.bottom = 0, 0, 600, 300
        return 1
    def ClientToScreen(self, hwnd, point):
        point._obj.x, point._obj.y = -800, -100
        return 1
    def GetTopWindow(self, hwnd): return 20 if self.overlap else 10
    def GetWindow(self, hwnd, flag): return 10 if hwnd == 20 else 0
    def GetWindowRect(self, hwnd, rect):
        rect._obj.left, rect._obj.top, rect._obj.right, rect._obj.bottom = -750, -90, -700, -10
        return 1
    def GetAncestor(self, hwnd, flag): return self.root
    def WindowFromPoint(self, point): return 10
    def SetCursorPos(self, x, y):
        self.cursor = self.clip if self.clip is not None else (x, y)
        if self.after_move:
            self.after_move()
        return 1
    def GetCursorPos(self, point):
        point._obj.x, point._obj.y = self.cursor
        return self.cursor_ok
    def SendInput(self, count, inputs, size):
        self.input_calls.append((count, self.cursor))
        return self.sent


class FakeDWM:
    def __init__(self, cloaked=(), result=0):
        self.cloaked, self.result = set(cloaked), result
    def DwmGetWindowAttribute(self, hwnd, attribute, value, size):
        assert attribute == 14 and size == 4  # DWMWA_CLOAKED, DWORD
        value._obj.value = 1 if hwnd in self.cloaked else 0
        return self.result


class WindowsContractTests(unittest.TestCase):
    def setUp(self):
        self.api = FakeAPI()
        self.backend = object.__new__(WindowsBackend)
        self.backend.api = self.api
        self.backend._input_target = None
    def test_client_origin_is_negative_screen_position(self):
        self.assertEqual(self.backend.snapshot(10), Geometry(10, 44, -800, -100, 600, 300, True, False))
    def test_higher_overlapping_window_is_rejected(self):
        self.assertFalse(self.backend.safe(self.backend.snapshot(10)))
        self.api.overlap = False
        self.assertTrue(self.backend.safe(self.backend.snapshot(10)))
    def test_cloaked_higher_window_does_not_occlude(self):
        # Windows 11 keeps never-drawn cloaked windows above normal apps.
        self.backend.dwm = FakeDWM(cloaked={20})
        self.assertTrue(self.backend.safe(self.backend.snapshot(10)))
        self.backend.dwm = FakeDWM(cloaked={30})
        self.assertFalse(self.backend.safe(self.backend.snapshot(10)))
    def test_failed_cloak_query_counts_as_drawn(self):
        self.backend.dwm = FakeDWM(cloaked={20}, result=-2147024809)  # E_INVALIDARG
        self.assertFalse(self.backend.safe(self.backend.snapshot(10)))
    def test_point_root_must_match_target(self):
        self.api.overlap = False
        self.api.root = 30
        self.assertFalse(self.backend.safe(self.backend.snapshot(10), (-700, -50)))
    def test_partial_sendinput_is_an_error(self):
        self.api.overlap = False
        self.assertTrue(self.backend.safe(self.backend.snapshot(10), (-700, -50)))
        self.api.sent = 1
        with self.assertRaises(SafetyError):
            self.backend.click(-700, -50, deadline=2.0, clock=lambda: 0.0)

    def controlled_state(self):
        self.api.overlap = False
        self.now = 100.0
        self.backend.capture = lambda g: Image.new('RGB', (g.width, g.height))
        state = PanelState(self.backend, clock=lambda: self.now)
        state.configure(10, [[0, 0, 600, 300]])
        state.set_control(True)
        return state, state.capture()['id']

    def test_clipped_cursor_never_sends_input_and_pauses(self):
        state, frame = self.controlled_state()
        self.api.clip = (0, 0)
        with self.assertRaises(SafetyError):
            state.click(frame, 0, .5, .5)
        self.assertEqual(self.api.input_calls, [])
        self.assertTrue(state.status()['paused'])
        self.assertFalse(state.status()['control'])

    def test_cursor_read_failure_never_sends_input_and_pauses(self):
        state, frame = self.controlled_state()
        self.api.cursor_ok = False
        with self.assertRaises(SafetyError):
            state.click(frame, 0, .5, .5)
        self.assertEqual(self.api.input_calls, [])
        self.assertTrue(state.status()['paused'])

    def test_deadline_expiring_inside_native_checks_never_sends_input(self):
        state, frame = self.controlled_state()
        self.now = 101.9
        self.api.after_move = lambda: setattr(self, 'now', 102.0)
        with self.assertRaises(SafetyError):
            state.click(frame, 0, .5, .5)
        self.assertEqual(self.api.input_calls, [])
        self.assertTrue(state.status()['paused'])

    def test_fresh_negative_cursor_position_sends_one_click(self):
        state, frame = self.controlled_state()
        state.click(frame, 0, .5, .5)
        self.assertEqual(self.api.input_calls, [(2, (-500, 50))])
        self.assertFalse(state.status()['paused'])

if __name__ == '__main__': unittest.main()
