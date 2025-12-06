import math
import os
import traceback
from datetime import timedelta
from enum import Enum
from math import atan, degrees
import random
from string import Formatter
from tkinter import messagebox

import cv2

from simple_localization import LocalizationManager

from EDAP_EDMesg_Server import EDMesgServer
from EDGalaxyMap import EDGalaxyMap
from EDGraphicsSettings import EDGraphicsSettings
from EDShipControl import EDShipControl
from EDStationServicesInShip import EDStationServicesInShip
from EDSystemMap import EDSystemMap
from EDlogger import logging
import Image_Templates
import Screen
import Screen_Regions
from EDWayPoint import *
from EDJournal import *
from EDKeys import *
from EDafk_combat import AFK_Combat
from EDInternalStatusPanel import EDInternalStatusPanel
from NavRouteParser import NavRouteParser
from OCR import OCR
from EDNavigationPanel import EDNavigationPanel
from Overlay import *
from StatusParser import StatusParser
from Voice import *
from Robigo import *
from TCE_Integration import TceIntegration

"""
File:EDAP.py    EDAutopilot

Description:

Note:
Ideas taken from: https://github.com/skai2/EDAutopilot

Author: sumzer0@yahoo.com
"""


# Exception class used to unroll the call tree to to stop execution
class EDAP_Interrupt(Exception):
    pass


class ScTargetAlignReturn(Enum):
    Lost = 1
    Found = 2
    Disengage = 3


class FSDAssistReturn(Enum):
    Failed = 0  # Failed to reach system
    Partial = 1  # Reached final system, but there is a local destination
    Complete = 2  # Reached final system and there is no local destination

def scale(inp: float, in_min: float, in_max: float, out_min: float, out_max: float) -> float:
    """ Does scaling of the input based on input and output min/max."""
    return (inp - in_min)/(in_max - in_min) * (out_max - out_min) + out_min

