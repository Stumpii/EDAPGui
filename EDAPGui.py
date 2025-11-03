# import queue
# import sys
# import os
# import threading
# import kthread
# from datetime import datetime
# from time import sleep
# import cv2
# import json
# from pathlib import Path
import subprocess

import keyboard
import webbrowser
# import requests


# from PIL import Image, ImageGrab, ImageTk
import tkinter as tk
from tkinter import filedialog as fd
# from tkinter import messagebox
from tkinter import ttk
import sv_ttk
import pywinstyles
import sys  # Do not delete - prevents a 'super' error from tktoolip.
from tktooltip import ToolTip  # In requirements.txt as 'tkinter-tooltip'.

# from OCR import RegionCalibration
# from Voice import *
# from MousePt import MousePoint

# from Image_Templates import *
# from Screen import *
# from Screen_Regions import *
# from EDKeys import *
# from EDJournal import *
from ED_AP import *
from EDAPWaypointEditor import WaypointEditorTab

from EDlogger import logger


"""
File:EDAPGui.py

Description:
User interface for controlling the ED Autopilot

Note:
Ideas taken from:  https://github.com/skai2/EDAutopilot

 HotKeys:
    Home - Start FSD Assist
    INS  - Start SC Assist
    PG UP - Start Robigo Assist
    End - Terminate any ongoing assist (FSD, SC, AFK)

Author: sumzer0@yahoo.com
"""


# ---------------------------------------------------------------------------
# must be updated with a new release so that the update check works properly!
# contains the names of the release.
EDAP_VERSION = "V1.8.0 beta 13"
# depending on how release versions are best marked you could also change it to the release tag, see function check_update.
# ---------------------------------------------------------------------------

FORM_TYPE_CHECKBOX = 0
FORM_TYPE_SPINBOX = 1
FORM_TYPE_ENTRY = 2


def str_to_float(input_str: str) -> float:
    try:
        return float(input_str)
    except ValueError:
        return 0.0  # Assign a default value on error


