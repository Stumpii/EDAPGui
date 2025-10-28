# Waypoint Editor
Waypoints editor allows you to edit Waypoints.

## Waypoint Editor

![Alt text](../screen/WaypointEditorWaypoints.png?raw=true "Waypoint Editor - Waypoints")

### Main buttons

* New
* Open
* Save
* Save As
* Import Spansh CSV
* Import from Inara - see below

### Import from Inara
Select with the mouse the data from one 'row' as shown below.

![Alt text](../screen/InaraTradeRoute.png?raw=true "Inara Trade Route")

When pasted into the window, the data should look like this, with the data To, From, Buy, Buy Price, Sell, Sell Price on separate rows:

```py
From Fraknoi Hub | Tschapa︎
To Aisling's Asteroid | Col 285 Sector TD-Q b19-2︎
Station distance	936 Ls
Buy	Bertrandite
Buy price	1,683 Cr
Supply	5,757
Sell	Haematite
Sell price	9,140 Cr | +5,567 Cr (155%)
Demand	187,972︎
Station distance	4 Ls
```

### Waypoints List

![Alt text](../screen/WaypointEditorWaypoints1.png?raw=true "Waypoint Editor - Waypoints")

The list...

### Waypoints Options

![Alt text](../screen/WaypointEditorWaypoints2.png?raw=true "Waypoint Editor - Waypoints")

* Gal
  * Typ
  * Num
* Sys
  * typ
  * Num
* Upda
* Flle

### Buy/Sell Commodities

![Alt text](../screen/WaypointEditorWaypoints3.png?raw=true "Waypoint Editor - Waypoints")

* Name
* Qua
* Add/Sub
* Up/Down
* Add/Del

## Global Shopping List
A set of waypoints can be endlessly repeated by using a special row at the end of the waypoint file with the system name as **'REPEAT'**. When hitting this record and as long as **Skip** is not ture, the Waypoint Assist will start from the top jumping through the defined Systems until the user ends the Waypoint Assist.

![Alt text](../screen/WaypointEditorShoppingList.png?raw=true "Waypoint Editor - Global Shopping List")

### Options

![Alt text](../screen/WaypointEditorShoppingList1.png?raw=true "Waypoint Editor - Global Shopping List")

* Upda

### Global Buy Commodities

![Alt text](../screen/WaypointEditorShoppingList2.png?raw=true "Waypoint Editor - Global Shopping List")

* Name
* Qua
* Add/Sub
* Up/Down
* Add/Del
