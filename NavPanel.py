from time import sleep

import numpy as np
import cv2
from OCR import OCR

"""
File:navPanel.py    

Description:
  TBD 

Author: Stumpii
"""


class NavPanel:
    def __init__(self, screen, keys):
        self.screen = screen
        self.ocr = OCR()
        self.keys = keys

        self.using_screen = True  # True to use screen, false to use an image. Set screen_image to the image
        self.screen_image = None  # Screen image captured from screen, or loaded by user for testing.
        self.navigation_tab_text = "NAVIGATION"
        self.transactions_tab_text = "TRANSACTIONS"
        self.contacts_tab_text = "CONTACTS"
        self.target_tab_text = "TARGET"

        self.reg = {}
        # The rect is top left x, y, and bottom right x, y in fraction of screen resolution
        # Nav Panel region covers the entire navigation panel.
        self.reg['nav_panel'] = {'rect': [0.10, 0.23, 0.72, 0.83]} # Fraction with ref to the screen/image
        self.reg['tab_bar'] = {'rect': [0.0, 0.0, 1.0, 0.1152]} # Fraction with ref to the Nav Panel
        self.reg['location_panel'] = {'rect': [0.2218, 0.3069, 0.8537, 0.9652]} # Fraction with ref to the Nav Panel

    def __capture_nav_panel_on_screen(self):
        """ Just grab the screen based on the region name/rect.
        Returns an unfiltered image, squared (no perspective).
         """
        rect = self.reg['nav_panel']['rect']

        abs_rect = [int(rect[0] * self.screen.screen_width), int(rect[1] * self.screen.screen_height),
                    int(rect[2] * self.screen.screen_width), int(rect[3] * self.screen.screen_height)]
        image = self.screen.get_screen_region(abs_rect)
        self.screen_image = image

        straightened = self.__nav_panel_perspective_warp(image)
        return straightened

    def __capture_nav_panel_from_image(self):
        """ Just grab the image based on the region name/rect.
        Returns an unfiltered image, squared (no perspective).
         """
        rect = self.reg['nav_panel']['rect']

        if self.screen_image is None:
            return None

        image = self.screen_image

        # Existing size
        h, w, ch = image.shape

        # Crop to leave only the selected rectangle
        x0 = int(w * rect[0])
        y0 = int(h * rect[1])
        x1 = int(w * rect[2])
        y1 = int(h * rect[3])

        # Crop image
        cropped = image[y0:y1, x0:x1]

        straightened = self.__nav_panel_perspective_warp(cropped)
        return straightened

    def capture_nav_panel(self):
        """ Just grab the nav_panel image based on the region name/rect.
            Returns an unfiltered image, squared (no perspective).
            Capture may be from an image or the screen.
         """
        if self.using_screen:
            return self.__capture_nav_panel_on_screen()
        else:
            return self.__capture_nav_panel_from_image()

    def __nav_panel_perspective_warp(self, image):
        """ Performs warping of the nav panel image and returns the result.
        The warping removes the perspective slanting of all sides so the
        returning image has vertical columns and horizontal rows for matching
        or OCR. """
        # Existing size
        h, w, ch = image.shape

        pts1 = np.float32(
            [[w * 0.05, h],  # bottom left
             [w, h * 0.835],  # bottom right
             [0, 0],  # top left
             [w * 0.99, 0]]  # top right
        )
        pts2 = np.float32(
            [[0, h],  # bottom left
             [w, h],  # bottom right
             [0, 0],  # top left
             [w, h * 0.0175]]  # top right
        )
        M = cv2.getPerspectiveTransform(pts1, pts2)
        dst = cv2.warpPerspective(image, M, (w, h))

        return dst

    def capture_location_panel(self):
        """ Get the location panel from within the nav panel.
        Returns an image.
        """
        nav_panel = self.capture_nav_panel()

        # Existing size
        h, w, ch = nav_panel.shape

        # The rect is top left x, y, and bottom right x, y in fraction of screen resolution
        location_panel_rect = self.reg['location_panel']['rect']

        # Crop to leave only the selected rectangle
        x0 = int(w * location_panel_rect[0])
        y0 = int(h * location_panel_rect[1])
        x1 = int(w * location_panel_rect[2])
        y1 = int(h * location_panel_rect[3])

        # Crop image
        location_panel = nav_panel[y0:y1, x0:x1]
        return location_panel

    def capture_tab_bar(self):
        """ Get the tab bar (NAVIGATION/TRANSACTIONS/CONTACTS/TARGET).
        Returns an image.
        """
        nav_pnl = self.capture_nav_panel()

        # Existing size
        h, w, ch = nav_pnl.shape

        # The rect is top left x, y, and bottom right x, y in fraction of screen resolution
        tab_bar_rect = self.reg['tab_bar']['rect']

        # Crop to leave only the selected rectangle
        x0 = int(w * tab_bar_rect[0])
        y0 = int(h * tab_bar_rect[1])
        x1 = int(w * tab_bar_rect[2])
        y1 = int(h * tab_bar_rect[3])

        # Crop image
        tab_bar = nav_pnl[y0:y1, x0:x1]

        #cv2.imwrite('test/nav-panel/tab_bar.png', tab_bar)

        #cv2.imshow("tab_bar", tab_bar)

        return tab_bar

    def show_nav_panel(self):
        """ Shows the Nav Panel. Opens the Nav Panel if not already open.
        Returns True if successful, else False.
        """
        # Is nav panel active?
        active, active_tab_name = self.is_nav_panel_active()
        if active:
            return active, active_tab_name
        else:
            print("Open Nav Panel")
            self.keys.send("UI_Back", repeat=10)
            self.keys.send("HeadLookReset")
            self.keys.send('UIFocus', state=1)
            self.keys.send('UI_Left')
            self.keys.send('UIFocus', state=0)
            sleep(0.5)

            # Check if it opened
            active, active_tab_name = self.is_nav_panel_active()
            if active:
                return active, active_tab_name
            else:
                return False, ""

    def show_navigation_tab(self) -> bool:
        """ Shows the NAVIGATION tab of the Nav Panel. Opens the Nav Panel if not already open.
        Returns True if successful, else False.
        """
        # Show nav panel
        active, active_tab_name = self.show_nav_panel()
        if not active:
            print("Nav Panel could not be opened")
            return False
        elif active_tab_name is self.navigation_tab_text:
            # Do nothing
            return True
        elif active_tab_name is self.transactions_tab_text:
            self.keys.send('CycleNextPanel', hold=0.2)
            sleep(0.2)
            self.keys.send('CycleNextPanel', hold=0.2)
            return True
        elif active_tab_name is self.contacts_tab_text:
            self.keys.send('CycleNextPanel', hold=0.2)
            return True
        elif active_tab_name is self.target_tab_text:
            self.keys.send('CycleNextPanel', hold=0.2)
            return True

    def show_contacts_tab(self) -> bool:
        """ Shows the CONTACTS tab of the Nav Panel. Opens the Nav Panel if not already open.
        Returns True if successful, else False.
        """
        # Show nav panel
        active, active_tab_name = self.show_nav_panel()
        if not active:
            print("Nav Panel could not be opened")
            return False
        elif active_tab_name is self.navigation_tab_text:
            self.keys.send('CycleNextPanel', hold=0.2)
            sleep(0.2)
            self.keys.send('CycleNextPanel', hold=0.2)
            return True
        elif active_tab_name is self.transactions_tab_text:
            self.keys.send('CycleNextPanel', hold=0.2)
            return True
        elif active_tab_name is self.contacts_tab_text:
            # Do nothing
            return True
        elif active_tab_name is self.target_tab_text:
            self.keys.send('CycleNextPanel', hold=0.2)
            sleep(0.2)
            self.keys.send('CycleNextPanel', hold=0.2)
            return True

    def hide_nav_panel(self):
        """ Hides the Nav Panel if open.
        """
        # Is nav panel active?
        active, active_tab_name = self.is_nav_panel_active()
        if active is not None:
            self.keys.send("UI_Back", repeat=10)
            self.keys.send("HeadLookReset")

    def is_nav_panel_active(self) -> (bool, str):
        """ Determine if the Nav Panel is open and if so, which tab is active.
            Returns True if active, False if not and also the string of the tab name.
        """
        tab_bar = self.capture_tab_bar()
        img_selected, ocr_data, ocr_textlist = self.get_selected_item_data(tab_bar, 50, 10)
        if img_selected is not None:
            if self.navigation_tab_text in str(ocr_textlist):
                return True, self.navigation_tab_text
            if self.transactions_tab_text in str(ocr_textlist):
                return True, self.transactions_tab_text
            if self.contacts_tab_text in str(ocr_textlist):
                return True, self.contacts_tab_text
            if self.target_tab_text in str(ocr_textlist):
                return True, self.target_tab_text

        return False, ""

    def get_selected_item_image(self, image, min_w, min_h):
        """ Attempts to find a selected item in an image. The selected item is identified by being solid orange or blue
        rectangle with dark text, instead of orange/blue text on a dark background.
        The image of the first item matching the criteria and minimum width and height is returned, otherwise None.
        """
        # Perform HSV mask
        hsv = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)
        lower_range = np.array([0, 0, 180])
        upper_range = np.array([255, 255, 255])
        mask = cv2.inRange(hsv, lower_range, upper_range)
        masked_image = cv2.bitwise_and(image, image, mask=mask)
        # cv2.imwrite('test/nav-panel/out/masked.png', masked_image)

        # Convert to gray scale and invert
        gray = cv2.cvtColor(masked_image, cv2.COLOR_BGR2GRAY)
        # cv2.imwrite('test/nav-panel/out/gray.png', gray)

        # Convert to B&W to allow FindContours to find rectangles.
        ret, thresh1 = cv2.threshold(gray, 0, 255, cv2.THRESH_OTSU)  # | cv2.THRESH_BINARY_INV)
        # cv2.imwrite('test/nav-panel/out/thresh1.png', thresh1)

        # Finding contours in B&W image. White are the areas detected
        contours, hierarchy = cv2.findContours(thresh1, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

        cropped = image
        for cnt in contours:
            x, y, w, h = cv2.boundingRect(cnt)
            # The whole row will be wider than random matching elements.
            if w > min_w and h > min_h:
                # Drawing a rectangle on the copied image
                # rect = cv2.rectangle(crop, (x, y), (x + w, y + h), (0, 255, 0), 2)

                # Crop to leave only the contour (the selected rectangle)
                cropped = image[y:y + h, x:x + w]

                # cv2.imshow("cropped", cropped)
                return cropped

        # No good matches, then return None
        return None

    def get_selected_item_data(self, image, min_w, min_h):
        """ Attempts to find a selected item in an image. The selected item is identified by being solid orange or blue
            rectangle with dark text, instead of orange/blue text on a dark background.
            The OCR daya of the first item matching the criteria is returned, otherwise None.
            @param image: The image to check.
            @param min_w: The minimum width of the text block.
            @param min_h: The minimum height of the text block.
        """
        # Find the selected item/menu (solid orange)
        img_selected = self.get_selected_item_image(image, min_w, min_h)
        if img_selected is not None:
            # cv2.imshow("img", img_selected)

            #crop_with_border = cv2.copyMakeBorder(img_selected, 40, 20, 20, 20, cv2.BORDER_CONSTANT)
            ocr_data, ocr_textlist = self.ocr.image_ocr_no_filter(img_selected)

            #draw_bounding_boxes(crop_with_border, ocr_data, 0.25)
            #cv2.imwrite(image_out_path, crop_with_border)
            #draw_bounding_boxes(crop_with_border, ocr_data, 0.25)
            #cv2.imwrite(image_out_path, crop_with_border)
            #cv2.imshow("ocr", crop_with_border)
            if ocr_data is not None:
                return img_selected, ocr_data, ocr_textlist
            else:
                return None, None, None

        else:
            return None, None, None

    def lock_destination(self, dst_name) -> bool:
        """ For test to try to lock target to a location.
        """
        res = self.show_navigation_tab()
        if not res:
            print("Nav Panel could not be opened")
            return False

        self.keys.send("UI_Down")  # go down
        self.keys.send("UI_Up", hold=2)  # got to top row

        # tries is the number of rows to go through to find the item looking for
        # the Nav Panel should be filtered to reduce the number of rows in the list
        found = False
        tries = 0
        while not found and tries < 50:
            # Get the location panel image
            loc_panel = self.capture_location_panel()

            # Find the selected item/menu (solid orange)
            img_selected = self.get_selected_item_image(loc_panel, 100, 10)
            if img_selected is not None:
                # OCR the selected item
                ocr_textlist = self.ocr.image_simple_ocr_no_filter(img_selected)
                if ocr_textlist is not None:
                    if dst_name in str(ocr_textlist):
                        self.keys.send("UI_Select", repeat=2)  # Select it and lock target
                        break
                    else:
                        tries += 1
                        self.keys.send("UI_Down")  # up to next item
                        sleep(0.2)

        self.hide_nav_panel()
        return True

    def request_docking(self) -> bool:
        """ Try to request docking.
        """
        res = self.show_contacts_tab()
        if not res:
            print("Contacts Panel could not be opened")
            return False

        # On the CONTACT TAB, go to top selection, do this 4 seconds to ensure at top
        # then go right, which will be "REQUEST DOCKING" and select it
        self.keys.send('UI_Up', hold=4)
        self.keys.send('UI_Right')
        self.keys.send('UI_Select')
        sleep(0.3)

        self.hide_nav_panel()
        return True