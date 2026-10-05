import math
import unittest
from dataclasses import replace
from PIL import Image

from panelpop.core import PanelState, Geometry, SafetyError, validate_regions


class Backend:
    """OS fixture: fixed geometry, pixel values, and observable input."""
    demo = True
    def __init__(self):
        self.geometry = Geometry(12, 99, -200, 40, 400, 200, True, False)
        self.covered = False
        self.inputs = []
        self.after_capture = None
    def snapshot(self, hwnd):
        return self.geometry
    def safe(self, geometry, point=None):
        return not self.covered
    def capture(self, geometry):
        image = Image.new('RGB', (400, 200), (30, 60, 90))
        if self.after_capture:
            self.geometry = self.after_capture
        return image
    def click(self, x, y, *, deadline, clock):
        self.inputs.append((x, y))


class CoreTests(unittest.TestCase):
    def setUp(self):
        self.backend = Backend()
        self.now = 100.0
        self.state = PanelState(self.backend, clock=lambda: self.now)
        self.state.configure(12, [[10, 20, 100, 50]])
    def test_rectangle_pixel_bounds(self):
        self.assertEqual(validate_regions([[0, 0, 400, 200]], 400, 200), [(0, 0, 400, 200)])
        for value in ([[0, 0, 0, 5]], [[-1, 0, 2, 2]], [[390, 0, 11, 5]], [[0, 0, math.nan, 5]], [[0, 0, True, 5]], [[0, 0, 1.5, 5]], [], [[0, 0, 1, 1]] * 5):
            with self.subTest(value=value), self.assertRaises(SafetyError):
                validate_regions(value, 400, 200)
    def test_view_only_is_default(self):
        frame = self.state.capture()
        with self.assertRaises(SafetyError):
            self.state.click(frame['id'], 0, .5, .5)
        self.assertEqual(self.backend.inputs, [])
    def test_negative_monitor_origin_and_region_offset(self):
        self.state.set_control(True)
        frame = self.state.capture()
        self.state.click(frame['id'], 0, .5, .5)
        self.assertEqual(self.backend.inputs, [(-140, 85)])
    def test_outside_and_nonfinite_taps_never_click(self):
        self.state.set_control(True)
        frame = self.state.capture()
        for x, y in ((-0.1, .2), (1, .2), (.1, 1), (math.nan, .2), (.1, math.inf), (True, .5)):
            with self.subTest(x=x, y=y), self.assertRaises(SafetyError):
                self.state.click(frame['id'], 0, x, y)
        self.assertEqual(self.backend.inputs, [])
    def test_old_and_unknown_frames_rejected(self):
        self.state.set_control(True)
        frame = self.state.capture()
        self.now += 2.1
        for frame_id in (frame['id'], 'invented'):
            with self.assertRaises(SafetyError):
                self.state.click(frame_id, 0, .5, .5)
        self.assertEqual(self.backend.inputs, [])
    def test_frame_at_exact_deadline_is_rejected(self):
        self.state.set_control(True)
        frame = self.state.capture()
        self.now += 2.0
        with self.assertRaises(SafetyError):
            self.state.click(frame['id'], 0, .5, .5)
        self.assertEqual(self.backend.inputs, [])
    def test_deadline_expiring_in_core_safety_check_never_calls_backend(self):
        self.state.set_control(True)
        frame = self.state.capture()
        self.now += 1.9
        def slow_safe(geometry, point=None):
            if point is not None:
                self.now += .2
            return True
        self.backend.safe = slow_safe
        with self.assertRaises(SafetyError):
            self.state.click(frame['id'], 0, .5, .5)
        self.assertEqual(self.backend.inputs, [])
    def test_geometry_pid_visibility_minimize_change_latches_pause(self):
        changes = ({'x': -199}, {'width': 399}, {'pid': 100}, {'visible': False}, {'minimized': True})
        for change in changes:
            with self.subTest(change=change):
                self.setUp()
                self.state.set_control(True)
                frame = self.state.capture()
                self.backend.geometry = replace(self.backend.geometry, **change)
                with self.assertRaises(SafetyError):
                    self.state.click(frame['id'], 0, .5, .5)
                self.backend.geometry = Geometry(12, 99, -200, 40, 400, 200, True, False)
                with self.assertRaises(SafetyError):
                    self.state.capture()
                self.assertTrue(self.state.status()['paused'])
                self.assertEqual(self.backend.inputs, [])
    def test_capture_rejects_pre_post_change(self):
        self.backend.after_capture = replace(self.backend.geometry, y=41)
        with self.assertRaises(SafetyError):
            self.state.capture()
        self.assertTrue(self.state.status()['paused'])
    def test_occlusion_rejected_and_latched(self):
        self.state.set_control(True)
        frame = self.state.capture()
        self.backend.covered = True
        with self.assertRaises(SafetyError):
            self.state.click(frame['id'], 0, .5, .5)
        self.assertEqual(self.backend.inputs, [])
        self.assertTrue(self.state.status()['paused'])
    def test_stop_clears_frames_and_requires_explicit_resume(self):
        self.state.set_control(True)
        frame = self.state.capture()
        self.state.stop()
        with self.assertRaises(SafetyError):
            self.state.set_control(True)
        with self.assertRaises(SafetyError):
            self.state.click(frame['id'], 0, .5, .5)
        self.state.resume()
        self.assertFalse(self.state.status()['control'])
        self.assertFalse(self.state.status()['paused'])
        with self.assertRaises(SafetyError):
            self.state.click(frame['id'], 0, .5, .5)
    def test_frame_contains_jpeg_for_each_panel(self):
        self.state.configure(12, [[0, 0, 30, 20], [10, 10, 40, 30]])
        frame = self.state.capture()
        import io
        self.assertEqual(frame['panels'], [{'width': 30, 'height': 20}, {'width': 40, 'height': 30}])
        self.assertEqual(Image.open(io.BytesIO(self.state.image(frame['id'], 1))).size, (40, 30))

if __name__ == '__main__':
    unittest.main()