class APGui:

    def __init__(self, root):
        self.statusbar = None
        self.root = root
        root.title("EDAutopilot " + EDAP_VERSION)
        # root.overrideredirect(True)
        # root.geometry("400x550")
        # root.configure(bg="blue")
        root.protocol("WM_DELETE_WINDOW", self.close_window)
        root.resizable(False, False)

        self.tooltips = {
            'FSD Route Assist': "Will execute your route. \nAt each jump the sequence will perform some fuel scooping.",
            'Supercruise Assist': "Will keep your ship pointed to target, \nyou target can only be a station for the autodocking to work.",
            'Waypoint Assist': "When selected, will prompt for the waypoint file. \nThe waypoint file contains System names that \nwill be entered into Galaxy Map and route plotted.",
            'Robigo Assist': "",
            'DSS Assist': "When selected, will perform DSS scans while you are traveling between stars.",
            'Single Waypoint Assist': "",
            'ELW Scanner': "Will perform FSS scans while FSD Assist is traveling between stars. \nIf the FSS shows a signal in the region of Earth, \nWater or Ammonia type worlds, it will announce that discovery.",
            'AFK Combat Assist': "Used with a AFK Combat ship in a Rez Zone.",
            'RollRate': "Roll rate your ship has in deg/sec. Higher the number the more maneuverable the ship.",
            'PitchRate': "Pitch (up/down) rate your ship has in deg/sec. Higher the number the more maneuverable the ship.",
            'YawRate': "Yaw rate (rudder) your ship has in deg/sec. Higher the number the more maneuverable the ship.",
            'RollFactor': "TBD",
            'PitchFactor': "TBD",
            'YawFactor': "TBD",
            'SunPitchUp+Time': "This field are for ship that tend to overheat. \nProviding 1-2 more seconds of Pitch up when avoiding the Sun \nwill overcome this problem.",
            'Sun Bright Threshold': "The low level for brightness detection, \nrange 0-255, want to mask out darker items",
            'Nav Align Tries': "How many attempts the ap should make at alignment.",
            'Jump Tries': "How many attempts the ap should make to jump.",
            'Docking Retries': "How many attempts to make to dock.",
            'Wait For Autodock': "After docking granted, \nwait this amount of time for us to get docked with autodocking",
            'Start FSD': "Button to start FSD route assist.",
            'Start SC': "Button to start Supercruise assist.",
            'Start Robigo': "Button to start Robigo assist.",
            'Stop All': "Button to stop all assists.",
            'Refuel Threshold': "If fuel level get below this level, \nit will attempt refuel.",
            'Scoop Timeout': "Number of second to wait for full tank, \nmight mean we are not scooping well or got a small scooper",
            'Fuel Threshold Abort': "Level at which AP will terminate, \nbecause we are not scooping well.",
            'X Offset': "Offset left the screen to start place overlay text.",
            'Y Offset': "Offset down the screen to start place overlay text.",
            'Font Size': "Font size of the overlay.",
            'Calibrate': "Will iterate through a set of scaling values \ngetting the best match for your system. \nSee HOWTO-Calibrate.md",
            'Waypoint List Button': "Read in a file with with your Waypoints.",
            'Cap Mouse XY': "This will provide the StationCoord value of the Station in the SystemMap. \nSelecting this button and then clicking on the Station in the SystemMap \nwill return the x,y value that can be pasted in the waypoints file",
            'Reset Waypoint List': "Reset your waypoint list, \nthe waypoint assist will start again at the first point in the list.",
            'Debug Overlay': "Enables debug data to be displayed over the \nElite Dangerous screen while playing the game.",
            'Debug OCR': "Enables OCR debug output to be stored in the 'ocr_output' folder.",
            'Debug Images': "Enables debug images to be stored in the 'debug_output' folder.",
            'Modifier Key Delay': "Delay for key modifiers to ensure modifier is detected before/after the key.",
            'Default Hold Time': "Default hold time for a key press.",
            'Repeat Key Delay': "Delay between key press repeats.",
        }

        self.gui_loaded = False
        self.log_buffer = queue.Queue()
        self.callback('log', f'Starting ED Autopilot {EDAP_VERSION}.')

        self.load_ocr_calibration_data()
        self.ed_ap = EDAutopilot(cb=self.callback)
        self.ed_ap.robigo.set_single_loop(self.ed_ap.config['Robigo_Single_Loop'])
        # self.calibrator = RegionCalibration(root, self.ed_ap, cb=self.callback)

        self.ocr_calibration_data = {}

        self.mouse = MousePoint()

        self.checkboxvar = {}
        self.radiobuttonvar = {}
        self.entries = {}
        self.lab_ck = {}
        self.single_waypoint_system = tk.StringVar()
        self.single_waypoint_station = tk.StringVar()
        self._global_shopping_list_tab = None
        self.waypoint_editor_tab = None

        self.FSD_A_running = False
        self.SC_A_running = False
        self.WP_A_running = False
        self.RO_A_running = False
        self.DSS_A_running = False
        self.SWP_A_running = False

        self.cv_view = False

        self.msgList = self.gui_gen(root)

        self.checkboxvar['Enable Randomness'].set(self.ed_ap.config['EnableRandomness'])
        self.checkboxvar['Activate Elite for each key'].set(self.ed_ap.config['ActivateEliteEachKey'])
        self.checkboxvar['Automatic logout'].set(self.ed_ap.config['AutomaticLogout'])
        self.checkboxvar['Enable Overlay'].set(self.ed_ap.config['OverlayTextEnable'])
        self.checkboxvar['Enable Voice'].set(self.ed_ap.config['VoiceEnable'])
        self.checkboxvar['Enable Hotkeys'].set(self.ed_ap.config['HotkeysEnable'])
        self.checkboxvar['Debug Overlay'].set(self.ed_ap.config['DebugOverlay'])
        self.checkboxvar['Debug OCR'].set(self.ed_ap.config['DebugOCR'])
        self.checkboxvar['Debug Images'].set(self.ed_ap.config['DebugImages'])
        self.checkboxvar['AFKCombat AttackAtWill'].set(self.ed_ap.config['AFKCombat_AttackAtWill'])

        self.radiobuttonvar['dss_button'].set(self.ed_ap.config['DSSButton'])

        self.entries['ship']['PitchRate'].delete(0, tk.END)
        self.entries['ship']['RollRate'].delete(0, tk.END)
        self.entries['ship']['YawRate'].delete(0, tk.END)
        self.entries['ship']['SunPitchUp+Time'].delete(0, tk.END)
        self.entries['ship']['PitchFactor'].delete(0, tk.END)
        self.entries['ship']['RollFactor'].delete(0, tk.END)
        self.entries['ship']['YawFactor'].delete(0, tk.END)
        
        self.entries['autopilot']['Sun Bright Threshold'].delete(0, tk.END)
        self.entries['autopilot']['Nav Align Tries'].delete(0, tk.END)
        self.entries['autopilot']['Jump Tries'].delete(0, tk.END)
        self.entries['autopilot']['Docking Retries'].delete(0, tk.END)
        self.entries['autopilot']['Wait For Autodock'].delete(0, tk.END)

        self.entries['refuel']['Refuel Threshold'].delete(0, tk.END)
        self.entries['refuel']['Scoop Timeout'].delete(0, tk.END)
        self.entries['refuel']['Fuel Threshold Abort'].delete(0, tk.END)

        self.entries['overlay']['X Offset'].delete(0, tk.END)
        self.entries['overlay']['Y Offset'].delete(0, tk.END)
        self.entries['overlay']['Font Size'].delete(0, tk.END)

        self.entries['buttons']['Start FSD'].delete(0, tk.END)
        self.entries['buttons']['Start SC'].delete(0, tk.END)
        self.entries['buttons']['Start Robigo'].delete(0, tk.END)
        self.entries['buttons']['Stop All'].delete(0, tk.END)

        self.entries['keys']['Modifier Key Delay'].delete(0, tk.END)
        self.entries['keys']['Default Hold Time'].delete(0, tk.END)
        self.entries['keys']['Repeat Key Delay'].delete(0, tk.END)

        self.entries['ship']['PitchRate'].insert(0, float(self.ed_ap.pitchrate))
        self.entries['ship']['RollRate'].insert(0, float(self.ed_ap.rollrate))
        self.entries['ship']['YawRate'].insert(0, float(self.ed_ap.yawrate))
        self.entries['ship']['SunPitchUp+Time'].insert(0, float(self.ed_ap.sunpitchuptime))
        self.entries['ship']['PitchFactor'].insert(0, float(self.ed_ap.pitchfactor))
        self.entries['ship']['RollFactor'].insert(0, float(self.ed_ap.rollfactor))
        self.entries['ship']['YawFactor'].insert(0, float(self.ed_ap.yawfactor))
        
        self.entries['autopilot']['Sun Bright Threshold'].insert(0, int(self.ed_ap.config['SunBrightThreshold']))
        self.entries['autopilot']['Nav Align Tries'].insert(0, int(self.ed_ap.config['NavAlignTries']))
        self.entries['autopilot']['Jump Tries'].insert(0, int(self.ed_ap.config['JumpTries']))
        self.entries['autopilot']['Docking Retries'].insert(0, int(self.ed_ap.config['DockingRetries']))
        self.entries['autopilot']['Wait For Autodock'].insert(0, int(self.ed_ap.config['WaitForAutoDockTimer']))
        self.entries['refuel']['Refuel Threshold'].insert(0, int(self.ed_ap.config['RefuelThreshold']))
        self.entries['refuel']['Scoop Timeout'].insert(0, int(self.ed_ap.config['FuelScoopTimeOut']))
        self.entries['refuel']['Fuel Threshold Abort'].insert(0, int(self.ed_ap.config['FuelThreasholdAbortAP']))
        self.entries['overlay']['X Offset'].insert(0, int(self.ed_ap.config['OverlayTextXOffset']))
        self.entries['overlay']['Y Offset'].insert(0, int(self.ed_ap.config['OverlayTextYOffset']))
        self.entries['overlay']['Font Size'].insert(0, int(self.ed_ap.config['OverlayTextFontSize']))

        self.entries['buttons']['Start FSD'].insert(0, str(self.ed_ap.config['HotKey_StartFSD']))
        self.entries['buttons']['Start SC'].insert(0, str(self.ed_ap.config['HotKey_StartSC']))
        self.entries['buttons']['Start Robigo'].insert(0, str(self.ed_ap.config['HotKey_StartRobigo']))
        self.entries['buttons']['Stop All'].insert(0, str(self.ed_ap.config['HotKey_StopAllAssists']))

        self.entries['keys']['Modifier Key Delay'].insert(0, float(self.ed_ap.config['Key_ModDelay']))
        self.entries['keys']['Default Hold Time'].insert(0, float(self.ed_ap.config['Key_DefHoldTime']))
        self.entries['keys']['Repeat Key Delay'].insert(0, float(self.ed_ap.config['Key_RepeatDelay']))

        if self.ed_ap.config['LogDEBUG']:
            self.radiobuttonvar['debug_mode'].set("Debug")
        elif self.ed_ap.config['LogINFO']:
            self.radiobuttonvar['debug_mode'].set("Info")
        else:
            self.radiobuttonvar['debug_mode'].set("Error")

        # global trap for these keys, the 'end' key will stop any current AP action
        # the 'home' key will start the FSD Assist.  May want another to start SC Assist
        if self.ed_ap.config['HotkeysEnable']:
            keyboard.add_hotkey(self.ed_ap.config['HotKey_StopAllAssists'], self.stop_all_assists)
            keyboard.add_hotkey(self.ed_ap.config['HotKey_StartFSD'], self.callback, args=('fsd_start', None))
            keyboard.add_hotkey(self.ed_ap.config['HotKey_StartSC'],  self.callback, args=('sc_start',  None))
            keyboard.add_hotkey(self.ed_ap.config['HotKey_StartRobigo'],  self.callback, args=('robigo_start',  None))

        # check for updates
        self.check_updates()

        sleep(0.25)  # Added because the custom tkinter takes longer to load? Without, you occasionally get errors
        # that the main thread is not in main loop.
        self.ed_ap.gui_loaded = True
        self.gui_loaded = True
        # Send a log entry which will flush out the buffer.
        self.callback('log', 'ED Autopilot loaded successfully.')

    # callback from the EDAP, to configure GUI items
    def callback(self, msg, body=None):
        if msg == 'log':
            self.log_msg(body)
        elif msg == 'log+vce':
            self.log_msg(body)
            self.ed_ap.vce.say(body)
        elif msg == 'statusline':
            self.update_statusline(body)
        elif msg == 'fsd_stop':
            logger.debug("Detected 'fsd_stop' callback msg")
            self.checkboxvar['FSD Route Assist'].set(0)
            self.check_cb('FSD Route Assist')
        elif msg == 'fsd_start':
            self.checkboxvar['FSD Route Assist'].set(1)
            self.check_cb('FSD Route Assist')
        elif msg == 'sc_stop':
            logger.debug("Detected 'sc_stop' callback msg")
            self.checkboxvar['Supercruise Assist'].set(0)
            self.check_cb('Supercruise Assist')
        elif msg == 'sc_start':
            self.checkboxvar['Supercruise Assist'].set(1)
            self.check_cb('Supercruise Assist')
        elif msg == 'waypoint_stop':
            logger.debug("Detected 'waypoint_stop' callback msg")
            self.checkboxvar['Waypoint Assist'].set(0)
            self.check_cb('Waypoint Assist')
        elif msg == 'waypoint_start':
            self.checkboxvar['Waypoint Assist'].set(1)
            self.check_cb('Waypoint Assist')
        elif msg == 'robigo_stop':
            logger.debug("Detected 'robigo_stop' callback msg")
            self.checkboxvar['Robigo Assist'].set(0)
            self.check_cb('Robigo Assist')
        elif msg == 'robigo_start':
            self.checkboxvar['Robigo Assist'].set(1)
            self.check_cb('Robigo Assist')
        elif msg == 'afk_stop':
            logger.debug("Detected 'afk_stop' callback msg")
            self.checkboxvar['AFK Combat Assist'].set(0)
            self.check_cb('AFK Combat Assist')
        elif msg == 'dss_start':
            logger.debug("Detected 'dss_start' callback msg")
            self.checkboxvar['DSS Assist'].set(1)
            self.check_cb('DSS Assist')
        elif msg == 'dss_stop':
            logger.debug("Detected 'dss_stop' callback msg")
            self.checkboxvar['DSS Assist'].set(0)
            self.check_cb('DSS Assist')
        elif msg == 'single_waypoint_stop':
            logger.debug("Detected 'single_waypoint_stop' callback msg")
            self.checkboxvar['Single Waypoint Assist'].set(0)
            self.check_cb('Single Waypoint Assist')

        elif msg == 'stop_all_assists':
            logger.debug("Detected 'stop_all_assists' callback msg")

            self.checkboxvar['FSD Route Assist'].set(0)
            self.check_cb('FSD Route Assist')

            self.checkboxvar['Supercruise Assist'].set(0)
            self.check_cb('Supercruise Assist')

            self.checkboxvar['Waypoint Assist'].set(0)
            self.check_cb('Waypoint Assist')

            self.checkboxvar['Robigo Assist'].set(0)
            self.check_cb('Robigo Assist')

            self.checkboxvar['AFK Combat Assist'].set(0)
            self.check_cb('AFK Combat Assist')

            self.checkboxvar['DSS Assist'].set(0)
            self.check_cb('DSS Assist')

            self.checkboxvar['Single Waypoint Assist'].set(0)
            self.check_cb('Single Waypoint Assist')

        elif msg == 'jumpcount':
            self.update_jumpcount(body)
        elif msg == 'update_ship_cfg':
            self.update_ship_cfg()

    def update_ship_cfg(self):
        # load up the display with what we read from ED_AP for the current ship
        self.entries['ship']['PitchRate'].delete(0, tk.END)
        self.entries['ship']['RollRate'].delete(0, tk.END)
        self.entries['ship']['YawRate'].delete(0, tk.END)
        self.entries['ship']['SunPitchUp+Time'].delete(0, tk.END)
        self.entries['ship']['PitchFactor'].delete(0, tk.END)
        self.entries['ship']['RollFactor'].delete(0, tk.END)
        self.entries['ship']['YawFactor'].delete(0, tk.END)
        
        self.entries['ship']['PitchRate'].insert(0, self.ed_ap.pitchrate)
        self.entries['ship']['RollRate'].insert(0, self.ed_ap.rollrate)
        self.entries['ship']['YawRate'].insert(0, self.ed_ap.yawrate)
        self.entries['ship']['SunPitchUp+Time'].insert(0, self.ed_ap.sunpitchuptime)
        self.entries['ship']['PitchFactor'].insert(0, self.ed_ap.pitchfactor)
        self.entries['ship']['RollFactor'].insert(0, self.ed_ap.rollfactor)
        self.entries['ship']['YawFactor'].insert(0, self.ed_ap.yawfactor)
        
    def calibrate_callback(self):
        self.ed_ap.calibrate_target()

    def calibrate_compass_callback(self):
        self.ed_ap.calibrate_compass()

    def quit(self):
        logger.debug("Entered: quit")
        self.close_window()

    def close_window(self):
        logger.debug("Entered: close_window")
        self.stop_fsd()
        self.stop_sc()
        self.ed_ap.quit()
        sleep(0.1)
        self.root.destroy()

    # this routine is to stop any current autopilot activity
    def stop_all_assists(self):
        logger.debug("Entered: stop_all_assists")
        self.callback('stop_all_assists')

    def start_fsd(self):
        logger.debug("Entered: start_fsd")
        self.ed_ap.set_fsd_assist(True)
        self.FSD_A_running = True
        self.log_msg("FSD Route Assist start")
        self.ed_ap.vce.say("FSD Route Assist On")

    def stop_fsd(self):
        logger.debug("Entered: stop_fsd")
        self.ed_ap.set_fsd_assist(False)
        self.FSD_A_running = False
        self.log_msg("FSD Route Assist stop")
        self.ed_ap.vce.say("FSD Route Assist Off")
        self.update_statusline("Idle")

    def start_sc(self):
        logger.debug("Entered: start_sc")
        self.ed_ap.set_sc_assist(True)
        self.SC_A_running = True
        self.log_msg("SC Assist start")
        self.ed_ap.vce.say("Supercruise Assist On")

    def stop_sc(self):
        logger.debug("Entered: stop_sc")
        self.ed_ap.set_sc_assist(False)
        self.SC_A_running = False
        self.log_msg("SC Assist stop")
        self.ed_ap.vce.say("Supercruise Assist Off")
        self.update_statusline("Idle")

    def start_waypoint(self):
        logger.debug("Entered: start_waypoint")
        self.ed_ap.set_waypoint_assist(True)
        self.WP_A_running = True
        self.log_msg("Waypoint Assist start")
        self.ed_ap.vce.say("Waypoint Assist On")

    def stop_waypoint(self):
        logger.debug("Entered: stop_waypoint")
        self.ed_ap.set_waypoint_assist(False)
        self.WP_A_running = False
        self.log_msg("Waypoint Assist stop")
        self.ed_ap.vce.say("Waypoint Assist Off")
        self.update_statusline("Idle")

    def start_robigo(self):
        logger.debug("Entered: start_robigo")
        self.ed_ap.set_robigo_assist(True)
        self.RO_A_running = True
        self.log_msg("Robigo Assist start")
        self.ed_ap.vce.say("Robigo Assist On")

    def stop_robigo(self):
        logger.debug("Entered: stop_robigo")
        self.ed_ap.set_robigo_assist(False)
        self.RO_A_running = False
        self.log_msg("Robigo Assist stop")
        self.ed_ap.vce.say("Robigo Assist Off")
        self.update_statusline("Idle")

    def start_dss(self):
        logger.debug("Entered: start_dss")
        self.ed_ap.set_dss_assist(True)
        self.DSS_A_running = True
        self.log_msg("DSS Assist start")
        self.ed_ap.vce.say("DSS Assist On")

    def stop_dss(self):
        logger.debug("Entered: stop_dss")
        self.ed_ap.set_dss_assist(False)
        self.DSS_A_running = False
        self.log_msg("DSS Assist stop")
        self.ed_ap.vce.say("DSS Assist Off")
        self.update_statusline("Idle")

    def start_single_waypoint_assist(self):
        """ The debug command to go to a system or station or both."""
        logger.debug("Entered: start_single_waypoint_assist")
        system = self.single_waypoint_system.get()
        station = self.single_waypoint_station.get()

        if system != "" or station != "":
            self.ed_ap.set_single_waypoint_assist(system, station, True)
            self.SWP_A_running = True
            self.log_msg("Single Waypoint Assist start")
            self.ed_ap.vce.say("Single Waypoint Assist On")

    def stop_single_waypoint_assist(self):
        """ The debug command to go to a system or station or both."""
        logger.debug("Entered: stop_single_waypoint_assist")
        self.ed_ap.set_single_waypoint_assist("", "", False)
        self.SWP_A_running = False
        self.log_msg("Single Waypoint Assist stop")
        self.ed_ap.vce.say("Single Waypoint Assist Off")
        self.update_statusline("Idle")

    def about(self):
        webbrowser.open_new("https://github.com/SumZer0-git/EDAPGui")

    def check_for_updates(self, repo_path):
        try:
            # Fetch the latest changes from the remote repository
            subprocess.run(["git", "fetch"], cwd=repo_path, check=True, capture_output=True)

            # Get the current commit hash of the local repository
            local_hash = subprocess.run(["git", "rev-parse", "HEAD"], cwd=repo_path, capture_output=True, text=True,
                                        check=True).stdout.strip()

            # Get the commit hash of the remote repository
            remote_hash = subprocess.run(["git", "rev-parse", "origin/HEAD"], cwd=repo_path, capture_output=True,
                                         text=True, check=True).stdout.strip()

            # Compare the commit hashes
            if local_hash != remote_hash:
                print("The repository has been updated. Please clone it again to get the latest version.")
                return True
            else:
                print("The repository is up to date.")
                return False

        except subprocess.CalledProcessError as e:
            print(f"Error checking for updates: {e}")
            return False
        except FileNotFoundError:
            print("Git command not found. Please ensure Git is installed and in your system's PATH.")
            return False

    def check_updates(self):
        # response = requests.get("https://api.github.com/repos/SumZer0-git/EDAPGui/releases/latest")
        # if EDAP_VERSION != response.json()["name"]:
        #     mb = messagebox.askokcancel("Update Check", "A new release version is available. Download now?")
        #     if mb == True:
        #         webbrowser.open_new("https://github.com/SumZer0-git/EDAPGui/releases/latest")

        # Example usage:
        # repo_path = "/path/to/your/local/repo"
        repo_path = "./"
        updates_available = self.check_for_updates(repo_path)

        if updates_available:
            # Optionally, provide further instructions or automate the cloning process
            self.log_msg("=====================================================")
            self.log_msg("========== An update to EDAP is available ===========")
            self.log_msg("==== Click 'Check for Updates' on the Debug tab, ====")
            self.log_msg("====== or go directly to the EDAP Github page =======")
            self.log_msg("=====================================================")

            # print("You can use the following command to clone the repository again:")
            # print("git clone <repository_url> <new_directory_name>")
        else:
            self.log_msg("You have the latest version of EDAP!")

    def open_changelog(self):
        webbrowser.open_new("https://github.com/SumZer0-git/EDAPGui/blob/main/ChangeLog.md")

    def open_discord(self):
        webbrowser.open_new("https://discord.gg/HCgkfSc")

    def open_logfile(self):
        os.startfile('autopilot.log')

    def log_msg(self, msg):
        message = datetime.now().strftime("%H:%M:%S: ") + msg

        try:
            if not self.gui_loaded:
                # Store message in queue
                self.log_buffer.put(message)
                logger.info(msg)
            else:
                # Add queued messages to the list
                while not self.log_buffer.empty():
                    self.msgList.insert(tk.END, self.log_buffer.get())

                self.msgList.insert(tk.END, message)
                self.msgList.yview(tk.END)
                logger.info(msg)
        except:
            # Store message in queue
            self.log_buffer.put(message)
            logger.info(msg)

    def set_statusbar(self, txt):
        self.statusbar.configure(text=txt)

    def update_jumpcount(self, txt):
        self.jumpcount.configure(text=txt)

    def update_statusline(self, txt):
        self.status.configure(text="Status: " + txt)
        self.log_msg(f"Status update: {txt}")

    def ship_tst_pitch(self):
        self.ed_ap.ship_tst_pitch(360)

    def ship_tst_roll(self):
        self.ed_ap.ship_tst_roll(360)

    def ship_tst_yaw(self):
        self.ed_ap.ship_tst_yaw(360)

    def ship_tst_pitch_30(self):
        self.ed_ap.ship_tst_pitch(30)

    def ship_tst_roll_30(self):
        self.ed_ap.ship_tst_roll(30)

    def ship_tst_yaw_30(self):
        self.ed_ap.ship_tst_yaw(30)

    def ship_tst_pitch_45(self):
        self.ed_ap.ship_tst_pitch(45)

    def ship_tst_roll_45(self):
        self.ed_ap.ship_tst_roll(45)

    def ship_tst_yaw_45(self):
        self.ed_ap.ship_tst_yaw(45)

    def ship_tst_pitch_90(self):
        self.ed_ap.ship_tst_pitch(90)

    def ship_tst_roll_90(self):
        self.ed_ap.ship_tst_roll(90)

    def ship_tst_yaw_90(self):
        self.ed_ap.ship_tst_yaw(90)
        
    def open_wp_file(self):
        filetypes = (
            ('json files', '*.json'),
            ('All files', '*.*')
        )
        filename = fd.askopenfilename(title="Waypoint File", initialdir='./waypoints/', filetypes=filetypes)
        if filename != "":
            res = self.ed_ap.waypoint.load_waypoint_file(filename)
            if res:
                self.wp_filelabel.set("loaded: " + Path(filename).name)
            else:
                self.wp_filelabel.set("<no list loaded>")

    def reset_wp_file(self):
        if not self.WP_A_running:
            mb = messagebox.askokcancel("Waypoint List Reset", "After resetting the Waypoint List, the Waypoint Assist will start again from the first point in the list at the next start.")
            if mb:
                self.ed_ap.waypoint.mark_all_waypoints_not_complete()
        else:
            mb = messagebox.showerror("Waypoint List Error", "Waypoint Assist must be disabled before you can reset the list.")

    def save_settings(self):
        self.entry_update(None)
        self.ed_ap.update_config()
        self.ed_ap.update_ship_configs()
        self.save_ocr_calibration_data()

    # new data was added to a field, re-read them all for simple logic
    def entry_update(self, event):
        try:
            self.ed_ap.pitchrate = float(self.entries['ship']['PitchRate'].get())
            self.ed_ap.rollrate = float(self.entries['ship']['RollRate'].get())
            self.ed_ap.yawrate = float(self.entries['ship']['YawRate'].get())
            self.ed_ap.sunpitchuptime = float(self.entries['ship']['SunPitchUp+Time'].get())
            self.ed_ap.pitchfactor = float(self.entries['ship']['PitchFactor'].get())
            self.ed_ap.rollfactor = float(self.entries['ship']['RollFactor'].get())
            self.ed_ap.yawfactor = float(self.entries['ship']['YawFactor'].get())
            
            self.ed_ap.config['SunBrightThreshold'] = int(self.entries['autopilot']['Sun Bright Threshold'].get())
            self.ed_ap.config['NavAlignTries'] = int(self.entries['autopilot']['Nav Align Tries'].get())
            self.ed_ap.config['JumpTries'] = int(self.entries['autopilot']['Jump Tries'].get())
            self.ed_ap.config['DockingRetries'] = int(self.entries['autopilot']['Docking Retries'].get())
            self.ed_ap.config['WaitForAutoDockTimer'] = int(self.entries['autopilot']['Wait For Autodock'].get())
            self.ed_ap.config['RefuelThreshold'] = int(self.entries['refuel']['Refuel Threshold'].get())
            self.ed_ap.config['FuelScoopTimeOut'] = int(self.entries['refuel']['Scoop Timeout'].get())
            self.ed_ap.config['FuelThreasholdAbortAP'] = int(self.entries['refuel']['Fuel Threshold Abort'].get())
            self.ed_ap.config['OverlayTextXOffset'] = int(self.entries['overlay']['X Offset'].get())
            self.ed_ap.config['OverlayTextYOffset'] = int(self.entries['overlay']['Y Offset'].get())
            self.ed_ap.config['OverlayTextFontSize'] = int(self.entries['overlay']['Font Size'].get())
            self.ed_ap.config['HotKey_StartFSD'] = str(self.entries['buttons']['Start FSD'].get())
            self.ed_ap.config['HotKey_StartSC'] = str(self.entries['buttons']['Start SC'].get())
            self.ed_ap.config['HotKey_StartRobigo'] = str(self.entries['buttons']['Start Robigo'].get())
            self.ed_ap.config['HotKey_StopAllAssists'] = str(self.entries['buttons']['Stop All'].get())
            self.ed_ap.config['VoiceEnable'] = self.checkboxvar['Enable Voice'].get()
            self.ed_ap.config['DebugOverlay'] = self.checkboxvar['Debug Overlay'].get()
            self.ed_ap.config['AFKCombat_AttackAtWill'] = self.checkboxvar['AFKCombat AttackAtWill'].get()
            self.ed_ap.config['HotkeysEnable'] = self.checkboxvar['Enable Hotkeys'].get()
            self.ed_ap.config['DebugOCR'] = self.checkboxvar['Debug OCR'].get()
            self.ed_ap.config['DebugImages'] = self.checkboxvar['Debug Images'].get()
            self.ed_ap.config['Key_ModDelay'] = float(self.entries['keys']['Modifier Key Delay'].get())
            self.ed_ap.config['Key_DefHoldTime'] = float(self.entries['keys']['Default Hold Time'].get())
            self.ed_ap.config['Key_RepeatDelay'] = float(self.entries['keys']['Repeat Key Delay'].get())

            # Process config[] settings to update classes as necessary
            self.ed_ap.process_config_settings()
        except:
            messagebox.showinfo("Exception", "Invalid float entered")

    # ckbox.state:(ACTIVE | DISABLED)

    # ('FSD Route Assist', 'Supercruise Assist', 'Enable Voice', 'Enable CV View')
    def check_cb(self, field):
        # print("got event:",  checkboxvar['FSD Route Assist'].get(), " ", str(FSD_A_running))
        if field == 'FSD Route Assist':
            if self.checkboxvar['FSD Route Assist'].get() == 1 and self.FSD_A_running == False:
                self.lab_ck['AFK Combat Assist'].config(state='disabled')
                self.lab_ck['Supercruise Assist'].config(state='disabled')
                self.lab_ck['Waypoint Assist'].config(state='disabled')
                self.lab_ck['Robigo Assist'].config(state='disabled')
                self.lab_ck['DSS Assist'].config(state='disabled')
                self.start_fsd()

            elif self.checkboxvar['FSD Route Assist'].get() == 0 and self.FSD_A_running == True:
                self.stop_fsd()
                self.lab_ck['Supercruise Assist'].config(state='active')
                self.lab_ck['AFK Combat Assist'].config(state='active')
                self.lab_ck['Waypoint Assist'].config(state='active')
                self.lab_ck['Robigo Assist'].config(state='active')
                self.lab_ck['DSS Assist'].config(state='active')

        if field == 'Supercruise Assist':
            if self.checkboxvar['Supercruise Assist'].get() == 1 and self.SC_A_running == False:
                self.lab_ck['FSD Route Assist'].config(state='disabled')
                self.lab_ck['AFK Combat Assist'].config(state='disabled')
                self.lab_ck['Waypoint Assist'].config(state='disabled')
                self.lab_ck['Robigo Assist'].config(state='disabled')
                self.lab_ck['DSS Assist'].config(state='disabled')
                self.start_sc()

            elif self.checkboxvar['Supercruise Assist'].get() == 0 and self.SC_A_running == True:
                self.stop_sc()
                self.lab_ck['FSD Route Assist'].config(state='active')
                self.lab_ck['AFK Combat Assist'].config(state='active')
                self.lab_ck['Waypoint Assist'].config(state='active')
                self.lab_ck['Robigo Assist'].config(state='active')
                self.lab_ck['DSS Assist'].config(state='active')

        if field == 'Waypoint Assist':
            if self.checkboxvar['Waypoint Assist'].get() == 1 and self.WP_A_running == False:
                self.lab_ck['FSD Route Assist'].config(state='disabled')
                self.lab_ck['Supercruise Assist'].config(state='disabled')
                self.lab_ck['AFK Combat Assist'].config(state='disabled')
                self.lab_ck['Robigo Assist'].config(state='disabled')
                self.lab_ck['DSS Assist'].config(state='disabled')
                self.start_waypoint()

            elif self.checkboxvar['Waypoint Assist'].get() == 0 and self.WP_A_running == True:
                self.stop_waypoint()
                self.lab_ck['FSD Route Assist'].config(state='active')
                self.lab_ck['Supercruise Assist'].config(state='active')
                self.lab_ck['AFK Combat Assist'].config(state='active')
                self.lab_ck['Robigo Assist'].config(state='active')
                self.lab_ck['DSS Assist'].config(state='active')

        if field == 'Robigo Assist':
            if self.checkboxvar['Robigo Assist'].get() == 1 and self.RO_A_running == False:
                self.lab_ck['FSD Route Assist'].config(state='disabled')
                self.lab_ck['Supercruise Assist'].config(state='disabled')
                self.lab_ck['AFK Combat Assist'].config(state='disabled')
                self.lab_ck['Waypoint Assist'].config(state='disabled')
                self.lab_ck['DSS Assist'].config(state='disabled')
                self.start_robigo()

            elif self.checkboxvar['Robigo Assist'].get() == 0 and self.RO_A_running == True:
                self.stop_robigo()
                self.lab_ck['FSD Route Assist'].config(state='active')
                self.lab_ck['Supercruise Assist'].config(state='active')
                self.lab_ck['AFK Combat Assist'].config(state='active')
                self.lab_ck['Waypoint Assist'].config(state='active')
                self.lab_ck['DSS Assist'].config(state='active')

        if field == 'AFK Combat Assist':
            if self.checkboxvar['AFK Combat Assist'].get() == 1:
                self.ed_ap.set_afk_combat_assist(True)
                self.log_msg("AFK Combat Assist start")
                self.lab_ck['FSD Route Assist'].config(state='disabled')
                self.lab_ck['Supercruise Assist'].config(state='disabled')
                self.lab_ck['Waypoint Assist'].config(state='disabled')
                self.lab_ck['Robigo Assist'].config(state='disabled')
                self.lab_ck['DSS Assist'].config(state='disabled')

            elif self.checkboxvar['AFK Combat Assist'].get() == 0:
                self.ed_ap.set_afk_combat_assist(False)
                self.log_msg("AFK Combat Assist stop")
                self.lab_ck['FSD Route Assist'].config(state='active')
                self.lab_ck['Supercruise Assist'].config(state='active')
                self.lab_ck['Waypoint Assist'].config(state='active')
                self.lab_ck['Robigo Assist'].config(state='active')
                self.lab_ck['DSS Assist'].config(state='active')

        if field == 'DSS Assist':
            if self.checkboxvar['DSS Assist'].get() == 1:
                self.lab_ck['FSD Route Assist'].config(state='disabled')
                self.lab_ck['AFK Combat Assist'].config(state='disabled')
                self.lab_ck['Supercruise Assist'].config(state='disabled')
                self.lab_ck['Waypoint Assist'].config(state='disabled')
                self.lab_ck['Robigo Assist'].config(state='disabled')
                self.start_dss()

            elif self.checkboxvar['DSS Assist'].get() == 0:
                self.stop_dss()
                self.lab_ck['FSD Route Assist'].config(state='active')
                self.lab_ck['Supercruise Assist'].config(state='active')
                self.lab_ck['AFK Combat Assist'].config(state='active')
                self.lab_ck['Waypoint Assist'].config(state='active')
                self.lab_ck['Robigo Assist'].config(state='active')

        if self.checkboxvar['Enable Randomness'].get():
            self.ed_ap.set_randomness(True)
        else:
            self.ed_ap.set_randomness(False)

        if self.checkboxvar['Activate Elite for each key'].get():
            self.ed_ap.set_activate_elite_eachkey(True)
            self.ed_ap.keys.activate_window=True
        else:
            self.ed_ap.set_activate_elite_eachkey(False)
            self.ed_ap.keys.activate_window = False

        if self.checkboxvar['Automatic logout'].get():
            self.ed_ap.set_automatic_logout(True)
        else:
            self.ed_ap.set_automatic_logout(False)

        if self.checkboxvar['Enable Overlay'].get():
            self.ed_ap.set_overlay(True)
        else:
            self.ed_ap.set_overlay(False)

        if self.checkboxvar['Enable Voice'].get():
            self.ed_ap.set_voice(True)
        else:
            self.ed_ap.set_voice(False)

        if self.checkboxvar['ELW Scanner'].get():
            self.ed_ap.set_fss_scan(True)
        else:
            self.ed_ap.set_fss_scan(False)

        if self.checkboxvar['Enable CV View'].get() == 1:
            self.cv_view = True
            x = self.root.winfo_x() + self.root.winfo_width() + 4
            y = self.root.winfo_y()
            self.ed_ap.set_cv_view(True, x, y)
        else:
            self.cv_view = False
            self.ed_ap.set_cv_view(False)

        self.ed_ap.config['DSSButton'] = self.radiobuttonvar['dss_button'].get()

        if self.radiobuttonvar['debug_mode'].get() == "Error":
            self.ed_ap.set_log_error(True)
        elif self.radiobuttonvar['debug_mode'].get() == "Debug":
            self.ed_ap.set_log_debug(True)
        elif self.radiobuttonvar['debug_mode'].get() == "Info":
            self.ed_ap.set_log_info(True)

        if field == 'Single Waypoint Assist':
            if self.checkboxvar['Single Waypoint Assist'].get() == 1 and self.SWP_A_running == False:
                self.start_single_waypoint_assist()
            elif self.checkboxvar['Single Waypoint Assist'].get() == 0 and self.SWP_A_running == True:
                self.stop_single_waypoint_assist()

        if field == 'Debug Overlay':
            if self.checkboxvar['Debug Overlay'].get():
                self.ed_ap.debug_overlay = True
            else:
                self.ed_ap.debug_overlay = False

        self.ed_ap.config['AFKCombat_AttackAtWill'] = self.checkboxvar['AFKCombat AttackAtWill'].get()
        self.ed_ap.config['HotkeysEnable'] = self.checkboxvar['Enable Hotkeys'].get()

        if field == 'Debug OCR':
            self.ed_ap.debug_ocr = self.checkboxvar['Debug OCR'].get()

        if field == 'Debug Images':
            self.ed_ap.debug_images = self.checkboxvar['Debug Images'].get()

    def makeform(self, win, ftype, fields, r: int = 0, inc: float = 1, r_from: float = 0, rto: float = 1000):
        entries = {}
        win.columnconfigure(1, weight=1)

        for field in fields:
            if ftype == FORM_TYPE_CHECKBOX:
                self.checkboxvar[field] = tk.IntVar()
                lab = ttk.Checkbutton(win, text=field, variable=self.checkboxvar[field], command=(lambda field=field: self.check_cb(field)))
                self.lab_ck[field] = lab
                lab.grid(row=r, column=0, columnspan=2, padx=2, pady=2, sticky=tk.W)
            else:
                lab = ttk.Label(win, text=field + ": ")
                if ftype == FORM_TYPE_SPINBOX:
                    ent = ttk.Spinbox(win, width=10, from_=r_from, to=rto, increment=inc, justify=tk.RIGHT)
                else:
                    ent = ttk.Entry(win, width=10, justify=tk.RIGHT)
                ent.bind('<FocusOut>', self.entry_update)
                ent.insert(0, "0")
                lab.grid(row=r, column=0, padx=2, pady=2, sticky=tk.W)
                ent.grid(row=r, column=1, padx=2, pady=2, sticky=tk.E)
                entries[field] = ent

            lab = ToolTip(lab, msg=self.tooltips[field], delay=1.0, bg="#808080", fg="#FFFFFF")
            r += 1
        return entries

    # OCR calibration methods moved to before __init__

    def on_region_select(self, event):
        selected_region = self.calibration_region_var.get()
        if selected_region in self.ocr_calibration_data:
            rect = self.ocr_calibration_data[selected_region]['rect']
            self.calibration_rect_label_var.set(f"[{rect[0]:.4f}, {rect[1]:.4f}, {rect[2]:.4f}, {rect[3]:.4f}]")
            self.calibration_rect_text_var.set(f"{self.ocr_calibration_data[selected_region].get('text','')}")
            self.calibration_rect_left_var.set(rect[0])
            self.calibration_rect_top_var.set(rect[1])
            self.calibration_rect_right_var.set(rect[2])
            self.calibration_rect_bottom_var.set(rect[3])

            reg_f = Quad.from_rect(rect)
            self.ed_ap.overlay.overlay_quad_pct('region select', reg_f, (0, 255, 0), 2, 15)
            self.ed_ap.overlay.overlay_paint()

    def on_region_size_change(self):
        # Check if variables are valid
        l_str = self.calibration_rect_left_var.get()
        t_str = self.calibration_rect_top_var.get()
        r_str = self.calibration_rect_right_var.get()
        b_str = self.calibration_rect_bottom_var.get()
        # Check if any are empty
        if l_str == '' or r_str == '' or t_str == '' or b_str == '':
            return

        selected_region = self.calibration_region_var.get()
        if selected_region in self.ocr_calibration_data:
            rect = self.ocr_calibration_data[selected_region]['rect']
            rect[0] = str_to_float(l_str)
            rect[1] = str_to_float(t_str)
            rect[2] = str_to_float(r_str)
            rect[3] = str_to_float(b_str)

            self.calibration_rect_label_var.set(f"[{rect[0]:.4f}, {rect[1]:.4f}, {rect[2]:.4f}, {rect[3]:.4f}]")
            self.calibration_rect_text_var.set(f"{self.ocr_calibration_data[selected_region].get('text','')}")

            reg_f = Quad.from_rect(rect)
            self.ed_ap.overlay.overlay_quad_pct('region select', reg_f, (0, 255, 0), 2, 15)
            self.ed_ap.overlay.overlay_paint()

    @staticmethod
    def calibrate_region_help():
        # TODO - delete first line and enable the second.
        webbrowser.open_new("https://github.com/Stumpii/EDAPGui/blob/main/docs/Calibration.md")
        # webbrowser.open_new("https://github.com/SumZer0-git/EDAPGui/blob/main/docs/Calibration.md")

    def create_calibration_tab(self, tab):
        self.load_ocr_calibration_data()
        tab.columnconfigure(0, weight=1)

        # Region Calibration
        blk_region_cal = ttk.LabelFrame(tab, text="Region Calibration")
        blk_region_cal.grid(row=0, column=0, padx=10, pady=5, sticky="NSEW")
        blk_region_cal.columnconfigure(1, weight=1)

        region_keys = sorted([key for key, value in self.ocr_calibration_data.items() if isinstance(value, dict) and 'rect' in value and 'compass' not in key and 'target' not in key])
        self.calibration_region_var = tk.StringVar()
        self.calibration_region_combo = ttk.Combobox(blk_region_cal, textvariable=self.calibration_region_var, values=region_keys)
        self.calibration_region_combo.grid(row=0, column=1, padx=5, pady=5, sticky="EW")
        self.calibration_region_combo.bind("<<ComboboxSelected>>", self.on_region_select)

        ttk.Label(blk_region_cal, text="Region:").grid(row=0, column=0, padx=5, pady=5, sticky=tk.W)

        ttk.Label(blk_region_cal, text="Procedure:").grid(row=1, column=0, padx=5, pady=5, sticky="NW")
        self.calibration_rect_text_var = tk.StringVar()
        ttk.Label(blk_region_cal, textvariable=self.calibration_rect_text_var).grid(row=1, column=1, padx=5, pady=5, sticky=tk.W)

        ttk.Label(blk_region_cal, text="Rect:").grid(row=2, column=0, padx=5, pady=5, sticky=tk.W)
        self.calibration_rect_label_var = tk.StringVar()
        ttk.Label(blk_region_cal, textvariable=self.calibration_rect_label_var).grid(row=2, column=1, padx=5, pady=5, sticky=tk.W)

        ttk.Label(blk_region_cal, text="Manually change the region below and save.\nHint: You can also use your keyboard up and down arrow keys.").grid(row=3, column=0, columnspan=2, padx=5, pady=5, sticky=tk.W)

        self.calibration_rect_left_var = tk.StringVar()
        lbl_calibration_rect_left = ttk.Label(blk_region_cal, text='Left:')
        lbl_calibration_rect_left.grid(row=4, column=0, padx=5, pady=5, sticky=tk.W)
        spn_calibration_rect_left = ttk.Spinbox(blk_region_cal, textvariable=self.calibration_rect_left_var, width=10, from_=0, to=1, increment=0.001, justify=tk.RIGHT, command=self.on_region_size_change)
        spn_calibration_rect_left.grid(row=4, column=1, padx=5, pady=5, sticky=tk.W)

        self.calibration_rect_top_var = tk.StringVar()
        lbl_calibration_rect_top = ttk.Label(blk_region_cal, text='Top:')
        lbl_calibration_rect_top.grid(row=5, column=0, padx=5, pady=5, sticky=tk.W)
        spn_calibration_rect_top = ttk.Spinbox(blk_region_cal, textvariable=self.calibration_rect_top_var, width=10, from_=0, to=1, increment=0.001, justify=tk.RIGHT, command=self.on_region_size_change)
        spn_calibration_rect_top.grid(row=5, column=1, padx=5, pady=5, sticky=tk.W)

        self.calibration_rect_right_var = tk.StringVar()
        lbl_calibration_rect_right = ttk.Label(blk_region_cal, text='Right:')
        lbl_calibration_rect_right.grid(row=6, column=0, padx=5, pady=5, sticky=tk.W)
        spn_calibration_rect_right = ttk.Spinbox(blk_region_cal, textvariable=self.calibration_rect_right_var, width=10, from_=0, to=1, increment=0.001, justify=tk.RIGHT, command=self.on_region_size_change)
        spn_calibration_rect_right.grid(row=6, column=1, padx=5, pady=5, sticky=tk.W)

        self.calibration_rect_bottom_var = tk.StringVar()
        lbl_calibration_rect_bottom = ttk.Label(blk_region_cal, text='Bottom:')
        lbl_calibration_rect_bottom.grid(row=7, column=0, padx=5, pady=5, sticky=tk.W)
        spn_calibration_rect_bottom = ttk.Spinbox(blk_region_cal, textvariable=self.calibration_rect_bottom_var, width=10, from_=0, to=1, increment=0.001, justify=tk.RIGHT, command=self.on_region_size_change)
        spn_calibration_rect_bottom.grid(row=7, column=1, padx=5, pady=5, sticky=tk.W)

        # ttk.Button(blk_region_cal, text="Calibrate Region", command=self.calibrate_ocr_region).grid(row=8, column=0, padx=5, pady=10, sticky=tk.W)
        ttk.Button(blk_region_cal, text="Calibrate Region help online", command=self.calibrate_region_help).grid(row=8, column=0, padx=5, pady=10, sticky=tk.W)

        # Compass and Target Calibrations
        blk_other_cal = ttk.LabelFrame(tab, text="Compass and Target Calibrations")
        blk_other_cal.grid(row=2, column=0, padx=10, pady=5, sticky="NSEW")

        btn_calibrate_compass = ttk.Button(blk_other_cal, text="Calibrate Compass", command=self.calibrate_compass_callback)
        btn_calibrate_compass.grid(row=1, padx=10, pady=5, sticky="W")

        lbl_calibrate_compass = ttk.Label(blk_other_cal, wraplength=500, text='Performs compass calibration for your '
                                                                              'screen. Perform when the compass is '
                                                                              'visible in the cockpit.')
        lbl_calibrate_compass.grid(row=1, column=1, padx=10, pady=5, sticky=tk.W)

        btn_calibrate_target = ttk.Button(blk_other_cal, text="Calibrate Target", command=self.calibrate_callback)
        btn_calibrate_target.grid(row=2, padx=10, pady=5, sticky="W")

        lbl_calibrate_target = ttk.Label(blk_other_cal, wraplength=500, text='Performs target calibration for your '
                                                                             'screen. Perform when the target is '
                                                                             'visible center screen.')
        lbl_calibrate_target.grid(row=2, column=1, padx=10, pady=5, sticky=tk.W)

        # Button Frame
        button_frame = ttk.Frame(tab)
        button_frame.grid(row=3, column=0, padx=10, pady=10, sticky=tk.W)
        ttk.Button(button_frame, text="Save All Calibrations", command=self.save_ocr_calibration_data, style="Accent.TButton").pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="Reset All to Default", command=self.reset_all_calibrations).pack(side=tk.LEFT, padx=5)

    def gui_gen(self, win):

        modes_check_fields = ('FSD Route Assist', 'Supercruise Assist', 'Waypoint Assist', 'Robigo Assist', 'AFK Combat Assist', 'DSS Assist')
        ship_entry_fields = ('RollRate', 'PitchRate', 'YawRate', 'RollFactor', 'PitchFactor', 'YawFactor')
        autopilot_entry_fields = ('Sun Bright Threshold', 'Nav Align Tries', 'Jump Tries', 'Docking Retries', 'Wait For Autodock')
        buttons_entry_fields = ('Start FSD', 'Start SC', 'Start Robigo', 'Stop All')
        refuel_entry_fields = ('Refuel Threshold', 'Scoop Timeout', 'Fuel Threshold Abort')
        overlay_entry_fields = ('X Offset', 'Y Offset', 'Font Size')
        keys_entry_fields = ('Modifier Key Delay', 'Default Hold Time', 'Repeat Key Delay')

        # notebook pages
        btn_save = ttk.Button(win, text='Save All Settings', command=self.save_settings, style="Accent.TButton")
        btn_save.grid(row=0, padx=10, pady=5, sticky="W")

        nb = ttk.Notebook(win)
        nb.grid(row=1, padx=10, pady=5, sticky="NSEW")
        
        page0 = ttk.Frame(nb)
        page0.grid_columnconfigure(0, weight=1)
        page0.grid_rowconfigure(0, weight=0)
        page0.grid_rowconfigure(1, weight=0)
        page0.grid_rowconfigure(2, weight=1)  # Log row
        nb.add(page0, text="Main")  # main page
        
        page1 = ttk.Frame(nb)
        page1.grid_columnconfigure(0, weight=1)
        nb.add(page1, text="Settings")  # options page
        
        page2 = ttk.Frame(nb)
        page2.grid_columnconfigure([0, 1], weight=1)
        nb.add(page2, text="Debug/Test")  # debug/test page

        # === Calibration Tab ===
        page_calibration = ttk.Frame(nb)
        page_calibration.grid_columnconfigure(0, weight=1)
        nb.add(page_calibration, text="Calibration")
        self.create_calibration_tab(page_calibration)

        # === Waypoint Editor Tab ===
        page_waypoint_editor = ttk.Frame(nb)
        page_waypoint_editor.grid_columnconfigure(0, weight=1)
        nb.add(page_waypoint_editor, text="Waypoint Editor")
        self.waypoint_editor_tab = WaypointEditorTab(page_waypoint_editor, self.ed_ap.waypoint)
        self.waypoint_editor_tab.frame.pack(fill="both", expand=True)

        # === TCE Integration ===
        page_tce_integration = ttk.Frame(nb)
        page_tce_integration.grid_columnconfigure(0, weight=1)
        nb.add(page_tce_integration, text="TCE")
        tce_integration_tab = self.ed_ap.tce_integration.create_gui_tab(self, page_tce_integration)

        # === MAIN TAB ===
        # main options block
        blk_main = ttk.Frame(page0)
        blk_main.grid(row=0, column=0, padx=10, pady=5, sticky="NSEW")
        blk_main.columnconfigure([0, 1], weight=1, minsize=100, uniform="group1")

        # ap mode checkboxes block
        blk_modes = ttk.LabelFrame(blk_main, text="MODE", padding=(10, 5))
        blk_modes.grid(row=0, column=0, padx=2, pady=2, sticky="NSEW")
        self.makeform(blk_modes, FORM_TYPE_CHECKBOX, modes_check_fields)

        # ship values block
        blk_ship = ttk.LabelFrame(blk_main, text="SHIP", padding=(10, 5))
        blk_ship.grid(row=0, column=1, padx=2, pady=2, sticky="NSEW")
        self.entries['ship'] = self.makeform(blk_ship, FORM_TYPE_SPINBOX, ship_entry_fields, 0, 0.5)

        lbl_sun_pitch_up = ttk.Label(blk_ship, text='SunPitchUp +/- Time:')
        lbl_sun_pitch_up.grid(row=6, column=0, pady=3, sticky=tk.W)
        spn_sun_pitch_up = ttk.Spinbox(blk_ship, width=10, from_=-100, to=100, increment=0.5, justify=tk.RIGHT)
        spn_sun_pitch_up.grid(row=6, column=1, padx=2, pady=2, sticky=tk.E)
        spn_sun_pitch_up.bind('<FocusOut>', self.entry_update)
        self.entries['ship']['SunPitchUp+Time'] = spn_sun_pitch_up

        btn_tst_roll = ttk.Button(blk_ship, text='Test Roll Rate', command=self.ship_tst_roll)
        btn_tst_roll.grid(row=7, column=0, padx=2, pady=2, columnspan=2, sticky="NSEW")
        btn_tst_pitch = ttk.Button(blk_ship, text='Test Pitch Rate', command=self.ship_tst_pitch)
        btn_tst_pitch.grid(row=8, column=0, padx=2, pady=2, columnspan=2, sticky="NSEW")
        btn_tst_yaw = ttk.Button(blk_ship, text='Test Yaw Rate', command=self.ship_tst_yaw)

        # waypoints button block
        blk_wp_buttons = ttk.LabelFrame(page0, text="Waypoints", padding=(10, 5))
        blk_wp_buttons.grid(row=1, column=0, padx=10, pady=5, columnspan=2, sticky="NSEW")
        blk_wp_buttons.columnconfigure([0, 1], weight=1, minsize=100, uniform="group1")

        self.wp_filelabel = tk.StringVar()
        self.wp_filelabel.set("<no list loaded>")
        btn_wp_file = ttk.Button(blk_wp_buttons, textvariable=self.wp_filelabel, command=self.open_wp_file)
        btn_wp_file.grid(row=0, column=0, padx=2, pady=2, columnspan=2, sticky="NSEW")
        tip_wp_file = ToolTip(btn_wp_file, msg=self.tooltips['Waypoint List Button'], delay=1.0, bg="#808080", fg="#FFFFFF")

        btn_reset = ttk.Button(blk_wp_buttons, text='Reset List', command=self.reset_wp_file)
        btn_reset.grid(row=1, column=0, padx=2, pady=2, columnspan=2, sticky="NSEW")
        tip_reset = ToolTip(btn_reset, msg=self.tooltips['Reset Waypoint List'], delay=1.0, bg="#808080", fg="#FFFFFF")
        btn_tst_yaw.grid(row=9, column=0, padx=2, pady=2, columnspan=2, sticky="NSEW")

        # log window
        log = ttk.LabelFrame(page0, text="LOG", padding=(10, 5))
        log.grid(row=2, column=0, padx=10, pady=5, sticky="NSEW")
        log.grid_columnconfigure(0, weight=1)
        log.grid_rowconfigure(0, weight=1)
        y_scrollbar = ttk.Scrollbar(log)
        y_scrollbar.grid(row=0, column=1, sticky="NSE")
        x_scrollbar = ttk.Scrollbar(log, orient="horizontal")
        x_scrollbar.grid(row=1, column=0, sticky="EW")
        mylist = tk.Listbox(log, width=100, yscrollcommand=y_scrollbar.set, xscrollcommand=x_scrollbar.set)
        mylist.grid(row=0, column=0, sticky="NSEW")
        y_scrollbar.config(command=mylist.yview)
        x_scrollbar.config(command=mylist.xview)

        # === SETTINGS TAB ===
        # settings block
        blk_settings = ttk.Frame(page1)
        blk_settings.grid(row=0, column=0, padx=10, pady=5, sticky="EW")
        blk_settings.columnconfigure([0, 1], weight=1, minsize=100, uniform="group1")

        # autopilot settings block
        blk_ap = ttk.LabelFrame(blk_settings, text="AUTOPILOT", padding=(10, 5))
        blk_ap.grid(row=0, column=0, padx=2, pady=2, sticky="NSEW")
        self.entries['autopilot'] = self.makeform(blk_ap, FORM_TYPE_SPINBOX, autopilot_entry_fields)
        self.checkboxvar['Enable Randomness'] = tk.BooleanVar()
        cb_random = ttk.Checkbutton(blk_ap, text='Enable Randomness', variable=self.checkboxvar['Enable Randomness'], command=(lambda field='Enable Randomness': self.check_cb(field)))
        cb_random.grid(row=5, column=0, columnspan=2, sticky=tk.W)
        self.checkboxvar['Automatic logout'] = tk.BooleanVar()
        cb_logout = ttk.Checkbutton(blk_ap, text='Automatic logout', variable=self.checkboxvar['Automatic logout'], command=(lambda field='Automatic logout': self.check_cb(field)))
        cb_logout.grid(row=6, column=0, columnspan=2, sticky=tk.W)

        # buttons settings block
        blk_buttons = ttk.LabelFrame(blk_settings, text="BUTTONS", padding=(10, 5))
        blk_buttons.grid(row=0, column=1, padx=2, pady=2, sticky="NSEW")
        blk_dss = ttk.Frame(blk_buttons)
        blk_dss.grid(row=0, column=0, columnspan=2, padx=0, pady=0, sticky="NSEW")
        lb_dss = ttk.Label(blk_dss, text="DSS Button: ")
        lb_dss.grid(row=0, column=0, sticky=tk.W)
        self.radiobuttonvar['dss_button'] = tk.StringVar()
        rb_dss_primary = ttk.Radiobutton(blk_dss, text="Primary", variable=self.radiobuttonvar['dss_button'], value="Primary", command=(lambda field='dss_button': self.check_cb(field)))
        rb_dss_primary.grid(row=0, column=1, sticky=tk.W)
        rb_dss_secandary = ttk.Radiobutton(blk_dss, text="Secondary", variable=self.radiobuttonvar['dss_button'], value="Secondary", command=(lambda field='dss_button': self.check_cb(field)))
        rb_dss_secandary.grid(row=1, column=1, sticky=tk.W)
        self.checkboxvar['Enable Hotkeys'] = tk.BooleanVar()
        cb_enable = ttk.Checkbutton(blk_buttons, text='Enable Hotkeys (requires restart)', variable=self.checkboxvar['Enable Hotkeys'], command=(lambda field='Enable Hotkeys': self.check_cb(field)))
        cb_enable.grid(row=2, column=0, columnspan=2, sticky=tk.W)
        self.entries['buttons'] = self.makeform(blk_buttons, FORM_TYPE_ENTRY, buttons_entry_fields, 3)

        # refuel settings block
        blk_fuel = ttk.LabelFrame(blk_settings, text="FUEL", padding=(10, 5))
        blk_fuel.grid(row=1, column=0, padx=2, pady=2, sticky="NSEW")
        self.entries['refuel'] = self.makeform(blk_fuel, FORM_TYPE_SPINBOX, refuel_entry_fields)

        # overlay settings block
        blk_overlay = ttk.LabelFrame(blk_settings, text="OVERLAY", padding=(10, 5))
        blk_overlay.grid(row=1, column=1, padx=2, pady=2, sticky="NSEW")
        self.checkboxvar['Enable Overlay'] = tk.BooleanVar()
        cb_enable = ttk.Checkbutton(blk_overlay, text='Enable', variable=self.checkboxvar['Enable Overlay'], command=(lambda field='Enable Overlay': self.check_cb(field)))
        cb_enable.grid(row=0, column=0, columnspan=2, sticky=tk.W)
        self.entries['overlay'] = self.makeform(blk_overlay, FORM_TYPE_SPINBOX, overlay_entry_fields, 1, 1.0, 0.0, 3000.0)

        # Keys settings block
        blk_keys = ttk.LabelFrame(blk_settings, text="KEYS", padding=(10, 5))
        blk_keys.grid(row=2, column=0, padx=2, pady=2, sticky="NSEW")
        self.checkboxvar['Activate Elite for each key'] = tk.BooleanVar()
        cb_activate_elite = ttk.Checkbutton(blk_keys, text='Activate Elite for each key', variable=self.checkboxvar['Activate Elite for each key'], command=(lambda field='Activate Elite for each key': self.check_cb(field)))
        cb_activate_elite.grid(row=0, column=0, columnspan=2, sticky=tk.W)
        self.entries['keys'] = self.makeform(blk_keys, FORM_TYPE_SPINBOX, keys_entry_fields, 1, 0.01)

        # voice settings block
        blk_voice = ttk.LabelFrame(blk_settings, text="VOICE", padding=(10, 5))
        blk_voice.grid(row=3, column=0, padx=2, pady=2, sticky="NSEW")
        self.checkboxvar['Enable Voice'] = tk.BooleanVar()
        cb_enable = ttk.Checkbutton(blk_voice, text='Enable', variable=self.checkboxvar['Enable Voice'], command=(lambda field='Enable Voice': self.check_cb(field)))
        cb_enable.grid(row=0, column=0, columnspan=2, sticky=tk.W)

        # ELW Scanner settings block
        blk_voice = ttk.LabelFrame(blk_settings, text="ELW SCANNER", padding=(10, 5))
        blk_voice.grid(row=3, column=1, padx=2, pady=2, sticky="NSEW")
        self.checkboxvar['ELW Scanner'] = tk.BooleanVar()
        cb_enable = ttk.Checkbutton(blk_voice, text='Enable', variable=self.checkboxvar['ELW Scanner'], command=(lambda field='ELW Scanner': self.check_cb(field)))
        cb_enable.grid(row=0, column=0, columnspan=2, sticky=tk.W)

        # AFK Combat settings block
        blk_afk_combat = ttk.LabelFrame(blk_settings, text="AFK Combat", padding=(10, 5))
        blk_afk_combat.grid(row=4, column=0, padx=2, pady=2, sticky="NSEW")
        self.checkboxvar['AFKCombat AttackAtWill'] = tk.BooleanVar()
        cb_enable = ttk.Checkbutton(blk_afk_combat, text='Command SLF to Attack At Will', variable=self.checkboxvar['AFKCombat AttackAtWill'], command=(lambda field='AFKCombat AttackAtWill': self.check_cb(field)))
        cb_enable.grid(row=0, column=0, columnspan=2, sticky=tk.W)

        # settings button block
        blk_settings_buttons = ttk.Frame(page1)
        blk_settings_buttons.grid(row=5, column=0, padx=10, pady=5, sticky="NSEW")
        blk_settings_buttons.columnconfigure([0, 1], weight=1, minsize=100)
        btn_save = ttk.Button(blk_settings_buttons, text='Save All Settings', command=self.save_settings, style="Accent.TButton")
        btn_save.grid(row=0, column=0, padx=2, pady=2, columnspan=2, sticky="NSEW")

        # ==== DEBUG/TEST TAB ====
        # File Actions
        blk_file_actions = ttk.LabelFrame(page2, text="File Actions", padding=(10, 5))
        blk_file_actions.grid(row=0, column=0, padx=10, pady=5, sticky="NSEW")
        self.checkboxvar['Enable CV View'] = tk.IntVar()
        self.checkboxvar['Enable CV View'].set(int(self.ed_ap.config['Enable_CV_View']))
        cb_enable_cv_view = ttk.Checkbutton(blk_file_actions, text='Enable CV View', variable=self.checkboxvar['Enable CV View'], command=(lambda field='Enable CV View': self.check_cb(field)))
        cb_enable_cv_view.grid(row=2, column=0, padx=2, pady=2, sticky=tk.W)
        btn_restart = ttk.Button(blk_file_actions, text="Restart", command=self.restart_program)
        btn_restart.grid(row=3, column=0, padx=2, pady=2, sticky=tk.W)
        btn_exit = ttk.Button(blk_file_actions, text="Exit", command=self.close_window)
        btn_exit.grid(row=4, column=0, padx=2, pady=2, sticky=tk.W)

        # Help Actions
        blk_help_actions = ttk.LabelFrame(page2, text="Help Actions", padding=(10, 5))
        blk_help_actions.grid(row=0, column=1, padx=10, pady=5, sticky="NSEW")
        btn_check_updates = ttk.Button(blk_help_actions, text="Check for Updates", command=self.check_updates)
        btn_check_updates.grid(row=0, column=0, padx=2, pady=2, sticky=tk.W)
        btn_view_changelog = ttk.Button(blk_help_actions, text="View Changelog", command=self.open_changelog)
        btn_view_changelog.grid(row=1, column=0, padx=2, pady=2, sticky=tk.W)
        btn_join_discord = ttk.Button(blk_help_actions, text="Join Discord", command=self.open_discord)
        btn_join_discord.grid(row=2, column=0, padx=2, pady=2, sticky=tk.W)
        btn_about = ttk.Button(blk_help_actions, text="About", command=self.about)
        btn_about.grid(row=3, column=0, padx=2, pady=2, sticky=tk.W)

        # # debug block
        # blk_debug = ttk.Frame(page2)
        # blk_debug.grid(row=1, column=0, padx=10, pady=5, sticky=(tk.E, tk.W))
        # blk_debug.columnconfigure([0, 1], weight=1, minsize=100, uniform="group2")

        # Debug Settings frame
        blk_debug_settings = ttk.LabelFrame(page2, text="Debug Settings", padding=(10, 5))
        blk_debug_settings.grid(row=1, column=0, padx=10, pady=5, sticky="NSEW")
        self.radiobuttonvar['debug_mode'] = tk.StringVar()
        rb_debug_debug = ttk.Radiobutton(blk_debug_settings, text="Debug + Info + Errors", variable=self.radiobuttonvar['debug_mode'], value="Debug", command=(lambda field='debug_mode': self.check_cb(field)))
        rb_debug_debug.grid(row=0, column=1, columnspan=2, sticky=tk.W)
        rb_debug_info = ttk.Radiobutton(blk_debug_settings, text="Info + Errors", variable=self.radiobuttonvar['debug_mode'], value="Info", command=(lambda field='debug_mode': self.check_cb(field)))
        rb_debug_info.grid(row=1, column=1, columnspan=2, sticky=tk.W)
        rb_debug_error = ttk.Radiobutton(blk_debug_settings, text="Errors only (default)", variable=self.radiobuttonvar['debug_mode'], value="Error", command=(lambda field='debug_mode': self.check_cb(field)))
        rb_debug_error.grid(row=2, column=1, columnspan=2, sticky=tk.W)
        btn_open_logfile = ttk.Button(blk_debug_settings, text='Open Log File', command=self.open_logfile)
        btn_open_logfile.grid(row=3, column=0, padx=2, pady=2, columnspan=2, sticky="NSEW")

        # Single Waypoint Assist frame
        blk_single_waypoint_asst = ttk.LabelFrame(page2, text="Single Waypoint Assist", padding=(10, 5))
        blk_single_waypoint_asst.grid(row=1, column=1, padx=10, pady=5, sticky="NSEW")
        blk_single_waypoint_asst.columnconfigure(0, weight=1, minsize=10)
        blk_single_waypoint_asst.columnconfigure(1, weight=3, minsize=10)

        lbl_system = ttk.Label(blk_single_waypoint_asst, text='System:')
        lbl_system.grid(row=0, column=0, padx=2, pady=2, columnspan=1, sticky="NSEW")
        txt_system = ttk.Entry(blk_single_waypoint_asst, textvariable=self.single_waypoint_system)
        txt_system.grid(row=0, column=1, padx=2, pady=2, columnspan=1, sticky="NSEW")
        lbl_station = ttk.Label(blk_single_waypoint_asst, text='Station:')
        lbl_station.grid(row=1, column=0, padx=2, pady=2, columnspan=1, sticky="NSEW")
        txt_station = ttk.Entry(blk_single_waypoint_asst, textvariable=self.single_waypoint_station)
        txt_station.grid(row=1, column=1, padx=2, pady=2, columnspan=1, sticky="NSEW")
        self.checkboxvar['Single Waypoint Assist'] = tk.BooleanVar()
        cb_single_waypoint = ttk.Checkbutton(blk_single_waypoint_asst, text='Single Waypoint Assist', variable=self.checkboxvar['Single Waypoint Assist'], command=(lambda field='Single Waypoint Assist': self.check_cb(field)))
        cb_single_waypoint.grid(row=2, column=0, padx=2, pady=2, columnspan=2, sticky="NSEW")

        blk_debug_buttons = ttk.Frame(page2)
        blk_debug_buttons.grid(row=2, column=0, columnspan=2, padx=10, pady=5, sticky="NSEW")
        blk_debug_buttons.columnconfigure([0, 1], weight=1, minsize=100)

        self.checkboxvar['Debug Overlay'] = tk.BooleanVar()
        cb_debug_overlay = ttk.Checkbutton(blk_debug_buttons, text='Debug Overlay', variable=self.checkboxvar['Debug Overlay'], command=(lambda field='Debug Overlay': self.check_cb(field)))
        cb_debug_overlay.grid(row=6, column=0, padx=2, pady=2, columnspan=2, sticky="NSEW")
        tip = ToolTip(cb_debug_overlay, msg=self.tooltips['Debug Overlay'], delay=1.0, bg="#808080", fg="#FFFFFF")

        self.checkboxvar['Debug OCR'] = tk.BooleanVar()
        cb_debug_ocr = ttk.Checkbutton(blk_debug_buttons, text="Debug OCR - Writes OCR output to 'ocr-output' folder", variable=self.checkboxvar['Debug OCR'], command=(lambda field='Debug OCR': self.check_cb(field)))
        cb_debug_ocr.grid(row=7, column=0, padx=2, pady=2, columnspan=2, sticky="NSEW")
        tip = ToolTip(cb_debug_ocr, msg=self.tooltips['Debug OCR'], delay=1.0, bg="#808080", fg="#FFFFFF")

        self.checkboxvar['Debug Images'] = tk.BooleanVar()
        cb_debug_images = ttk.Checkbutton(blk_debug_buttons, text="Debug Images - Writes debug images to 'debug-output' folder", variable=self.checkboxvar['Debug Images'], command=(lambda field='Debug Images': self.check_cb(field)))
        cb_debug_images.grid(row=8, column=0, padx=2, pady=2, columnspan=2, sticky="NSEW")
        tip = ToolTip(cb_debug_images, msg=self.tooltips['Debug Images'], delay=1.0, bg="#808080", fg="#FFFFFF")

        btn_save = ttk.Button(blk_debug_buttons, text='Save All Settings', command=self.save_settings, style="Accent.TButton")
        btn_save.grid(row=9, column=0, padx=2, pady=2, columnspan=2, sticky="NSEW")

        blk_rpy = ttk.LabelFrame(page2, text="RPY Test", padding=(10, 5))
        blk_rpy.grid(row=10, column=0, columnspan=2, padx=2, pady=2, sticky="NSEW")
        blk_rpy.columnconfigure([0, 1, 2], weight=1, minsize=100)

        btn_tst_roll_30 = ttk.Button(blk_rpy, text='Test Roll Rate (30 deg)', command=self.ship_tst_roll_30)
        btn_tst_roll_30.grid(row=1, column=0, padx=2, pady=2, columnspan=1, sticky="NSEW")
        btn_tst_pitch_30 = ttk.Button(blk_rpy, text='Test Pitch Rate (30 deg)', command=self.ship_tst_pitch_30)
        btn_tst_pitch_30.grid(row=1, column=1, padx=2, pady=2, columnspan=1, sticky="NSEW")
        btn_tst_yaw_30 = ttk.Button(blk_rpy, text='Test Yaw Rate (30 deg)', command=self.ship_tst_yaw_30)
        btn_tst_yaw_30.grid(row=1, column=2, padx=2, pady=2, columnspan=1, sticky="NSEW")

        btn_tst_roll_45 = ttk.Button(blk_rpy, text='Test Roll Rate (45 deg)', command=self.ship_tst_roll_45)
        btn_tst_roll_45.grid(row=2, column=0, padx=2, pady=2, columnspan=1, sticky="NSEW")
        btn_tst_pitch_45 = ttk.Button(blk_rpy, text='Test Pitch Rate (45 deg)', command=self.ship_tst_pitch_45)
        btn_tst_pitch_45.grid(row=2, column=1, padx=2, pady=2, columnspan=1, sticky="NSEW")
        btn_tst_yaw_45 = ttk.Button(blk_rpy, text='Test Yaw Rate (45 deg)', command=self.ship_tst_yaw_45)
        btn_tst_yaw_45.grid(row=2, column=2, padx=2, pady=2, columnspan=1, sticky="NSEW")

        btn_tst_roll_90 = ttk.Button(blk_rpy, text='Test Roll Rate (90 deg)', command=self.ship_tst_roll_90)
        btn_tst_roll_90.grid(row=3, column=0, padx=2, pady=2, columnspan=1, sticky="NSEW")
        btn_tst_pitch_90 = ttk.Button(blk_rpy, text='Test Pitch Rate (90 deg)', command=self.ship_tst_pitch_90)
        btn_tst_pitch_90.grid(row=3, column=1, padx=2, pady=2, columnspan=1, sticky="NSEW")
        btn_tst_yaw_90 = ttk.Button(blk_rpy, text='Test Yaw Rate (90 deg)', command=self.ship_tst_yaw_90)
        btn_tst_yaw_90.grid(row=3, column=2, padx=2, pady=2, columnspan=1, sticky="NSEW")

        # === Status Bar ===
        statusbar = ttk.Frame(win)
        statusbar.grid(row=4, column=0)
        self.status = ttk.Label(win, text="Status: ", relief=tk.SUNKEN, anchor=tk.W, justify=tk.LEFT, width=29)
        self.jumpcount = ttk.Label(statusbar, text="<info> ", relief=tk.SUNKEN, anchor=tk.W, justify=tk.LEFT, width=40)
        self.status.pack(in_=statusbar, side=tk.LEFT, fill=tk.BOTH, expand=True)
        self.jumpcount.pack(in_=statusbar, side=tk.RIGHT, fill=tk.Y, expand=False)

        return mylist

    # def calibrate_ocr_region(self):
    #     selected_region = self.calibration_region_var.get()
    #     self.calibrator.calibrate_ocr_region(self.ocr_calibration_data, selected_region)

    def load_ocr_calibration_data(self):
        self.ocr_calibration_data = {}
        calibration_file = 'configs/ocr_calibration.json'

        default_regions = {
            # "Screen_Regions.sun": {"rect": [0.30, 0.30, 0.70, 0.68]},
            # "Screen_Regions.disengage": {"rect": [0.42, 0.65, 0.60, 0.80]},
            # "Screen_Regions.sco": {"rect": [0.42, 0.65, 0.60, 0.80]},
            # "Screen_Regions.fss": {"rect": [0.5045, 0.7545, 0.532, 0.7955]},
            # "Screen_Regions.mission_dest": {"rect": [0.46, 0.38, 0.65, 0.86]},
            # "Screen_Regions.missions": {"rect": [0.50, 0.78, 0.65, 0.85]},
            "EDCodex.full_panel": {"rect": [0.0589, 0.0983, 0.9406, 0.8617], "text": "1. Open the Codex from right hand cockpit panel.\n2. Draw a rectangle from the top left corner of the codex 'book' to the end of the line above the exit button at the bottom right."},
            "EDInternalStatusPanel.panel_bounds1": {"rect": [0.1197, 0.2733, 0.6937, 0.7125], "text": "1. Open Internal Status Panel (right hand panel).\n2. Draw a rectangle from the top left corner of the nav panel to the bottom right corner."},
            "EDInternalStatusPanel.panel_bounds2": {"rect": [0.1541, 0.2408, 0.6781, 0.8], "text": "1. Open Internal Status Panel (right hand panel).\n2. Draw a rectangle from the bottom left corner of the nav panel to the top right corner."},
            # "EDInternalStatusPanel.tab_bar": {"rect": [0.35, 0.2, 0.85, 0.26]},
            # "EDInternalStatusPanel.inventory_list": {"rect": [0.2, 0.3, 0.8, 0.9]},
            # "EDInternalStatusPanel.size.inventory_item": {"width": 100, "height": 20},
            # "EDInternalStatusPanel.size.nav_pnl_tab": {"width": 100, "height": 20},
            "EDStationServicesInShip.station_services": {"rect": [0.0809, 0.1136, 0.9186, 0.8464], "text": "1. Open Station Service.\n2. Draw a rectangle from the top left of the left panel box to the bottom right of the right panel box."},
            "EDStationServicesInShip.commodities_market": {"rect": [0.0479, 0.0983, 0.9516, 0.8617], "text": "This is calculated automatically from the Codex screen values. Do not change."},
            # "EDStationServicesInShip.connected_to": {"rect": [0.0, 0.0, 0.0, 0.0], "text": "This is calculated automatically from the Codex screen values. Do not change."},
            # "EDStationServicesInShip.carrier_admin_header": {"rect": [0.4, 0.1, 0.6, 0.2]},
            # "EDStationServicesInShip.commodities_list": {"rect": [0.2, 0.2, 0.8, 0.9]},
            # "EDStationServicesInShip.commodity_quantity": {"rect": [0.4, 0.5, 0.6, 0.6]},
            # "EDStationServicesInShip.size.commodity_item": {"width": 100, "height": 15},
            # "EDStationServicesInShip.mission_board_header": {"rect": [0.4, 0.1, 0.6, 0.2]},
            # "EDStationServicesInShip.missions_list": {"rect": [0.06, 0.25, 0.48, 0.8]},
            # "EDStationServicesInShip.mission_loaded": {"rect": [0.06, 0.25, 0.48, 0.35]},
            # "EDStationServicesInShip.size.mission_item": {"width": 100, "height": 15},
            # "EDSystemMap.cartographics": {"rect": [0.0, 0.0, 0.25, 0.25]},
            "EDGalaxyMap.full_panel": {"rect": [0.0, 0.0, 0.0, 0.0], "text": "This is calculated automatically from the Codex screen values. Do not change."},
            "EDSystemMap.full_panel": {"rect": [0.0, 0.0, 0.0, 0.0], "text": "This is calculated automatically from the Codex screen values. Do not change."},
            "EDNavigationPanel.panel_bounds1": {"rect": [0.1197, 0.2733, 0.6937, 0.7125], "text": "1. Open Navigation Panel.\n2. Draw a rectangle from the top left corner of the nav panel to the bottom right corner."},
            "EDNavigationPanel.panel_bounds2": {"rect": [0.1541, 0.2408, 0.6781, 0.8], "text": "1. Open Navigation Panel.\n2. Draw a rectangle from the bottom left corner of the nav panel to the top right corner."},
            # "EDNavigationPanel.tab_bar": {"rect": [0.0, 0.2, 0.7, 0.35]},
            # "EDNavigationPanel.size.nav_pnl_tab": {"width": 260, "height": 35},
            # "EDNavigationPanel.size.nav_pnl_location": {"width": 500, "height": 35},
            # "EDNavigationPanel.deskew_angle": -1.0
        }

        if not os.path.exists(calibration_file):
            # Create the file with default values if it doesn't exist
            with open(calibration_file, 'w') as f:
                json.dump(default_regions, f, indent=4)
            self.ocr_calibration_data = default_regions
        else:
            with open(calibration_file, 'r') as f:
                self.ocr_calibration_data = json.load(f)

            # Check for missing keys and add them
            updated = False
            for key, value in default_regions.items():
                if key not in self.ocr_calibration_data:
                    self.ocr_calibration_data[key] = value
                    updated = True

            # If we updated the data, save it back to the file
            if updated:
                with open(calibration_file, 'w') as f:
                    json.dump(self.ocr_calibration_data, f, indent=4)

    def save_ocr_calibration_data(self):
        # q = Quad.from_rect(self.ocr_calibration_data['EDCodex.full_panel']['rect'])
        # fx = 0.95
        # fy = 0.96
        # q.scale(fx, fy)
        # self.ocr_calibration_data['EDStationServicesInShip.station_services']['rect'] = q.to_rect_list(round_dp=4)

        q = Quad.from_rect(self.ocr_calibration_data['EDCodex.full_panel']['rect'])
        q.scale(fx=1.025, fy=1.0)
        self.ocr_calibration_data['EDStationServicesInShip.commodities_market']['rect'] = q.to_rect_list(round_dp=4)

        q = Quad.from_rect(self.ocr_calibration_data['EDCodex.full_panel']['rect'])
        q.scale(fx=1.05, fy=1.08)
        self.ocr_calibration_data['EDSystemMap.full_panel']['rect'] = q.to_rect_list(round_dp=4)

        q = Quad.from_rect(self.ocr_calibration_data['EDCodex.full_panel']['rect'])
        q.scale(fx=1.05, fy=1.08)
        self.ocr_calibration_data['EDGalaxyMap.full_panel']['rect'] = q.to_rect_list(round_dp=4)

        # q = Quad.from_rect(self.ocr_calibration_data['EDStationServicesInShip.station_services']['rect'])
        # q.crop(0.0, 0.0, 0.25, 0.25)
        # self.ocr_calibration_data['EDStationServicesInShip.connected_to']['rect'] = q.to_rect_list(round_dp=4)

        calibration_file = 'configs/ocr_calibration.json'
        with open(calibration_file, 'w') as f:
            json.dump(self.ocr_calibration_data, f, indent=4)
        self.log_msg("OCR calibration data saved.")
        messagebox.showinfo("Saved", "OCR calibration data saved.\nPlease restart the application for changes to take effect.")

    def reset_all_calibrations(self):
        if messagebox.askyesno("Reset All Calibrations", "Are you sure you want to reset all OCR calibrations to their default values? This cannot be undone."):
            calibration_file = 'configs/ocr_calibration.json'
            if os.path.exists(calibration_file):
                os.remove(calibration_file)
                self.log_msg("Removed existing ocr_calibration.json.")

            # This will recreate the file with defaults
            self.load_ocr_calibration_data()

            # --- Repopulate UI ---
            # Clear current selections
            self.calibration_region_var.set('')
            # self.calibration_size_var.set('')
            self.calibration_rect_label_var.set('')
            # self.calibration_rect_left_var.set('')
            # self.calibration_size_label_var.set('')

            # Repopulate region dropdown
            region_keys = sorted([key for key in self.ocr_calibration_data.keys() if '.size.' not in key and 'compass' not in key and 'target' not in key])
            self.calibration_region_combo['values'] = region_keys

            # Repopulate size dropdown
            # size_keys = sorted([key for key in self.ocr_calibration_data.keys() if '.size.' in key])
            # self.calibration_size_combo['values'] = size_keys

            self.log_msg("All OCR calibrations have been reset to default.")
            messagebox.showinfo("Reset Complete", "All calibrations have been reset to default. Please restart the application for all changes to take effect.")

    def restart_program(self):
        logger.debug("Entered: restart_program")
        print("restart now")

        self.stop_fsd()
        self.stop_sc()
        self.ed_ap.quit()
        sleep(0.1)

        import sys
        print("argv was", sys.argv)
        print("sys.executable was", sys.executable)
        print("restart now")

        import os
        os.execv(sys.executable, ['python'] + sys.argv)


