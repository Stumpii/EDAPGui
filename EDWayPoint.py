from __future__ import annotations

from time import sleep

from EDAP_data import FlagsDocked
from EDKeys import EDKeys
from EDlogger import logger
import json
from pyautogui import typewrite

from MarketParser import MarketParser
from MousePt import MousePoint
from pathlib import Path

"""
File: EDWayPoint.py    

Description:
   Class will load file called waypoints.json which contains a list of System name to jump to.
   Provides methods to select a waypoint pass into it.  

Author: sumzer0@yahoo.com
"""


class EDWayPoint:
    def __init__(self, ed_ap, is_odyssey=True):
        self.ap = ed_ap
        self.is_odyssey = is_odyssey
        self.filename = './waypoints.json'

        self.waypoints = {}
        #  { "Ninabin": {"DockWithTarget": false, "TradeSeq": None, "Completed": false} }
        # for i, key in enumerate(self.waypoints):
        # self.waypoints[target]['DockWithTarget'] == True ... then go into SC Assist
        # self.waypoints[target]['Completed'] == True
        # if docked and self.waypoints[target]['Completed'] == False
        #    execute_seq(self.waypoints[target]['TradeSeq'])
 
        ss = self.read_waypoints()

        # if we read it then point to it, otherwise use the default table above
        if ss is not None:
            self.waypoints = ss
            logger.debug("EDWayPoint: read json:"+str(ss))    
            
        self.num_waypoints = len(self.waypoints)
     
        #print("waypoints: "+str(self.waypoints))
        self.step = 0
        
        self.mouse = MousePoint()
        self.market_parser = MarketParser()

    def load_waypoint_file(self, filename=None) -> bool:
        if filename is None:
            return False
        
        ss = self.read_waypoints(filename)
        
        if ss is not None:
            self.waypoints = ss
            self.filename = filename
            logger.debug("EDWayPoint: read json:"+str(ss))
            return True

        return False

    def read_waypoints(self, filename='./waypoints/waypoints.json'):
        s = None
        try:
            with open(filename,"r") as fp:
                s = json.load(fp)

            # Perform any checks on the data returned
            # Check if the waypoint data contains the 'GlobalShoppingList' (new requirement)
            if 'GlobalShoppingList' not in s:
                # self.ap.ap_ckb('log', f"Waypoint file is invalid. Check log file for details.")
                logger.warning(f"Waypoint file {filename} is invalid or old version. "
                               f"It does not contain a 'GlobalShoppingList' waypoint.")
                s = None

            # Check the
            err = False
            for key, value in s.items():
                if key == 'GlobalShoppingList':
                    # Special case
                    if 'BuyCommodities' not in value:
                        logger.warning(f"Waypoint file key '{key}' does not contain 'BuyCommodities'.")
                        err = True
                    if 'UpdateCommodityCount' not in value:
                        logger.warning(f"Waypoint file key '{key}' does not contain 'UpdateCommodityCount'.")
                        err = True
                else:
                    # All other cases
                    if 'SystemName' not in value:
                        logger.warning(f"Waypoint file key '{key}' does not contain 'SystemName'.")
                        err = True
                    if 'StationName' not in value:
                        logger.warning(f"Waypoint file key '{key}' does not contain 'StationName'.")
                        err = True
                    if 'GalaxyBookmarkType' not in value:
                        logger.warning(f"Waypoint file key '{key}' does not contain 'GalaxyBookmarkType'.")
                        err = True
                    if 'GalaxyBookmarkNumber' not in value:
                        logger.warning(f"Waypoint file key '{key}' does not contain 'GalaxyBookmarkNumber'.")
                        err = True
                    if 'SystemBookmarkType' not in value:
                        logger.warning(f"Waypoint file key '{key}' does not contain 'SystemBookmarkType'.")
                        err = True
                    if 'SystemBookmarkNumber' not in value:
                        logger.warning(f"Waypoint file key '{key}' does not contain 'SystemBookmarkNumber'.")
                        err = True
                    if 'SellCommodities' not in value:
                        logger.warning(f"Waypoint file key '{key}' does not contain 'SellCommodities'.")
                        err = True
                    if 'BuyCommodities' not in value:
                        logger.warning(f"Waypoint file key '{key}' does not contain 'BuyCommodities'.")
                        err = True
                    if 'UpdateCommodityCount' not in value:
                        logger.warning(f"Waypoint file key '{key}' does not contain 'UpdateCommodityCount'.")
                        err = True
                    if 'FleetCarrierTransfer' not in value:
                        logger.warning(f"Waypoint file key '{key}' does not contain 'FleetCarrierTransfer'.")
                        err = True
                    if 'Skip' not in value:
                        logger.warning(f"Waypoint file key '{key}' does not contain 'Skip'.")
                        err = True
                    if 'Completed' not in value:
                        logger.warning(f"Waypoint file key '{key}' does not contain 'Completed'.")
                        err = True

            if err:
                s = None

        except Exception as e:
            logger.warning("EDWayPoint.py read_waypoints error :" + str(e))

        return s    

    def write_waypoints(self, data, filename='./waypoints/waypoints.json'):
        if data is None:
            data = self.waypoints
        try:
            with open(filename,"w") as fp:
                json.dump(data,fp, indent=4)
        except Exception as e:
            logger.warning("EDWayPoint.py write_waypoints error:" + str(e))

    def mark_waypoint_complete(self, key):
        self.waypoints[key]['Completed'] = True
        self.write_waypoints(data=None, filename='./waypoints/' + Path(self.filename).name)

    def set_next_system(self, ap, target_system) -> bool:
        """ Sets the next system to jump to, or the final system to jump to.
        If the system is already selected or is selected correctly, returns True,
        otherwise False.
        """
        # TODO - Move to ED_AP.py
        # Call sequence to select route
        if self.set_gal_map_destination_text(ap, target_system, None):
            return True
        else:
            # Error setting target
            logger.warning("Error setting waypoint, breaking")
            return False

    def get_waypoint(self) -> tuple[str, dict] | tuple[None, None]:
        """ Returns the next waypoint list or None if we are at the end of the waypoints.
        """
        dest_key = "-1"

        # loop back to beginning if last record is "REPEAT"
        while dest_key == "-1":
            for i, key in enumerate(self.waypoints):
                # skip records we already processed
                if i < self.step:
                    continue

                # if this entry is REPEAT, mark them all as Completed = False
                if self.waypoints[key].get('SystemName', "") == "REPEAT":
                    self.mark_all_waypoints_not_complete()
                    break

                # if this step is marked to skip.. i.e. completed, go to next step
                if (key == "GlobalShoppingList" or self.waypoints[key]['Completed']
                        or self.waypoints[key]['Skip']):
                    continue

                # This is the next uncompleted step
                self.step = i
                dest_key = key
                break
            else:
                return None, None

        return dest_key, self.waypoints[dest_key]

    def mark_all_waypoints_not_complete(self):
        for j, tkey in enumerate(self.waypoints):
            # Ensure 'Completed' key exists before trying to set it
            if 'Completed' in self.waypoints[tkey]:
                self.waypoints[tkey]['Completed'] = False
            else:
                # Handle legacy format where 'Completed' might be missing
                # Or log a warning if the structure is unexpected
                logger.warning(f"Waypoint {tkey} missing 'Completed' key during reset.")
            self.step = 0 
        self.write_waypoints(data=None, filename='./waypoints/' + Path(self.filename).name)
    
    def is_station_targeted(self, dest_key) -> bool:
        """ Check if a station is specified in the waypoint by name or by bookmark."""
        if self.waypoints[dest_key]['StationName'] is not None:
            if self.waypoints[dest_key]['StationName'] != "":
                return True
        if self.waypoints[dest_key]['SystemBookmarkNumber'] is not None:
            if self.waypoints[dest_key]['SystemBookmarkNumber'] != -1:
                return True
        return False

    def set_station_target(self, ap, dest_key):
        """ Sets the target in the System Map. Can be a station, body, etc.
        """
        # check if SystemBookmarkNumber exists to get the transition compatibility with old waypoint lists
        if "SystemBookmarkNumber" in self.waypoints[dest_key]:
            bookmark = self.waypoints[dest_key]['SystemBookmarkNumber']
        else:
            bookmark = -1

        # Set destination via bookmark
        if bookmark != -1:
            self.set_sys_map_destination_bookmark(ap, dest_key)

    def set_sys_map_destination_bookmark(self, ap, dest_key) -> bool:
        """ Set the sys map destination using a bookmark. """
        # TODO - Move this to System Map class
        # Get bookmark type
        if "SystemBookmarkType" in self.waypoints[dest_key]:
            bookmark_type = self.waypoints[dest_key]['SystemBookmarkType']
        else:
            bookmark_type = "Fav"

        # check if SystemBookmarkNumber exists to get the transition compatibility with old waypoint lists
        if "SystemBookmarkNumber" in self.waypoints[dest_key]:
            bookmark = self.waypoints[dest_key]['SystemBookmarkNumber']
        else:
            bookmark = -1

        if self.is_odyssey and bookmark != -1:
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
                sleep(.25)
                ap.keys.send('UI_Down', repeat=bookmark - 1)
                sleep(.25)
                ap.keys.send('UI_Select', hold=3.0)

                ap.keys.send('SystemMapOpen')
                sleep(0.5)
                return True

            elif bookmark_type.lower().startswith("nav"):
                # This is a nav-panel bookmark
                # get to the Left Panel menu: Navigation
                ap.keys.send("UI_Back", repeat=2)
                ap.keys.send("HeadLookReset")
                ap.keys.send("UIFocus", state=1)
                ap.keys.send("UI_Left")
                ap.keys.send("UIFocus", state=0)  # this gets us over to the Nav panel
                ap.keys.send('UI_Up', hold=4)
                ap.keys.send('UI_Down', repeat=bookmark - 1)
                sleep(1.0)
                ap.keys.send('UI_Select')
                sleep(0.25)
                ap.keys.send('UI_Select')
                ap.keys.send("UI_Back")
                ap.keys.send("HeadLookReset")
                return True

        return False

    def set_gal_map_destination_bookmark(self, ap, dest_key) -> bool:
        """ Set the gal map destination using a bookmark. """
        # TODO - Move this to Gal Map class

        # Get bookmark type
        if "GalaxyBookmarkType" in self.waypoints[dest_key]:
            bookmark_type = self.waypoints[dest_key]['GalaxyBookmarkType']
        else:
            bookmark_type = "Fav"

        # check if GalaxyBookmarkNumber exists to get the transition compatibility with old waypoint lists
        if "GalaxyBookmarkNumber" in self.waypoints[dest_key]:
            bookmark = self.waypoints[dest_key]['GalaxyBookmarkNumber']
        else:
            bookmark = -1

        if self.is_odyssey and bookmark != -1:
            ap.keys.send('GalaxyMapOpen')
            sleep(2)

            ap.keys.send('UI_Left')  # Go to BOOKMARKS
            sleep(.5)
            ap.keys.send('UI_Select')  # Select BOOKMARKS
            sleep(.25)
            ap.keys.send('UI_Right')  # Go to FAVORITES
            sleep(.25)

            # If bookmark type is Fav, do nothing as this is the first item
            if bookmark_type.lower().startswith("sys"):
                ap.keys.send('UI_Down')  # Go to SYSTEMS
            elif bookmark_type.lower().startswith("bod"):
                ap.keys.send('UI_Down', repeat=2)  # Go to BODIES
            elif bookmark_type.lower().startswith("sta"):
                ap.keys.send('UI_Down', repeat=3)  # Go to STATIONS
            elif bookmark_type.lower().startswith("set"):
                ap.keys.send('UI_Down', repeat=4)  # Go to SETTLEMENTS

            sleep(.25)
            ap.keys.send('UI_Select')  # Select bookmark type, moves you to bookmark list
            sleep(.25)
            ap.keys.send('UI_Down', repeat=bookmark - 1)
            sleep(.25)
            ap.keys.send('UI_Select', hold=3.0)

            ap.keys.send('GalaxyMapOpen')
            sleep(0.5)
            return True

        return False

    def set_gal_map_destination_text(self, ap, target_name, target_select_cb=None) -> bool:
        """ Call either the Odyssey or Horizons version of the Galactic Map sequence. """
        # TODO - Move this to Gal Map class
        if not self.is_odyssey:
            return self.set_gal_map_destination_text_horizons(ap, target_name, target_select_cb)
        else:
            return self.set_gal_map_destination_text_odyssey(ap, target_name, target_select_cb)

    @staticmethod
    def set_gal_map_destination_text_horizons(ap, target_name, target_select_cb=None) -> bool:
        """ This sequence for the Horizons. """
        # TODO - Move this to Gal Map class
        ap.keys.send('GalaxyMapOpen')
        sleep(2)
        ap.keys.send('CycleNextPanel')
        sleep(1)
        ap.keys.send('UI_Select')
        sleep(2)
              
        typewrite(target_name, interval=0.25)
        sleep(1)         
  
        # send enter key
        ap.keys.send_key('Down', 28)
        sleep(0.05)
        ap.keys.send_key('Up', 28)
        
        sleep(7)
        ap.keys.send('UI_Right')
        sleep(1)
        ap.keys.send('UI_Select')   
        
        # if got passed through the ship() object, lets call it to see if a target has been
        # selected yet.. otherwise we wait.  If long route, it may take a few seconds      
        if target_select_cb is not None:
            while not target_select_cb()['target']:
                sleep(1)
                
        ap.keys.send('GalaxyMapOpen')
        sleep(2)
        return True

    @staticmethod
    def set_gal_map_destination_text_odyssey(ap, target_name, target_select_cb=None) -> bool:
        """ This sequence for the Odyssey. """
        # TODO - Move this to Gal Map class

        # Check if the current nav route is to the target system
        last_nav_route_sys = ap.nav_route.get_last_system()
        if last_nav_route_sys.upper() == target_name.upper():
            return True

        ap.keys.send('GalaxyMapOpen')
        sleep(2)

        # navigate to and select: search field
        ap.keys.send('UI_Up')
        sleep(0.05)
        ap.keys.send('UI_Select')
        sleep(0.05)

        #print("Target:"+target_name)       
        # type in the System name
        typewrite(target_name, interval=0.25)
        sleep(0.05)

        # send enter key (removes focus out of input field)
        ap.keys.send_key('Down', 28)  # 28=ENTER
        sleep(0.05)
        ap.keys.send_key('Up', 28)  # 28=ENTER
        sleep(0.05)

        # According to some reports, the ENTER key does not always reselect the text
        # box, so this down and up will reselect the text box.
        ap.keys.send('UI_Down')
        sleep(0.05)
        ap.keys.send('UI_Up')
        sleep(0.05)

        # navigate to and select: search button
        ap.keys.send('UI_Right')
        sleep(0.05)
        ap.keys.send('UI_Select')

        # zoom camera which puts focus back on the map
        ap.keys.send('CamZoomIn')
        sleep(0.05)

        # plot route. Not that once the system has been selected, as shown in the info panel
        # and the gal map has focus, there is no need to wait for the map to bring the system
        # to the center screen, the system can be selected while the map is moving.
        ap.keys.send('UI_Select', hold=0.75)

        sleep(0.05)

        # if got passed through the ship() object, lets call it to see if a target has been
        # selected yet.. otherwise we wait.  If long route, it may take a few seconds
        if ap.nav_route is not None:
            while 1:
                last_nav_route_sys = ap.nav_route.get_last_system()
                if last_nav_route_sys.upper() == target_name.upper():
                    break
                sleep(1)

        ap.keys.send('GalaxyMapOpen')
        
        return True

    def execute_trade(self, ap, dest_key):
        # Get trade commodities from waypoint
        sell_commodities = self.waypoints[dest_key]['SellCommodities']
        buy_commodities = self.waypoints[dest_key]['BuyCommodities']
        fleetcarrier_transfer = self.waypoints[dest_key]['FleetCarrierTransfer']
        global_buy_commodities = self.waypoints['GlobalShoppingList']['BuyCommodities']

        if len(sell_commodities) == 0 and len(buy_commodities) == 0 and len(global_buy_commodities) == 0:
            return

        # Determine type of station we are at
        colonisation_ship = "ColonisationShip".upper() in ap.jn.ship_state()['cur_station'].upper()
        orbital_construction_site = "ColonisationShip".upper() in ap.jn.ship_state()['cur_station'].upper()
        fleet_carrier = ap.jn.ship_state()['cur_station_type'].upper() == "FleetCarrier".upper()

        if colonisation_ship or orbital_construction_site:
            if colonisation_ship:
                # Colonisation Ship
                logger.debug(f"Execute Trade: On Colonisation Ship")
            if orbital_construction_site:
                # Colonisation Ship
                logger.debug(f"Execute Trade: On Orbital Construction Site")

            # We start off on the Main Menu in the Station
            ap.keys.send('UI_Up', repeat=3)  # make sure at the top
            ap.keys.send('UI_Down')
            ap.keys.send('UI_Select')  # Select StarPort Services

            sleep(5)  # wait for new menu to finish rendering

            # --------- SELL ----------
            if len(sell_commodities) > 0:
                ap.keys.send('UI_Left', repeat=3)  # Go to table
                ap.keys.send('UI_Down', hold=2)  # Go to bottom
                ap.keys.send('UI_Up')  # Select RESET/CONFIRM TRANSFER/TRANSFER ALL
                ap.keys.send('UI_Left', repeat=2)  # Go to RESET
                ap.keys.send('UI_Right', repeat=2)  # Go to TRANSFER ALL
                ap.keys.send('UI_Select')  # Select TRANSFER ALL
                sleep(0.5)

                ap.keys.send('UI_Left')  # Go to CONFIRM TRANSFER
                ap.keys.send('UI_Select')  # Select CONFIRM TRANSFER
                sleep(2)

                ap.keys.send('UI_Down')  # Go to EXIT
                ap.keys.send('UI_Select')  # Select EXIT

                sleep(2)  # give time to popdown menu

        elif fleet_carrier and fleetcarrier_transfer:
            # Fleet Carrier in Tranfer mode
            # --------- SELL ----------
            if len(sell_commodities) > 0:
                # Transfer to Fleet Carrier
                self.transfer_to_fleetcarrier(ap)

            # --------- BUY ----------
            if len(buy_commodities) > 0:
                self.transfer_from_fleetcarrier(ap)

        else:
            # Regular Station or Fleet Carrier in Buy/Sell mode
            logger.debug(f"Execute Trade: On Regular Station")
            self.market_parser.get_market_data()
            market_time_old = self.market_parser.current_data['timestamp']

            # We start off on the Main Menu in the Station
            ap.keys.send('UI_Up', repeat=3)  # make sure at the top
            ap.keys.send('UI_Down')
            ap.keys.send('UI_Select')  # Select StarPort Services

            sleep(8)   # wait for new menu to finish rendering

            ap.keys.send('UI_Down')
            ap.keys.send('UI_Select')  # Select Commodities

            # Wait for market to update
            self.market_parser.get_market_data()
            market_time_new = self.market_parser.current_data['timestamp']
            while market_time_new == market_time_old:
                self.market_parser.get_market_data()
                market_time_new = self.market_parser.current_data['timestamp']
                sleep(1)   # wait for new menu to finish rendering

            cargo_capacity = ap.jn.ship_state()['cargo_capacity']
            logger.info(f"Execute trade: Current cargo capacity: {cargo_capacity}")

            # --------- SELL ----------
            if len(sell_commodities) > 0:
                self.select_sell(ap.keys)

                for i, key in enumerate(sell_commodities):
                    result, qty = self.sell_commodity(ap.keys, key, sell_commodities[key])

                    # Update counts if necessary
                    if qty > 0 and self.waypoints[dest_key]['UpdateCommodityCount']:
                        sell_commodities[key] = sell_commodities[key] - qty

                # Save changes
                self.write_waypoints(data=None, filename='./waypoints/' + Path(self.filename).name)

            # TODO: Note, if the waypoint plan has sell_down != -1, then we are assuming we have
            # cargo to sell, if not we are in limbo here as the Sell button not selectable
            #  Could look at the ship_status['MarketSel'] == True (to be added), to see that we sold
            #  and if not, go down 1 and select cancel

            sleep(1)

            # --------- BUY ----------
            if len(buy_commodities) > 0 or len(global_buy_commodities):
                self.select_buy(ap.keys)

                # Go through buy commodities list
                for i, key in enumerate(buy_commodities):
                    curr_cargo_qty = int(ap.status.get_cleaned_data()['Cargo'])
                    cargo_timestamp = ap.status.current_data['timestamp']

                    free_cargo = cargo_capacity - curr_cargo_qty
                    logger.info(f"Execute trade: Free cargo space: {free_cargo}")

                    if free_cargo == 0:
                        logger.info(f"Execute trade: No space for additional cargo")
                        break

                    qty_to_buy = buy_commodities[key]
                    logger.info(f"Execute trade: Shopping list requests {qty_to_buy} units of {key}")

                    # Attempt to buy the commodity
                    result, qty = self.buy_commodity(ap.keys, key, qty_to_buy, free_cargo)
                    logger.info(f"Execute trade: Bought {qty} units of {key}")

                    # If we bought any goods, wait for status file to update with
                    # new cargo count for next commodity
                    if qty > 0:
                        res = ap.status.wait_for_file_change(cargo_timestamp, 5)

                    # Update counts if necessary
                    if qty > 0 and self.waypoints[dest_key]['UpdateCommodityCount']:
                        buy_commodities[key] = qty_to_buy - qty

                # Go through global buy commodities list
                for i, key in enumerate(global_buy_commodities):
                    curr_cargo_qty = int(ap.status.get_cleaned_data()['Cargo'])
                    cargo_timestamp = ap.status.current_data['timestamp']

                    free_cargo = cargo_capacity - curr_cargo_qty
                    logger.info(f"Execute trade: Free cargo space: {free_cargo}")

                    if free_cargo == 0:
                        logger.info(f"Execute trade: No space for additional cargo")
                        break

                    qty_to_buy = global_buy_commodities[key]
                    logger.info(f"Execute trade: Global shopping list requests {qty_to_buy} units of {key}")

                    # Attempt to buy the commodity
                    result, qty = self.buy_commodity(ap.keys, key, qty_to_buy, free_cargo)
                    logger.info(f"Execute trade: Bought {qty} units of {key}")

                    # If we bought any goods, wait for status file to update with
                    # new cargo count for next commodity
                    if qty > 0:
                        res = ap.status.wait_for_file_change(cargo_timestamp, 5)

                    # Update counts if necessary
                    if qty > 0 and self.waypoints['GlobalShoppingList']['UpdateCommodityCount']:
                        global_buy_commodities[key] = qty_to_buy - qty

                # Save changes
                self.write_waypoints(data=None, filename='./waypoints/' + Path(self.filename).name)

            sleep(1.5)  # give time to popdown
            ap.keys.send('UI_Left')    # back to left menu
            ap.keys.send('UI_Down', repeat=8)    # go down 4x to highlight Exit
            ap.keys.send('UI_Select')  # Select Exit, back to StartPort Menu
            sleep(1) # give time to get back to menu
            if self.is_odyssey:
                ap.keys.send('UI_Down', repeat=4)    # go down 4x to highlight Exit

            ap.keys.send('UI_Select')  # Select Exit, back to top menu
            sleep(2)  # give time to popdown menu

    def transfer_to_fleetcarrier(self, ap):
        """ Transfer all goods to Fleet Carrier """
        # get to the Right Panel menu: Inventory, must initial set to inventory tab
        #ap.keys.send("UI_Back", repeat=5)
        #ap.keys.send("HeadLookReset")
        #sleep(0.5)
        #ap.keys.send("UIFocus", state=1)
        #sleep(0.2)
        #ap.keys.send("UI_Right", hold=0.5)
        #sleep(1)
        #ap.keys.send("UIFocus", state=0)  # this gets us over to the right panel
        #sleep(0.5)

        # print("Quitting")
        # quit()

        # Go to the internal (right) panel inventory tab
        res = ap.internal_panel.show_inventory_tab()

        # Assumes on the INVENTORY tab
        ap.keys.send('UI_Right')
        sleep(0.1)
        ap.keys.send('UI_Up')  # To FILTERS
        sleep(0.1)
        ap.keys.send('UI_Right')  # To TRANSFER >>
        sleep(0.1)
        ap.keys.send('UI_Select')  # Click TRANSFER >>
        sleep(0.1)
        ap.keys.send('UI_Up', hold=3)
        sleep(0.1)
        ap.keys.send('UI_Up')
        sleep(0.1)
        ap.keys.send('UI_Select')

        ap.keys.send('UI_Select')
        sleep(0.1)

        ap.keys.send("UI_Back", repeat=4)
        sleep(0.2)
        ap.keys.send("HeadLookReset")
        print("End of unload FC")
        # quit()

    def transfer_from_fleetcarrier(self, ap):
        """ Transfer all goods to Fleet Carrier """
        # get to the Right Panel menu: Inventory, must initial set to inventory tab
        # ap.keys.send("UI_Back", repeat=5)
        # ap.keys.send("HeadLookReset")
        # sleep(0.5)
        # ap.keys.send("UIFocus", state=1)
        # sleep(0.2)
        # ap.keys.send("UI_Right", hold=0.5)
        # sleep(1)
        # ap.keys.send("UIFocus", state=0)  # this gets us over to the right panel
        # sleep(0.5)

        # print("Quitting")
        # quit()

        # Go to the internal (right) panel inventory tab
        res = ap.internal_panel.show_inventory_tab()

        # Assumes on the INVENTORY tab
        ap.keys.send('UI_Right')
        sleep(0.1)
        ap.keys.send('UI_Up')  # To FILTERS
        sleep(0.1)
        ap.keys.send('UI_Left')  # To << TRANSFER
        sleep(0.1)
        ap.keys.send('UI_Select')  # Click << TRANSFER
        sleep(0.1)
        ap.keys.send('UI_Up', hold=3)
        sleep(0.1)
        ap.keys.send('UI_Up')
        sleep(0.1)
        ap.keys.send('UI_Select')

        ap.keys.send('UI_Select')
        sleep(0.1)

        ap.keys.send("UI_Back", repeat=4)
        sleep(0.2)
        ap.keys.send("HeadLookReset")
        print("End of unload FC")
        # quit()

    def select_buy(self, keys) -> bool:
        """ Select Buy. Assumes on Commodities Market screen. """

        # Select Buy
        keys.send("UI_Left", repeat=2)
        keys.send("UI_Up", repeat=4)

        keys.send("UI_Select")  # Select Buy

        sleep(0.5)  # give time to bring up list
        keys.send('UI_Right')  # Go to top of commodities list
        return True

    def select_sell(self, keys) -> bool:
        """ Select Buy. Assumes on Commodities Market screen. """

        # Select Buy
        keys.send("UI_Left", repeat=2)
        keys.send("UI_Up", repeat=4)

        keys.send("UI_Down")
        keys.send("UI_Select")  # Select Sell

        sleep(0.5)  # give time to bring up list
        keys.send('UI_Right')  # Go to top of commodities list
        return True

    def buy_commodity(self, keys, name: str, qty: int, free_cargo: int) -> tuple[bool, int]:
        """ Buy qty of commodity. If qty >= 9999 then buy as much as possible.
        Assumed to be in the commodities buy screen in the list. """

        # If we are updating requirement count, me might have all the qty we need
        if qty <= 0:
            return False, 0

        # Determine if station sells the commodity!
        self.market_parser.get_market_data()
        if not self.market_parser.can_buy_item(name):
            logger.debug(f"Item '{name}' is not sold or has no stock at {self.market_parser.get_market_name()}.")
            return False, 0

        # Find commodity in market and return the index
        buyable_items = self.market_parser.get_buyable_items()
        index = -1
        stock = 0
        for i, value in enumerate(buyable_items):
            if value['Name_Localised'].upper() == name.upper():
                index = i
                stock = value['Stock']
                logger.debug(f"Execute trade: Buy {name} (want {qty} of {stock} avail.) at position {index}.")
                break

        # Actual qty we can sell
        act_qty = min(qty, stock, free_cargo)

        # See if we buy all and if so, remove the item to update the list, as the item will be removed
        # from the commodities screen, but the market.json will not be updated.
        buy_all = act_qty == stock
        if buy_all:
            for i, value in enumerate(self.market_parser.current_data['Items']):
                if value['Name_Localised'].upper() == name.upper():
                    # Set the stock bracket to 0, so it does not get included in available commodities list.
                    self.market_parser.current_data['Items'][i]['StockBracket'] = 0

        if index > -1:
            keys.send('UI_Up', hold=2.0)  # go up 10x in case were not on top of list
            # keys.send('UI_Up', repeat=sell_down+5)  # go up sell_down times in case were not on top of list (+5 for pad)
            keys.send('UI_Down', hold=0.05, repeat=index)  # go down # of times user specified
            sleep(0.5)
            keys.send('UI_Select')  # Select that commodity

            sleep(0.5)  # give time to popup
            keys.send('UI_Up', repeat=2)  # go up to quantity to buy (may not default to this)
            # Log the planned quantity
            logger.info(f"Attempting to buy {act_qty} units of {name}")
            # Increment count
            if qty >= 9999 or qty >= stock or qty >= free_cargo:
                keys.send("UI_Right", hold=4)
            else:
                keys.send("UI_Right", hold=0.04, repeat=act_qty)
            keys.send('UI_Down')
            keys.send('UI_Select')  # Select Buy
            sleep(0.5)
            #keys.send('UI_Back')  # Back to commodities list

        return True, act_qty

    def sell_commodity(self, keys, name: str, qty: int) -> tuple[bool, int]:
        """ Sell qty of commodity. If qty >= 9999 then sell as much as possible.
        Assumed to be in the commodities sell screen in the list. """

        # If we are updating requirement count, me might have sold all we have
        if qty <= 0:
            return False, 0

        # Determine if station buys the commodity!
        self.market_parser.get_market_data()
        if not self.market_parser.can_sell_item(name):
            logger.debug(f"Item '{name}' is not bought at {self.market_parser.get_market_name()}.")
            return False, 0

        # Find commodity in market and return the index
        sellable_items = self.market_parser.get_sellable_items()
        index = -1
        demand = 0
        for i, value in enumerate(sellable_items):
            if value['Name_Localised'].upper() == name.upper():
                index = i
                demand = value['Demand']
                logger.debug(f"Execute trade: Sell {name} ({qty} of {demand} demanded) at position {index}.")
                break

        # Qty we can sell. Unlike buying, we can sell more than the demand
        # But maybe not at all stations!
        act_qty = qty

        if index > -1:
            keys.send('UI_Up', hold=2.0)  # go up 10x in case were not on top of list
            # ap.keys.send('UI_Up', repeat=10)  # go up 10x in case were not on top of list
            keys.send('UI_Down', hold=0.05, repeat=index)  # go down # of times user specified
            sleep(0.5)
            keys.send('UI_Select')  # Select that commodity

            sleep(0.5)  # give time for popup
            keys.send('UI_Up', repeat=2)  # make sure at top
            
            # Log the planned quantity
            logger.info(f"Attempting to sell {act_qty} units of {name}")
            if qty >= 9999:
                keys.send("UI_Right", hold=4)
            else:
                keys.send('UI_Left', hold=4.0)  # Clear quantity to 0
                keys.send("UI_Right", hold=0.04, repeat=act_qty)
            keys.send('UI_Down')  # Down to the Sell button (already assume sell all)
            keys.send('UI_Select')  # Select to Sell all
            sleep(0.5)
            #keys.send('UI_Back')  # Back to commodities list

        return True, act_qty

    def waypoint_assist(self, scr_reg):
        """ Processes the waypoints, performing jumps and sc assist if going to a station
        also can then perform trades if specific in the waypoints file."""
        # TODO - Move this function to EDWayPoint class
        if len(self.waypoints) == 0:
            self.ap.ap_ckb('log', "No Waypoint file loaded. Exiting Waypoint Assist.")
            return

        self.step = 0  # start at first waypoint
        self.ap.ap_ckb('log', "Waypoint file: "+str(Path(self.filename).name))

        # Loop until complete, or error
        while 1:
            # Current location
            cur_star_system = self.ap.jn.ship_state()['cur_star_system'].upper()
            cur_station = self.ap.jn.ship_state()['cur_station'].upper()
            cur_station_type = self.ap.jn.ship_state()['cur_station_type'].upper()

            # Current in game destination
            status = self.ap.status.get_cleaned_data()
            destination_system = status['Destination_System']  # The system ID
            destination_body = status['Destination_Body']  # The body number (0 for prim star)
            destination_name = status['Destination_Name']  # The system/body/station/settlement name

            # ====================================
            # Get next Waypoint
            # ====================================

            # Get the waypoint details
            dest_key, next_waypoint = self.get_waypoint()
            if dest_key is None:
                self.ap.ap_ckb('log', "Waypoint list complete.")
                break

            # Flag if we are using bookmarks
            gal_bookmark = next_waypoint.get('GalaxyBookmarkNumber', -1) > 0
            sys_bookmark = next_waypoint.get('SystemBookmarkNumber', -1) > 0

            next_system = next_waypoint.get('SystemName', '').upper()
            next_station = next_waypoint.get('StationName', '').upper()

            self.ap.ap_ckb('log', f"Next Waypoint: {next_system} | {next_station}")

            # ====================================
            # Target and travel to a System
            # ====================================

            # Check current system and go to next system if different and not blank
            if cur_star_system != next_system and next_system != "":
                # Check if the current nav route is to the target system
                last_nav_route_sys = self.ap.nav_route.get_last_system()
                if last_nav_route_sys.upper() == next_system.upper():
                    # No need to target system
                    self.ap.ap_ckb('log', f"Waypoint Assist: Next system already targeted.")
                else:
                    # Select destination in galaxy map based on name
                    res = self.set_gal_map_destination_text(self.ap, next_system, self.ap.jn.ship_state)
                    if res:
                        self.ap.ap_ckb('log', f"Waypoint Assist: Next system has been targeted.")
                    else:
                        self.ap.ap_ckb('log', f"Waypoint Assist: Unable to set Galaxy Map target.")
                        # TODO determine what to do here. Stop all waypoints?

                # Jump to the system
                self.ap.ap_ckb('log', f"Waypoint Assist: Jumping to next system.")
                res = self.ap.jump_to_system(scr_reg, next_system)

                continue 
            else:
                self.ap.update_ap_status(f"Already in target System: {next_system}")
                self.ap.ap_ckb('log', f"Already in target System: {next_system}")

            # ====================================
            # Target and travel to a local Station
            # ====================================

            # If we are in the right system, check if we are already docked.
            docked_at_stn = False
            is_docked = self.ap.status.get_flag(FlagsDocked)
            if is_docked:
                # Check if we are at the correct station. Note that for FCs, the station name
                # reported by the Journal is only the ship identifier (ABC-123) and not the carrier name.
                # So we need to check if the ID (ABC-123) is at the end of the target ('Fleety McFleet ABC-123').
                if cur_station_type == 'FleetCarrier'.upper():
                    docked_at_stn = next_station.endswith(cur_station)
                elif next_station == 'System Colonisation Ship'.upper():
                    if (cur_station_type == 'SurfaceStation'.upper() and
                            'ColonisationShip'.upper() in cur_station.upper()):
                        docked_at_stn = True
                elif next_station.startswith('Orbital Construction Site'.upper()):
                    if (cur_station_type == 'SurfaceStation'.upper() and
                            'ColonisationShip'.upper() in cur_station.upper()):
                        docked_at_stn = True
                else:
                    docked_at_stn = cur_station == next_station

            # Check current station and go to it if different
            if not docked_at_stn:
                # Check if we need to travel to a station, else we are done.
                # This may be by 1) System bookmark, 2) Galaxy bookmark or 3) by Station Name text
                if sys_bookmark or gal_bookmark or next_station != "":
                    # If waypoint file has a Station Name associated then attempt targeting it
                    self.ap.update_ap_status(f"Targeting Station: {next_station}")

                    if gal_bookmark:
                        # Set destination via gal bookmark, not system bookmark
                        res = self.set_gal_map_destination_bookmark(self.ap, dest_key)
                        if not res:
                            self.ap.ap_ckb('log', f"Waypoint Assist: Unable to set Galaxy Map target")

                    elif sys_bookmark:
                        # Set destination via system bookmark
                        res = self.set_sys_map_destination_bookmark(self.ap, dest_key)
                        if not res:
                            self.ap.ap_ckb('log', f"Waypoint Assist: Unable to set System Map target")

                    elif next_station != "":
                        # Need OCR added in for this (WIP)
                        need_ocr = True
                        # res = self.nav_panel.lock_destination(station_name)

                    # Jump to the station by name
                    res = self.ap.supercruise_to_station(scr_reg, next_station)
                    continue
                else:
                    self.ap.update_ap_status(f"Arrived at target System: {next_system}")
                    self.ap.ap_ckb('log', f"Arrived at target System: {next_system}")
            else:
                self.ap.update_ap_status(f"Already at target Station: {next_station}")
                self.ap.ap_ckb('log', f"Already at target Station: {next_station}")

            # ====================================
            # Dock and Trade at Station
            # ====================================

            # Are we at the correct station to trade?
            if docked_at_stn:  # and (next_station != "" or sys_bookmark):
                # Docked - let do trade
                self.ap.ap_ckb('log', f"Execute trade at Station: {next_station}")
                self.execute_trade(self.ap, dest_key)

            # Mark this waypoint as completed
            self.mark_waypoint_complete(dest_key)

            self.ap.update_ap_status("Setting route to next waypoint")
            self.ap.update_ap_status("Setting route to next waypoint")

        # Done with waypoints
        self.ap.ap_ckb('log', "Waypoint Route Complete, total distance jumped: "+str(self.ap.total_dist_jumped)+"LY")
        self.ap.update_ap_status("Idle")

