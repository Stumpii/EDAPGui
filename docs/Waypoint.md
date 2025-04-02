# Waypoints
Waypoints are Systems that are captured in a waypoints.json file and read and processed by this Autopilot.  An example waypoint file is below:

```py
{
"Mylaifai EP-G c27-631": {"DockWithStation": null, "StationCoord": [0,0], "StationBookmark": -1, "SellNumDown": -1, "BuyNumDown": -1, "Completed": false}, 
"Striechooe QR-S b37-0": {"DockWithStation": null, "StationCoord": [0,0], "StationBookmark": -1, "SellNumDown": -1, "BuyNumDown": -1, "Completed": false} ,
"Ploxao JV-E b31-1":     {"DockWithStation": null, "StationCoord": [0,0], "StationBookmark": -1, "SellNumDown": -1, "BuyNumDown": -1, "Completed": false} ,
"Beagle Point":          {"DockWithStation": null, "StationCoord": [0,0], "StationBookmark": -1, "SellNumDown": -1, "BuyNumDown": -1, "Completed": false} 
}
```

With this waypoint file this Autopilot will take you to Beagle Point without your intervention.  The Autopilot will read and process each
row, plotting the course to that System in the GalaxyMap and executing that route via the FSD Route Assist.  When entering that System, 
if no Station is defined (i.e. null), the assist will plot the route for the next row in this waypoint file.  The waypoint file is read 
in when selecting Waypoint Assist.  When reaching the final waypoint, the Autopilot will go idle.  The Waypoint Assist writes to 
waypoints-completd.json file, marking which Systems that has been reached by setting the Completed entity to true.

## Repeating Waypoints
A set of waypoints can endless be repeated by using a special row at the end of the waypoint file.  When hitting this record, the Waypoint 
Assist will start from the top jumping through the defined Systems until the user ends the Waypoint Assist.
<br>
```py
{ 
"Ninabin":   {"DockWithStation": null, "StationCoord": [0,0], "StationBookmark": -1, "SellNumDown": -1, "BuyNumDown": -1, "Completed": false}, 
"Wailaroju": {"DockWithStation": null, "StationCoord": [0,0], "StationBookmark": -1, "SellNumDown": -1, "BuyNumDown": -1, "Completed": false}, 
"REPEAT":    {"DockWithStation": null, "StationCoord": [0,0], "StationBookmark": -1, "SellNumDown": -1, "BuyNumDown": -1, "Completed": false}  
}
```

## Docking with a Station
When entering a System via Waypoint Assist, if the DockWithStation is not null, the Waypoint Assist
will go into **SystemMap** and select the Station at the StationCoord X, Y location (i.e. mouse click) to select and plot route to that 
Station. Alternatively and with Odyssey you can set a bookmark for the desired station instead of the x,y coordinates and then enter 
the position of the bookmark in the station list of the **System Map** from top to bottom and starting at 0 in StationBookmark. 
-1 means bookmark is disabled. 
Upon arriving at the station, the SC Assist (which is acting on behalf of the Waypoint Assist), will drop your ship
out of Supercruise and attempt docking.  Once docked, the fuel and repair will automatically be commanded.  The StationCoord can be 
determined by bringing up the SystemMap (and not moving it or adjusting it), going to the EDAPGui interface and selecting 
"Get Mouse X, Y", in the popup select Yes and your next Mouse click needs to be on the Station on the SystemMap.  The [X,Y]
Mouse coordinates will be copied to the Windows clipboard so it can be pasted into your waypoints file.  The X, Y values are
monitor resolution dependent.  So you may not be able to share with others unless they use the same resolution.
NOTE: When bringing up SystemMap
it will show the System the same way and if your Station is not visible (i.e. you have to zoom or move the map) then this
capability cannot be used for that Station.  The Station must be visible when bringing up SystemMap.
<br>
```py
{ 
    "Ninabin":   {"DockWithStation": null, "StationCoord": [0,0], "StationBookmark": -1, "SellNumDown": -1, "BuyNumDown": -1, "Completed": false}, 
    "Wailaroju": {"DockWithStation": null, "StationCoord": [0,0], "StationBookmark": -1, "SellNumDown": -1, "BuyNumDown": -1, "Completed": false},
    "Enayex":    {"DockWithStation": "Watt Port", "StationCoord": [1977,509], "StationBookmark": -1, "SellNumDown": 12, "BuyNumDown": 5, "Completed": false}, 
    "Eurybia":   {"DockWithStation": null, "StationCoord": [0,0], "StationBookmark": -1, "SellNumDown": -1, "BuyNumDown": -1, "Completed": false} 
}
```

