from __future__ import annotations

import json
import os
import time
from datetime import datetime, timedelta
import queue
from sys import platform
import threading
from time import sleep
from EDlogger import logger
from WindowsKnownPaths import *


class CargoParser:
    """ Parses the Cargo.json file generated by the game. """
    def __init__(self, file_path=None):
        if platform != "win32":
            self.file_path = file_path if file_path else "./linux_ed/Cargo.json"
        else:
            from WindowsKnownPaths import get_path, FOLDERID, UserHandle

            self.file_path = file_path if file_path else (get_path(FOLDERID.SavedGames, UserHandle.current)
                                                          + "/Frontier Developments/Elite Dangerous/Cargo.json")
        self.last_mod_time = None

        # Read json file data
        self.current_data = self.get_cargo_data()

        # self.watch_thread = threading.Thread(target=self._watch_file_thread, daemon=True)
        # self.watch_thread.start()
        # self.status_queue = queue.Queue()

    # def _watch_file_thread(self):
    #     backoff = 1
    #     while True:
    #         try:
    #             self._watch_file()
    #         except Exception as e:
    #             logger.debug('An error occurred when reading status file')
    #             sleep(backoff)
    #             logger.debug('Attempting to restart status file reader after failure')
    #             backoff *= 2
    #
    # def _watch_file(self):
    #     """Detects changes in the Status.json file."""
    #     while True:
    #         status = self.get_cleaned_data()
    #         if status != self.current_data:
    #             self.status_queue.put(status)
    #             self.current_data = status
    #         sleep(1)

    def get_file_modified_time(self) -> float:
        return os.path.getmtime(self.file_path)

    def get_cargo_data(self):
        """Loads data from the JSON file and returns the data.
        {
            "timestamp": "2024-09-22T15:23:23Z",
            "event": "Cargo",
            "Vessel": "Ship",
            "Count": 356,
            "Inventory": [
                {
                    "Name": "tritium",
                    "Count": 356,
                    "Stolen": 0
                },
                { etc. } ]
        }
        """
        # Check if file changed
        if self.get_file_modified_time() == self.last_mod_time:
            logger.debug(f'Cargo.json mod timestamp {self.last_mod_time} unchanged.')
            return self.current_data

        # Read file
        backoff = 1
        while True:
            try:
                with open(self.file_path, 'r') as file:
                    data = json.load(file)
                    break
            except Exception as e:
                logger.debug('An error occurred when reading Cargo.json file')
                sleep(backoff)
                logger.debug('Attempting to restart status file reader after failure')
                backoff *= 2

        # Store data
        self.current_data = data
        self.last_mod_time = self.get_file_modified_time()
        logger.debug(f'Cargo.json mod timestamp {self.last_mod_time} updated.')
        # print(json.dumps(data, indent=4))
        return data

    def get_item(self, item_name) -> dict[any] | None:
        """ Get details of one item. Returns the item detail as below, or None if item does not exist.
            Will not trigger a read of the json file.
        {
            "Name":"tritium",
            "Count":356,
            "Stolen":0
        }
        """
        for good in self.current_data['Inventory']:
            if good['Name'].upper() == item_name.upper():
                # print(json.dumps(good, indent=4))
                return good

        return None


# Usage Example
if __name__ == "__main__":
    parser = CargoParser()
    while True:
        cleaned_data = parser.get_cargo_data()
        item = parser.get_item('Tritium')
        time.sleep(1)