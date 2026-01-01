from __future__ import annotations

import tkinter as tk
from tkinter import ttk, messagebox
import json
import os
from EDlogger import logger


class Commodity:
    def __init__(self, name="", name_localised="", required=0, provided=0, payment=0):
        self.name = tk.StringVar(value=name)
        self.name_localised = tk.StringVar(value=name_localised)
        need = required - provided
        self.need = tk.IntVar(value=need)
        self.required = tk.IntVar(value=required)
        self.provided = tk.IntVar(value=provided)
        self.payment = tk.IntVar(value=payment)


class ConstructionSite:
    def __init__(self, system_name="", station_name="", market_id=0, include=True, construction_progress=0.0,
                 construction_complete=False, construction_failed=False):
        self.system_name = tk.StringVar(value=system_name)
        self.station_name = tk.StringVar(value=station_name)
        self.station_display_name = tk.StringVar(value=station_name)
        self.market_id = tk.IntVar(value=market_id)
        self.include = tk.BooleanVar(value=include)
        self.construction_progress = tk.DoubleVar(value=construction_progress)
        self.construction_complete = tk.BooleanVar(value=construction_complete)
        self.construction_failed = tk.BooleanVar(value=construction_failed)
        self.commodities = []
        self.total = tk.StringVar()


class ConstructionSites:
    def __init__(self):
        self.sites = []


