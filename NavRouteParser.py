from __future__ import annotations

import json
import os
import time
from sys import platform
from time import sleep
from EDlogger import logger


class NavRouteParser:
    """ Parses the NavRoute.json file generated by the game. """
    def __init__(self, file_path=None):
        if platform != "win32":
            self.file_path = file_path if file_path else "./linux_ed/NavRoute.json"
        else:
            from WindowsKnownPaths import get_path, FOLDERID, UserHandle

            self.file_path = file_path if file_path else (get_path(FOLDERID.SavedGames, UserHandle.current)
                                                          + "/Frontier Developments/Elite Dangerous/NavRoute.json")
        self.last_mod_time = None

        # Read json file data
        self.current_data = self.get_nav_route_data()

        # self.watch_thread = threading.Thread(target=self._watch_file_thread, daemon=True)
        # self.watch_thread.start()
        # self.status_queue = queue.Queue()

    # def _watch_file_thread(self):
    #     backoff = 1
    #     while True:
    #         try:
    #             self._watch_file()
    #         except Exception as e:
    #             logger.error('An error occurred when reading status file')
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

    def get_nav_route_data(self):
        """Loads data from the JSON file and returns the data. The first entry is the starting system.
        When there is a route:
        {
        "timestamp": "2024-09-29T20:02:20Z", "event": "NavRoute", "Route": [
            {"StarSystem": "Leesti", "SystemAddress": 3932277478114, "StarPos": [72.75000, 48.75000, 68.25000],
             "StarClass": "K"},
            {"StarSystem": "Crucis Sector NY-R b4-3", "SystemAddress": 7268561200585,
             "StarPos": [46.84375, 31.59375, 76.21875], "StarClass": "M"},
            {"StarSystem": "Devataru", "SystemAddress": 5069269509577, "StarPos": [24.28125, 19.34375, 90.93750],
             "StarClass": "M"},
            {"StarSystem": "Scorpii Sector ZU-Y b4", "SystemAddress": 9467047519689,
             "StarPos": [-0.50000, -0.65625, 86.65625], "StarClass": "M"},
            {"StarSystem": "HR 6836", "SystemAddress": 1384866908531, "StarPos": [-7.53125, -11.03125, 98.53125],
             "StarClass": "F"}
        ]}
        or... when route is clear:
        {"timestamp": "2024-09-29T21:06:53Z", "event": "NavRouteClear", "Route": [
        ]}
        """
        # Check if file changed
        if self.get_file_modified_time() == self.last_mod_time:
            logger.debug(f'NavRoute.json mod timestamp {self.last_mod_time} unchanged.')
            return self.current_data

        # Read file
        backoff = 1
        while True:
            try:
                with open(self.file_path, 'r') as file:
                    data = json.load(file)
                    break
            except Exception as e:
                logger.error('An error occurred when reading NavRoute.json file')
                sleep(backoff)
                logger.debug('Attempting to restart status file reader after failure')
                backoff *= 2

        # Store data
        self.current_data = data
        self.last_mod_time = self.get_file_modified_time()
        logger.debug(f'NavRoute.json mod timestamp {self.last_mod_time} updated.')
        # print(json.dumps(data, indent=4))
        return data

    def get_last_system(self) -> str | None:
        """ Gets the final destination (system name) or None.
        """
        # Get latest data
        self.get_nav_route_data()

        # Check if there is a route
        if self.current_data['event'] == "NavRouteClear":
            return None

        if self.current_data['Route'] is None:
            return None

        # Find last system in route
        last_system = self.current_data['Route'][-1]
        # print(json.dumps(last_system, indent=4))
        return last_system['StarSystem']


# Usage Example
if __name__ == "__main__":
    parser = NavRouteParser()
    while True:
        item = parser.get_last_system()
        print(f"last_system: {item}")
        time.sleep(1)