class EDAutopilot:

    def __init__(self, cb, doThread=True):

        # NOTE!!! When adding a new config value below, add the same after read_config() to set
        # a default value or an error will occur reading the new value!
        self.config = {
            "DSSButton": "Primary",        # if anything other than "Primary", it will use the Secondary Fire button for DSS
            "JumpTries": 3,                #
            "NavAlignTries": 3,            #
            "RefuelThreshold": 65,         # if fuel level get below this level, it will attempt refuel
            "FuelThreasholdAbortAP": 10,   # level at which AP will terminate, because we are not scooping well
            "WaitForAutoDockTimer": 240,   # After docking granted, wait this amount of time for us to get docked with autodocking
            "SunBrightThreshold": 125,     # The low level for brightness detection, range 0-255, want to mask out darker items
            "FuelScoopTimeOut": 35,        # number of second to wait for full tank, might mean we are not scooping well or got a small scooper
            "DockingRetries": 30,          # number of time to attempt docking
            "HotKey_StartFSD": "home",     # if going to use other keys, need to look at the python keyboard package
            "HotKey_StartSC": "ins",       # to determine other keynames, make sure these keys are not used in ED bindings
            "HotKey_StartRobigo": "pgup",  #
            "HotKey_StopAllAssists": "end",
            "Robigo_Single_Loop": False,   # True means only 1 loop will executed and then terminate the Robigo, will not perform mission processing
            "EnableRandomness": False,     # add some additional random sleep times to avoid AP detection (0-3sec at specific locations)
            "ActivateEliteEachKey": False, # Activate Elite window before each key or group of keys
            "OverlayTextEnable": False,    # Experimental at this stage
            "OverlayTextYOffset": 400,     # offset down the screen to start place overlay text
            "OverlayTextXOffset": 50,      # offset left the screen to start place overlay text
            "OverlayTextFont": "Eurostyle",
            "OverlayTextFontSize": 14,
            "OverlayGraphicEnable": False, # not implemented yet
            "DiscordWebhook": False,       # discord not implemented yet
            "DiscordWebhookURL": "",
            "DiscordUserID": "",
            "VoiceEnable": False,
            "VoiceID": 1,                  # my Windows only have 3 defined (0-2)
            "ElwScannerEnable": False,
            "LogDEBUG": False,             # enable for debug messages
            "LogINFO": True,
            "Enable_CV_View": 0,           # Should CV View be enabled by default
            "ShipConfigFile": None,        # Ship config to load on start - deprecated
            "TargetScale": 1.0,            # Scaling of the target when a system is selected
            "ScreenScale": 1.0,            # Scaling of the target when a system is selected
            "TCEDestinationFilepath": "C:\\TCE\\DUMP\\Destination.json",  # Destination file for TCE
            "TCEInstallationPath": "C:\\TCE",
            "AutomaticLogout": False,      # Logout when we are done with the mission
            "FCDepartureTime": 5.0,        # Extra time to fly away from a Fleet Carrier
            "FCDepartureAngle": 90.0,      # Angle to pitch up when leaving a Fleet Carrier
            "OCDepartureAngle": 90.0,      # Angle to pitch up when leaving an Orbital Construction Site
            "Language": 'en',              # Language (matching ./locales/xx.json file)
            "OCRLanguage": 'en',           # Language for OCR detection (see OCR language doc in \docs)
            "EnableEDMesg": False,
            "EDMesgActionsPort": 15570,
            "EDMesgEventsPort": 15571,
            "DebugOverlay": False,
            "AFKCombat_AttackAtWill": False,
            "HotkeysEnable": False,        # Enable hotkeys
            "WaypointFilepath": "",        # The previous waypoint file path
            "DebugOCR": False,             # For debug, write all OCR data to output folder
            "DebugImages": False,          # For debug, write debug images to output folder
            "Key_ModDelay": 0.01,          # Delay for key modifiers to ensure modifier is detected before/after the key
            "Key_DefHoldTime": 0.2,        # Default hold time for a key press
            "Key_RepeatDelay": 0.1,        # Delay between key press repeats
            "DisengageUseMatch": False,    # For 'Disengage' use old image match instead of OCR
            "target_align_outer_lim": 1.0, # For test
            "target_align_inner_lim": 0.5, # For test
            "Debug_ShowCompassOverlay": False, # For test
            "Debug_ShowTargetOverlay": False, # For test
            "GalMap_SystemSelectDelay": 0.5,  # Delay selecting the system when in galaxy map
        }
        # NOTE!!! When adding a new config value above, add the same after read_config() to set
        # a default value or an error will occur reading the new value!

        self.ship_configs = {
            "Ship_Configs": {},  # Dictionary of ship types with additional settings
        }
        self._sc_sco_active_loop_thread = None
        self._sc_sco_active_loop_enable = False
        self.sc_sco_is_active = 0
        self._sc_sco_active_on_ls = 0
        self._single_waypoint_station = None
        self._single_waypoint_system = None
        self._prev_star_system = None
        self.honk_thread = None
        self.speed_demand = None
        self._tce_integration = None
        self._ocr = None
        self._sc_disengage_active = False  # Is SC Disengage active
        self.ship_tst_roll_enabled = False
        self.ship_tst_pitch_enabled = False
        self.ship_tst_yaw_enabled = False

        # used this to write the self.config table to the json file
        # self.write_config(self.config)

        cnf = self.read_config()
        # if we read it then point to it, otherwise use the default table above
        if cnf is not None:
            # NOTE!!! Add default values for new entries below!
            if 'SunBrightThreshold' not in cnf:
                cnf['SunBrightThreshold'] = 125
            if 'TargetScale' not in cnf:
                cnf['TargetScale'] = 1.0
            if 'ScreenScale' not in cnf:
                cnf['ScreenScale'] = 1.0
            if 'TCEDestinationFilepath' not in cnf:
                cnf['TCEDestinationFilepath'] = "C:\\TCE\\DUMP\\Destination.json"
            if 'TCEInstallationPath' not in cnf:
                cnf['TCEInstallationPath'] = "C:\\TCE"
            if 'AutomaticLogout' not in cnf:
                cnf['AutomaticLogout'] = False
            if 'FCDepartureTime' not in cnf:
                cnf['FCDepartureTime'] = 5.0
            if 'Language' not in cnf:
                cnf['Language'] = 'en'
            if 'OCRLanguage' not in cnf:
                cnf['OCRLanguage'] = 'en'
            if 'EnableEDMesg' not in cnf:
                cnf['EnableEDMesg'] = False
            if 'EDMesgActionsPort' not in cnf:
                cnf['EDMesgActionsPort'] = 15570
            if 'EDMesgEventsPort' not in cnf:
                cnf['EDMesgEventsPort'] = 15571
            if 'DebugOverlay' not in cnf:
                cnf['DebugOverlay'] = False
            if 'AFKCombat_AttackAtWill' not in cnf:
                cnf['AFKCombat_AttackAtWill'] = False
            if 'HotkeysEnable' not in cnf:
                cnf['HotkeysEnable'] = False
            if 'WaypointFilepath' not in cnf:
                cnf['WaypointFilepath'] = ""
            if 'DebugOCR' not in cnf:
                cnf['DebugOCR'] = False
            if 'DebugImages' not in cnf:
                cnf['DebugImages'] = False
            if 'Key_ModDelay' not in cnf:
                cnf['Key_ModDelay'] = 0.01
            if 'Key_DefHoldTime' not in cnf:
                cnf['Key_DefHoldTime'] = 0.2
            if 'Key_RepeatDelay' not in cnf:
                cnf['Key_RepeatDelay'] = 0.1
            if 'DisengageUseMatch' not in cnf:
                cnf['DisengageUseMatch'] = False
            if 'target_align_outer_lim' not in cnf:
                cnf['target_align_outer_lim'] = 1.0 # For test
            if 'target_align_inner_lim' not in cnf:
                cnf['target_align_inner_lim'] = 0.5 # For test
            if 'Debug_ShowCompassOverlay' not in cnf:
                cnf['Debug_ShowCompassOverlay'] = False # For test
            if 'Debug_ShowTargetOverlay' not in cnf:
                cnf['Debug_ShowTargetOverlay'] = False # For test
            if 'GalMap_SystemSelectDelay' not in cnf:
                cnf['GalMap_SystemSelectDelay'] = 0.5
            if 'FCDepartureAngle' not in cnf:
                cnf['FCDepartureAngle'] = 90.0
            if 'OCDepartureAngle' not in cnf:
                cnf['OCDepartureAngle'] = 90.0
            self.config = cnf
            logger.debug("read AP json:"+str(cnf))
        else:
            self.write_config(self.config)

        # Load selected language
        self.locale = LocalizationManager('locales', self.config['Language'])

        # config the voice interface
        self.vce = Voice()
        self.vce.v_enabled = self.config['VoiceEnable']
        self.vce.set_voice_id(self.config['VoiceID'])
        self.vce.say("Welcome to Autopilot")

        # set log level based on config input, defaulting to warning
        logger.setLevel(logging.WARNING)
        if self.config['LogINFO']:
            logger.setLevel(logging.INFO)
        if self.config['LogDEBUG']:
            logger.setLevel(logging.DEBUG)

        # initialize all to false
        self.fsd_assist_enabled = False
        self.sc_assist_enabled = False
        self.afk_combat_assist_enabled = False
        self.waypoint_assist_enabled = False
        self.robigo_assist_enabled = False
        self.dss_assist_enabled = False
        self.single_waypoint_enabled = False

        # Create instance of each of the needed Classes
        self.scr = Screen.Screen(cb)
        self.scr.scaleX = self.config['ScreenScale']
        self.scr.scaleY = self.config['ScreenScale']
        self.target_scale = self.config['TargetScale']

        self.gfx_settings = EDGraphicsSettings()
        # Aspect ratio greater than 1920/1080 (1.7777) seems to be the magic cutoff. At > 1920/1080 (1.7777), the FOV
        # appears to be the top of the screen. Looks like FDev made the FOV for 1920x1080 resolution height.
        if self.scr.aspect_ratio >= 1.7777:
            self.ver_fov = round(float(self.gfx_settings.fov), 4)
            logger.debug(f'Vertical FOV: {self.ver_fov} deg (-{self.ver_fov / 2} to {self.ver_fov / 2} deg).')
            self.hor_fov = round(self.ver_fov * self.scr.aspect_ratio, 4)
            logger.debug(f'Horizontal FOV: {self.hor_fov} deg (-{self.hor_fov / 2} to {self.hor_fov / 2} deg).')
        else:
            self.ver_fov = round(float(self.gfx_settings.fov) * (1.7777 / self.scr.aspect_ratio), 4)
            logger.debug(f'Vertical FOV: {self.ver_fov} deg (-{self.ver_fov / 2} to {self.ver_fov / 2}).')
            self.hor_fov = round(self.ver_fov * self.scr.aspect_ratio, 4)
            logger.debug(f'Horizontal FOV: {self.hor_fov} deg (-{self.hor_fov / 2} to {self.hor_fov / 2}).')

        self.templ = Image_Templates.Image_Templates(self.scr.scaleX, self.scr.scaleY, self.scr.scaleX, self.scr.scaleX)
        self.scrReg = Screen_Regions.Screen_Regions(self.scr, self.templ)
        self.jn = EDJournal(cb)
        self.keys = EDKeys(cb)
        self.afk_combat = AFK_Combat(self, self.keys, self.jn, self.vce)
        self.waypoint = EDWayPoint(self, self.jn.ship_state()['odyssey'])
        self.robigo = Robigo(self)
        self.status = StatusParser()
        self.nav_route = NavRouteParser()
        self.ship_control = EDShipControl(self, self.scr, self.keys, cb)
        self.internal_panel = EDInternalStatusPanel(self, self.scr, self.keys, cb)
        self.galaxy_map = EDGalaxyMap(self, self.scr, self.keys, cb, self.jn.ship_state()['odyssey'])
        self.system_map = EDSystemMap(self, self.scr, self.keys, cb, self.jn.ship_state()['odyssey'])
        self.stn_svcs_in_ship = EDStationServicesInShip(self, self.scr, self.keys, cb)
        self.nav_panel = EDNavigationPanel(self, self.scr, self.keys, cb)

        self.mesg_server = EDMesgServer(self, cb)
        self.mesg_server.actions_port = self.config['EDMesgActionsPort']
        self.mesg_server.events_port = self.config['EDMesgEventsPort']
        if self.config['EnableEDMesg']:
            self.mesg_server.start_server()

        # Set defaults for data read from ships config
        self.compass_scale = 1.0
        self.yawrate   = 8.0
        self.rollrate  = 80.0
        self.pitchrate = 33.0
        self.sunpitchuptime = 0.0
        self.yawfactor = 0.0
        self.rollfactor = 0.0
        self.pitchfactor = 0.0

        self.ap_ckb = cb

        self.load_ship_configs()

        self.jump_cnt = 0
        self._eta = 0
        self._str_eta = ''
        self.total_dist_jumped = 0
        self.total_jumps = 0
        self.refuel_cnt = 0
        self.current_ship_type = None
        self.gui_loaded = False
        self._nav_cor_x = 0.0  # Nav Point correction to pitch
        self._nav_cor_y = 0.0  # Nav Point correction to yaw
        self.target_align_outer_lim = 1.0  # In deg. Anything outside of this range will cause alignment.
        self.target_align_inner_lim = 0.5  # In deg. Will stop alignment when in this range.
        self.debug_show_compass_overlay = False
        self.debug_show_target_overlay = False

        # Overlay vars
        self.ap_state = "Idle"
        self.fss_detected = "nothing found"

        # Initialize the Overlay class
        self.overlay = Overlay("", elite=1)
        self.overlay.overlay_setfont(self.config['OverlayTextFont'], self.config['OverlayTextFontSize'])
        self.overlay.overlay_set_pos(self.config['OverlayTextXOffset'], self.config['OverlayTextYOffset'])
        # must be called after we initialized the objects above
        self.update_overlay()

        self.debug_overlay = self.config['DebugOverlay']
        self.debug_ocr = self.config['DebugOCR']
        self.debug_images = self.config['DebugImages']
        self.debug_image_folder = './debug-output/images'
        if not os.path.exists(self.debug_image_folder):
            os.makedirs(self.debug_image_folder)

        # debug window
        self.cv_view = self.config['Enable_CV_View']
        self.cv_view_x = 10
        self.cv_view_y = 10

        #start the engine thread
        self.terminate = False  # terminate used by the thread to exit its loop
        if doThread:
            self.ap_thread = kthread.KThread(target=self.engine_loop, name="EDAutopilot")
            self.ap_thread.start()

        # Start thread to delete old log files.
        del_log_files_thread = threading.Thread(target=delete_old_log_files, daemon=True)
        del_log_files_thread.start()

        # Process config[] settings to update classes as necessary
        self.process_config_settings()

    @property
    def tce_integration(self) -> TceIntegration:
        """ Load TCE Integration class when needed. """
        if not self._tce_integration:
            self._tce_integration = TceIntegration(self, self.ap_ckb)
        return self._tce_integration

    @property
    def ocr(self) -> OCR:
        """ Load OCR class when needed. """
        if not self._ocr:
            self._ocr = OCR(self, self.scr)
        return self._ocr

    # Loads the configuration file
    #
    def read_config(self, fileName='./configs/AP.json'):
        s = None
        try:
            with open(fileName, "r") as fp:
                s = json.load(fp)
        except  Exception as e:
            logger.warning("EDAPGui.py read_config error :"+str(e))

        return s

    def update_config(self):
        # Get values from classes
        if self.keys:
            self.config['ActivateEliteEachKey'] = self.keys.activate_window
            self.config['Key_ModDelay'] = self.keys.key_mod_delay
            self.config['Key_DefHoldTime'] = self.keys.key_def_hold_time
            self.config['Key_RepeatDelay'] = self.keys.key_repeat_delay

        # Delete old settings
        self.config.pop('target_align_inertia_pitch_factor', None)
        self.config.pop('target_align_inertia_yaw_factor', None)

        self.write_config(self.config)

    def write_config(self, data, fileName='./configs/AP.json'):
        try:
            with open(fileName, "w") as fp:
                json.dump(data, fp, indent=4)
        except Exception as e:
            logger.warning("EDAPGui.py write_config error:"+str(e))

    def read_ship_configs(self, filename='./configs/ship_configs.json'):
        """ Read the user's ship configuration file."""
        s = None
        try:
            with open(filename, "r") as fp:
                s = json.load(fp)
        except  Exception as e:
            logger.warning("EDAPGui.py read_ship_configs error :"+str(e))

        return s

    def load_ship_configs(self):
        shp_cnf = self.read_ship_configs()
        # if we read it then point to it, otherwise use the default table above
        if shp_cnf is not None:
            if len(shp_cnf) != len(self.ship_configs):
                # If configs of different lengths, then a new parameter was added.
                # self.write_config(self.config)
                # Add default values for new entries
                if 'Ship_Configs' not in shp_cnf:
                    shp_cnf['Ship_Configs'] = dict()
                self.ship_configs = shp_cnf
                logger.debug("read Ships Config json:" + str(shp_cnf))
            else:
                self.ship_configs = shp_cnf
                logger.debug("read Ships Config json:" + str(shp_cnf))
        else:
            self.write_ship_configs(self.ship_configs)

        # Load ship configuration with proper hierarchy
        if self.jn:
            ship = self.jn.ship_state()['type']
            if ship:
                self.load_ship_configuration(ship)

    def update_ship_configs(self):
        """ Update the user's ship configuration file."""
        # Check if a ship and not a suit (on foot)
        if self.current_ship_type in ship_size_map:
            # Ensure ship entry exists in config
            if self.current_ship_type not in self.ship_configs['Ship_Configs']:
                self.ship_configs['Ship_Configs'][self.current_ship_type] = {}
                logger.debug(f"Created new ship config entry for: {self.current_ship_type}")
            
            self.ship_configs['Ship_Configs'][self.current_ship_type]['compass_scale'] = round(self.compass_scale, 4)
            self.ship_configs['Ship_Configs'][self.current_ship_type]['PitchRate'] = self.pitchrate
            self.ship_configs['Ship_Configs'][self.current_ship_type]['RollRate'] = self.rollrate
            self.ship_configs['Ship_Configs'][self.current_ship_type]['YawRate'] = self.yawrate
            self.ship_configs['Ship_Configs'][self.current_ship_type]['SunPitchUp+Time'] = self.sunpitchuptime
            self.ship_configs['Ship_Configs'][self.current_ship_type]['PitchFactor'] = self.pitchfactor
            self.ship_configs['Ship_Configs'][self.current_ship_type]['RollFactor'] = self.rollfactor
            self.ship_configs['Ship_Configs'][self.current_ship_type]['YawFactor'] = self.yawfactor

            self.write_ship_configs(self.ship_configs)
            logger.debug(f"Saved ship config for: {self.current_ship_type}")

    def write_ship_configs(self, data, filename='./configs/ship_configs.json'):
        """ Write the user's ship configuration file."""
        try:
            with open(filename, "w") as fp:
                json.dump(data, fp, indent=4)
        except Exception as e:
            logger.warning("EDAPGui.py write_ship_configs error:"+str(e))

    def load_ship_configuration(self, ship_type):
        """ Load ship configuration with the following priority:
            1. User's ship values from ship_configs.json file
            2. Default ship values from default_ships_cfg_sc_50.json file
            3. Hardcoded default values
        """
        self.ap_ckb('log', f"Loading ship configuration for your {ship_type}")

        # Step 1: Use hardcoded defaults
        self.compass_scale = self.scr.scaleX
        self.rollrate = 80.0
        self.pitchrate = 33.0
        self.yawrate = 8.0
        self.sunpitchuptime = 0.0
        self.rollfactor = 20.0
        self.pitchfactor = 12.0
        self.yawfactor = 12.0
        logger.info(f"Loaded hardcoded default configuration for {ship_type}")

        # Step 2: Try to load defaults from ship file
        if ship_type in ship_rpy_sc_50:
            ship_defaults = ship_rpy_sc_50[ship_type]
            # Use default configuration - this means it's been modified and saved to ship_configs.json
            self.compass_scale = self.scr.scaleX  # Always use current scale for compass
            self.rollrate = ship_defaults.get('RollRate', 80.0)
            self.pitchrate = ship_defaults.get('PitchRate', 33.0)
            self.yawrate = ship_defaults.get('YawRate', 8.0)
            self.sunpitchuptime = ship_defaults.get('SunPitchUp+Time', 0.0)
            logger.info(f"Loaded default configuration for {ship_type} from default ship cfg file")

        # if ship_type in ship_rpy_factor_sc_50:
        #     ship_defaults = ship_rpy_factor_sc_50[ship_type]
        #     # Use default configuration - this means it's been modified and saved to ship_configs.json
        #     self.rollfactor = ship_defaults.get('RollFactor', 20.0)
        #     self.pitchfactor = ship_defaults.get('PitchFactor', 12.0)
        #     self.yawfactor = ship_defaults.get('YawFactor', 12.0)
        #     # return

        # Step 3: Check if we have custom config in ship_configs.json (skip if forcing defaults)
        if ship_type in self.ship_configs['Ship_Configs']:
            current_ship_cfg = self.ship_configs['Ship_Configs'][ship_type]
            # Check if the custom config has actual values (not just empty dict)
            if any(key in current_ship_cfg for key in ['compass_scale', 'RollRate', 'PitchRate', 'YawRate', 'SunPitchUp+Time']):
                # Use custom configuration - this means it's been modified and saved to ship_configs.json
                self.compass_scale = current_ship_cfg.get('compass_scale', self.scr.scaleX)
                self.rollrate = current_ship_cfg.get('RollRate', 80.0)
                self.pitchrate = current_ship_cfg.get('PitchRate', 33.0)
                self.yawrate = current_ship_cfg.get('YawRate', 8.0)
                self.sunpitchuptime = current_ship_cfg.get('SunPitchUp+Time', 0.0)
                logger.info(f"Loaded your custom configuration for {ship_type} from ship_configs.json")

            if any(key in current_ship_cfg for key in ['RollFactor', 'PitchFactor', 'YawFactor']):
                # Use custom configuration - this means it's been modified and saved to ship_configs.json
                self.rollfactor = current_ship_cfg.get('RollFactor', 20.0)
                self.pitchfactor = current_ship_cfg.get('PitchFactor', 12.0)
                self.yawfactor = current_ship_cfg.get('YawFactor', 12.0)
                # return

            # Check RPY Calibration
            spd_dmd = 'SCSpeed50'
            if spd_dmd not in current_ship_cfg:
                self.ap_ckb('log', "WARNING: Perform Roll/Pitch/Yaw Calibration on this ship.")
            else:
                speed_demand = current_ship_cfg[spd_dmd]
                if 'RollRate' not in speed_demand:
                    self.ap_ckb('log', "WARNING: Perform Roll Calibration on this ship.")
                if 'PitchRate' not in speed_demand:
                    self.ap_ckb('log', "WARNING: Perform Pitch Calibration on this ship.")
                if 'YawRate' not in speed_demand:
                    self.ap_ckb('log', "WARNING: Perform Yaw Calibration on this ship.")

        # Add empty entry to ship_configs for future customization
        if ship_type not in self.ship_configs['Ship_Configs']:
            self.ship_configs['Ship_Configs'][ship_type] = dict()

    def update_overlay(self):
        """ Draw the overlay data on the ED Window """
        if self.config['OverlayTextEnable']:
            ap_mode = "Offline"
            if self.fsd_assist_enabled:
                ap_mode = "FSD Route Assist"
            elif self.robigo_assist_enabled:
                ap_mode = "Robigo Assist"
            elif self.sc_assist_enabled:
                ap_mode = "SC Assist"
            elif self.waypoint_assist_enabled:
                ap_mode = "Waypoint Assist"
            elif self.afk_combat_assist_enabled:
                ap_mode = "AFK Combat Assist"
            elif self.dss_assist_enabled:
                ap_mode = "DSS Assist"

            ship_state = self.jn.ship_state()['status']
            if ship_state is None:
                ship_state = '<init>'

            sclass = self.jn.ship_state()['star_class']
            if sclass is None:
                sclass = "<init>"

            location = self.jn.ship_state()['location']
            if location is None:
                location = "<init>"
            self.overlay.overlay_text('1', "AP MODE: "+ap_mode, 1, 1, (136, 53, 0), -1)
            self.overlay.overlay_text('2', "AP STATUS: "+self.ap_state, 2, 1, (136, 53, 0), -1)
            self.overlay.overlay_text('3', "SHIP STATUS: "+ship_state, 3, 1, (136, 53, 0), -1)
            self.overlay.overlay_text('4', "CURRENT SYSTEM: "+location+", "+sclass, 4, 1, (136, 53, 0), -1)
            self.overlay.overlay_text('5', "JUMPS: {} of {}".format(self.jump_cnt, self.total_jumps), 5, 1, (136, 53, 0), -1)
            self.overlay.overlay_text('6', "ETA (to System): "+self._str_eta, 6, 1, (136, 53, 0), -1)
            if self.config["ElwScannerEnable"]:
                self.overlay.overlay_text('7', "ELW SCANNER: "+self.fss_detected, 7, 1, (136, 53, 0), -1)
            self.overlay.overlay_paint()

    def update_ap_status(self, txt):
        self.ap_state = txt
        self.update_overlay()
        self.ap_ckb('statusline', txt)

    def process_config_settings(self):
        """ Update subclasses as necessary with config setting changes. """
        if self.keys:
            self.keys.activate_window = self.config['ActivateEliteEachKey']
            self.keys.key_mod_delay = self.config['Key_ModDelay']
            self.keys.key_def_hold_time = self.config['Key_DefHoldTime']
            self.keys.key_repeat_delay = self.config['Key_RepeatDelay']

        if self.galaxy_map:
            self.galaxy_map.SystemSelectDelay = self.config['GalMap_SystemSelectDelay']

        self.target_align_outer_lim = self.config['target_align_outer_lim']
        self.target_align_inner_lim = self.config['target_align_inner_lim']
        self.debug_show_compass_overlay = self.config['Debug_ShowCompassOverlay']
        self.debug_show_target_overlay = self.config['Debug_ShowTargetOverlay']

    def draw_match_rect(self, img, pt1, pt2, color, thick):
        """ Draws the matching rectangle within the image. """
        wid = pt2[0]-pt1[0]
        hgt = pt2[1]-pt1[1]

        if wid < 20:
            #cv2.rectangle(screen, pt, (pt[0] + compass_width, pt[1] + compass_height),  (0,0,255), 2)
            cv2.rectangle(img, pt1, pt2, color, thick)
        else:
            len_wid = wid/5
            len_hgt = hgt/5
            half_wid = wid/2
            half_hgt = hgt/2
            tic_len = thick-1
            # top
            cv2.line(img, (int(pt1[0]), int(pt1[1])), (int(pt1[0]+len_wid), int(pt1[1])), color, thick)
            cv2.line(img, (int(pt1[0]+(2*len_wid)), int(pt1[1])), (int(pt1[0]+(3*len_wid)), int(pt1[1])), color, 1)
            cv2.line(img, (int(pt1[0]+(4*len_wid)), int(pt1[1])), (int(pt2[0]), int(pt1[1])), color, thick)
            # top tic
            cv2.line(img, (int(pt1[0]+half_wid), int(pt1[1])), (int(pt1[0]+half_wid), int(pt1[1])-tic_len), color, thick)
            # bot
            cv2.line(img, (int(pt1[0]), int(pt2[1])), (int(pt1[0]+len_wid), int(pt2[1])), color, thick)
            cv2.line(img, (int(pt1[0]+(2*len_wid)), int(pt2[1])), (int(pt1[0]+(3*len_wid)), int(pt2[1])), color, 1)
            cv2.line(img, (int(pt1[0]+(4*len_wid)), int(pt2[1])), (int(pt2[0]), int(pt2[1])), color, thick)
            # bot tic
            cv2.line(img, (int(pt1[0]+half_wid), int(pt2[1])), (int(pt1[0]+half_wid), int(pt2[1])+tic_len), color, thick)
            # left
            cv2.line(img, (int(pt1[0]), int(pt1[1])), (int(pt1[0]), int(pt1[1]+len_hgt)), color, thick)
            cv2.line(img, (int(pt1[0]), int(pt1[1]+(2*len_hgt))), (int(pt1[0]), int(pt1[1]+(3*len_hgt))), color, 1)
            cv2.line(img, (int(pt1[0]), int(pt1[1]+(4*len_hgt))), (int(pt1[0]), int(pt2[1])), color, thick)
            # left tic
            cv2.line(img, (int(pt1[0]), int(pt1[1]+half_hgt)), (int(pt1[0]-tic_len), int(pt1[1]+half_hgt)), color, thick)
            # right
            cv2.line(img, (int(pt2[0]), int(pt1[1])), (int(pt2[0]), int(pt1[1]+len_hgt)), color, thick)
            cv2.line(img, (int(pt2[0]), int(pt1[1]+(2*len_hgt))), (int(pt2[0]), int(pt1[1]+(3*len_hgt))), color, 1)
            cv2.line(img, (int(pt2[0]), int(pt1[1]+(4*len_hgt))), (int(pt2[0]), int(pt2[1])), color, thick)
            # right tic
            cv2.line(img, (int(pt2[0]), int(pt1[1]+half_hgt)), (int(pt2[0]+tic_len), int(pt1[1]+half_hgt)), color, thick)

    def calibrate_region(self, range_low, range_high, range_step, threshold: float, reg_name: str, templ_name: str, no_overlay: bool = False):
        """ Find the best scale value in the given range of scales with the passed in threshold
        @param reg_name:
        @param range_low: Lowest scaling value (0-100%)
        @param range_high: Highest scaling value (0-100%)
        @param range_step: Scaling value step increment (0-100%) for each loop
        @param threshold: The minimum threshold to match (0.0 - 1.0)
        @param templ_name: The region name i.i 'compass' or 'target'
        @param no_overlay: Do not show overlay.
        @return:
        """
        scale = 0
        max_pick = 0
        i = range_low
        while i <= range_high:
            scale_x = float(i / 100)
            scale_y = scale_x

            # reload the templates with this scale value
            self.templ.reload_templates(scale_x, scale_y, scale_x, scale_x)

            # do image matching on the compass and the target
            image, (minVal, maxVal, minLoc, maxLoc), match = self.scrReg.match_template_in_region_x3(reg_name, templ_name)

            if not no_overlay:
                border = 10  # border to prevent the box from interfering with future matches
                reg_pos = self.scrReg.reg[reg_name]['rect']
                width = self.scrReg.templates.template[templ_name]['width'] + border + border
                height = self.scrReg.templates.template[templ_name]['height'] + border + border
                left = reg_pos[0] + maxLoc[0] - border
                top = reg_pos[1] + maxLoc[1] - border

                if maxVal > threshold and maxVal > max_pick:
                    # Draw box around region
                    self.overlay.overlay_rect(20, (left, top), (left + width, top + height), (0, 255, 0), 2)
                    self.overlay.overlay_floating_text(20, f'Match: {maxVal:5.4f}(%)', left, top - 25, (0, 255, 0))
                else:
                    # Draw box around region
                    self.overlay.overlay_rect(21, (left, top), (left + width, top + height), (255, 0, 0), 2)
                    self.overlay.overlay_floating_text(21, f'Match: {maxVal:5.4f}(%)', left, top - 25, (255, 0, 0))

                self.overlay.overlay_paint()

            # Check the match percentage
            if maxVal > threshold:
                if maxVal > max_pick:
                    max_pick = maxVal
                    scale = i
                    #self.ap_ckb('log', 'Cal: Found match:' + f'{max_pick:5.4f}' + "% with scale:" + f'{self.scr.scaleX:5.4f}')

            # Next range
            i = i + range_step

        return scale, max_pick

    def calibrate_target(self):
        """ Routine to find the optimal scaling values for the template images. """
        msg = 'Select OK to begin Calibration. You must be in space and have a star system targeted in center screen.'
        self.vce.say(msg)
        ans = messagebox.askokcancel('Calibration', msg)
        if not ans:
            return

        self.ap_ckb('log+vce', 'Calibration starting.')

        set_focus_elite_window()

        # Draw the target and compass regions on the screen
        key = 'target'
        targ_region = self.scrReg.reg[key]
        self.overlay.overlay_rect1('calib_target', targ_region['rect'], (0, 0, 255), 2, -1)
        self.overlay.overlay_floating_text('calib_target', key, targ_region['rect'][0], targ_region['rect'][1], (0, 0, 255), -1)
        self.overlay.overlay_paint()

        # Calibrate system target
        self.calibrate_target_worker()

        # Clean up
        self.overlay.overlay_remove_rect('calib_target')
        self.overlay.overlay_remove_floating_text('calib_target')
        self.overlay.overlay_paint()

        self.ap_ckb('log+vce', 'Calibration complete.')

    def calibrate_compass(self):
        """ Routine to find the optimal scaling values for the template images. """
        msg = 'Select OK to begin Calibration. You must be in space and have the compass visible.'
        self.vce.say(msg)
        ans = messagebox.askokcancel('Calibration', msg)
        if not ans:
            return

        self.ap_ckb('log+vce', 'Calibration starting.')

        set_focus_elite_window()

        # Draw the target and compass regions on the screen
        key = 'compass'
        targ_region = self.scrReg.reg[key]
        self.overlay.overlay_rect1('calib_compass', targ_region['rect'], (0, 0, 255), 2, -1)
        self.overlay.overlay_floating_text('calib_compass', key, targ_region['rect'][0], targ_region['rect'][1], (0, 0, 255), -1)
        self.overlay.overlay_paint()

        # Calibrate compass
        self.calibrate_compass_worker()

        # Clean up
        self.overlay.overlay_remove_rect('calib_compass')
        self.overlay.overlay_remove_floating_text('calib_compass')
        self.overlay.overlay_paint()

        self.ap_ckb('log+vce', 'Calibration complete.')

    def calibrate_target_worker(self):
        """ Calibrate target and screen. """
        range_low = 50  # Minimum scale (30%)
        range_high = 200  # Maximum scale (200%)
        range_step = 1  # Scale increment to step (1%)
        scale_max = 0
        max_val = 0

        # loop through the test twice. Once over the wide scaling range at 1% increments and once over a
        # small scaling range at 0.1% increments.
        # Find out which scale factor meets the highest threshold value.
        for i in range(2):
            threshold = 0.0  # Minimum match is constant. Result will always be the highest match.
            scale, max_pick = self.calibrate_region(range_low, range_high, range_step, threshold, 'target', 'target')
            if scale != 0:
                scale_max = scale
                max_val = max_pick
                range_low = scale - 5  # Current scale - 5%
                range_high = scale + 5  # Current scale + 5%
                range_step = 0.1  # Scale increment to step (0.1%)
                if i == 1:
                    self.ap_ckb('log',
                                f'Target Cal: Best rough match: {max_val:5.4f}(%) at scale: {float(scale_max / 100):5.4f}')
                else:
                    self.ap_ckb('log',
                                f'Target Cal: Best fine match: {max_val:5.4f}(%) at scale: {float(scale_max / 100):5.4f}')

            else:
                break  # no match found with threshold

        # if we found a scaling factor that meets our criteria, then save it to the resolution.json file
        if max_val != 0:
            self.ap_ckb('log', f'Target Cal: Best match: {max_val:5.4f}(%) at scale: {self.scr.scaleX:5.4f}')
            self.scr.scaleX = float(scale_max / 100)
            self.scr.scaleY = self.scr.scaleX
            self.target_scale = self.scr.scaleX
            self.config['ScreenScale'] = round(self.scr.scaleX, 4)
            self.config['TargetScale'] = round(self.target_scale, 4)

            self.scr.write_config(
                data=None)  # None means the writer will use its own scales variable which we modified
        else:
            self.ap_ckb('log',
                        f'Target Cal: Insufficient matching to meet reliability, max % match: {max_val:5.4f}(%)')

        # reload the templates with the new (or previous value)
        self.templ.reload_templates(self.scr.scaleX, self.scr.scaleY, self.compass_scale, self.target_scale)

    def quick_calibrate_target(self):
        """ Quick Calibrate Target (not the screen) based on current scaling, without overlay. """
        self.ap_ckb('log+vce', 'Performing quick target calibration.')

        cur_scale = self.scr.scaleX * 100
        range_low = cur_scale - 15  # Current scale - 15%
        range_high = cur_scale + 15  # Current scale + 15%
        range_step = 0.25  # Scale increment to step (0.25%)

        # loop through the test.
        threshold = 0.5  # Minimum match is constant. Result will always be the highest match.
        no_overlay = not self.debug_overlay
        scale_max, max_val = self.calibrate_region(range_low, range_high, range_step, threshold, 'target','target', no_overlay)
        # if we found a scaling factor that meets our criteria, then save it to the resolution.json file
        if max_val != 0:
            self.ap_ckb('log', f'Target Cal: Best match: {max_val:5.4f}(%) at scale: {self.scr.scaleX:5.4f}')
            # self.scr.scaleX = float(scale_max / 100)
            # self.scr.scaleY = self.scr.scaleX
            self.target_scale = float(scale_max / 100)
            self.config['TargetScale'] = round(self.target_scale, 4)

            self.scr.write_config(
                data=None)  # None means the writer will use its own scales variable which we modified
        else:
            self.ap_ckb('log', f'Target Cal: Insufficient matching to meet reliability, max % match: {max_val:5.4f}(%)')

        # reload the templates with the new (or previous value)
        self.templ.reload_templates(self.scr.scaleX, self.scr.scaleY, self.compass_scale, self.target_scale)

    def calibrate_compass_worker(self):
        """ Calibrate Compass """
        range_low = 50  # Minimum scale (30%)
        range_high = 200  # Maximum scale (200%)
        range_step = 1  # Scale increment to step (1%)
        scale_max = 0
        max_val = 0

        # loop through the test twice. Once over the wide scaling range at 1% increments and once over a
        # small scaling range at 0.1% increments.
        # Find out which scale factor meets the highest threshold value.
        for i in range(1):
            threshold = 0.0  # Minimum match is constant. Result will always be the highest match.
            scale, max_pick = self.calibrate_region(range_low, range_high, range_step, threshold, 'compass','compass')
            if scale != 0:
                scale_max = scale
                max_val = max_pick
                range_low = scale - 5  # Current scale - 5%
                range_high = scale + 5  # Current scale + 5%
                range_step = 0.1  # Scale increment to step (0.1%)
                if i == 1:
                    self.ap_ckb('log',
                                f'Target Cal: Best rough match: {max_val * 100:5.2f}% at scale: {float(scale_max / 100):5.4f}')
                else:
                    self.ap_ckb('log',
                                f'Target Cal: Best fine match: {max_val * 100:5.2f}% at scale: {float(scale_max / 100):5.4f}')

            else:
                break  # no match found with threshold

        # if we found a scaling factor that meets our criteria, then save it to the resolution.json file
        if max_val != 0:
            c_scale_x = float(scale_max / 100)
            self.ap_ckb('log',
                        f'Compass Cal: Max best match: {max_val * 100:5.2f}% with scale: {c_scale_x:5.4f}')
            # Keep new value
            self.compass_scale = c_scale_x

        else:
            self.ap_ckb('log',
                        f'Compass Cal: Insufficient matching to meet reliability, max % match: {max_val * 100:5.2f}%')

        # reload the templates with the new (or previous value)
        self.templ.reload_templates(self.scr.scaleX, self.scr.scaleY, self.compass_scale, self.target_scale)

    def quick_calibrate_compass(self):
        """ Quick Calibrate Compass based on current scaling, without overlay. """
        self.ap_ckb('log+vce', 'Performing quick compass calibration.')

        cur_scale = self.compass_scale * 100
        range_low = cur_scale - 15  # Current scale - 15%
        range_high = cur_scale + 15  # Current scale + 15%
        range_step = 0.25  # Scale increment to step (0.25%)

        # loop through the test.
        threshold = 0.5  # Minimum match is constant. Result will always be the highest match.
        no_overlay = not self.debug_overlay
        scale_max, max_val = self.calibrate_region(range_low, range_high, range_step, threshold, 'compass','compass', no_overlay)
        # if we found a scaling factor that meets our criteria, then save it to the resolution.json file
        if max_val != 0:
            c_scale_x = float(scale_max / 100)
            self.ap_ckb('log',
                        f'Compass Cal: Max best match: {max_val * 100:5.2f}% with scale: {c_scale_x:5.4f}')
            # Keep new value
            self.compass_scale = c_scale_x

        else:
            self.ap_ckb('log',
                        f'Compass Cal: Insufficient matching to meet reliability, max % match: {max_val * 100:5.2f}%')

        # reload the templates with the new (or previous value)
        self.templ.reload_templates(self.scr.scaleX, self.scr.scaleY, self.compass_scale, self.target_scale)

    def fss_detect_elw(self, scr_reg):
        """ Go into FSS, check to see if we have a signal waveform in the Earth, Water or Ammonia zone
        if so, announce finding and log the type of world found. """
        # open fss
        self.set_speed_0()
        sleep(0.1)
        self.keys.send('ExplorationFSSEnter')
        sleep(2.5)

        # look for a circle or signal in this region
        elw_image, (minVal, maxVal, minLoc, maxLoc), match = scr_reg.match_template_in_region('fss', 'elw')
        elw_sig_image, (minVal1, maxVal1, minLoc1, maxLoc1), match = scr_reg.match_template_in_image(elw_image, 'elw_sig')

        # dvide the region in thirds.  Earth, then Water, then Ammonio
        wid_div3 = scr_reg.reg['fss']['width']/3

        # Exit out of FSS, we got the images we need to process
        self.keys.send('ExplorationFSSQuit')

        # Uncomment this to show on the ED Window where the region is define.  Must run this file as an App, so uncomment out
        # the main at the bottom of file
        #self.overlay.overlay_rect('fss', (scr_reg.reg['fss']['rect'][0], scr_reg.reg['fss']['rect'][1]),
        #                (scr_reg.reg['fss']['rect'][2],  scr_reg.reg['fss']['rect'][3]), (120, 255, 0),2)
        #self.overlay.overlay_paint()

        if self.cv_view:
            elw_image_d = elw_image.copy()
            elw_image_d = cv2.cvtColor(elw_image_d, cv2.COLOR_GRAY2RGB)
            #self.draw_match_rect(elw_image_d, maxLoc, (maxLoc[0]+15,maxLoc[1]+15), (255,255,255), 1)
            self.draw_match_rect(elw_image_d, maxLoc1, (maxLoc1[0]+15, maxLoc1[1]+25), (0, 0, 255), 1)
            cv2.putText(elw_image_d, f'{maxVal1:5.2f}> .70', (1, 40), cv2.FONT_HERSHEY_SIMPLEX, 0.30, (255, 255, 255), 1, cv2.LINE_AA)
            cv2.imshow('fss', elw_image_d)
            cv2.moveWindow('fss', self.cv_view_x, self.cv_view_y+100)
            cv2.waitKey(30)

        logger.info("elw detected:{0:6.2f} ".format(maxVal)+" sig:{0:6.2f}".format(maxVal1))

        # check if the circle or the signal meets probability number, if so, determine which type by its region
        #if (maxVal > 0.65 or (maxVal1 > 0.60 and maxLoc1[1] < 30) ):
        # only check for singal
        if maxVal1 > 0.70 and maxLoc1[1] < 30:
            if maxLoc1[0] < wid_div3:
                sstr = "Earth"
            elif maxLoc1[0] > (wid_div3*2):
                sstr = "Water"
            else:
                sstr = "Ammonia"
            # log the entry into the elw.txt file
            f = open("elw.txt", 'a')
            f.write(self.jn.ship_state()["location"]+", Type: "+sstr+
                    ", Probabilty: {0:3.0f}% ".format((maxVal1*100))+
                    ", Date: "+str(datetime.now())+str("\n"))
            f.close()
            self.vce.say(sstr+" like world detected ")
            self.fss_detected = sstr+" like world detected "
            logger.info(sstr+" world at: "+str(self.jn.ship_state()["location"]))
        else:
            self.fss_detected = "nothing found"

        self.set_speed_100()

        return

    def have_destination(self, scr_reg) -> bool:
        """ Check to see if the compass is on the screen. """
        icompass_image, (minVal, maxVal, minLoc, maxLoc), match = scr_reg.match_template_in_region_x3('compass', 'compass')

        logger.debug("has_destination:"+str(maxVal))

        # need > x in the match to say we do have a destination
        if maxVal < scr_reg.compass_match_thresh:
            return False
        else:
            return True

    def interdiction_check(self) -> bool:
        """ Checks if we are being interdicted. This can occur in SC and maybe in system jump by Thargoids
        (needs to be verified). Returns False if not interdicted, True after interdiction is detected and we
        get away. Use return result to determine the next action (continue, or do something else).
        """
        # Return if we are not being interdicted.
        if not self.status.get_flag(FlagsBeingInterdicted):
            return False

        # Interdiction detected.
        self.vce.say("Danger. Interdiction detected.")
        self.ap_ckb('log', 'Interdiction detected.')

        # Keep setting speed to zero to submit while in supercruise or system jump.
        while self.status.get_flag(FlagsSupercruise) or self.status.get_flag2(Flags2FsdHyperdriveCharging):
            self.set_speed_0()  # Submit.
            sleep(0.5)

        # Set speed to 100%.
        self.set_speed_100()

        # Wait for cooldown to start.
        self.status.wait_for_flag_on(FlagsFsdCooldown)

        # Boost while waiting for cooldown to complete.
        while not self.status.wait_for_flag_off(FlagsFsdCooldown, timeout=1):
            self.keys.send('UseBoostJuice')

        # Ensure we are in supercruise
        self.sc_engage(True)

        # Update journal flag.
        self.jn.ship_state()['interdicted'] = False  # reset flag
        return True

    def get_nav_offset(self, scr_reg, disable_auto_cal: bool = False):
        """ Determine the x,y offset from center of the compass of the nav point.
        @return: Returns the x,y,z value as x,y in degrees (-90 to 90) and z as 1 or -1.
        {'x': x.xx, 'y': y.yy, 'z': -1|0|+1,'roll': r.rr, 'pit': p.pp, 'yaw': y.yy} | None
        Where 'roll' is:
           -180deg (6 o'clock anticlockwise) to
            0deg (12 o'clock) to
            180deg (6 o'clock clockwise)
        """
        full_compass_image = None
        maxLoc = 0
        maxVal = 0
        # for i in range(2):
        full_compass_image, (minVal, maxVal, minLoc, maxLoc), match = scr_reg.match_template_in_region_x3('compass', 'compass')

            # # need > x in the match to say we do have a destination
            # if maxVal < (scr_reg.compass_match_thresh / 2):
            #     # If we are so far below threshold, then compass must not be up
            #     return None
            # if maxVal < scr_reg.compass_match_thresh:
            #     # We are below match, but only just, recalibrate
            #     if not disable_auto_cal:
            #         self.ap_ckb('log', f'Compass Offset below threshold: {maxVal:5.4f} with scale: {self.compass_scale:5.4f}')
            #         self.quick_calibrate_compass()

        # need > x in the match to say we do have a destination
        if maxVal < scr_reg.compass_match_thresh:
            if self.debug_images:
                f = get_timestamped_filename('[get_nav_offset] no_compass_match', '', '.png')
                cv2.imwrite(f'{self.debug_image_folder}/{f}', full_compass_image)
            return None

        pt = maxLoc

        # get wid/hgt of templates
        c_left = scr_reg.reg['compass']['rect'][0]
        c_top = scr_reg.reg['compass']['rect'][1]
        c_wid = scr_reg.templates.template['compass']['width']
        c_hgt = scr_reg.templates.template['compass']['height']
        wid = scr_reg.templates.template['navpoint']['width']
        hgt = scr_reg.templates.template['navpoint']['height']

        # cut out the compass from the region
        pad = 5
        compass_image = full_compass_image[abs(pt[1]-pad): pt[1]+c_hgt+pad, abs(pt[0]-pad): pt[0]+c_wid+pad].copy()
        #compass_image_gray = cv2.cvtColor(compass_image, cv2.COLOR_BGR2GRAY)
        compass_image_gray = self.scrReg.equalize(compass_image)

        # find the nav point within the compass box
        navpt_image, (n_minVal, n_maxVal, n_minLoc, n_maxLoc), match = scr_reg.match_template_in_image_x3(compass_image, 'navpoint')
        navpt_image_beh, (n_minVal, n_maxVal_beh, n_minLoc, n_maxLoc_beh), match_beh = scr_reg.match_template_in_image_x3(compass_image, 'navpoint-behind')

        n_pt = n_maxLoc
        n_pt_beh = n_maxLoc_beh

        compass_x_min = pad
        compass_x_max = c_wid + pad - wid
        compass_y_min = pad
        compass_y_max = c_hgt + pad - hgt

        # Check if the Nav Point is visible. If not, the Nav Point Behind may be visible
        if n_maxVal > scr_reg.navpoint_match_thresh:
            final_z_pct = 1.0  # Ahead
            n_pt = n_maxLoc
        else:
            final_z_pct = -1.0  # Behind
            n_pt = n_maxLoc_beh

        # Continue calc
        final_x_pct = 2*(((n_pt[0]-compass_x_min)/(compass_x_max-compass_x_min))-0.5)  # X as percent (-1.0 to 1.0, 0.0 in the center)
        final_x_pct = final_x_pct - self._nav_cor_x
        final_x_pct = max(min(final_x_pct, 1.0), -1.0)

        final_y_pct = -2*(((n_pt[1]-compass_y_min)/(compass_y_max-compass_y_min))-0.5)  # Y as percent (-1.0 to 1.0, 0.0 in the center)
        final_y_pct = final_y_pct - self._nav_cor_y
        final_y_pct = max(min(final_y_pct, 1.0), -1.0)

        # Calc angle in degrees starting at 0 deg at 12 o'clock and increasing clockwise
        # so 3 o'clock is +90° and 9 o'clock is -90°.
        final_roll_deg = 0.0
        if final_x_pct > 0.0:
            final_roll_deg = 90 - degrees(atan(final_y_pct/final_x_pct))
        elif final_x_pct < 0.0:
            final_roll_deg = -90 - degrees(atan(final_y_pct/final_x_pct))
        elif final_y_pct < 0.0:
            final_roll_deg = 180.0

        # 'longitudinal' radius of compass at given 'latitude'
        lng_rad_at_lat = math.cos(math.asin(final_y_pct))
        lng_rad_at_lat = max(lng_rad_at_lat, 0.001)  # Prevent div by zero

        # 'Latitudinal' radius of compass at given 'longitude'
        lat_rad_at_lng = math.sin(math.acos(final_x_pct))
        lat_rad_at_lng = max(lat_rad_at_lng, 0.001)  # Prevent div by zero

        # Pitch and yaw as a % of the max as defined by the compass circle
        pit_pct = max(min(final_y_pct/lat_rad_at_lng, 1.0), -1.0)
        yaw_pct = max(min(final_x_pct/lng_rad_at_lat, 1.0), -1.0)

        if final_z_pct > 0:
            final_pit_deg = (-1 * degrees(math.acos(pit_pct))) + 90  # Y in deg (-90.0 to 90.0, 0.0 in the center)
            final_yaw_deg = (-1 * degrees(math.acos(yaw_pct))) + 90  # X in deg (-90.0 to 90.0, 0.0 in the center)
        else:
            if final_y_pct > 0:
                final_pit_deg = degrees(math.acos(pit_pct)) + 90  # Y in deg (-90.0 to 90.0, 0.0 in the center)
            else:
                final_pit_deg = degrees(math.acos(pit_pct)) - 270  # Y in deg (-90.0 to 90.0, 0.0 in the center)

            if final_x_pct > 0:
                final_yaw_deg = degrees(math.acos(yaw_pct)) + 90  # X in deg (-90.0 to 90.0, 0.0 in the center)
            else:
                final_yaw_deg = degrees(math.acos(yaw_pct)) - 270  # X in deg (-90.0 to 90.0, 0.0 in the center)

        result = {'x': round(final_x_pct, 4), 'y': round(final_y_pct, 4), 'z': round(final_z_pct, 2),
                  'roll': round(final_roll_deg, 2), 'pit': round(final_pit_deg, 2), 'yaw': round(final_yaw_deg, 2)}

        # Draw box around region
        if self.debug_overlay:
            border = 10  # border to prevent the box from interfering with future matches
            left = c_left + maxLoc[0]
            top = c_top + maxLoc[1]
            self.overlay.overlay_rect('compass', (left - border, top - border), (left + c_wid + border, top + c_hgt + border), (0, 255, 0), 2)
            self.overlay.overlay_floating_text('compass', f'Com: {maxVal:5.2f} > {scr_reg.compass_match_thresh}', left - border, top - border - 65, (0, 255, 0))
            self.overlay.overlay_floating_text('nav', f'Nav: {n_maxVal:5.2f} > {scr_reg.navpoint_match_thresh}', left - border, top - border - 45, (0, 255, 0))
            self.overlay.overlay_floating_text('nav_beh', f'NavB: {n_maxVal_beh:5.2f}', left - border, top - border - 25, (0, 255, 0))
            self.overlay.overlay_floating_text('compass_rpy', f'r: {round(final_roll_deg, 2)} p: {round(final_pit_deg, 2)} y: {round(final_yaw_deg, 2)}', left - border, top + c_hgt + border, (0, 255, 0))
            self.overlay.overlay_paint()

        if self.cv_view:
            #icompass_image_d = cv2.cvtColor(compass_image_gray, cv2.COLOR_GRAY2RGB)
            icompass_image_d = full_compass_image
            self.draw_match_rect(icompass_image_d, pt, (pt[0]+c_wid, pt[1]+c_hgt), (0, 0, 255), 2)
            #cv2.rectangle(icompass_image_display, pt, (pt[0]+c_wid, pt[1]+c_hgt), (0, 0, 255), 2)
            #self.draw_match_rect(compass_image, n_pt, (n_pt[0] + wid, n_pt[1] + hgt), (255,255,255), 2)
            self.draw_match_rect(icompass_image_d, (pt[0]+n_pt[0]-pad, pt[1]+n_pt[1]-pad), (pt[0]+n_pt[0]+wid-pad, pt[1]+n_pt[1]+hgt-pad), (0, 255, 0), 1)
            #cv2.rectangle(icompass_image_display, (pt[0]+n_pt[0]-pad, pt[1]+n_pt[1]-pad), (pt[0]+n_pt[0] + wid-pad, pt[1]+n_pt[1] + hgt-pad), (0, 0, 255), 2)

            #   dim = (int(destination_width/3), int(destination_height/3))

            #   img = cv2.resize(dst_image, dim, interpolation =cv2.INTER_AREA)
            icompass_image_d = cv2.rectangle(icompass_image_d, (0, 0), (1000, 60), (0, 0, 0), -1)
            cv2.putText(icompass_image_d, f'Compass: {maxVal:5.4f} > {scr_reg.compass_match_thresh:5.2f}', (1, 10), cv2.FONT_HERSHEY_SIMPLEX, 0.4, (255, 255, 255), 1, cv2.LINE_AA)
            cv2.putText(icompass_image_d, f'Nav Point: {n_maxVal:5.4f} > {scr_reg.navpoint_match_thresh:5.2f}', (1, 25), cv2.FONT_HERSHEY_SIMPLEX, 0.4, (255, 255, 255), 1, cv2.LINE_AA)
            #cv2.putText(icompass_image_d, f'Result: {result}', (1, 40), cv2.FONT_HERSHEY_SIMPLEX, 0.4, (255, 255, 255), 1, cv2.LINE_AA)
            cv2.putText(icompass_image_d, f'x: {final_x_pct:5.2f} y: {final_y_pct:5.2f} z: {final_z_pct:5.2f}', (1, 40), cv2.FONT_HERSHEY_SIMPLEX, 0.4, (255, 255, 255), 1, cv2.LINE_AA)
            cv2.putText(icompass_image_d, f'r: {final_roll_deg:5.2f}deg p: {final_pit_deg:5.2f}deg y: {final_yaw_deg:5.2f}deg', (1, 55), cv2.FONT_HERSHEY_SIMPLEX, 0.4, (255, 255, 255), 1, cv2.LINE_AA)
            cv2.imshow('compass', icompass_image_d)
            cv2.moveWindow('compass', self.cv_view_x - 400, self.cv_view_y + 600)
            cv2.waitKey(30)

        return result

    def get_target_offset(self, scr_reg, disable_auto_cal: bool = False):
        """ Determine how far off we are from the target being in the middle of the screen
        (in this case the specified region).
        @return: {'roll': r.rr, 'pit': p.pp, 'yaw': y.yy, 'occ': True|False}, where all are in degrees
            Where 'roll' is:
            -180deg (6 o'clock anticlockwise) to
             0deg (12 o'clock) to
             180deg (6 o'clock clockwise)
            'occ' is True if the target is occluded, else False
        """
        # Clear the overlays before grabbing image
        # if self.debug_overlay:
        #     self.overlay.overlay_remove_rect('target')
        #     self.overlay.overlay_remove_floating_text('target')
        #     self.overlay.overlay_remove_floating_text('target_rpy')
        #     self.overlay.overlay_paint()

        dst_image = None
        maxLoc = 0
        maxVal = 0
        # for i in range(2):
        dst_image, (minVal, maxVal, minLoc, maxLoc), match = scr_reg.match_template_in_region('target', 'target')
        dst_image_occ, (minVal, maxVal_occ, minLoc, maxLoc_occ), match_occ = scr_reg.match_template_in_region('target_occluded', 'target_occluded', inv_col=False)
        #
        #     # need > x in the match to say we do have a destination
        #     if maxVal < (scr_reg.target_thresh / 2):
        #         # If we are so far below threshold, then target must not be up
        #         return None
        #     elif maxVal < scr_reg.target_thresh:
        #         # We are below match, but only just, recalibrate
        #         if not disable_auto_cal:
        #             self.ap_ckb('log', f'Target Offset below threshold: {maxVal:5.4f} with scale: {self.scr.scaleX:5.4f}')
        #             self.quick_calibrate_target()

        pt = maxLoc
        pt_occ = maxLoc_occ

        # Check if target is occluded
        if maxVal > maxVal_occ:
            sel_pt = pt
            sel_loc = maxLoc
            occluded = False
        else:
            sel_pt = pt_occ
            sel_loc = maxLoc_occ
            occluded = True

        destination_left = scr_reg.reg['target']['rect'][0]
        destination_top = scr_reg.reg['target']['rect'][1]
        destination_width = scr_reg.reg['target']['width']
        destination_height = scr_reg.reg['target']['height']

        width = scr_reg.templates.template['target']['width']
        height = scr_reg.templates.template['target']['height']

        target_x_max = self.scr.screen_width - width
        target_y_max = self.scr.screen_height - height

        # X as percent (-1.0 to 1.0, 0.0 in the center)
        final_x_pct = 2.0*(((sel_pt[0]+destination_left) / target_x_max) - 0.5)
        final_x_pct = 100 * max(min(final_x_pct, 1.0), -1.0)

        # Y as percent (-1.0 to 1.0, 0.0 in the center)
        final_y_pct = -2.0*(((sel_pt[1]+destination_top) / target_y_max) - 0.5)
        final_y_pct = 100 * max(min(final_y_pct, 1.0), -1.0)

        final_yaw_deg = final_x_pct / 100 * (self.hor_fov / 2)  # X in deg (-90.0 to 90.0, 0.0 in the center)
        final_pit_deg = final_y_pct / 100 * (self.ver_fov / 2)  # Y in deg (-90.0 to 90.0, 0.0 in the center)

        # Calc angle in degrees starting at 0 deg at 12 o'clock and increasing clockwise
        # so 3 o'clock is +90° and 9 o'clock is -90°.
        final_roll_deg = 0.0
        if final_x_pct > 0.0:
            final_roll_deg = 90 - degrees(atan(final_pit_deg/final_yaw_deg))
        elif final_x_pct < 0.0:
            final_roll_deg = -90 - degrees(atan(final_pit_deg/final_yaw_deg))
        elif final_y_pct < 0.0:
            final_roll_deg = 180.0

        # Draw box around region
        if self.debug_overlay:
            border = 10  # border to prevent the box from interfering with future matches
            left = destination_left + sel_loc[0]
            top = destination_top + sel_loc[1]
            self.overlay.overlay_rect('target', (left - border, top - border), (left + width + border, top + height + border), (0, 255, 0), 2)
            self.overlay.overlay_floating_text('target', f'Tar: {maxVal:5.2f} > {scr_reg.target_thresh}', left - border, top - border - 45, (0, 255, 0))
            self.overlay.overlay_floating_text('target_occ', f'TarOcc: {maxVal_occ:5.2f} > {scr_reg.target_occluded_thresh}', left - border, top - border - 25, (0, 255, 0))
            self.overlay.overlay_floating_text('target_rpy', f'r: {round(final_roll_deg, 2)} p: {round(final_pit_deg, 2)} y: {round(final_yaw_deg, 2)}', left - border, top + height + border, (0, 255, 0))
            self.overlay.overlay_paint()

        if self.cv_view:
            dst_image_d = cv2.cvtColor(dst_image, cv2.COLOR_GRAY2RGB)
            try:
                self.draw_match_rect(dst_image_d, sel_pt, (sel_pt[0]+width, sel_pt[1]+height), (0, 0, 255), 2)
                dim = (int(destination_width/2), int(destination_height/2))

                img = cv2.resize(dst_image_d, dim, interpolation=cv2.INTER_AREA)
                img = cv2.rectangle(img, (0, 0), (1000, 25), (0, 0, 0), -1)
                cv2.putText(img, f'{maxVal:5.4f} > {scr_reg.target_thresh:5.2f}', (1, 10), cv2.FONT_HERSHEY_SIMPLEX, 0.4, (255, 255, 255), 1, cv2.LINE_AA)
                cv2.putText(img, f'p: {round(final_pit_deg, 4)} y: {round(final_yaw_deg, 4)}',
                            (1, 25), cv2.FONT_HERSHEY_SIMPLEX, 0.4, (255, 255, 255), 1, cv2.LINE_AA)
                cv2.imshow('target', img)
                #cv2.moveWindow('target', self.cv_view_x, self.cv_view_y+425)
            except Exception as e:
                print("exception in getdest: "+str(e))
            cv2.waitKey(30)

        # must be > x to have solid hit, otherwise we are facing wrong way (empty circle)
        if maxVal < scr_reg.target_thresh and maxVal_occ < scr_reg.target_occluded_thresh:
            if self.debug_images:
                f = get_timestamped_filename('[get_target_offset] no_target_match', '', '.png')
                cv2.imwrite(f'{self.debug_image_folder}/{f}', dst_image)
            result = None
        else:
            result = {'roll': round(final_roll_deg, 2), 'pit': round(final_pit_deg, 2), 'yaw': round(final_yaw_deg, 2), 'occ': occluded}

        return result

    # def is_destination_occluded(self, scr_reg) -> bool:
    #     """ Looks to see if the 'dashed' line of the target is present indicating the target
    #     is occluded by the planet.
    #     @param scr_reg: The screen region to check.
    #     @return: True if target occluded (meets threshold), else False.
    #     """
    #     dst_image, (minVal, maxVal, minLoc, maxLoc), match = scr_reg.match_template_in_region('target_occluded', 'target_occluded', inv_col=False)
    #
    #     pt = maxLoc
    #
    #     if self.cv_view:
    #         dst_image_d = cv2.cvtColor(dst_image, cv2.COLOR_GRAY2RGB)
    #         destination_width = scr_reg.reg['target']['width']
    #         destination_height = scr_reg.reg['target']['height']
    #
    #         width  = scr_reg.templates.template['target_occluded']['width']
    #         height = scr_reg.templates.template['target_occluded']['height']
    #         try:
    #             self.draw_match_rect(dst_image_d, pt, (pt[0]+width, pt[1]+height), (0, 0, 255), 2)
    #             dim = (int(destination_width/2), int(destination_height/2))
    #
    #             img = cv2.resize(dst_image_d, dim, interpolation=cv2.INTER_AREA)
    #             img = cv2.rectangle(img, (0, 0), (1000, 25), (0, 0, 0), -1)
    #             cv2.putText(img, f'{maxVal:5.4f} > {scr_reg.target_occluded_thresh:5.2f}', (1, 20), cv2.FONT_HERSHEY_SIMPLEX, 0.4, (255, 255, 255), 1, cv2.LINE_AA)
    #             cv2.imshow('occluded', img)
    #             cv2.moveWindow('occluded', self.cv_view_x, self.cv_view_y+650)
    #         except Exception as e:
    #             print("exception in getdest: "+str(e))
    #         cv2.waitKey(30)
    #
    #     if maxVal > scr_reg.target_occluded_thresh:
    #         logger.debug(f"Target is occluded ({maxVal:5.4f} > {scr_reg.target_occluded_thresh:5.2f})")
    #         return True
    #     else:
    #         #logger.debug(f"Target is not occluded ({maxVal:5.4f} < {scr_reg.target_occluded_thresh:5.2f})")
    #         return False

    def sc_disengage_label_up(self, scr_reg) -> bool:
        """ look for messages like "PRESS [J] TO DISENGAGE" or "SUPERCRUISE OVERCHARGE ACTIVE",
         if in this region then return true.
        The aim of this function is to return that a message is there, and then use OCR to determine
        what the message is. This will only use the high CPU usage OCR when necessary."""
        dis_image, (minVal, maxVal, minLoc, maxLoc), match = scr_reg.match_template_in_region('disengage', 'disengage')

        pt = maxLoc

        width = scr_reg.templates.template['disengage']['width']
        height = scr_reg.templates.template['disengage']['height']

        # # Draw box around region
        # reg_rect = scr_reg.reg['disengage']['rect']
        # if self.debug_overlay:
        #     abs_rect = [pt[0] + reg_rect[0], pt[1] + reg_rect[1], pt[0] + reg_rect[0] + width, pt[1] + reg_rect[1] + height]
        #     self.overlay.overlay_rect1('sc_disengage_label_up', abs_rect, (0, 255, 0), 2)
        #     self.overlay.overlay_floating_text('sc_disengage_label_up', f'Match: {maxVal:5.4f} > {scr_reg.disengage_thresh}', abs_rect[0], abs_rect[1] - 25, (0, 255, 0))
        #     self.overlay.overlay_paint()

        if self.cv_view:
            self.draw_match_rect(dis_image, pt, (pt[0] + width, pt[1] + height), (0,255,0), 2)
            dis_image = cv2.rectangle(dis_image, (0, 0), (1000, 25), (0, 0, 0), -1)
            cv2.putText(dis_image, f'{maxVal:5.4f} > {scr_reg.disengage_thresh}', (1, 20), cv2.FONT_HERSHEY_SIMPLEX, 0.4, (255, 255, 255), 1, cv2.LINE_AA)
            cv2.imshow('sc_disengage_label_up', dis_image)
            cv2.moveWindow('sc_disengage_label_up', self.cv_view_x-460,self.cv_view_y+575)
            cv2.waitKey(1)

        if maxVal > scr_reg.disengage_thresh:
            return True
        else:
            return False

    def sc_disengage(self, scr_reg) -> bool:
        """ DEPRECATED - Replaced with 'sc_disengage_label_up' and 'sc_disengage_active' using OCR.
        look for the "PRESS [J] TO DISENGAGE" image, if in this region then return true
        """
        dis_image, (minVal, maxVal, minLoc, maxLoc), match = scr_reg.match_template_in_region('disengage', 'disengage')

        pt = maxLoc

        width = scr_reg.templates.template['disengage']['width']
        height = scr_reg.templates.template['disengage']['height']

        # Draw box around region
        if self.debug_overlay:
            abs_rect = scr_reg.reg['disengage']['rect']
            self.overlay.overlay_rect1('sc_disengage', abs_rect, (0, 255, 0), 2)
            self.overlay.overlay_floating_text('sc_disengage', f'Dis: {maxVal:5.4f} > {scr_reg.disengage_thresh}', abs_rect[0], abs_rect[1] - 25, (0, 255, 0))
            self.overlay.overlay_paint()

        if self.cv_view:
            self.draw_match_rect(dis_image, pt, (pt[0] + width, pt[1] + height), (0,255,0), 2)
            dis_image = cv2.rectangle(dis_image, (0, 0), (1000, 25), (0, 0, 0), -1)
            cv2.putText(dis_image, f'{maxVal:5.4f} > {scr_reg.disengage_thresh}', (1, 20), cv2.FONT_HERSHEY_SIMPLEX, 0.4, (255, 255, 255), 1, cv2.LINE_AA)
            cv2.imshow('disengage', dis_image)
            cv2.moveWindow('disengage', self.cv_view_x-460,self.cv_view_y+575)
            cv2.waitKey(1)

        if maxVal > scr_reg.disengage_thresh:
            # logger.info("'PRESS [] TO DISENGAGE' detected. Disengaging Supercruise")
            # self.ap_ckb('log+vce', "Disengaging Supercruise")
            return True
        else:
            return False

    def sc_disengage_ocr(self, scr_reg) -> bool:
        """ look for the "SUPERCRUISE OVERCHARGE ACTIVE" text using OCR, if in this region then return true. """
        # Do we have cockpit view? If not, return
        if self.status.get_gui_focus() != GuiFocusNoFocus:
            return False

        image = self.scr.get_screen_region(scr_reg.reg['disengage']['rect'])
        # TODO delete this line when COLOR_RGB2BGR is removed from get_screen()
        image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
        mask = scr_reg.capture_region_filtered(self.scr, 'disengage')
        masked_image = cv2.bitwise_and(image, image, mask=mask)
        image = masked_image

        start_time = None
        if self.debug_overlay:
            start_time = time.time()

        # OCR the selected item
        sim_match = 0.35  # Similarity match 0.0 - 1.0 for 0% - 100%)
        sim = 0.0
        ocr_textlist = self.ocr.image_simple_ocr(image, 'disengage')
        if ocr_textlist is not None:
            sim = self.ocr.string_similarity(self.locale["PRESS_TO_DISENGAGE_MSG"], str(ocr_textlist))
            logger.info(f"Disengage similarity with {str(ocr_textlist)} is {sim}")

        # Draw box around region
        if self.debug_overlay:
            elapsed_time = time.time() - start_time
            abs_rect = scr_reg.reg['disengage']['rect']
            self.overlay.overlay_rect1('sc_disengage_active', abs_rect, (0, 255, 0), 2)
            self.overlay.overlay_floating_text('sc_disengage_active', f'{str(ocr_textlist)} ({round(elapsed_time, 4)} Secs)', abs_rect[0], abs_rect[1] - 25, (0, 255, 0))
            self.overlay.overlay_paint()

        if self.cv_view:
            image = cv2.rectangle(image, (0, 0), (1000, 30), (0, 0, 0), -1)
            cv2.putText(image, f'Text: {str(ocr_textlist)}', (1, 10), cv2.FONT_HERSHEY_SIMPLEX, 0.4, (255, 255, 255), 1, cv2.LINE_AA)
            cv2.putText(image, f'Similarity: {sim:5.4f} > {sim_match}', (1, 25), cv2.FONT_HERSHEY_SIMPLEX, 0.4, (255, 255, 255), 1, cv2.LINE_AA)
            cv2.imshow('disengage2', image)
            cv2.moveWindow('disengage2', self.cv_view_x - 460, self.cv_view_y + 650)
            cv2.waitKey(30)

        if sim > sim_match:
            # logger.info("'PRESS [] TO DISENGAGE' detected. Disengaging Supercruise")
            # cv2.imwrite(f'test/disengage.png', image)
            return True

        return False

    def start_sco_monitoring(self):
        """ Start Supercruise Overcharge Monitoring. This starts a parallel thread used to detect SCO
        until stop_sco_monitoring if called. """
        self._sc_sco_active_loop_enable = True

        if self._sc_sco_active_loop_thread is None or not self._sc_sco_active_loop_thread.is_alive():
            self._sc_sco_active_loop_thread = threading.Thread(target=self._sc_sco_active_loop, daemon=True)
            self._sc_sco_active_loop_thread.start()

    def stop_sco_monitoring(self):
        """ Stop Supercruise Overcharge Monitoring. """
        self._sc_sco_active_loop_enable = False
        self._sc_disengage_active = False

    def _sc_sco_active_loop(self):
        """ A loop to determine is Supercruise Overcharge is active.
        This runs on a separate thread monitoring the status in the background. """
        while self._sc_sco_active_loop_enable:
            start_time = time.time()

            # Try to determine if the disengage/sco text is there
            sc_sco_is_active_ls = self.sc_sco_is_active

            # Check if SCO active in flags
            self.sc_sco_is_active = self.status.get_flag2(Flags2FsdScoActive)

            if self.sc_sco_is_active and not sc_sco_is_active_ls:
                self.ap_ckb('log+vce', "Supercruise Overcharge activated")
            if sc_sco_is_active_ls and not self.sc_sco_is_active:
                self.ap_ckb('log+vce', "Supercruise Overcharge deactivated")

            # Protection if SCO is active
            if self.sc_sco_is_active:
                if self.status.get_flag(FlagsOverHeating):
                    logger.info("SCO Aborting, overheating")
                    self.ap_ckb('log+vce', "SCO Aborting, overheating")
                    self.keys.send('UseBoostJuice')
                elif self.status.get_flag(FlagsLowFuel):
                    logger.info("SCO Aborting, < 25% fuel")
                    self.ap_ckb('log+vce', "SCO Aborting, < 25% fuel")
                    self.keys.send('UseBoostJuice')
                elif self.jn.ship_state()['fuel_percent'] < self.config['FuelThreasholdAbortAP']:
                    logger.info("SCO Aborting, < users low fuel threshold")
                    self.ap_ckb('log+vce', "SCO Aborting, < users low fuel threshold")
                    self.keys.send('UseBoostJuice')

            # Check SC Disengage, but only when not in SC Overcharge
            if not self.sc_sco_is_active:
                # Enable one or the other!
                # self._sc_disengage_active = self.sc_disengage(self.scrReg)

                # if self.sc_disengage_label_up(scr_reg):
                self._sc_disengage_active = self.sc_disengage_ocr(self.scrReg)
            else:
                self._sc_disengage_active = False

            # Sleep upto 1 sec max. If OCR takes > 1 sec, there will be no delay
            elapsed_time = time.time() - start_time
            if elapsed_time < 1.0:
                sleep(1.0 - elapsed_time)

    def undock(self):
        """ Performs menu action to undock from Station """
        # Go to cockpit view
        self.ship_control.goto_cockpit_view()

        # Now we are on initial menu, we go up to top (which is Refuel)
        self.keys.send('UI_Up', repeat=3)

        # down to Auto Undock and Select it...
        self.keys.send('UI_Down')
        self.keys.send('UI_Down')
        self.keys.send('UI_Select')
        self.set_speed_0(repeat=2)

        # Performs left menu ops to request docking

    def request_docking(self):
        """ Request docking from Nav Panel. """
        self.nav_panel.request_docking()

    def dock(self):
        """ Docking sequence.  Assumes in normal space, will get closer to the Station
        then zero the velocity and execute menu commands to request docking, when granted
        will wait a configurable time for dock.  Perform Refueling and Repair.
        """
        # if not in normal space, give a few more sections as at times it will take a little bit
        if self.jn.ship_state()['status'] != "in_space":
            sleep(3)  # sleep a little longer

        if self.jn.ship_state()['status'] != "in_space":
            logger.error('In dock(), after wait, but still not in_space')

        sleep(5)  # wait 5 seconds to get to 7.5km to request docking
        self.set_speed_50()

        if self.jn.ship_state()['status'] != "in_space":
            self.set_speed_0()
            logger.error('In dock(), after long wait, but still not in_space')
            raise Exception('Docking failed (not in space)')

        sleep(12)
        # At this point (of sleep()) we should be < 7.5km from the station.  Go 0 speed
        # if we get docking granted ED's docking computer will take over
        self.set_speed_0(repeat=2)
        sleep(3)  # Wait for ship to come to stop
        self.ap_ckb('log+vce', "Initiating Docking Procedure")
        # Request docking through Nav panel.
        self.request_docking()
        sleep(1)

        tries = self.config['DockingRetries']
        granted = False
        if self.jn.ship_state()['status'] == "dockinggranted":
            granted = True
        else:
            for i in range(tries):
                if self.jn.ship_state()['no_dock_reason'] == "Distance":
                    self.set_speed_50()
                    sleep(5)
                    self.set_speed_0(repeat=2)
                sleep(3)  # Wait for ship to come to stop
                # Request docking through Nav panel.
                self.request_docking()
                self.set_speed_0(repeat=2)

                sleep(1.5)
                if self.jn.ship_state()['status'] == "dockinggranted":
                    granted = True
                    # Go back to navigation tab
                    #self.request_docking_cleanup()
                    break
                if self.jn.ship_state()['status'] == "dockingdenied":
                    pass

        if not granted:
            self.ap_ckb('log', 'Docking denied: '+str(self.jn.ship_state()['no_dock_reason']))
            logger.warning('Did not get docking authorization, reason:'+str(self.jn.ship_state()['no_dock_reason']))
            raise Exception('Docking failed (Did not get docking authorization)')
        else:
            self.ap_ckb('log+vce', "Docking request granted")
            # allow auto dock to take over
            for i in range(self.config['WaitForAutoDockTimer']):
                sleep(1)
                if self.jn.ship_state()['status'] == "in_station":
                    # go to top item, select (which should be refuel)
                    self.keys.send('UI_Up', hold=3)
                    self.keys.send('UI_Select')  # Refuel
                    sleep(0.5)
                    self.keys.send('UI_Right')  # Repair
                    self.keys.send('UI_Select')
                    sleep(0.5)
                    self.keys.send('UI_Right')  # Ammo
                    self.keys.send('UI_Select')
                    sleep(0.5)
                    self.keys.send("UI_Left", repeat=2)  # back to fuel
                    return

            self.ap_ckb('log', 'Auto dock timer timed out.')
            logger.warning('Auto dock timer timed out. Aborting Docking.')
            raise Exception('Docking failed (Auto dock timer timed out)')

    def is_sun_dead_ahead(self, scr_reg):
        return scr_reg.sun_percent(scr_reg.screen) > 5

    # use to orient the ship to not be pointing right at the Sun
    # Checks brightness in the region in front of us, if brightness exceeds a threshold
    # then will pitch up until below threshold.
    #
    def sun_avoid(self, scr_reg):
        logger.debug('align= avoid sun')

        sleep(0.5)

        # close to core the 'sky' is very bright with close stars, if we are pitch due to a non-scoopable star
        #  which is dull red, the star field is 'brighter' than the sun, so our sun avoidance could pitch up
        #  endlessly. So we will have a fail_safe_timeout to kick us out of pitch up if we've pitch past 110 degrees, but
        #  we'll add 3 more second for pad in case the user has a higher pitch rate than the vehicle can do
        fail_safe_timeout = (120/self.pitchrate)+3
        starttime = time.time()

        # if sun in front of us, then keep pitching up until it is below us
        while self.is_sun_dead_ahead(scr_reg):
            self.keys.send('PitchUpButton', state=1)

            # check if we are being interdicted
            interdicted = self.interdiction_check()
            if interdicted:
                # Continue journey after interdiction
                self.set_speed_0()

            # if we are pitching more than N seconds break, may be in high density area star area (close to core)
            if ((time.time()-starttime) > fail_safe_timeout):
                logger.debug('sun avoid failsafe timeout')
                print("sun avoid failsafe timeout")
                break

        sleep(0.35)                 # up slightly so not to overheat when scooping
        # Some ships heat up too much and need pitch up a little further
        if self.sunpitchuptime > 0.0:
            sleep(self.sunpitchuptime)
        self.keys.send('PitchUpButton', state=0)

        # Some ships run cool so need to pitch down a little
        if self.sunpitchuptime < 0.0:
            self.keys.send('PitchDownButton', state=1)
            sleep(-1.0 * self.sunpitchuptime)
            self.keys.send('PitchDownButton', state=0)

    def compass_align(self, scr_reg) -> bool:
        """ Use the compass to find the nav point position when in SC or in space.  Will then perform rotation and
        pitching to put the nav point in the middle of the compass, i.e. target right in front of us.
        @return: True if aligned, else False.
        """
        close = 5.0  # in degrees
        if not (self.jn.ship_state()['status'] == 'in_supercruise' or self.jn.ship_state()['status'] == 'in_space'):
            logger.error('align=err1, nav_align not in super or space')
            raise Exception('nav_align not in super or space')

        self.ap_ckb('log+vce', 'Compass Align')

        # try multiple times to get aligned.  If the sun is shining on console, this it will be hard to match
        # the vehicle should be positioned with the sun below us via the sun_avoid() routine after a jump
        for ii in range(self.config['NavAlignTries']):
            off = self.get_nav_offset(scr_reg)
            if off is None:
                self.ap_ckb('log', 'Unable to detect compass. Rolling to new position.')
                # Try rolling if star glare is obscuring the compass
                self.roll_clockwise_anticlockwise(90)
                continue

            logger.debug(f"Compass position: yaw: {str(off['yaw'])} pit: {str(off['pit'])}")

            # Check if we are close enough already
            if abs(off['yaw']) < close and abs(off['pit']) < close:
                self.ap_ckb('log', 'Compass Align complete')
                return True

            # Roll if the nav point is not directly behind us.
            if ((-180 + close) < off['yaw'] < (180 - close) and
                    (-180 + close) < off['pit'] < (180 - close)):

                for i in range(20):
                    # Calc roll time based on nav point location
                    if off is None:
                        self.ap_ckb('log', 'Unable to detect compass.')
                        continue
                    if abs(off['roll']) > close and (180 - abs(off['roll']) > close):
                        # Clear the overlays before moving
                        if self.debug_overlay:
                            self.overlay.overlay_remove_rect('compass')
                            self.overlay.overlay_remove_floating_text('compass')
                            self.overlay.overlay_remove_floating_text('nav')
                            self.overlay.overlay_remove_floating_text('nav_beh')
                            self.overlay.overlay_remove_floating_text('compass_rpy')
                            self.overlay.overlay_paint()

                        self.roll_clockwise_anticlockwise(off['roll'])
                        sleep(1)
                        off = self.get_nav_offset(scr_reg)
                    else:
                        break

            for i in range(20):
                # Calc pitch time based on nav point location
                if off is None:
                    self.ap_ckb('log', 'Unable to detect compass.')
                    continue
                if abs(off['pit']) > close:
                    # Clear the overlays before moving
                    if self.debug_overlay:
                        self.overlay.overlay_remove_rect('compass')
                        self.overlay.overlay_remove_floating_text('compass')
                        self.overlay.overlay_remove_floating_text('nav')
                        self.overlay.overlay_remove_floating_text('nav_beh')
                        self.overlay.overlay_remove_floating_text('compass_rpy')
                        self.overlay.overlay_paint()

                    self.pitch_up_down(off['pit'])
                    sleep(0.75)
                    off = self.get_nav_offset(scr_reg)
                else:
                    break

            for i in range(20):
                # Calc yaw time based on nav point location
                if off is None:
                    self.ap_ckb('log', 'Unable to detect compass.')
                    continue
                if abs(off['yaw']) > close:
                    # Clear the overlays before moving
                    if self.debug_overlay:
                        self.overlay.overlay_remove_rect('compass')
                        self.overlay.overlay_remove_floating_text('compass')
                        self.overlay.overlay_remove_floating_text('nav')
                        self.overlay.overlay_remove_floating_text('nav_beh')
                        self.overlay.overlay_remove_floating_text('compass_rpy')
                        self.overlay.overlay_paint()

                    self.yaw_right_left(off['yaw'])
                    sleep(0.5)
                    off = self.get_nav_offset(scr_reg)
                else:
                    break

            sleep(.1)
            if off is not None:
                logger.debug(f"Compass position: yaw: {str(off['yaw'])} pit: {str(off['pit'])}")

        # Not aligned
        self.ap_ckb('log+vce', 'Compass Align failed - exhausted all retries')
        return False

    def mnvr_to_target(self, scr_reg):
        """ Maneuver to Target using compass then target before performing a jump."""
        logger.debug('mnvr_to_target entered')

        if not (self.jn.ship_state()['status'] == 'in_supercruise' or self.jn.ship_state()['status'] == 'in_space'):
            logger.error('align() not in sc or space')
            raise Exception('align() not in sc or space')

        self.sun_avoid(scr_reg)

        res = self.compass_align(scr_reg)
        # Quick calibrate the compass
        if res:
            self.quick_calibrate_compass()
        self.set_speed_100()

        self.ap_ckb('log+vce', 'Target Align')
        for i in range(5):
            align_res = self.sc_target_align(scr_reg)
            if align_res == ScTargetAlignReturn.Lost:
                self.compass_align(scr_reg)  # Compass Align

            elif align_res == ScTargetAlignReturn.Found:
                return

            elif align_res == ScTargetAlignReturn.Disengage:
                break

        logger.error('mnvr_to_target failed 5 times')
        raise Exception('mnvr_to_target failed 5 times')

    def sc_target_align(self, scr_reg) -> ScTargetAlignReturn:
        """ Align to the target, monitoring for disengage and obscured.
        @param scr_reg: The screen region class.
        @return: A string detailing the reason for the method return. Current return options:
            'lost': Lost target
            'found': Target found
            'disengage': Disengage text found
        """
        target_align_compass_mult = 3  # Multiplier to close and target_align_inner_lim when using compass for align.
        target_align_pit_off = 0.25  # In deg. To keep the target above the center line (prevent it going down out of view).

        target_pit = target_align_pit_off
        target_yaw = 0.0

        # Copy locally as we will change the values
        target_align_outer_lim = self.target_align_outer_lim
        target_align_inner_lim = self.target_align_inner_lim

        off = None
        tar_off1 = None
        nav_off1 = None
        tar_off2 = None
        nav_off2 = None

        # Try to get the target 5 times before quiting
        for i in range(5):
            # Check Target and Compass
            nav_off1 = self.get_nav_offset(scr_reg)
            tar_off1 = self.get_target_offset(scr_reg)
            if tar_off1:
                # Target detected
                off = tar_off1
                # logger.debug(f"sc_target_align x: {str(off['x'])} y:{str(off['y'])}")
                # Apply offset to keep target above center
                off['pit'] = off['pit'] - target_align_pit_off
            elif nav_off1:
                # Try to use the compass data if the target is not visible.
                off = nav_off1
                self.ap_ckb('log+vce', 'Using Compass for Target Align')

                # We are using compass align, increase the values as compass is much less accurate
                target_align_outer_lim = target_align_outer_lim * target_align_compass_mult
                target_align_inner_lim = target_align_inner_lim * target_align_compass_mult
                target_align_pit_off = target_align_pit_off * target_align_compass_mult

                # Check if Target is now behind us
                if nav_off1['z'] < 0:
                    self.ap_ckb('log', 'Target is behind us')
                    return ScTargetAlignReturn.Lost

            # Check if target occluded
            if tar_off1 and tar_off1['occ']:
                self.occluded_reposition(scr_reg)
                self.ap_ckb('log+vce', 'Target Align')

            # if self.is_destination_occluded(scr_reg):
            #     self.occluded_reposition(scr_reg)
            #     self.ap_ckb('log+vce', 'Target Align')

            # check for SC Disengage
            # if self.sc_disengage_label_up(scr_reg):
            #     if self.sc_disengage_ocr(scr_reg):
            if self._sc_disengage_active:
                self.ap_ckb('log+vce', 'Disengage Supercruise')
                self.keys.send('HyperSuperCombination')
                self.stop_sco_monitoring()
                return ScTargetAlignReturn.Disengage

            # Quit loop if we found Target or Compass
            if off:
                break

        # Target could not be found, return
        if tar_off1 is None and nav_off1 is None:
            logger.debug("sc_target_align not finding target")
            self.ap_ckb('log', 'Target Align failed - target not found')
            return ScTargetAlignReturn.Lost

        # We have Target or Compass. Are we close to Target?
        while ((abs(off['yaw']) > target_align_outer_lim) or
               (abs(off['pit']) > target_align_outer_lim)):

            target_align_outer_lim = target_align_inner_lim  # Keep aligning until we are within this lower range.

            # Clear the overlays before moving
            if self.debug_overlay:
                self.overlay.overlay_remove_rect('compass')
                self.overlay.overlay_remove_floating_text('compass')
                self.overlay.overlay_remove_floating_text('nav')
                self.overlay.overlay_remove_floating_text('nav_beh')
                self.overlay.overlay_remove_floating_text('compass_rpy')

                self.overlay.overlay_remove_rect('target')
                self.overlay.overlay_remove_floating_text('target')
                self.overlay.overlay_remove_floating_text('target_occ')
                self.overlay.overlay_remove_floating_text('target_rpy')
                self.overlay.overlay_paint()

            # Calc pitch time based on nav point location
            logger.debug(f"sc_target_align before: pit: {off['pit']} yaw: {off['yaw']} ")

            p_deg = 0.0
            if abs(off['pit']) > target_align_outer_lim:
                p_deg = off['pit']
                self.pitch_up_down(p_deg)

            # Calc yaw time based on nav point location
            y_deg = 0.0
            if abs(off['yaw']) > target_align_outer_lim:
                y_deg = off['yaw']
                self.yaw_right_left(y_deg)

            # Wait for ship to finish moving and picture to stabilize
            sleep(1.0)

            # Check Target and Compass
            nav_off2 = self.get_nav_offset(scr_reg)  # For cv view only
            tar_off2 = self.get_target_offset(scr_reg)
            if tar_off2:
                off = tar_off2
                logger.debug(f"sc_target_align after: pit:{off['pit']} yaw: {off['yaw']} ")
                # Apply offset to keep target above center
                off['pit'] = off['pit'] - target_align_pit_off
            elif nav_off2:
                # Try to use the compass data if the target is not visible.
                off = nav_off2
                self.ap_ckb('log+vce', 'Using Compass for Target Align')
                # Check if Target is now behind us
                if nav_off2['z'] < 0:
                    self.ap_ckb('log', 'Target is behind us')
                    return ScTargetAlignReturn.Lost

            if tar_off1 and tar_off2:
                # Check diff from before and after movement
                pit_delta = tar_off2['pit'] - tar_off1['pit']
                yaw_delta = tar_off2['yaw'] - tar_off1['yaw']
                if ((tar_off1['pit'] < 0.0 and tar_off2['pit'] > target_align_outer_lim) or
                        (tar_off1['pit'] > 0.0 and tar_off2['pit'] < -target_align_outer_lim)):
                    self.ap_ckb('log', f"TEST - Pitch correction gone too far. Reducing Pitch Factor.")
                    # Correct factor
                    # self.pitchfactor = self.pitchfactor - 1.0
                    # Update GUI with ship config
                    self.ap_ckb('update_ship_cfg')

                if ((tar_off1['yaw'] < 0.0 and tar_off2['yaw'] > target_align_outer_lim) or
                        (tar_off1['yaw'] > 0.0 and tar_off2['yaw'] < -target_align_outer_lim)):
                    self.ap_ckb('log', f"TEST - Yaw correction gone too far. Reducing Yaw Factor.")
                    # Correct factor
                    # self.yawfactor = self.yawfactor - 1.0
                    # Update GUI with ship config
                    self.ap_ckb('update_ship_cfg')

            if tar_off2:
                # Store current offsets
                tar_off1 = tar_off2.copy()

            # Check if target occluded
            if tar_off2 and tar_off2['occ']:
                self.occluded_reposition(scr_reg)
                self.ap_ckb('log+vce', 'Target Align')

            # if self.is_destination_occluded(scr_reg):
            #     self.occluded_reposition(scr_reg)
            #     self.ap_ckb('log+vce', 'Target Align')

            # check for SC Disengage
            # if self.sc_disengage_label_up(scr_reg):
            #     if self.sc_disengage_ocr(scr_reg):
            if self._sc_disengage_active:
                self.ap_ckb('log+vce', 'Disengage Supercruise')
                self.keys.send('HyperSuperCombination')
                self.stop_sco_monitoring()
                return ScTargetAlignReturn.Disengage

            # Check if target is outside the target region (behind us) and break loop
            if tar_off2 is None and nav_off2 is None:
                logger.debug("sc_target_align lost target")
                self.ap_ckb('log', 'Target Align failed - lost target.')
                return ScTargetAlignReturn.Lost

        # We are aligned, so define the navigation correction as the current offset. This won't be 100% accurate, but
        # will be within a few degrees.
        if tar_off1 and nav_off1:
            self._nav_cor_x = self._nav_cor_x + nav_off1['x']
            self._nav_cor_y = self._nav_cor_y + nav_off1['y']
        elif tar_off2 and nav_off2:
            self._nav_cor_x = self._nav_cor_x + nav_off2['x']
            self._nav_cor_y = self._nav_cor_y + nav_off2['y']

        # self.ap_ckb('log', 'Target Align complete.')
        return ScTargetAlignReturn.Found

    def occluded_reposition(self, scr_reg):
        """ Reposition is use when the target is occluded by a planet or other.
        We pitch 90 deg down for a bit, then up 90, this should make the target underneath us
        this is important because when we do nav_align() if it does not see the Nav Point
        in the compass (because it is a hollow circle), then it will pitch down, this will
        bring the target into view quickly. """
        self.ap_ckb('log+vce', 'Target occluded, repositioning.')
        self.set_speed_0()
        self.pitch_up_down(-90)

        # Speed away
        self.set_speed_100()
        sleep(15)

        self.set_speed_0()
        self.pitch_up_down(90)
        self.compass_align(scr_reg)
        self.set_speed_50()

    def honk(self):
        # Do the Discovery Scan (Honk)

        if self.status.get_flag(FlagsAnalysisMode):
            if self.config['DSSButton'] == 'Primary':
                logger.debug('position=scanning')
                self.keys.send('PrimaryFire', state=1)
            else:
                logger.debug('position=scanning')
                self.keys.send('SecondaryFire', state=1)

            sleep(7)  # roughly 6 seconds for DSS

            # stop pressing the Scanner button
            if self.config['DSSButton'] == 'Primary':
                logger.debug('position=scanning complete')
                self.keys.send('PrimaryFire', state=0)
            else:
                logger.debug('position=scanning complete')
                self.keys.send('SecondaryFire', state=0)
        else:
            self.ap_ckb('log', 'Not in analysis mode. Skipping discovery scan (honk).')

    def logout(self):
        """ Performs menu action to log out of game """
        self.update_ap_status("Logout")
        self.keys.send_key('Down', SCANCODE["Key_Escape"])
        sleep(0.5)
        self.keys.send_key('Up', SCANCODE["Key_Escape"])
        sleep(0.5)
        self.keys.send('UI_Up')
        sleep(0.5)
        self.keys.send('UI_Select')
        sleep(0.5)
        self.keys.send('UI_Select')
        sleep(0.5)
        self.update_ap_status("Idle")

    # position() happens after a refuel and performs
    #   - accelerate past sun
    #   - perform Discovery scan
    #   - perform fss (if enabled)
    def position(self, scr_reg, did_refuel=True):
        logger.debug('position')
        add_time = 12

        self.set_speed_100()

        self.vce.say("Passing star")

        # Need time to move past Sun, account for slowed ship if refueled
        pause_time = add_time
        if self.config["EnableRandomness"]:
            pause_time = pause_time+random.randint(0, 3)
        # need time to get away from the Sun so heat will dissipate before we use FSD
        sleep(pause_time)

        if self.config["ElwScannerEnable"]:
            self.fss_detect_elw(scr_reg)
            if self.config["EnableRandomness"]:
                sleep(random.randint(0, 3))
            sleep(3)
        else:
            sleep(5)  # since not doing FSS, need to give a little more time to get away from Sun, for heat

        self.vce.say("Maneuvering")

        logger.debug('position=complete')
        return True

    # jump() happens after we are aligned to Target
    # TODO: nees to check for Thargoid interdiction and their wave that would shut us down,
    #       if thargoid, then we wait until reboot and continue on.. go back into FSD and align
    def jump(self, scr_reg):
        logger.debug('jump')

        self.vce.say("Frameshift Jump")

        # Stop SCO monitoring
        self.stop_sco_monitoring()

        jump_tries = self.config['JumpTries']
        for i in range(jump_tries):

            logger.debug('jump= try:'+str(i))
            if not (self.jn.ship_state()['status'] == 'in_supercruise' or self.jn.ship_state()['status'] == 'in_space'):
                logger.error('Not ready to FSD jump. jump=err1')
                raise Exception('not ready to jump')
            sleep(0.5)
            logger.debug('jump= start fsd')

            # Initiate FSD Jump
            self.keys.send('HyperSuperCombination')

            res = self.status.wait_for_flag_on(FlagsFsdCharging, 5)
            if not res:
                logger.error('FSD failed to charge.')
                continue

            res = self.status.wait_for_flag_on(FlagsFsdJump, 30)
            if not res:
                logger.warning('FSD failure to start jump timeout.')
                self.mnvr_to_target(scr_reg)  # attempt realign to target
                continue

            logger.debug('jump= in jump')
            # Wait for jump to complete. Should never err
            res = self.status.wait_for_flag_off(FlagsFsdJump, 360)
            if not res:
                logger.error('FSD failure to complete jump timeout.')
                continue

            logger.debug('jump= speed 0')
            self.jump_cnt = self.jump_cnt+1
            self.set_speed_0(repeat=3)  # Let's be triply sure that we set speed to 0% :)
            sleep(1)  # wait 1 sec after jump to allow graphics to stablize and accept inputs
            logger.debug('jump=complete')

            # Start SCO monitoring ready when we drop back to SC.
            self.start_sco_monitoring()

            # We completed the jump
            return True

        logger.error(f'FSD Jump failed {jump_tries} times. jump=err2')
        raise Exception("FSD Jump failure")

        # a set of convience routes to pitch, rotate by specified degress

    def roll_clockwise_anticlockwise(self, deg):
        abs_deg = abs(deg)
        htime = abs_deg/self.rollrate

        # if self.speed_demand is None:
        #     self.set_speed_50()

        # # Using Power calc for roll rate
        # if 0 < abs_deg < 45:
        #     value = self.rollrate * math.pow((abs_deg / 45), (1 / self.roll_factor))
        #     value = min(value, self.rollrate)
        #     value = max(value, 0.01)
        #     htime = abs_deg / value

        # Calculate rate for less than 45 degrees, else use default
        if abs_deg < 45:
            # Roll rate from ship config
            ship_type = self.ship_configs['Ship_Configs'][self.current_ship_type]
            if self.speed_demand not in ship_type:
                ship_type[self.speed_demand] = dict()
            speed_demand = ship_type[self.speed_demand]
            if 'RollRate' not in speed_demand:
                speed_demand['RollRate'] = dict()

            last_deg = 0.0
            last_val = 0.0
            for key, value in speed_demand['RollRate'].items():
                key_deg = float(int(key)) / 10
                if abs_deg <= key_deg:
                    print(f"Roll demand: {deg}. Closest lookup: {key_deg}, {value}")

                    # Ratio based on the last value and this value
                    ratio_val = scale(abs_deg, last_deg, key_deg, last_val, value)
                    print(f"Roll demand: {deg}. Ratio value: {round(ratio_val, 2)}")

                    htime = abs_deg / ratio_val
                    break
                else:
                    last_deg = key_deg
                    last_val = value

        # Check if we are rolling right or left
        if deg > 0.0:
            self.keys.send('RollRightButton', hold=htime)
        else:
            self.keys.send('RollLeftButton', hold=htime)

    def pitch_up_down(self, deg):
        abs_deg = abs(deg)
        htime = abs_deg/self.pitchrate

        # if self.speed_demand is None:
        #     self.set_speed_50()

        # # Using Power calc for pitch rate
        # if 0 < abs_deg < 30:
        #     value = self.pitchrate * math.pow((abs_deg / 30), (1 / self.pitch_factor))
        #     value = min(value, self.pitchrate)
        #     value = max(value, 0.01)
        #     htime = abs_deg / value

        # Calculate rate for less than 30 degrees, else use default
        if abs_deg < 30:
            # Pitch rate from ship config
            ship_type = self.ship_configs['Ship_Configs'][self.current_ship_type]
            if self.speed_demand not in ship_type:
                ship_type[self.speed_demand] = dict()
            speed_demand = ship_type[self.speed_demand]
            if 'PitchRate' not in speed_demand:
                speed_demand['PitchRate'] = dict()

            last_deg = 0.0
            last_val = 0.0
            for key, value in speed_demand['PitchRate'].items():
                key_deg = float(int(key)) / 10
                if abs_deg <= key_deg:
                    print(f"Pitch demand: {deg}. Closest lookup: {key_deg}, {value}")

                    # Ratio based on the last value and this value
                    ratio_val = scale(abs_deg, last_deg, key_deg, last_val, value)
                    print(f"Pitch demand: {deg}. Ratio value: {round(ratio_val, 2)}")

                    htime = abs_deg / ratio_val
                    break
                else:
                    last_deg = key_deg
                    last_val = value

        # Check if we are pitching up or down
        if deg > 0.0:
            self.keys.send('PitchUpButton', hold=htime)
        else:
            self.keys.send('PitchDownButton', hold=htime)

    def yaw_right_left(self, deg):
        """ Yaw in deg. (> 0.0 for yaw right, < 0.0 for yaw left)
        @return: The key hold duration.
        """
        abs_deg = abs(deg)
        htime = abs_deg/self.yawrate

        # if self.speed_demand is None:
        #     self.set_speed_50()

        # # Using Power calc for yaw rate
        # if 0 < abs_deg < 30:
        #     value = self.yawrate * math.pow((abs_deg / 30), (1 / self.yaw_factor))
        #     value = min(value, self.yawrate)
        #     value = max(value, 0.01)
        #     htime = abs_deg / value

        # Calculate rate for less than 30 degrees, else use default
        if abs_deg < 30:
            # Yaw rate from ship config
            ship_type = self.ship_configs['Ship_Configs'][self.current_ship_type]
            if self.speed_demand not in ship_type:
                ship_type[self.speed_demand] = dict()
            speed_demand = ship_type[self.speed_demand]
            if 'YawRate' not in speed_demand:
                speed_demand['YawRate'] = dict()

            last_deg = 0.0
            last_val = 0.0
            for key, value in speed_demand['YawRate'].items():
                key_deg = float(int(key)) / 10
                if abs_deg <= key_deg:
                    print(f"Yaw demand: {deg}. Closest lookup: {key_deg}, {value}")

                    # Ratio based on the last value and this value
                    ratio_val = scale(abs_deg, last_deg, key_deg, last_val, value)
                    print(f"Yaw demand: {deg}. Ratio value: {round(ratio_val, 2)}")

                    htime = abs_deg / ratio_val
                    break
                else:
                    last_deg = key_deg
                    last_val = value

        # Check if we are yawing right or left
        if deg > 0.0:
            self.keys.send('YawRightButton', hold=htime)
        else:
            self.keys.send('YawLeftButton', hold=htime)

    def refuel(self, scr_reg):
        """ Check if refueling needed, ensure correct start type. """
        # Check if we have a fuel scoop
        has_fuel_scoop = self.jn.ship_state()['has_fuel_scoop']

        logger.debug('refuel')
        scoopable_stars = ['F', 'O', 'G', 'K', 'B', 'A', 'M']

        if self.jn.ship_state()['status'] != 'in_supercruise':
            logger.error('refuel=err1')
            return False

        is_star_scoopable = self.jn.ship_state()['star_class'] in scoopable_stars

        # if the sun is not scoopable, then set a low low threshold so we can pick up the dull red
        # sun types.  Since we won't scoop it doesn't matter how much we pitch up
        # if scoopable we know white/yellow stars are bright, so set higher threshold, this will allow us to
        #  mast out the galaxy edge (which is bright) and not pitch up too much and avoid scooping
        if is_star_scoopable == False or not has_fuel_scoop:
            scr_reg.set_sun_threshold(25)
        else:
            scr_reg.set_sun_threshold(self.config['SunBrightThreshold'])

        # Lets avoid the sun, shall we
        self.vce.say("Avoiding star")
        self.update_ap_status("Avoiding star")
        self.ap_ckb('log', 'Avoiding star')
        self.sun_avoid(scr_reg)

        if self.jn.ship_state()['fuel_percent'] < self.config['RefuelThreshold'] and is_star_scoopable and has_fuel_scoop:
            logger.debug('refuel= start refuel')
            self.vce.say("Refueling")
            self.ap_ckb('log', 'Refueling')
            self.update_ap_status("Refueling")

            # mnvr into position
            self.set_speed_100()
            sleep(5)
            self.set_speed_50()
            sleep(1.7)
            self.set_speed_0(repeat=3)

            self.refuel_cnt += 1

            # The log will not reflect a FuelScoop until first 5 tons filled, then every 5 tons until complete
            #if we don't scoop first 5 tons with 40 sec break, since not scooping or not fast enough or not at all, then abort
            startime = time.time()
            while not self.jn.ship_state()['is_scooping'] and not self.jn.ship_state()['fuel_percent'] == 100:
                # check if we are being interdicted
                interdicted = self.interdiction_check()
                if interdicted:
                    # Continue journey after interdiction
                    self.set_speed_0()

                if ((time.time()-startime) > int(self.config['FuelScoopTimeOut'])):
                    self.vce.say("Refueling abort, insufficient scooping")
                    return False

            logger.debug('refuel= wait for refuel')

            # We started fueling, so lets give it another timeout period to fuel up
            startime = time.time()
            while not self.jn.ship_state()['fuel_percent'] == 100:
                # check if we are being interdicted
                interdicted = self.interdiction_check()
                if interdicted:
                    # Continue journey after interdiction
                    self.set_speed_0()

                if ((time.time()-startime) > int(self.config['FuelScoopTimeOut'])):
                    self.vce.say("Refueling abort, insufficient scooping")
                    return True
                sleep(1)

            logger.debug('refuel=complete')
            return True

        elif is_star_scoopable == False:
            self.ap_ckb('log', 'Skip refuel - not a fuel star')
            logger.debug('refuel= needed, unsuitable star')
            self.pitch_up_down(20)
            return False

        elif self.jn.ship_state()['fuel_percent'] >= self.config['RefuelThreshold']:
            self.ap_ckb('log', 'Skip refuel - fuel level okay')
            logger.debug('refuel= not needed')
            return False

        elif not has_fuel_scoop:
            self.ap_ckb('log', 'Skip refuel - no fuel scoop fitted')
            logger.debug('No fuel scoop fitted.')
            self.pitch_up_down(20)
            return False

        else:
            self.pitch_up_down(15)  # if not refueling pitch up somemore so we won't heat up
            return False

    def waypoint_undock_seq(self):
        self.update_ap_status("Executing Undocking/Launch")

        # Store current location (on planet or in space)
        on_planet = self.status.get_flag(FlagsHasLatLong)
        on_orbital_construction_site = self.jn.ship_state()['exp_station_type'] == StationType.SpaceConstructionDepot
        fleet_carrier = self.jn.ship_state()['exp_station_type'] == StationType.FleetCarrier
        squadron_fleet_carrier = self.jn.ship_state()['exp_station_type'] == StationType.SquadronCarrier
        starport_outpost = not on_planet and not on_orbital_construction_site and not fleet_carrier and not squadron_fleet_carrier

        # Leave starport or planetary port
        if not on_planet:
            # Check that we are docked
            if self.status.get_flag(FlagsDocked):
                # Check if we have an advanced docking computer
                if not self.jn.ship_state()['has_adv_dock_comp']:
                    self.ap_ckb('log', "Unable to undock. Advanced Docking Computer not fitted.")
                    logger.warning('Unable to undock. Advanced Docking Computer not fitted.')
                    raise Exception('Unable to undock. Advanced Docking Computer not fitted.')

                # Undock from station
                self.undock()

                # need to wait until undock complete, that is when we are back in_space
                # TODO - This maybe an FDEV error. On leaving a FC, no music was played so the journal never logged that we went into space.
                while self.jn.ship_state()['status'] != 'in_space':
                    sleep(1)

                # If we are on a Fleet Carrier we will pitch up 90 deg and fly away to avoid planet
                if fleet_carrier:
                    self.ap_ckb('log+vce', 'Maneuvering')
                    # The pitch rates are defined in SC, not normal flights, so bump this up a bit
                    self.pitch_up_down(self.config['FCDepartureAngle'])

                    self.update_ap_status("Undock Complete, accelerating")

                    # Engage Supercruise
                    self.sc_engage(True)

                    # Wait the configured time before continuing
                    self.ap_ckb('log', 'Flying for configured FC departure time.')
                    sleep(self.config['FCDepartureTime'])

                # If we are on an Orbital Construction Site we will need to pitch up 90 deg to avoid crashes
                if on_orbital_construction_site:
                    self.ap_ckb('log+vce', 'Maneuvering')
                    # The pitch rates are defined in SC, not normal flights, so bump this up a bit
                    self.pitch_up_down(self.config['OCDepartureAngle'])

                if starport_outpost or on_orbital_construction_site:
                    # In space (launched from starport or outpost etc.) OR construction site
                    self.update_ap_status("Undock Complete, accelerating")

                    # Engage Supercruise
                    self.sc_engage(True)

        elif on_planet:
            # Check if we are on a landing pad (docked), or landed on the planet surface
            if self.status.get_flag(FlagsDocked):
                # We are on a landing pad (docked)
                # Check if we have an advanced docking computer
                if not self.jn.ship_state()['has_adv_dock_comp']:
                    self.ap_ckb('log', "Unable to undock. Advanced Docking Computer not fitted.")
                    logger.warning('Unable to undock. Advanced Docking Computer not fitted.')
                    raise Exception('Unable to undock. Advanced Docking Computer not fitted.')

                # Undock from port
                self.undock()

                # need to wait until undock complete, that is when we are back in_space
                while self.jn.ship_state()['status'] != 'in_space':
                    sleep(1)
                self.update_ap_status("Undock Complete, accelerating")

            elif self.status.get_flag(FlagsLanded):
                # We are on planet surface (not docked at planet landing pad)
                # Hold UP for takeoff
                self.keys.send('UpThrustButton', hold=6)
                self.keys.send('LandingGearToggle')
                self.update_ap_status("Takeoff Complete, accelerating")

            # Undocked or off the surface, so leave planet
            self.set_speed_50()
            # The pitch rates are defined in SC, not normal flights, so bump this up a bit
            self.pitch_up_down(90 * 1.25)

            # Engage Supercruise
            self.sc_engage(True)

            # Enable SCO. If SCO not fitted, this will do nothing.
            self.keys.send('UseBoostJuice')

            # Wait until out of orbit.
            res = self.status.wait_for_flag_off(FlagsHasLatLong, timeout=60)
            # TODO - do we need to check if we never leave orbit?

            # Disable SCO. If SCO not fitted, this will do nothing.
            self.keys.send('UseBoostJuice')

    def sc_engage(self, boost: bool) -> bool:
        """ Engages supercruise, then returns us to 50% speed, unless we are in SC already.
        """
        # Check if we are already in SC
        if self.status.get_flag(FlagsSupercruise):
            # Start SCO monitoring
            self.start_sco_monitoring()
            return True

        self.set_speed_100()

        # While Mass Locked, keep boosting.
        while self.status.get_flag(FlagsFsdMassLocked):
            if boost:
                self.keys.send('UseBoostJuice')
            sleep(1)

        # Engage Supercruise
        self.keys.send('Supercruise')

        # Start SCO monitoring
        self.start_sco_monitoring()

        # Wait for jump to supercruise, keep boosting.
        while not self.status.get_flag(FlagsFsdJump):
            if boost:
                self.keys.send('UseBoostJuice')
            sleep(1)

        # Wait for supercruise
        self.status.wait_for_flag_on(FlagsSupercruise, timeout=30)

        # Revert to 50%
        self.set_speed_50()

        return True

    def waypoint_assist(self, keys, scr_reg):
        """ Processes the waypoints, performing jumps and sc assist if going to a station
        also can then perform trades if specific in the waypoints file."""
        self.waypoint.waypoint_assist(keys, scr_reg)

    def jump_to_system(self, scr_reg) -> bool:
        """ Jumps to the currently targeted system. Returns True if we successfully travel there, else False. """
        # Disabled the below because when docking, after a system was selected, the status file did not update, so the
        # current status was never updated.
        # # Current in game destination
        # status = self.status.get_cleaned_data()
        # destination_body = status['Destination_Body']  # The body number (0 for prim star)
        # destination_name = status['Destination_Name']  # The system/body/station/settlement name
        #
        # # Check we have a route and that we have a destination to a star (body 0).
        # # We can have one without the other.
        # if destination_body != 0 or destination_name == "":
        #     self.ap_ckb('log', "A valid destination system is not selected.")
        #     return False

        # Check if the current nav route is to the target system
        last_nav_route_sys = self.nav_route.get_last_system().upper()
        if last_nav_route_sys == '':
            self.ap_ckb('log', "A valid destination system is not selected.")
            return False

        # if we are starting the waypoint docked at a station, we need to undock first
        if self.status.get_flag(FlagsDocked) or self.status.get_flag(FlagsLanded):
            self.waypoint_undock_seq()

        # Ensure we are in supercruise
        self.sc_engage(False)

        # Route sent...  FSD Assist to that destination
        fin = self.fsd_assist(scr_reg)
        if fin == FSDAssistReturn.Failed:
            return False

        return True

    def supercruise_to_station(self, scr_reg, station_name: str) -> bool:
        """ Supercruise to the specified target, which may be a station, FC, body, signal source, etc.
        Returns True if we travel successfully travel there, else False. """
        # If waypoint file has a Station Name associated then attempt targeting it
        self.update_ap_status(f"Targeting Station: {station_name}")
        #res = self.nav_panel.lock_destination(station_name)
        #if not res:
        #    return False

        # if we are starting the waypoint docked at a station, we need to undock first
        if self.status.get_flag(FlagsDocked) or self.status.get_flag(FlagsLanded):
            self.waypoint_undock_seq()

        # Ensure we are in supercruise
        self.sc_engage(False)

        # Successful targeting of Station, lets go to it
        sleep(3)  # Wait for compass to stop flashing blue!
        if self.have_destination(scr_reg):
            self.ap_ckb('log', " - Station: " + station_name)
            self.update_ap_status(f"SC to Station: {station_name}")
            self.sc_assist(scr_reg)
        else:
            self.ap_ckb('log', f" - Could not target station: {station_name}")
            return False

        return True

    def fsd_assist(self, scr_reg) -> FSDAssistReturn:
        """ FSD Route Assist. Jumps repeatedly to the destination system then returns.
        @return: True when arrived in system and no in-system target exists. False when
        arrived in system and an in-system target does exist."""
        # TODO - can we enable this? Seems like a better way
        # nav_route_parser = NavRouteParser()
        logger.debug('self.jn.ship_state='+str(self.jn.ship_state()))

        starttime = time.time()
        starttime -= 20  # to account for first instance not doing positioning

        # TODO - can we enable this? Seems like a better way
        # if nav_route_parser.get_last_system() is not None:
        if self.jn.ship_state()['target']:
            # if we are starting the waypoint docked at a station, we need to undock first
            if self.status.get_flag(FlagsDocked) or self.status.get_flag(FlagsLanded):
                self.update_overlay()
                self.waypoint_undock_seq()

        # Keep jumping as long as there is a system to jump to.
        # TODO - can we enable this? Seems like a better way
        # while nav_route_parser.get_last_system() is not None:
        while self.jn.ship_state()['target']:
            self.update_overlay()

            if self.jn.ship_state()['status'] == 'in_space' or self.jn.ship_state()['status'] == 'in_supercruise':
                self.update_ap_status("Align")

                self.mnvr_to_target(scr_reg)

                self.update_ap_status("Jump")

                self.jump(scr_reg)

                # update jump counters
                self.total_dist_jumped += self.jn.ship_state()['dist_jumped']
                self.total_jumps = self.jump_cnt + self.jn.ship_state()['jumps_remains']
                
                # reset, upon next Jump the Journal will be updated again, unless last jump,
                # so we need to clear this out
                
                self.jn.ship_state()['jumps_remains'] = 0

                avg_time_jump = (time.time()-starttime) / self.jump_cnt

                self._eta = (self.total_jumps - self.jump_cnt) * avg_time_jump
                self._str_eta = strfdelta(tdelta=self._eta, inputtype='seconds')

                self.update_overlay()

                self.ap_ckb('jumpcount', "Dist: {:,.1f}".format(self.total_dist_jumped)+"ly"+
                            "  Jumps: {}of{}".format(self.jump_cnt, self.total_jumps)+"  @{}s/j".format(int(avg_time_jump))+
                            "  Fu#: "+str(self.refuel_cnt) + " ETA: "+self._str_eta)
                self.ap_ckb('log', 'ETA (to System): '+self._str_eta)

                # Do the Discovery Scan (Honk)
                self.honk_thread = threading.Thread(target=self.honk, daemon=True)
                self.honk_thread.start()

                # Refuel
                refueled = self.refuel(scr_reg)

                self.update_ap_status("Maneuvering")

                self.position(scr_reg, refueled)

                if self.jn.ship_state()['fuel_percent'] < self.config['FuelThreasholdAbortAP']:
                    self.ap_ckb('log', "AP Aborting, low fuel")
                    self.vce.say("AP Aborting, low fuel")
                    return FSDAssistReturn.Failed

        sleep(2)  # wait until screen stabilizes from possible last positioning

        # if there is no destination defined, we are done
        if not self.have_destination(scr_reg):
            self.set_speed_0()
            self.ap_ckb('log+vce', f"Destination reached, distance jumped:"+str(int(self.total_dist_jumped))+" lightyears")
            if self.config["AutomaticLogout"]:
                sleep(5)
                self.logout()
            return FSDAssistReturn.Complete
        # else there is a destination in System, so let jump over to SC Assist
        else:
            self.set_speed_100()
            self.ap_ckb('log+vce', f"System reached, preparing for supercruise")
            sleep(1)
            return FSDAssistReturn.Partial

    def sc_assist(self, scr_reg, do_docking=True):
        """ Supercruise Assist loop to travel to target in system and perform autodock.
        """
        logger.debug("Entered sc_assist")

        # Goto cockpit view
        self.ship_control.goto_cockpit_view()

        align_failed = False
        # see if we have a compass up, if so then we have a target
        if not self.have_destination(scr_reg):
            self.ap_ckb('log', "Quiting SC Assist - Compass not found. Rotate ship and try again.")
            logger.debug("Quiting sc_assist - compass not found")
            return
        else:
            # Quick calibrate the compass
            self.quick_calibrate_compass()

        # if we are starting the waypoint docked at a station or landed, we need to undock/takeoff first
        if self.status.get_flag(FlagsDocked) or self.status.get_flag(FlagsLanded):
            self.update_overlay()
            self.waypoint_undock_seq()

        # Ensure we are in supercruise
        self.sc_engage(False)
        self.jn.ship_state()['interdicted'] = False

        # Ensure we are 50%, don't want the loop of shame
        # Align Nav to target
        self.set_speed_50()
        res = self.compass_align(scr_reg)  # Compass Align
        self.set_speed_50()

        # self.quick_calibrate_target()
        self.ap_ckb('log+vce', 'Target Align')
        align_res = self.sc_target_align(scr_reg)
        # Quick calibrate with the target in front
        # if align_res == ScTargetAlignReturn.Found:
        #     self.quick_calibrate_target()

        # Loop forever keeping tight align to target, until we get SC Disengage popup
        while True:
            sleep(0.05)
            if self.jn.ship_state()['status'] == 'in_supercruise':
                # Align and stay on target. If false is returned, we have lost the target behind us.
                align_res = self.sc_target_align(scr_reg)
                if align_res == ScTargetAlignReturn.Lost:
                    # Continue ahead before aligning to prevent us circling the target
                    # self.set_speed_100()
                    sleep(10)
                    self.set_speed_50()
                    self.compass_align(scr_reg)  # Compass Align

                elif align_res == ScTargetAlignReturn.Found:
                    pass

                elif align_res == ScTargetAlignReturn.Disengage:
                    break

            elif self.status.get_flag2(Flags2GlideMode):
                # Gliding - wait to complete
                logger.debug("Gliding")
                self.status.wait_for_flag2_off(Flags2GlideMode, 30)
                break
            else:
                # if we dropped from SC, then we rammed into planet
                logger.debug("No longer in supercruise")
                align_failed = True
                break

            # check if we are being interdicted
            interdicted = self.interdiction_check()
            if interdicted:
                # Continue journey after interdiction
                self.set_speed_50()
                self.compass_align(scr_reg)  # realign with station

            # check for SC Disengage
            # if self.sc_disengage_label_up(scr_reg):
            #     if self.sc_disengage_ocr(scr_reg):
            if self._sc_disengage_active:
                self.ap_ckb('log+vce', 'Disengage Supercruise')
                self.keys.send('HyperSuperCombination')
                self.stop_sco_monitoring()
                break

        # if no error, we must have gotten disengage
        if not align_failed and do_docking:
            sleep(4)  # wait for the journal to catch up

            # Check if this is a target we cannot dock at
            skip_docking = False
            if not self.jn.ship_state()['has_adv_dock_comp'] and not self.jn.ship_state()['has_std_dock_comp']:
                self.ap_ckb('log', "Skipping docking. No Docking Computer fitted.")
                skip_docking = True

            if not self.jn.ship_state()['SupercruiseDestinationDrop_type'] is None:
                if (self.jn.ship_state()['SupercruiseDestinationDrop_type'].startswith("$USS_Type")
                        # Bulk Cruisers
                        or "-class Cropper" in self.jn.ship_state()['SupercruiseDestinationDrop_type']
                        or "-class Hauler" in self.jn.ship_state()['SupercruiseDestinationDrop_type']
                        or "-class Reformatory" in self.jn.ship_state()['SupercruiseDestinationDrop_type']
                        or "-class Researcher" in self.jn.ship_state()['SupercruiseDestinationDrop_type']
                        or "-class Surveyor" in self.jn.ship_state()['SupercruiseDestinationDrop_type']
                        or "-class Traveller" in self.jn.ship_state()['SupercruiseDestinationDrop_type']
                        or "-class Tanker" in self.jn.ship_state()['SupercruiseDestinationDrop_type']):
                    self.ap_ckb('log', "Skipping docking. No docking privilege at MegaShips.")
                    skip_docking = True

            if not skip_docking:
                # go into docking sequence
                self.dock()
                self.ap_ckb('log+vce', "Docking complete, refueled, repaired and re-armed")
                self.update_ap_status("Docking Complete")
            else:
                self.set_speed_0()
        else:
            self.vce.say("Exiting Supercruise, setting throttle to zero")
            self.set_speed_0()  # make sure we don't continue to land
            self.ap_ckb('log', "Supercruise dropped, terminating SC Assist")

        self.ap_ckb('log+vce', "Supercruise Assist complete")

    def robigo_assist(self):
        self.robigo.loop(self)

    # Simply monitor for Shields down so we can boost away or our fighter got destroyed
    # and thus redeploy another one
    def afk_combat_loop(self):
        while True:
            if self.afk_combat.check_shields_up() == False:
                set_focus_elite_window()
                self.vce.say("Shields down, evading")
                self.afk_combat.evade()
                # after supercruise the menu is reset to top
                self.afk_combat.launch_fighter()  # at new location launch fighter
                break

            if self.afk_combat.check_fighter_destroyed() == True:
                set_focus_elite_window()
                self.vce.say("Fighter Destroyed, redeploying")
                self.afk_combat.launch_fighter()  # assuming two fighter bays

        self.vce.say("Terminating AFK Combat Assist")

    def dss_assist(self):
        while True:
            sleep(0.5)
            if self.jn.ship_state()['status'] == 'in_supercruise':
                cur_star_system = self.jn.ship_state()['cur_star_system']
                if cur_star_system != self._prev_star_system:
                    self.update_ap_status("DSS Scan")
                    self.ap_ckb('log', 'DSS Scan: '+cur_star_system)
                    set_focus_elite_window()
                    self.honk()
                    self._prev_star_system = cur_star_system
                    self.update_ap_status("Idle")

    def single_waypoint_assist(self):
        """ Travel to a system or station or both."""
        if self._single_waypoint_system == "" and self._single_waypoint_station == "":
            return False

        if self._single_waypoint_system != "":
            self.ap_ckb('log+vce', f"Targeting system {self._single_waypoint_system}.")
            # Select destination in galaxy map based on name
            res = self.galaxy_map.set_gal_map_destination_text(self, self._single_waypoint_system, self.jn.ship_state)
            if res:
                self.ap_ckb('log', f"System has been targeted.")
            else:
                self.ap_ckb('log+vce', f"Unable to target {self._single_waypoint_system} in Galaxy Map.")
                return False

            # Jump to destination
            res = self.jump_to_system(self.scrReg)
            if res is False:
                return False

        if self._single_waypoint_station != "":
            res = self.nav_panel.lock_destination(self._single_waypoint_station)
            if not res:
               return False

            res = self.supercruise_to_station(self.scrReg, self._single_waypoint_station)
            if res is False:
                return False

    # raising an exception to the engine loop thread, so we can terminate its execution
    #  if thread was in a sleep, the exception seems to not be delivered
    def ctype_async_raise(self, thread_obj, exception):
        found = False
        target_tid = 0
        for tid, tobj in threading._active.items():
            if tobj is thread_obj:
                found = True
                target_tid = tid
                break

        if not found:
            raise ValueError("Invalid thread object")

        ret = ctypes.pythonapi.PyThreadState_SetAsyncExc(ctypes.c_long(target_tid),
                                                         ctypes.py_object(exception))
        # ref: http://docs.python.org/c-api/init.html#PyThreadState_SetAsyncExc
        if ret == 0:
            raise ValueError("Invalid thread ID")
        elif ret > 1:
            # Huh? Why would we notify more than one threads?
            # Because we punch a hole into C level interpreter.
            # So it is better to clean up the mess.
            ctypes.pythonapi.PyThreadState_SetAsyncExc(target_tid, 0)
            raise SystemError("PyThreadState_SetAsyncExc failed")

    #
    # Setter routines for state variables
    #
    def set_fsd_assist(self, enable=True):
        if enable == False and self.fsd_assist_enabled == True:
            self.ctype_async_raise(self.ap_thread, EDAP_Interrupt)
        self.fsd_assist_enabled = enable

    def set_sc_assist(self, enable=True):
        if enable == False and self.sc_assist_enabled == True:
            self.ctype_async_raise(self.ap_thread, EDAP_Interrupt)
        self.sc_assist_enabled = enable

    def set_waypoint_assist(self, enable=True):
        if enable == False and self.waypoint_assist_enabled == True:
            self.ctype_async_raise(self.ap_thread, EDAP_Interrupt)
        self.waypoint_assist_enabled = enable

    def set_robigo_assist(self, enable=True):
        if enable == False and self.robigo_assist_enabled == True:
            self.ctype_async_raise(self.ap_thread, EDAP_Interrupt)
        self.robigo_assist_enabled = enable

    def set_afk_combat_assist(self, enable=True):
        if enable == False and self.afk_combat_assist_enabled == True:
            self.ctype_async_raise(self.ap_thread, EDAP_Interrupt)
        self.afk_combat_assist_enabled = enable

    def set_dss_assist(self, enable=True):
        if enable == False and self.dss_assist_enabled == True:
            self.ctype_async_raise(self.ap_thread, EDAP_Interrupt)
        self.dss_assist_enabled = enable

    def set_single_waypoint_assist(self, system: str, station: str, enable=True):
        if not enable and self.single_waypoint_enabled:
            self.ctype_async_raise(self.ap_thread, EDAP_Interrupt)
        self._single_waypoint_system = system
        self._single_waypoint_station = station
        self.single_waypoint_enabled = enable

    def set_cv_view(self, enable=True, x=0, y=0):
        self.cv_view = enable
        self.config['Enable_CV_View'] = int(self.cv_view)  # update the config
        self.update_config()  # save the config
        if enable == True:
            self.cv_view_x = x
            self.cv_view_y = y
        else:
            cv2.destroyAllWindows()
            cv2.waitKey(50)

    def set_randomness(self, enable=False):
        self.config["EnableRandomness"] = enable

    def set_activate_elite_eachkey(self, enable=False):
        self.config["ActivateEliteEachKey"] = enable

    def set_automatic_logout(self, enable=False):
        self.config["AutomaticLogout"] = enable

    def set_overlay(self, enable=False):
        # TODO: apply the change without restarting the program
        self.config["OverlayTextEnable"] = enable
        if not enable:
            self.overlay.overlay_clear()

        self.overlay.overlay_paint()

    def set_voice(self, enable=False):
        if enable == True:
            self.vce.set_on()
        else:
            self.vce.set_off()

    def set_fss_scan(self, enable=False):
        self.config["ElwScannerEnable"] = enable

    def set_log_error(self, enable=False):
        self.config["LogDEBUG"] = False
        self.config["LogINFO"] = False
        logger.setLevel(logging.ERROR)

    def set_log_debug(self, enable=False):
        self.config["LogDEBUG"] = True
        self.config["LogINFO"] = False
        logger.setLevel(logging.DEBUG)

    def set_log_info(self, enable=False):
        self.config["LogDEBUG"] = False
        self.config["LogINFO"] = True
        logger.setLevel(logging.INFO)

    # quit() is important to call to clean up, if we don't terminate the threads we created the AP will hang on exit
    # have then then kill python exec
    def quit(self):
        if self.vce != None:
            self.vce.quit()
        if self.overlay != None:
            self.overlay.overlay_quit()
        self.terminate = True

    #
    # This function will execute in its own thread and will loop forever until
    # the self.terminate flag is set
    #
    def engine_loop(self):
        while not self.terminate:
            # TODO - Remove these show compass/target all the time
            if self.debug_show_compass_overlay:
                self.get_nav_offset(self.scrReg, True)
            if self.debug_show_target_overlay:
                self.get_target_offset(self.scrReg, True)

            # TODO - Enable for test
            # self.start_sco_monitoring()

            # Ship calibration functions
            if self.ship_tst_roll_enabled:
                self.ship_tst_roll_new(0)
                self.ship_tst_roll_enabled = False
            if self.ship_tst_pitch_enabled:
                self.ship_tst_pitch_new(0)
                self.ship_tst_pitch_enabled = False
            if self.ship_tst_yaw_enabled:
                self.ship_tst_yaw_new(0)
                self.ship_tst_yaw_enabled = False

            if self.fsd_assist_enabled:
                logger.debug("Running fsd_assist")
                set_focus_elite_window()
                self.update_overlay()
                self.jump_cnt = 0
                self.refuel_cnt = 0
                self.total_dist_jumped = 0
                self.total_jumps = 0
                fin = True
                # could be deep in call tree when user disables FSD, so need to trap that exception
                try:
                    fin = self.fsd_assist(self.scrReg)
                except EDAP_Interrupt:
                    logger.debug("Caught stop exception")
                except Exception as e:
                    logger.debug("FSD Assist trapped generic:"+str(e))
                    print("Trapped generic:"+str(e))
                    traceback.print_exc()

                self.fsd_assist_enabled = False
                self.ap_ckb('fsd_stop')
                self.update_overlay()

                # if fsd_assist returned false then we are not finished, meaning we have an in system target
                # defined.  So lets enable Supercruise assist to get us there
                # Note: this is tricky, in normal FSD jumps the target is pretty much on the other side of Sun
                #  when we arrive, but not so when we are in the final system
                if fin == FSDAssistReturn.Partial:
                    self.ap_ckb("sc_start")

                # drop all out debug windows
                #cv2.destroyAllWindows()
                #cv2.waitKey(10)

            elif self.sc_assist_enabled == True:
                logger.debug("Running sc_assist")
                set_focus_elite_window()
                self.update_overlay()
                try:
                    self.update_ap_status("SC to Target")
                    self.sc_assist(self.scrReg)
                except EDAP_Interrupt:
                    logger.debug("Caught stop exception")
                except Exception as e:
                    print("Trapped generic:"+str(e))
                    logger.debug("SC Assist trapped generic:"+str(e))
                    traceback.print_exc()

                logger.debug("Completed sc_assist")
                self.sc_assist_enabled = False
                self.ap_ckb('sc_stop')
                self.update_overlay()

            elif self.waypoint_assist_enabled == True:
                logger.debug("Running waypoint_assist")

                set_focus_elite_window()
                self.update_overlay()
                self.jump_cnt = 0
                self.refuel_cnt = 0
                self.total_dist_jumped = 0
                self.total_jumps = 0
                try:
                    self.waypoint_assist(self.keys, self.scrReg)
                except EDAP_Interrupt:
                    logger.debug("Caught stop exception")
                except Exception as e:
                    print("Trapped generic:"+str(e))
                    logger.debug("Waypoint Assist trapped generic:"+str(e))
                    traceback.print_exc()

                self.waypoint_assist_enabled = False
                self.ap_ckb('waypoint_stop')
                self.update_overlay()

            elif self.robigo_assist_enabled == True:
                logger.debug("Running robigo_assist")
                set_focus_elite_window()
                self.update_overlay()
                try:
                    self.robigo_assist()
                except EDAP_Interrupt:
                    logger.debug("Caught stop exception")
                except Exception as e:
                    print("Trapped generic:"+str(e))
                    logger.debug("Robigo Assist trapped generic:"+str(e))
                    traceback.print_exc()

                self.robigo_assist_enabled = False
                self.ap_ckb('robigo_stop')
                self.update_overlay()

            elif self.afk_combat_assist_enabled == True:
                self.update_overlay()
                try:
                    self.afk_combat_loop()
                except EDAP_Interrupt:
                    logger.debug("Stopping afk_combat")
                except Exception as e:
                    print("Trapped generic:" + str(e))
                    logger.debug("AFK Combat Assist trapped generic:" + str(e))
                    traceback.print_exc()

                self.afk_combat_assist_enabled = False
                self.ap_ckb('afk_stop')
                self.update_overlay()

            elif self.dss_assist_enabled == True:
                logger.debug("Running dss_assist")
                set_focus_elite_window()
                self.update_overlay()
                try:
                    self.dss_assist()
                except EDAP_Interrupt:
                    logger.debug("Stopping DSS Assist")
                except Exception as e:
                    print("Trapped generic:" + str(e))
                    logger.debug("DSS Assist trapped generic:" + str(e))
                    traceback.print_exc()

                self.dss_assist_enabled = False
                self.ap_ckb('dss_stop')
                self.update_overlay()

            elif self.single_waypoint_enabled:
                self.update_overlay()
                try:
                    self.single_waypoint_assist()
                except EDAP_Interrupt:
                    logger.debug("Stopping Single Waypoint Assist")
                except Exception as e:
                    print("Trapped generic:" + str(e))
                    logger.debug("Single Waypoint Assist trapped generic:" + str(e))
                    traceback.print_exc()

                self.single_waypoint_enabled = False
                self.ap_ckb('single_waypoint_stop')
                self.update_overlay()

            # Check once EDAPGUI loaded to prevent errors logging to the listbox before loaded
            if self.gui_loaded:
                # Check if ship has changed
                ship = self.jn.ship_state()['type']
                # Check if a ship and not a suit (on foot)
                if ship not in ship_size_map:
                    # Clear current ship
                    self.current_ship_type = ''
                else:
                    ship_fullname = get_ship_fullname(ship)

                    # Check if ship changed or just loaded
                    if ship != self.current_ship_type:
                        if self.current_ship_type is not None:
                            cur_ship_fullname = get_ship_fullname(self.current_ship_type)
                            self.ap_ckb('log+vce', f"Switched ship from your {cur_ship_fullname} to your {ship_fullname}.")
                        else:
                            self.ap_ckb('log+vce', f"Welcome aboard your {ship_fullname}.")

                        # Check for fuel scoop and advanced docking computer
                        if not self.jn.ship_state()['has_fuel_scoop']:
                            self.ap_ckb('log+vce', f"Warning, your {ship_fullname} is not fitted with a Fuel Scoop.")
                        if not self.jn.ship_state()['has_adv_dock_comp']:
                            self.ap_ckb('log+vce', f"Warning, your {ship_fullname} is not fitted with an Advanced Docking Computer.")
                        if self.jn.ship_state()['has_std_dock_comp']:
                            self.ap_ckb('log+vce', f"Warning, your {ship_fullname} is fitted with a Standard Docking Computer.")

                        # Store ship for change detection BEFORE loading config and GUI update
                        self.current_ship_type = ship

                        # Load ship configuration with proper hierarchy
                        self.load_ship_configuration(ship)

                        # Update GUI with ship config
                        self.ap_ckb('update_ship_cfg')

                        # Reload templates
                        self.templ.reload_templates(self.scr.scaleX, self.scr.scaleY, self.compass_scale, self.target_scale)

            self.update_overlay()
            cv2.waitKey(10)
            sleep(1)

    def ship_tst_pitch(self, angle: float):
        """ Performs a ship pitch test by pitching 360 degrees.
        If the ship does not rotate enough, decrease the pitch value.
        If the ship rotates too much, increase the pitch value.
        """
        # if not self.status.get_flag(FlagsSupercruise):
        #     self.ap_ckb('log', "Enter Supercruise and try again.")
        #     return
        #
        # if self.jn.ship_state()['target'] is None:
        #     self.ap_ckb('log', "Select a target system and try again.")
        #     return

        set_focus_elite_window()
        sleep(0.25)
        # self.set_speed_50()
        self.pitch_up_down(angle)

    def ship_tst_pitch_new(self, angle: float):
        """ Performs a ship pitch test by pitching 360 degrees.
        If the ship does not rotate enough, decrease the pitch value.
        If the ship rotates too much, increase the pitch value.
        """
        self.ap_ckb('log', "Starting Pitch Calibration.")
        if not self.speed_demand == 'SCSpeed50':
            self.set_speed_50()
            # sleep(10)

        ship_type = self.ship_configs['Ship_Configs'][self.current_ship_type]
        if self.speed_demand not in ship_type:
            ship_type[self.speed_demand] = dict()

        # Clear existing data
        ship_type[self.speed_demand]['PitchRate'] = dict()

        test_time = 0.05
        delta_int = 0.0
        for targ_ang in [5, 10, 20, 40, 80, 160]:
            while 1:
                set_focus_elite_window()
                off = self.get_target_offset(self.scrReg)
                if not off:
                    print(f"Target lost")
                    break

                # Clear the overlays before moving
                if self.debug_overlay:
                    self.overlay.overlay_remove_rect('target')
                    self.overlay.overlay_remove_floating_text('target')
                    self.overlay.overlay_remove_floating_text('target_occ')
                    self.overlay.overlay_remove_floating_text('target_rpy')
                    self.overlay.overlay_paint()

                if off['pit'] > 0:
                    self.keys.send('PitchUpButton', hold=test_time)
                else:
                    self.keys.send('PitchDownButton', hold=test_time)

                sleep(1)

                off2 = self.get_target_offset(self.scrReg)
                if not off2:
                    print(f"Target lost")
                    break

                delta = abs(off2['pit'] - off['pit'])
                delta_int_lst = delta_int
                delta_int = int(round(delta * 10, 0))

                test_time = test_time * 1.04
                rate = round(delta / test_time, 2)
                rate = min(rate, self.pitchrate)  # Limit rate to no higher than the default
                if delta_int >= targ_ang and delta_int > delta_int_lst:
                    ship_type[self.speed_demand]['PitchRate'][delta_int] = rate

                    print(f"Pitch Angle: {round(delta, 2)}: Time: {round(test_time, 2)} Rate: {rate}")
                    self.ap_ckb('log', f"Pitch Angle: {round(delta, 2)}: Time: {round(test_time, 2)} Rate: {rate}")
                    break
                else:
                    print(f"Ignored Pitch Angle: {round(delta, 2)}: Time: {round(test_time, 2)} Rate: {rate}")

        # If we have logged values, add the ship default rate at 30 deg
        if len(ship_type[self.speed_demand]['PitchRate']) > 0:
            ship_type[self.speed_demand]['PitchRate'][300] = self.pitchrate
            self.ap_ckb('log', f"Default: Pitch Angle: 30: Rate: {self.pitchrate}")

        self.ap_ckb('log', "Completed Pitch Calibration.")
        self.ap_ckb('log', "Remember to Save if you wish to keep these values!")

    def ship_tst_pitch_calc_power(self, angle: float):
        """ Performs a ship pitch test by pitching 360 degrees.
        If the ship does not rotate enough, decrease the pitch value.
        If the ship rotates too much, increase the pitch value.
        """
        # if not self.status.get_flag(FlagsSupercruise):
        #     self.ap_ckb('log', "Enter Supercruise and try again.")
        #     return
        #
        # if self.jn.ship_state()['target'] is None:
        #     self.ap_ckb('log', "Select a target system and try again.")
        #     return

        set_focus_elite_window()
        # sleep(0.25)
        # # self.set_speed_50()
        # self.pitch_up_down(angle)

        target_align_outer_lim = 1.0
        target_align_inner_lim = 0.5

        off = None
        tar_off1 = None
        tar_off2 = None

        # Try to get the target 5 times before quiting
        for i in range(5):
            # Check Target and Compass
            tar_off1 = self.get_target_offset(self.scrReg)
            if tar_off1:
                # Target detected
                off = tar_off1

            # Quit loop if we found Target or Compass
            if off:
                break

        # We have Target or Compass. Are we close to Target?
        while ((abs(off['yaw']) > target_align_outer_lim) or
               (abs(off['pit']) > target_align_outer_lim)):

            target_align_outer_lim = target_align_inner_lim  # Keep aligning until we are within this lower range.

            # Clear the overlays before moving
            if self.debug_overlay:
                self.overlay.overlay_remove_rect('target')
                self.overlay.overlay_remove_floating_text('target')
                self.overlay.overlay_remove_floating_text('target_occ')
                self.overlay.overlay_remove_floating_text('target_rpy')
                self.overlay.overlay_paint()

            # Calc pitch time based on nav point location
            logger.debug(f"sc_target_align before: pit: {off['pit']} yaw: {off['yaw']} ")

            p_deg = 0.0
            if abs(off['pit']) > target_align_outer_lim:
                p_deg = off['pit']
                self.pitch_up_down(p_deg)

            # Calc yaw time based on nav point location
            y_deg = 0.0
            if abs(off['yaw']) > target_align_outer_lim:
                y_deg = off['yaw']
                self.yaw_right_left(y_deg)

            # Wait for ship to finish moving and picture to stabilize
            sleep(2.0)

            # Check Target and Compass
            tar_off2 = self.get_target_offset(self.scrReg)
            if tar_off2:
                off = tar_off2
                logger.debug(f"sc_target_align after: pit:{off['pit']} yaw: {off['yaw']}")

            if tar_off1 and tar_off2:
                # Check diff from before and after movement
                pit_delta = tar_off2['pit'] - tar_off1['pit']
                yaw_delta = tar_off2['yaw'] - tar_off1['yaw']
                if ((tar_off1['pit'] < 0.0 and tar_off2['pit'] > target_align_outer_lim) or
                        (tar_off1['pit'] > 0.0 and tar_off2['pit'] < -target_align_outer_lim)):
                    self.ap_ckb('log', f"TEST - Pitch correction gone too far {round(abs(pit_delta),2)} > {round(abs(tar_off1['pit']),2) + target_align_outer_lim}. Reducing Pitch Factor.")
                    # Correct factor
                    # self.pitchfactor = self.pitchfactor - 1.0
                    # Update GUI with ship config
                    self.ap_ckb('update_ship_cfg')

                if ((tar_off1['yaw'] < 0.0 and tar_off2['yaw'] > target_align_outer_lim) or
                        (tar_off1['yaw'] > 0.0 and tar_off2['yaw'] < -target_align_outer_lim)):
                    self.ap_ckb('log', f"TEST - Yaw correction gone too far {round(abs(yaw_delta),2)} > {round(abs(tar_off1['yaw']),2) + target_align_outer_lim}. Reducing Yaw Factor.")
                    # Correct factor
                    # self.yawfactor = self.yawfactor + 0.1
                    # Update GUI with ship config
                    self.ap_ckb('update_ship_cfg')

            if tar_off2:
                # Store current offsets
                tar_off1 = tar_off2.copy()

    def ship_tst_roll(self, angle: float):
        """ Performs a ship roll test by pitching 360 degrees.
        If the ship does not rotate enough, decrease the roll value.
        If the ship rotates too much, increase the roll value.
        """
        # if not self.status.get_flag(FlagsSupercruise):
        #     self.ap_ckb('log', "Enter Supercruise and try again.")
        #     return
        #
        # if self.jn.ship_state()['target'] is None:
        #     self.ap_ckb('log', "Select a target system and try again.")
        #     return

        set_focus_elite_window()
        sleep(0.25)
        # self.set_speed_50()
        self.roll_clockwise_anticlockwise(angle)

    def ship_tst_roll_new(self, angle: float):
        """ Performs a ship roll test by pitching 360 degrees.
        If the ship does not rotate enough, decrease the roll value.
        If the ship rotates too much, increase the roll value.
        """
        self.ap_ckb('log', "Starting Roll Calibration.")
        if not self.speed_demand == 'SCSpeed50':
            self.set_speed_50()
            #sleep(10)

        ship_type = self.ship_configs['Ship_Configs'][self.current_ship_type]
        if self.speed_demand not in ship_type:
            ship_type[self.speed_demand] = dict()

        # Clear existing data
        ship_type[self.speed_demand]['RollRate'] = dict()

        test_time = 0.05
        delta_int = 0.0
        for targ_ang in [40, 80, 160, 320]:
            while 1:
                set_focus_elite_window()
                off = self.get_nav_offset(self.scrReg)
                if not off:
                    break

                # Clear the overlays before moving
                if self.debug_overlay:
                    self.overlay.overlay_remove_rect('compass')
                    self.overlay.overlay_remove_floating_text('compass')
                    self.overlay.overlay_remove_floating_text('nav')
                    self.overlay.overlay_remove_floating_text('nav_beh')
                    self.overlay.overlay_remove_floating_text('compass_rpy')
                    self.overlay.overlay_paint()

                if off['roll'] > 0:
                    self.keys.send('RollRightButton', hold=test_time)
                else:
                    self.keys.send('RollLeftButton', hold=test_time)

                sleep(1)

                off2 = self.get_nav_offset(self.scrReg)
                if not off2:
                    break

                delta = abs(off2['roll'] - off['roll'])
                delta_int_lst = delta_int
                delta_int = int(round(delta * 10, 0))

                test_time = test_time * 1.03
                rate = round(delta / test_time, 2)
                rate = min(rate, self.rollrate)  # Limit rate to no higher than the default
                if delta_int >= targ_ang and delta_int > delta_int_lst:
                    ship_type[self.speed_demand]['RollRate'][delta_int] = rate

                    print(f"Roll Angle: {round(delta, 2)}: Time: {round(test_time, 2)} Rate: {rate}")
                    self.ap_ckb('log', f"Roll Angle: {round(delta, 2)}: Time: {round(test_time, 2)} Rate: {rate}")
                    break
                else:
                    print(f"Ignored Roll Angle: {round(delta, 2)}: Time: {round(test_time, 2)} Rate: {rate}")

        # If we have logged values, add the ship default rate at 45 deg
        if len(ship_type[self.speed_demand]['RollRate']) > 0:
            ship_type[self.speed_demand]['RollRate'][450] = self.rollrate
            self.ap_ckb('log', f"Default: Roll Angle: 45: Rate: {self.rollrate}")

        self.ap_ckb('log', "Completed Roll Calibration.")
        self.ap_ckb('log', "Remember to Save if you wish to keep these values!")

    def ship_tst_yaw(self, angle: float):
        """ Performs a ship yaw test by pitching 360 degrees.
        If the ship does not rotate enough, decrease the yaw value.
        If the ship rotates too much, increase the yaw value.
        """
        # if not self.status.get_flag(FlagsSupercruise):
        #     self.ap_ckb('log', "Enter Supercruise and try again.")
        #     return
        #
        # if self.jn.ship_state()['target'] is None:
        #     self.ap_ckb('log', "Select a target system and try again.")
        #     return

        set_focus_elite_window()
        sleep(0.25)
        # self.set_speed_50()
        self.yaw_right_left(angle)

    def ship_tst_yaw_new(self, angle: float):
        """ Performs a ship yaw test by pitching 360 degrees.
        If the ship does not rotate enough, decrease the yaw value.
        If the ship rotates too much, increase the yaw value.
        """
        self.ap_ckb('log', "Starting Yaw Calibration.")
        # self.compass_align(self.scrReg)
        # self.sc_target_align(self.scrReg)

        if not self.speed_demand == 'SCSpeed50':
            self.set_speed_50()
            # sleep(10)

        ship_type = self.ship_configs['Ship_Configs'][self.current_ship_type]
        if self.speed_demand not in ship_type:
            ship_type[self.speed_demand] = dict()

        # Clear existing data
        ship_type[self.speed_demand]['YawRate'] = dict()

        test_time = 0.07
        delta_int = 0.0
        for targ_ang in [5, 10, 20, 40, 80, 160]:
            while 1:
                set_focus_elite_window()
                off = self.get_target_offset(self.scrReg)
                if not off:
                    break

                # Clear the overlays before moving
                if self.debug_overlay:
                    self.overlay.overlay_remove_rect('target')
                    self.overlay.overlay_remove_floating_text('target')
                    self.overlay.overlay_remove_floating_text('target_occ')
                    self.overlay.overlay_remove_floating_text('target_rpy')
                    self.overlay.overlay_paint()

                if off['yaw'] > 0:
                    self.keys.send('YawRightButton', hold=test_time)
                else:
                    self.keys.send('YawLeftButton', hold=test_time)

                sleep(1)

                off2 = self.get_target_offset(self.scrReg)
                if not off2:
                    break

                delta = abs(off2['yaw'] - off['yaw'])
                delta_int_lst = delta_int
                delta_int = int(round(delta * 10, 0))

                test_time = test_time * 1.05
                rate = round(delta / test_time, 2)
                rate = min(rate, self.yawrate)  # Limit rate to no higher than the default
                if delta_int >= targ_ang and delta_int > delta_int_lst:
                    ship_type[self.speed_demand]['YawRate'][delta_int] = rate

                    print(f"Yaw Angle: {round(delta, 2)}: Time: {round(test_time, 2)} Rate: {rate}")
                    self.ap_ckb('log', f"Yaw Angle: {round(delta, 2)}: Time: {round(test_time, 2)} Rate: {rate}")
                    break
                else:
                    print(f"Ignored Yaw Angle: {round(delta, 2)}: Time: {round(test_time, 2)} Rate: {rate}")

        # If we have logged values, add the ship default rate at 30 deg
        if len(ship_type[self.speed_demand]['YawRate']) > 0:
            ship_type[self.speed_demand]['YawRate'][300] = self.yawrate
            self.ap_ckb('log', f"Default: Yaw Angle: 30: Rate: {self.yawrate}")

        self.ap_ckb('log', "Completed Yaw Calibration.")
        self.ap_ckb('log', "Remember to Save if you wish to keep these values!")

    def set_speed_0(self, repeat=1):
        if self.status.get_flag(FlagsSupercruise):
            self.speed_demand = 'SCSpeed0'
        else:
            self.speed_demand = 'Speed0'

        self.keys.send('SetSpeedZero', repeat)

    def set_speed_50(self, repeat=1):
        if self.status.get_flag(FlagsSupercruise):
            self.speed_demand = 'SCSpeed50'
        else:
            self.speed_demand = 'Speed50'

        self.keys.send('SetSpeed50', repeat)

    def set_speed_100(self, repeat=1):
        if self.status.get_flag(FlagsSupercruise):
            self.speed_demand = 'SCSpeed100'
        else:
            self.speed_demand = 'Speed100'

        self.keys.send('SetSpeed100', repeat)