class ColonizeEditorTab:
    def __init__(self, ed_ap, cb):
        self.ap = ed_ap
        self.ap_ckb = cb
        self.tk_const_sites = ConstructionSites()
        self.const_sites = None
        self.frame = None
        self.file_watcher_thread = None
        self.last_modified_time = None
        self.tk_commodities = []
        self.commodities = {}
        self._filepath = './configs/construction.json'

    def create_waypoints_tab(self, parent):
        self.frame = ttk.Frame(parent)

        # Main container for the waypoints tab
        waypoints_container = ttk.Frame(self.frame)
        waypoints_container.pack(fill="both", expand=True, padx=5, pady=5)

        # File operations buttons
        file_ops_frame = ttk.Frame(waypoints_container)
        file_ops_frame.pack(fill="x", pady=5)
        ttk.Button(file_ops_frame, text="Open", command=self.load_const_file).pack(side="left", padx=2)

        self.save_button = ttk.Button(file_ops_frame, text="Save", command=self.save_const_file)
        self.save_button.pack(side="left", padx=2)
        self.save_button.config(state="disabled")

        # notebook pages
        # nb = ttk.Notebook(waypoints_container)
        # nb.pack(fill="both", expand=True, padx=5, pady=5)
        #
        # page0 = ttk.Frame(nb)
        # nb.add(page0, text="Waypoints")  # main page

        # === WAYPOINT TAB ===
        # Top frame for waypoints list and buttons
        top_frame = ttk.Frame(waypoints_container)
        top_frame.pack(fill="x", expand=False, pady=5)

        station_frame = ttk.LabelFrame(top_frame, text="Constructions")
        station_frame.pack(side="left", fill="both", expand=True, padx=(0, 5))

        # Waypoints list (Treeview)
        columns = ("include", "system_name", "station_name", "progress")
        self.waypoints_tree = ttk.Treeview(station_frame, columns=columns, show="headings")

        self.waypoints_tree.heading("include", text="Include")
        self.waypoints_tree.heading("system_name", text="System Name")
        self.waypoints_tree.heading("station_name", text="Station Name")
        self.waypoints_tree.heading("progress", text="Progress")

        self.waypoints_tree.column("include", width=15, anchor=tk.CENTER)
        self.waypoints_tree.column("system_name", width=200)
        self.waypoints_tree.column("station_name", width=200)
        self.waypoints_tree.column("progress", width=20, anchor=tk.CENTER)

        self.waypoints_tree.pack(side="left", fill="both", expand=True)

        # self.waypoints_tree.bind("<<TreeviewSelect>>", self.on_waypoint_select)
        self.waypoints_tree.bind("<Button-1>", self.on_tree_click)

        # Waypoint buttons
        waypoint_buttons_frame = ttk.Frame(station_frame)
        waypoint_buttons_frame.pack(side="right", fill="y", padx=(5, 5))
        ttk.Button(waypoint_buttons_frame, text="Del", command=self.delete_waypoint).pack(padx=5, pady=2, fill="x")

        # Bottom frame for waypoint options and commodity lists
        bottom_frame = ttk.Frame(waypoints_container)
        bottom_frame.pack(fill="both", expand=True, pady=5)

        # --- Buy/Sell Commodities ---
        comm_frame = ttk.Frame(bottom_frame)
        comm_frame.pack(side="top", fill="both", expand=True, pady=(5,0))

        # Commodities
        commodities_frame = ttk.LabelFrame(comm_frame, text="Commodities")
        commodities_frame.pack(side="left", fill="both", expand=True, padx=(0, 5))
        self.commodities_tree = self.create_commodity_list(commodities_frame)

    def create_commodity_list(self, parent):
        frame = ttk.Frame(parent)
        frame.pack(fill="both", expand=True)

        columns = ("name", "need", "required", "provided")
        tree = ttk.Treeview(frame, columns=columns, show="headings")
        tree.heading("name", text="Name")
        tree.column("name", width=150)
        tree.heading("need", text="Need")
        tree.column("need", width=70, anchor=tk.W)
        tree.heading("required", text="Required")
        tree.column("required", width=70, anchor=tk.W)
        tree.heading("provided", text="Provided")
        tree.column("provided", width=70, anchor=tk.W)
        tree.pack(side="left", fill="both", expand=True)

        return tree

    def load_const_file(self):
        if not os.path.exists(self._filepath):
            return False

        try:
            # Load the waypoint file in the Waypoint system, and editor
            s = read_json_file(self._filepath)
            if s:
                self.const_sites = s
                self.populate_tk_construction()
                self.populate_commodities()
                self.populate_tk_commodities()
                self.update_ui()
                self.save_button.config(state="normal")
        except json.JSONDecodeError:
            messagebox.showerror("Error", f"Invalid JSON file: {self._filepath}")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to load construction file: {e}")

    def delete_waypoint(self):
        selected_item = self.waypoints_tree.selection()
        if selected_item:
            for item in selected_item:
                index = self.waypoints_tree.index(item)
                del self.tk_const_sites.sites[index]
            self.update_const_site_list()

    def save_const_file(self):

        # Add global shopping list and waypoints
        waypoints_to_save = self.convert_to_raw_waypoints()

        write_json_file(waypoints_to_save, self._filepath)
        # read_json_file(self._filepath)

    def populate_tk_construction(self):
        self.tk_const_sites = ConstructionSites()

        for key, value in self.const_sites.items():
            wp = ConstructionSite()
            wp.system_name.set(value.get('SystemName', ''))
            wp.station_name.set(value.get('StationName', ''))

            name = value.get('StationName', '')
            if 'Orbital Construction Site: '.upper() in name.upper():
                name = right(name, len(name) - len('Orbital Construction Site: '))
            if 'Planetary Construction Site: '.upper() in name.upper():
                name = right(name, len(name) - len('Planetary Construction Site: '))
            wp.station_display_name.set(name)
            wp.market_id.set(value.get('MarketID', 0))

            wp.include.set(value.get('Include', True))
            wp.construction_progress.set(value.get('ConstructionProgress', 0.0))
            wp.construction_complete.set(value.get('ConstructionComplete', False))
            wp.construction_failed.set(value.get('ConstructionFailed', False))

            wp.commodities = []
            for item in value.get('ResourcesRequired', []):
                wp.commodities.append(Commodity(item['Name'],
                                                item['Name_Localised'],
                                                item['RequiredAmount'],
                                                item['ProvidedAmount'],
                                                item['Payment']))

            self.tk_const_sites.sites.append(wp)

    def populate_commodities(self):
        self.commodities = {}

        for key, value in self.const_sites.items():
            if value.get('Include', True):
                for item in value.get('ResourcesRequired', []):
                    if item['Name_Localised'] in self.commodities:
                        self.commodities[item['Name_Localised']]['RequiredAmount'] = self.commodities[item['Name_Localised']]['RequiredAmount'] + item['RequiredAmount']
                        self.commodities[item['Name_Localised']]['ProvidedAmount'] = self.commodities[item['Name_Localised']]['ProvidedAmount'] + item['ProvidedAmount']
                    else:
                        self.commodities[item['Name_Localised']] = item.copy()

    def populate_tk_commodities(self):
        self.tk_commodities = []

        for item in sorted(self.commodities):
            com = self.commodities[item]
            self.tk_commodities.append(Commodity(com['Name'],
                                                 com['Name_Localised'],
                                                 com['RequiredAmount'],
                                                 com['ProvidedAmount'],
                                                 com['Payment']))


    def convert_to_raw_waypoints(self):
        raw_waypoints = {}

        # Waypoints
        for wp in self.tk_const_sites.sites:
            raw_wp = {
                'SystemName': wp.system_name.get(),
                'StationName': wp.station_name.get(),
                'MarketID': wp.market_id.get(),
                'Include': wp.include.get(),
                'ConstructionProgress': wp.construction_progress.get(),
                'ConstructionComplete': wp.construction_complete.get(),
                'ConstructionFailed': wp.construction_failed.get(),
                'ResourcesRequired': []
            }
            for item in wp.commodities:
                item_dic = {
                    'Name': item.name.get(),
                    'Name_Localised': item.name_localised.get(),
                    'RequiredAmount': item.required.get(),
                    'ProvidedAmount': item.provided.get(),
                    'Payment': item.payment.get()
                }
                raw_wp['ResourcesRequired'].append(item_dic)

            raw_waypoints[wp.market_id.get()] = raw_wp

        return raw_waypoints

    def update_ui(self):
        self.update_const_site_list()
        self.populate_commodities()
        self.populate_tk_commodities()
        self.update_commodity_tree()

    def update_const_site_list(self):
        # Clear existing items
        for item in self.waypoints_tree.get_children():
            self.waypoints_tree.delete(item)

        # Add new items
        # for i, wp in enumerate(self.const_sites.sites):
        for wp in self.tk_const_sites.sites:
            self.waypoints_tree.insert('', 'end', values=(
                "✓" if wp.include.get() else "",
                wp.system_name.get(),
                wp.station_display_name.get(),
                f"{round(wp.construction_progress.get() * 100, None)}%"
            ))

    def on_tree_click(self, event):
        region = self.waypoints_tree.identify("region", event.x, event.y)
        if region != "cell":
            return

        column = self.waypoints_tree.identify_column(event.x)
        column_index = int(column.replace('#', '')) - 1

        item_id = self.waypoints_tree.identify_row(event.y)
        if not item_id:
            return

        item_index = self.waypoints_tree.index(item_id)
        wp = self.tk_const_sites.sites[item_index]

        if column_index == 0:  # Include column
            wp.include.set(not wp.include.get())

            inc = wp.include.get()
            mkt_id = wp.market_id.get()
            market = self.const_sites[str(mkt_id)]
            market['Include'] = inc

            # self.update_waypoints_list()
            # self.update_commodity_tree()
            self.update_ui()

    def update_commodity_tree(self):
        for item in self.commodities_tree.get_children():
            self.commodities_tree.delete(item)

        for item in self.tk_commodities:
            if item.need.get() > 0:
                self.commodities_tree.insert('', 'end', values=(
                    item.name_localised.get(),
                    item.need.get(),
                    item.required.get(),
                    item.provided.get()))

    def get_selected_waypoint(self):
        selected_item = self.waypoints_tree.selection()
        if selected_item:
            index = self.waypoints_tree.index(selected_item[0])
            return self.tk_const_sites.sites[index]
        return None


def write_json_file(data, filepath: str):
    #  TODO - move to separate class/file
    if not os.path.exists(filepath):
        return False

    if data is None:
        return False
    try:
        with open(filepath, "w", encoding='utf-8') as fp:
            json.dump(data, fp, indent=4)
            return True
    except Exception as e:
        logger.warning(f"write_json_file error for filepath '{filepath}':" + str(e))
        return False


def read_json_file(filepath: str):
    #  TODO - move to separate class/file
    if not os.path.exists(filepath):
        return None

    s = None
    try:
        with open(filepath, "r", encoding='utf-8') as fp:
            s = json.load(fp)
    except Exception as e:
        logger.warning(f"read_json_file error for filepath '{filepath}':" + str(e))
    return s


def right(aString, howMany):
    if howMany < 1:
        return ''
    else:
        return aString[-howMany:]


def dummy_cb(msg, body=None):
    pass


def main():
    from ED_AP import EDAutopilot

    #ed_ap = EDAutopilot(cb=None)
    ce = ColonizeEditorTab(None, cb=dummy_cb)  # False = Horizons
    ce.load_const_file()


if __name__ == "__main__":
    main()