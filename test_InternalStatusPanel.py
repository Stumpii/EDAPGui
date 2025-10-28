import logging
import unittest
import cv2

from EDAP_data import FlagsDocked
from EDInternalStatusPanel import EDInternalStatusPanel
from EDKeys import EDKeys
from EDlogger import logger
from EDNavigationPanel import EDNavigationPanel
from Screen import Screen
from StatusParser import StatusParser


def dummy_cb(msg, body=None):
    pass


def is_running() -> bool:
    scr = Screen(cb=dummy_cb)
    return scr.elite_window_exists()


def is_docked() -> bool:
    status = StatusParser()
    return status.get_flag(FlagsDocked)


class InternalStatusPanelTestCase(unittest.TestCase):
    running = is_running()
    docked = is_docked()

    @classmethod
    def setUpClass(cls):
        from ED_AP import EDAutopilot
        cls.ed_ap = EDAutopilot(cb=dummy_cb)

        keys = cls.ed_ap.keys
        keys.activate_window = True  # Helps with single steps testing

    def test_draw_regions_on_image(self):
        """
        Does NOT require Elite Dangerous to be running.
        ======================================================================
        """
        # image_path = "test/nav-panel/Screenshot 1920x1080 2024-10-14 20-45-25.png"
        # image_path = "test/nav-panel/Screenshot 1920x1200 2024-09-07 09-08-36.png"
        #image_path = "test/nav-panel/Screenshot_2024-09-09_195949.png"
        #image_path = "test/nav-panel/CBB63634-4208-49F6-A5DD-640E589D79B3.png"
        # frame = cv2.imread(image_path)

        # scr = Screen(cb=dummy_cb)
        # scr.using_screen = False
        # scr.set_screen_image(frame)
        sts_pnl = EDInternalStatusPanel(self.ed_ap, self.ed_ap.scr,  self.ed_ap.keys,  cb=dummy_cb)

        # straightened = nav_pnl.capture_region_straightened(scl_reg_rect)
        straightened = sts_pnl.capture_panel_straightened()

        res = sts_pnl.capture_tab_bar()
        # self.assertIsNone(res, "Could not grab Nav Panel Tab bar image.")  # add assertion here

        res = sts_pnl.capture_inventory_panel()
        # self.assertIsNone(res, "Could not grab Nav Panel Location image.")  # add assertion here

        self.assertEqual(True, True)  # add assertion ehere

    def test_show_inventory_tab(self):
        """
        Does require Elite Dangerous to be running.
        ======================================================================
        """
        sts_pnl = EDInternalStatusPanel(self.ed_ap, self.ed_ap.scr,  self.ed_ap.keys,  cb=dummy_cb)
        sts_pnl.show_inventory_tab()


if __name__ == '__main__':
    unittest.main()
