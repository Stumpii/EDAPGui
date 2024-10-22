# Std
import argparse
import collections
import json
import sys
# External
from PyQt5 import QtCore
from PyQt5 import QtGui
from PyQt5 import QtWidgets, uic

from JsonViewerGUI import Ui_MainWindow

class MainWindow(QtWidgets.QMainWindow, Ui_MainWindow):
    def __init__(self, *args, obj=None, **kwargs):
        super(MainWindow, self).__init__(*args, **kwargs)
        self.setupUi(self)

        self.text_to_titem = TextToTreeItem()
        self.find_str = ""
        self.found_titem_list = []
        self.found_idx = 0

        fpath = 'C:/Users/shuttle/OneDrive/Programming/Python/EDAPGui/waypoints/waypoints.json'
        jfile = open(fpath)
        jdata = json.load(jfile, object_pairs_hook=collections.OrderedDict)

        # Tree
        self.tree_widget.setHeaderLabels(["Step", "System", "Station", "Action"])
        self.tree_widget.header().setSectionResizeMode(QtWidgets.QHeaderView.Stretch)

        for key in jdata:
            #root_item = QtWidgets.QTreeWidgetItem(["Root"])
            root_item = QtWidgets.QTreeWidgetItem([key])
            root_item.setText(2,jdata[key]['DockWithStation'])
            root_item.setText(3,jdata[key]['BuyItem'])
            root_item.setText(4,jdata[key]['SellItem'])
            self.recurse_jdata(jdata[key], root_item)
            self.tree_widget.addTopLevelItem(root_item)

        self.tree_widget.expandAll()


    def find_button_clicked(self):
        print("Clicked!")

        find_str = self.find_box.text()

        # Very common for use to click Find on empty string
        if find_str == "":
            return

        # New search string
        if find_str != self.find_str:
            self.find_str = find_str
            self.found_titem_list = self.text_to_titem.find(self.find_str)
            self.found_idx = 0
        else:
            item_num = len(self.found_titem_list)
            self.found_idx = (self.found_idx + 1) % item_num

        self.tree_widget.setCurrentItem(self.found_titem_list[self.found_idx])


    def recurse_jdata(self, jdata, tree_widget):

        if isinstance(jdata, dict):
            for key, val in jdata.items():
                self.tree_add_row(key, val, tree_widget)
        elif isinstance(jdata, list):
            for i, val in enumerate(jdata):
                key = str(i)
                self.tree_add_row(key, val, tree_widget)
        else:
            print("This should never be reached!")

    def tree_add_row(self, key, val, tree_widget):

        text_list = []

        if isinstance(val, dict) or isinstance(val, list):
            text_list.append(key)
            row_item = QtWidgets.QTreeWidgetItem([key])
            self.recurse_jdata(val, row_item)
        else:
            text_list.append(key)
            text_list.append(str(val))
            row_item = QtWidgets.QTreeWidgetItem([key, str(val)])

        tree_widget.addChild(row_item)
        self.text_to_titem.append(text_list, row_item)


class TextToTreeItem:
    def __init__(self):
        self.text_list = []
        self.titem_list = []

    def append(self, text_list, titem):
        for text in text_list:
            self.text_list.append(text)
            self.titem_list.append(titem)

    # Return model indices that match string
    def find(self, find_str):

        titem_list = []
        for i, s in enumerate(self.text_list):
            if find_str in s:
                titem_list.append(self.titem_list[i])

        return titem_list





def main():
    app = QtWidgets.QApplication(sys.argv)

    window = MainWindow()
    window.show()
    app.exec()


if "__main__" == __name__:
    main()