def delete_old_log_files():
    """ Deleted old .log files from the main folder."""
    folder = '.'
    n = 5  # days

    current_time = time.time()
    day = 86400  # seconds in a day

    for filename in os.listdir(folder):
        file_path = os.path.join(folder, filename)
        if os.path.isfile(file_path):
            if filename.endswith('.log'):
                file_time = os.path.getmtime(file_path)
                if file_time < current_time - day * n:
                    print(f"Deleting file: '{file_path}'")
                    os.remove(file_path)


def strfdelta(tdelta, fmt='{H:02}h {M:02}m {S:02.0f}s', inputtype='timedelta'):
    """Convert a datetime.timedelta object or a regular number to a custom
    formatted string, just like the stftime() method does for datetime.datetime
    objects.

    The fmt argument allows custom formatting to be specified.  Fields can
    include seconds, minutes, hours, days, and weeks.  Each field is optional.

    Some examples:
        '{D:02}d {H:02}h {M:02}m {S:02.0f}s' --> '05d 08h 04m 02s' (default)
        '{W}w {D}d {H}:{M:02}:{S:02.0f}'     --> '4w 5d 8:04:02'
        '{D:2}d {H:2}:{M:02}:{S:02.0f}'      --> ' 5d  8:04:02'
        '{H}h {S:.0f}s'                       --> '72h 800s'

    The inputtype argument allows tdelta to be a regular number instead of the
    default, which is a datetime.timedelta object.  Valid inputtype strings:
        's', 'seconds',
        'm', 'minutes',
        'h', 'hours',
        'd', 'days',
        'w', 'weeks'
    """

    # Convert tdelta to integer seconds.
    if inputtype == 'timedelta':
        remainder = tdelta.total_seconds()
    elif inputtype in ['s', 'seconds']:
        remainder = float(tdelta)
    elif inputtype in ['m', 'minutes']:
        remainder = float(tdelta)*60
    elif inputtype in ['h', 'hours']:
        remainder = float(tdelta)*3600
    elif inputtype in ['d', 'days']:
        remainder = float(tdelta)*86400
    elif inputtype in ['w', 'weeks']:
        remainder = float(tdelta)*604800
    else:
        remainder = 0.0

    f = Formatter()
    desired_fields = [field_tuple[1] for field_tuple in f.parse(fmt)]
    possible_fields = ('Y','m','W', 'D', 'H', 'M', 'S', 'mS', 'µS')
    constants = {'Y':86400*365.24,'m': 86400*30.44 ,'W': 604800, 'D': 86400, 'H': 3600, 'M': 60, 'S': 1, 'mS': 1/pow(10,3) , 'µS':1/pow(10,6)}
    values = {}
    for field in possible_fields:
        if field in desired_fields and field in constants:
            quotient, remainder = divmod(remainder, constants[field])
            values[field] = int(quotient) if field != 'S' else quotient + remainder
    return f.format(fmt, **values)


