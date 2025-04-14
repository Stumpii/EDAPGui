from __future__ import annotations

from OCR import OCR
from StatusParser import StatusParser
from time import sleep


class EDSystemMap:
    """ Handles the System Map. """
    def __init__(self, screen, keys, cb, is_odyssey=True):
        self.is_odyssey = is_odyssey
        self.screen = screen
        self.ocr = OCR(screen)
        self.keys = keys
        self.status_parser = StatusParser()
        self.ap_ckb = cb

    def set_sys_map_dest_bookmark(self, ap, bookmark_type, bookmark_position) -> bool:
        """ Set the System Map destination using a bookmark.
        @param ap: EDAP reference.
        @param bookmark_type: The bookmark type (Favorite, Body, Station, Settlement or Navigation), Favorite
         being the default if no match is made with the other options. Navigation is unique in that it uses
         the Nav Panel instead of the System Map.
        @param bookmark_position: The position in the bookmark list, starting at 1 for the first bookmark.
        @return: True if bookmark could be selected, else False
        """
        if self.is_odyssey and bookmark_position != -1:
            # Check if this is a nav-panel bookmark
            if not bookmark_type.lower().startswith("nav"):
                ap.keys.send('SystemMapOpen')
                sleep(3.5)

                ap.keys.send('UI_Left')  # Go to BOOKMARKS
                sleep(.5)
                ap.keys.send('UI_Select')  # Select BOOKMARKS
                sleep(.25)
                ap.keys.send('UI_Right')  # Go to FAVORITES
                sleep(.25)

                # If bookmark type is Fav, do nothing as this is the first item
                if bookmark_type.lower().startswith("bod"):
                    ap.keys.send('UI_Down', repeat=1)  # Go to BODIES
                elif bookmark_type.lower().startswith("sta"):
                    ap.keys.send('UI_Down', repeat=2)  # Go to STATIONS
                elif bookmark_type.lower().startswith("set"):
                    ap.keys.send('UI_Down', repeat=3)  # Go to SETTLEMENTS

                sleep(.25)
                ap.keys.send('UI_Select')  # Select bookmark type, moves you to bookmark list
                ap.keys.send('UI_Left')  # Sometimes the first bookmark is not selected, so we try to force it.
                ap.keys.send('UI_Right')
                sleep(.25)
                ap.keys.send('UI_Down', repeat=bookmark_position - 1)
                sleep(.25)
                ap.keys.send('UI_Select', hold=3.0)

                ap.keys.send('SystemMapOpen')
                sleep(0.5)
                return True

            elif bookmark_type.lower().startswith("nav"):
                # TODO - Move to, or call Nav Panel code instead?
                # This is a nav-panel bookmark
                # get to the Left Panel menu: Navigation
                ap.keys.send("UI_Back", repeat=2)
                ap.keys.send("HeadLookReset")
                ap.keys.send("UIFocus", state=1)
                ap.keys.send("UI_Left")
                ap.keys.send("UIFocus", state=0)  # this gets us over to the Nav panel
                ap.keys.send('UI_Up', hold=4)
                ap.keys.send('UI_Down', repeat=bookmark_position - 1)
                sleep(1.0)
                ap.keys.send('UI_Select')
                sleep(0.25)
                ap.keys.send('UI_Select')
                ap.keys.send("UI_Back")
                ap.keys.send("HeadLookReset")
                return True

        return False
