from __future__ import annotations

from time import sleep
import cv2
from EDAP_data import *
from EDKeys import EDKeys
from OCR import OCR
from Screen import Screen
from Screen_Regions import size_scale_for_station
from StatusParser import StatusParser


def goto_ship_view(keys, status_parser) -> bool:
    """ Goto ship view. """
    # Go down to ship view
    while not status_parser.get_gui_focus() == GuiFocusNoFocus:
        keys.send("UI_Back")  # make sure back in ship view

    # self.keys.send("UI_Back", repeat=5)  # make sure back in ship view
    keys.send("UI_Up", repeat=3)  # go to very top (refuel line)

    return True


class InternalStatusPanel:
    """ The Internal (Right hand) Ship Status Panel. """
    def __init__(self, screen, keys, cb):
        self.screen = screen
        self.ocr = OCR(screen)
        self.keys = keys
        self.status_parser = StatusParser()
        self.ap_ckb = cb

        self.modules_tab_text = "MODULES"
        self.fire_groups_tab_text = "FIRE GROUPS"
        self.ship_tab_text = "SHIP"
        self.inventory_tab_text = "INVENTORY"
        self.storage_tab_text = "STORAGE"
        self.status_tab_text = "STATUS"

        # The rect is top left x, y, and bottom right x, y in fraction of screen resolution
        self.reg = {'right_panel': {'rect': [0.25, 0.0, 1.0, 0.5]}}

        self.nav_pnl_tab_width = 140  # Nav panel tab width in pixels at 1920x1080
        self.nav_pnl_tab_height = 35  # Nav panel tab height in pixels at 1920x1080

    def show_right_panel(self):
        """ Shows the Internal (Right) Panel. Opens the Internal Panel if not already open.
        Returns True if successful, else False.
        """
        # Is nav panel active?
        active, active_tab_name = self.is_right_panel_active()
        if active:
            # Store image
            image = self.screen.get_screen_full()
            cv2.imwrite(f'test/internal-panel/int_panel_full.png', image)
            return active, active_tab_name
        else:
            print("Open Internal Panel")
            goto_ship_view(self.keys, self.status_parser)
            self.keys.send("HeadLookReset")

            self.keys.send('UIFocus', state=1)
            self.keys.send('UI_Right')
            self.keys.send('UIFocus', state=0)
            sleep(0.5)

            # Check if it opened
            active, active_tab_name = self.is_right_panel_active()
            if active:
                # Store image
                image = self.screen.get_screen_full()
                cv2.imwrite(f'test/internal-panel/internal_panel_full.png', image)
                return active, active_tab_name
            else:
                return False, ""

    def show_inventory_tab(self) -> bool | None:
        """ Shows the INVENTORY tab of the Nav Panel. Opens the Nav Panel if not already open.
        Returns True if successful, else False.
        """
        # Show nav panel
        active, active_tab_name = self.show_right_panel()
        if active is None:
            return None
        if not active:
            print("Internal (Right) Panel could not be opened")
            return False
        elif active_tab_name is self.inventory_tab_text:
            # Do nothing
            return True
        elif active_tab_name is self.modules_tab_text:
            self.keys.send('CycleNextPanel', repeat=3)
            return True
        elif active_tab_name is self.fire_groups_tab_text:
            self.keys.send('CycleNextPanel', repeat=2)
            return True
        elif active_tab_name is self.ship_tab_text:
            self.keys.send('CycleNextPanel', repeat=1)
            return True
        elif active_tab_name is self.storage_tab_text:
            self.keys.send('CycleNextPanel', repeat=7)
            return True
        elif active_tab_name is self.status_tab_text:
            self.keys.send('CycleNextPanel', repeat=6)
            return True

    def is_right_panel_active(self) -> (bool, str):
        """ Determine if the Nav Panel is open and if so, which tab is active.
            Returns True if active, False if not and also the string of the tab name.
        """
        # Check if nav panel is open
        status = self.status_parser.get_cleaned_data()
        if status['GuiFocus'] != GuiFocusInternalPanel:
            return False, ""

        # Try this 'n' times before giving up
        for i in range(10):
            # Is open, so proceed
            image = self.ocr.capture_region(self.reg['right_panel'])
            # tab_bar = self.capture_tab_bar()
            # if tab_bar is None:
            #     return None

            # Determine the nav panel tab size at this resolution
            scl_row_w, scl_row_h = size_scale_for_station(self.nav_pnl_tab_width, self.nav_pnl_tab_height,
                                                          self.screen.screen_width, self.screen.screen_height)

            img_selected, ocr_data, ocr_textlist = self.ocr.get_highlighted_item_data(image, scl_row_w, scl_row_h)
            if img_selected is not None:
                if self.modules_tab_text in str(ocr_textlist):
                    return True, self.modules_tab_text
                if self.fire_groups_tab_text in str(ocr_textlist):
                    return True, self.fire_groups_tab_text
                if self.ship_tab_text in str(ocr_textlist):
                    return True, self.ship_tab_text
                if self.inventory_tab_text in str(ocr_textlist):
                    return True, self.inventory_tab_text
                if self.storage_tab_text in str(ocr_textlist):
                    return True, self.storage_tab_text
                if self.status_tab_text in str(ocr_textlist):
                    return True, self.status_tab_text

            # Wait and retry
            sleep(1)

            # In case we are on a picture tab, cycle to the next tab
            self.keys.send('CycleNextPanel')

        # Did not find anything
        return False, ""

    def hide_right_panel(self):
        """ Hides the Nav Panel if open.
        """
        # active, active_tab_name = self.is_nav_panel_active()
        # if active is not None:

        # Is nav panel active?
        status = self.status_parser.get_cleaned_data()
        if status['GuiFocus'] == GuiFocusInternalPanel:
            self.keys.send("UI_Back")
            self.keys.send("HeadLookReset")


# Usage Example
if __name__ == "__main__":
    scr = Screen()
    mykeys = EDKeys()
    mykeys.activate_window = True  # Helps with single steps testing
    nav_pnl = InternalStatusPanel(scr, mykeys, None)
    nav_pnl.show_inventory_tab()