def apply_theme_to_titlebar(root):
    version = sys.getwindowsversion()

    if version.major == 10 and version.build >= 22000:
        # Set the title bar color to the background color on Windows 11 for better appearance
        pywinstyles.change_header_color(root, "#1c1c1c" if sv_ttk.get_theme() == "dark" else "#fafafa")
    elif version.major == 10:
        pywinstyles.apply_style(root, "dark" if sv_ttk.get_theme() == "dark" else "normal")

        # A hacky way to update the title bar's color on Windows 10 (it doesn't update instantly like on Windows 11)
        root.wm_attributes("-alpha", 0.99)
        root.wm_attributes("-alpha", 1)


def main():
    #   handle = win32gui.FindWindow(0, "Elite - Dangerous (CLIENT)")
    #   if handle != None:
    #       win32gui.SetForegroundWindow(handle)  # put the window in foreground

    root = tk.Tk()
    app = APGui(root)

    sv_ttk.set_theme("dark")

    # Remove focus outline from tabs by setting focuscolor to the background color
    style = ttk.Style()
    bg_color = "#1c1c1c" if sv_ttk.get_theme() == "dark" else "#fafafa"
    style.configure("TNotebook.Tab", focuscolor=bg_color)

    # if sys.platform == "win32":
    #     apply_theme_to_titlebar(root)

    root.mainloop()


if __name__ == "__main__":
    main()