## Docking with a System Colonisation Ship (Odyssey only)
When entering a System via Waypoint Assist, if the DockWithStation is **'System Colonisation Ship'** and **StationBookmark** is not **'-1'**, then the bookmark number will be used to select the appropriate bookmark from the **systems list** of the **Galaxy Map** from top to bottom and starting at 0 for the top bookmark. *NOTE: System Colonisation Ships are bookmarked in the System bookmarks of the Galaxy Map, not the Station bookmarks of the System Map.* The **'StationCoord'** field is not used for Colonisation Ships.

Upon arriving at the station, the SC Assist (which is acting on behalf of the Waypoint Assist), will drop your ship
out of Supercruise and attempt docking.  Once docked, the fuel and repair will automatically be commanded.

Note for trading: If **'SellNumDown'** is not **'-1'**, upon docking with a System Colonisation Ship, EDAP will sell all commodities that can be sold, regardless of the value of **'SellNumDown'**. **'BuyNumDown'** is ignored as there are no commodities that can be bought from a System Colonisation Ship.

Example below:
```py
{
    "HIP 112113": {"DockWithStation": "Nomen Vision", "StationCoord": [0,0], "StationBookmark": 0, "SellNumDown": -1, "BuyNumDown": 19, "Completed": true},
    "Shui Wei Sector AL-O b6-3": {"DockWithStation": "System Colonisation Ship", "StationCoord": [0,0], "StationBookmark": 0, "SellNumDown": 9999, "BuyNumDown": -1, "Completed": true}
}
```

## Trading
The SellNumDown and BuyNumDown fields are associated with auto-trading.  If either of those number are *not* -1, the 
trade executor kicks in, brings up Commodities and will perform the Sell (if not -1) and then the Buy (if not -1).
The *NumDown value (an integer) represents the number of rows down the commodity of interest is from the top.  Note:  Each Station's 
Commondity list is unique so you need to know for the specific Station your ship is docked at what row number your commodity is 
at.  *NumDown, essentally will IU_Down that number of times.  So you will have to manually perform the trade route once to acquire
the needed data to fill in the waypoints file.

If you try to Sell a Commodity you do not have, the system currently will get stuck as the Sell button is not highlighted.

# New Waypoints  Notes

Following actions:

### Travel to distant System
Enter system data, leave station data blank.
### Travel to Station
Enter system and station data, leave commodity data blank. For travel within the current system, leave system data blank. 
### Trade between stations

### Transfer to/from Fleet Carrier
Need to be on the INVENTORY tab in the right hand panel.
### System Colonisation Ship
Named: System Colonisation Ship
Bookmarked in Galaxy Map only, under Stations
### Orbital Construction Site
Named: Orbital Construction Site: xxx xxx 
Bookmarked in Galaxy Map only, under Stations