def get_timestamped_filename(prefix: str, suffix: str, extension: str):
    """ Get timestamped filename with milliseconds.
    @return: String in the format of 'prefix yyyy-mm-dd hh-mm-ss.xxx suffix.extension'
    """
    now = datetime.now()
    x = now.strftime("%Y-%m-%d %H-%M-%S.%f")[:-3]  # Date time with mS.
    if prefix != '':
        x = prefix + ' ' + x
    if suffix != '':
        x = x + ' ' + suffix
    x = x + "." + extension
    return x


def dummy_cb(msg, body=None):
    pass


#
# This main is for testing purposes.
#
def main():
    #handle = win32gui.FindWindow(0, "Elite - Dangerous (CLIENT)")
    #if handle != None:
    #    win32gui.SetForegroundWindow(handle)  # put the window in foreground

    delete_old_log_files()

    ed_ap = EDAutopilot(cb=dummy_cb, doThread=False)

    # for x in range(10):
    #     ed_ap.keys.send('RollLeftButton', 0.04)
    # sleep(1)

    set_focus_elite_window()
    ed_ap.set_speed_50()
    sleep(0.25)

    tar_off = ed_ap.get_target_offset(ed_ap.scrReg)
    if tar_off:
        off = tar_off
        logger.debug(f"sc_target_align before: pit:{off['pit']} yaw: {off['yaw']} ")

    # ed_ap.rotateLeft(1)
    x = 10
    ed_ap.pitchrate = 16.0
    ed_ap.pitch_up_down(-x)

    sleep(.5)

    tar_off = ed_ap.get_target_offset(ed_ap.scrReg)
    if tar_off:
        off = tar_off
        logger.debug(f"sc_target_align after: pit:{off['pit']} yaw: {off['yaw']} ")

    sleep(.5)

    ed_ap.pitch_up_down(x)

    # ed_ap.yawLeft(1)

    # for x in range(10):
    #     ed_ap.keys.send('PitchUpButton', 0.04)
    # sleep(1)
    # for x in range(10):
    #     ed_ap.keys.send('YawLeftButton', 0.04)

        #target_align(scrReg)
        # print("Calling nav_align")
        #ed_ap.nav_align(ed_ap.scrReg)
        #ed_ap.fss_detect_elw(ed_ap.scrReg)

        #loc = get_destination_offset(scrReg)
        #print("get_dest: " +str(loc))
        #loc = get_nav_offset(scrReg)
        #print("get_nav: " +str(loc))
        # cv2.waitKey(0)
        # print("Done nav")
        # sleep(8)

    # ed_ap.overlay.overlay_quit()




if __name__ == "__main__":
    main()