# this import the temp class needed for unit testing
"""
from EDKeys import *       
class temp:
    def __init__(self):
        self.keys = EDKeys()
"""

def main():
    
    #keys   = temp()
    wp = EDWayPoint(None, True)  # False = Horizons
    wp.step = 0   #start at first waypoint
    keys = EDKeys()
    keys.activate_window = True
    wp.select_buy(keys)
    wp.buy_commodity(keys,"Steel", 100, 200)
    wp.buy_commodity(keys,"Titanium", 5, 200)
    #wp.sell_commodity(keys,"Gold", 1)


    
    #dest = 'Enayex'
    #print(dest)
    
    #print("In waypoint_assist, at:"+str(dest))

    
    # already in doc config, test the trade
    #wp.execute_trade(keys, dest)    

    # Set the Route for the waypoint^#
    #dest = wp.waypoint_next(ap=None)

    #while dest != "":

      #  print("Doing: "+str(dest))
      #  print(wp.waypoints[dest])
       # print("Dock w/station: "+  str(wp.is_station_targeted(dest)))
        
        #wp.set_station_target(None, dest)
        
        # Mark this waypoint as complated
        #wp.mark_waypoint_complete(dest)
        
        # set target to next waypoint and loop)::@
        #dest = wp.waypoint_next(ap=None)




if __name__ == "__main__":
    main()
