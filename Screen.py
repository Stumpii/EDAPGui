from __future__ import annotations
import typing
import cv2
import win32con
import win32gui
from numpy import array
import json
import dxcam
from dxcam.dxcam import Output, Device
from dxcam.util.io import (enum_dxgi_adapters)

from EDlogger import logger

"""
File:Screen.py    

Description:
  Class to handle screen grabs

Author: sumzer0@yahoo.com
"""

elite_dangerous_window = "Elite - Dangerous (CLIENT)"


def set_focus_elite_window():
    """ set focus to the ED window, if ED does not have focus then the keystrokes will go to the window
    that does have focus. """
    ed_title = "Elite - Dangerous (CLIENT)"

    # TODO - determine if GetWindowText is faster than FindWindow if ED is in foreground
    if win32gui.GetWindowText(win32gui.GetForegroundWindow()) == ed_title:
        return

    handle = win32gui.FindWindow(0, ed_title)
    if handle != 0:
        try:
            win32gui.ShowWindow(handle, win32con.SW_NORMAL)  # give focus to ED
            win32gui.SetForegroundWindow(handle)  # give focus to ED
        except:
            print("set_focus_elite_window ERROR")
            pass


class Screen:
    def __init__(self, cb):
        self.ap_ckb = cb
        self.camera = None
        self.using_screen = True  # True to use screen, false to use an image. Set screen_image to the image
        self._screen_image = None  # Screen image captured from screen, or loaded by user for testing.
        self._last_camera_frame = None

        # Find ED window
        self.ed_rect = self.get_elite_window_rect()
        if self.ed_rect is None:
            self.ap_ckb('log', f"ERROR: Could not find window {elite_dangerous_window}.")
            logger.error(f'Could not find window {elite_dangerous_window}.')
            self.camera = dxcam.create(device_idx=0, output_idx=0,
                                       output_color="BGR")  # Output BGR to match CV2
            self.screen_width = 1920  # Fallback width
            self.screen_height = 1080  # Fallback height
        else:
            # Find adapter and monitor
            (adapter_idx, monitor_idx) = self.find_output(list(self.ed_rect))
            self.camera = dxcam.create(device_idx=adapter_idx, output_idx=monitor_idx,
                                       output_color="BGR")  # Output BGR to match CV2

            self.screen_width = self.ed_rect[2] - self.ed_rect[0]
            self.screen_height = self.ed_rect[3] - self.ed_rect[1]
            logger.debug(f'Found Elite Dangerous window position: {self.ed_rect}')

        self.scales = {
            '1024x768':   [0.39, 0.39],
            '1080x1080':  [0.5, 0.5],
            '1280x800':   [0.48, 0.48],
            '1280x1024':  [0.5, 0.5],
            '1600x900':   [0.6, 0.6],
            '1920x1080':  [0.75, 0.75],
            '1920x1200':  [0.73, 0.73],
            '1920x1440':  [0.8, 0.8],
            '2560x1080':  [0.75, 0.75],
            '2560x1440':  [1.0, 1.0],
            '3440x1440':  [1.0, 1.0],
        }

        # used this to write the self.scales table to the json file
        # self.write_config(self.scales)

        ss = self.read_config()

        # if we read it then point to it, otherwise use the default table above
        if ss is not None:
            self.scales = ss
            logger.debug("read json:" + str(ss))

        # try to find the resolution/scale values in table
        # if not, then take current screen size and divide it out by 3440 x1440
        try:
            scale_key = f"{self.screen_width}x{self.screen_height}"
            self.scaleX, self.scaleY = self.scales[scale_key]
        except:
            # if we don't have a definition for the resolution then use calculation
            self.scaleX = self.screen_width / 3440.0
            self.scaleY = self.screen_height / 1440.0

        logger.debug('screen size: ' + str(self.screen_width) + " " + str(self.screen_height))
        logger.debug('Default scale X, Y: ' + str(self.scaleX) + ", " + str(self.scaleY))

    def find_output(self, region: list[int]) -> tuple[int, int]:
        """ Finds adapter and monitor for a given input rectangle (left, top, right, bottom).
        @param region: Input rectangle (left, top, right, bottom).
        @return: Adapter index and monitor index as tuple.
        """
        x = region[0]
        y = region[1]
        w = region[2] - region[0]
        h = region[3] - region[1]
        p_adapters = enum_dxgi_adapters()
        for i, p_adapter in enumerate(p_adapters):
            device = Device(p_adapter)
            p_outputs = device.enum_outputs()
            for j, p_output in enumerate(p_outputs):
                output = Output(p_output)
                left = output.desc.DesktopCoordinates.left
                top = output.desc.DesktopCoordinates.top
                width, height = output.resolution
                # if the region is inside the output then return this monitor
                if left <= x <= (left + width) and top <= y <= (top + height):
                    # raise exception if the bounds overlaps monitors
                    if x + w > left + width or y + h > top + height:
                        self.ap_ckb('log', f"ERROR: Region {region} overlaps multiple monitors.")
                        logger.error(f'ERROR: Region {region} overlaps multiple monitors.')
                        raise Exception(f"ERROR: Region {region} overlaps multiple monitors.")
                    # adjust region to be relative to this monitor
                    # self._region = [x - left, y - top, w, h]
                    return i, j
        self.ap_ckb('log', f"ERROR: Monitor containing region {region} not found.")
        logger.error(f'ERROR: Monitor containing region {region} not found.')
        raise Exception(f"ERROR: Monitor containing region {region} not found.")

    @staticmethod
    def get_elite_window_rect() -> typing.Tuple[int, int, int, int] | None:
        """ Gets the ED window rectangle.
        Returns (left, top, right, bottom) or None.
        """
        hwnd = win32gui.FindWindow(None, elite_dangerous_window)
        if hwnd:
            return win32gui.GetWindowRect(hwnd)
        return None

    @staticmethod
    def elite_window_exists() -> bool:
        """ Does the ED Client Window exist (i.e. is ED running)
        """
        return bool(win32gui.FindWindow(None, elite_dangerous_window))

    def write_config(self, data, filename='./configs/resolution.json'):
        if data is None:
            data = self.scales
        try:
            with open(filename, "w") as fp:
                json.dump(data, fp, indent=4)
        except Exception as e:
            logger.warning("Screen.py write_config error:" + str(e))

    @staticmethod
    def read_config(filename='./configs/resolution.json'):
        try:
            with open(filename, "r") as fp:
                return json.load(fp)
        except Exception as e:
            logger.warning("Screen.py read_config error :" + str(e))
            return None

    def get_screen_size(self):
        return self.screen_width, self.screen_height

    def get_screen_region(self, reg, rgb=True):
        """ Gets the screen region. Should be BGR only for CV2.
        @param reg: Reg defines a box in pixels.
        @param rgb: Returns RGB when true, else BGR when false.
        """
        image = self.get_screen(int(reg[0]), int(reg[1]), int(reg[2]), int(reg[3]), rgb)
        return image

    def get_screen(self, x_left, y_top, x_right, y_bot, rgb=True):
        """ Gets the screen. Should be BGR only for CV2.
        @param x_left:
        @param y_top:
        @param x_right:
        @param y_bot:
        @param rgb: Returns RGB when true, else BGR when false.
        """
        region = (x_left, y_top, x_right, y_bot)
        frame = self.camera.grab(region=region)  # Frame is in RGB format
        if frame is None:
            if self._last_camera_frame is not None:
                frame = self._last_camera_frame
            else:
                return None

        self._last_camera_frame = frame

        # TODO delete this line when all the rgb=True calls to this function are removed.
        if rgb:
            frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        return frame
        
    def get_screen_rect_pct(self, rect):
        """ Grabs a screenshot and returns the selected region as an image in BGR format for CV2.
        @param rect: A rect array ([L, T, R, B]) in percent (0.0 - 1.0)
        @return: An image defined by the region.
        """
        if self.using_screen:
            abs_rect = self.screen_rect_to_abs(rect)
            image = self.get_screen(abs_rect[0], abs_rect[1], abs_rect[2], abs_rect[3], False)
            return image
        else:
            if self._screen_image is None:
                return None
       
            image = self.crop_image_by_pct(self._screen_image, rect)
            return image

    def screen_rect_to_abs(self, rect):
        """ Converts and array of real percentage screen values to int absolutes.
        @param rect: A rect array ([L, T, R, B]) in percent (0.0 - 1.0)
        @return: A rect array ([L, T, R, B]) in pixels
        """
        return [
            int(rect[0] * self.screen_width),
            int(rect[1] * self.screen_height),
            int(rect[2] * self.screen_width),
            int(rect[3] * self.screen_height)
        ]

    def get_screen_full(self):
        """ Grabs a full screenshot and returns the image in BGR format for CV2.
        """
        if self.using_screen:
            frame = self.camera.grab()  # Frame is in RGB format
            if frame is None:
                if self._last_camera_frame is not None:
                    return self._last_camera_frame
                return None
            self._last_camera_frame = frame
            return frame
        else:
            image = cv2.cvtColor(self._screen_image, cv2.COLOR_RGB2BGR)  # Convert to BGR format for CV2
            return image

    def crop_image_by_pct(self, image, rect):
        """ Crop an image using a percentage values (0.0 - 1.0).
        Rect is an array of crop % [0.10, 0.20, 0.90, 0.95] = [Left, Top, Right, Bottom]
        Returns the cropped image. """
        # Existing size
        h, w, ch = image.shape

        # Crop to leave only the selected rectangle
        x0 = int(w * rect[0])
        y0 = int(h * rect[1])
        x1 = int(w * rect[2])
        y1 = int(h * rect[3])

        # Crop image
        return image[y0:y1, x0:x1]

    def crop_image(self, image, rect):
        """ Crop an image using a pixel values.
        Rect is an array of pixel values [100, 200, 1800, 1600] = [X0, Y0, X1, Y1]
        Returns the cropped image."""
        return image[rect[1]:rect[3], rect[0]:rect[2]]  # i.e. [y:y+h, x:x+w]

    def set_screen_image(self, image):
        """ Use an image instead of a screen capture. Sets the image and also sets the
        screen width and height to the image properties.
        @param image: The image to use.
        """
        self.using_screen = False
        self._screen_image = image

        # Existing size
        h, w, ch = image.shape

        # Set the screen size to the original image size, not the region size
        self.screen_width = w
        self.screen_height = h


# Usage Example
if __name__ == "__main__":
    scr = Screen(cb=None)

    #while True:
    img = scr.get_screen_full()
    ii = 0