Example below:
```py
{
    "GlobalShoppingList": {                 # The Global shopping list. Will attempt to buy these items at every station before buying the waypoint defined items. Do not change this name.
        "BuyCommodities": {                 # The dictionary of commodities to buy. There are no global sell commodities.
            "Ceramic Composites": 14,       # Enter commodity name and quantity
            "CMM Composite": 3029,
            "Insulating Membrane": 324
        },
        "UpdateCommodityCount": true,       # Update the counts above when good purchased (not sold).
        "Skip": true,                       # Ignored for shopping list
        "Completed": false                  # Ignored for shopping list
    },
    "1": {                                  # System key. May be changed to something useful, but must be unique.
        "SystemName": "Hillaunges",         # The target system name as is mandatory. Should be actual system name. 
                                            #   Required to determine if you are already in the desired system because ED's bookmark system does not change the destination when using a bookmark to the current system.  
                                            #   If GalaxyBookmarkNumber is o, this is name searched for in the galaxy map.
        "GalaxyBookmarkType": "Sys",        # The Galaxy Map bookmark type. May be:
                                            #   'Fav' or '' - Favorites
                                            #   'Sys' - System
                                            #   'Bod' - Body
                                            #   'Sta' - Station
                                            #   'Set' - Settlement
                                            # Note: System Colonisation Ships are bookmarked at the Gal Map level, so would be 'Sta' above.
        "GalaxyBookmarkNumber": 6,          # The bookmark index within the type specified above.
                                            #   Set to 0 or -1 if bookmarks are not used.
        "StationName": "",                  # The destination name (station name, FC name etc. 
                                            #   If blank and no bookmark is set, then the waypoint is complete when reaching the system.
        "SystemBookmarkType": "Fav",        # The System Map bookmark type. May be:
                                            #   'Fav' or '' - Favorites
                                            #   'Bod' - Body
                                            #   'Sta' - Station
                                            #   'Set' - Settlement
                                            #   'Nav' - This is a special case that uses the Navigation Panel (Panel #1) to select the bookmark.
                                            #       This is primarily for system targets that do not show up in system map, like Mega Ships.
                                            #       Note that the Nav Panel list is highly variable due to what is in system and where you 
                                            #       drop into a system, so filter your Nav Panel first. So use with caution.
                                            #   Note: System Colonisation Ships can only be bookmarked at the Gal Map level, 
                                            #       so this is not applicable to Col Ships.
        "SystemBookmarkNumber": 1,          # The bookmark index within the type specified above.
                                            #   Set to 0 or -1 if bookmarks are not used.
        "SellCommodities": {},              # The dictionary of commodities to sell. Same format as the Global shopping list above.
                                            #   Additionally, for Colonisation Ships and Fleet Carriers in 'Transfer' mode, 
                                            #   as all commodities must be transferred, it is okay to put '"All": 0' as the sell good to trigger a sell all. 
        "BuyCommodities": {},               # The dictionary of commodities to buy. Same format as the Global shopping list above.
                                            #   If you define global and waypoint buy shopping lists, the waypoint shopping list will be processed first, 
        "UpdateCommodityCount": true,       # Update the buy counts above when goods are purchased (not sold). Sell counts are never updated.
        "FleetCarrierTransfer": false,      # If this 'station' is a Fleet Carrier allows option to TRANSFER goods rather than BUY/SELL,
                                            #   Set to False to Buy/sell, True to Transfer. Transfer is by default everything you have.
        "Skip": true,                       # Skip this waypoint. EDAP will not change this value, so a good way to disable a waypoint without deleting it.
        "Completed": false                  # If false, process this waypoint. One complete EDAP will switch to True. Once all waypoints are complete, EDAP will switch to False.
    },
    "2": {
        "SystemName": "Synuefe ZX-M b54-1",
        "GalaxyBookmarkType": "Sys",
        "GalaxyBookmarkNumber": 1,
        "StationName": "System Colonisation Ship",
        "SystemBookmarkType": "",
        "SystemBookmarkNumber": -1,
        "SellCommodities": {
            "ALL": 0
        },
        "BuyCommodities": {},
        "FleetCarrierTransfer": false,
        "UpdateCommodityCount": true,
        "Skip": false,
        "Completed": false
    },
    "rep": {
        "SystemName": "REPEAT",             # System name of REPEAT causes the waypoints to be repeated.
                                            # None of the other info below is used. 
        "GalaxyBookmarkType": "",
        "GalaxyBookmarkNumber": -1,
        "StationName": "",
        "SystemBookmarkType": "",
        "SystemBookmarkNumber": -1,
        "SellCommodities": {},
        "BuyCommodities": {},
        "FleetCarrierTransfer": false,
        "UpdateCommodityCount": false,
        "Skip": false,
        "Completed": false
    }
}
```

