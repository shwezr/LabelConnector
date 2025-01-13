import nuke
import labelConnector


editMenu = nuke.menu("Nuke").findItem("Edit")

"""
change your shortcut here, default is 'A'. 
"""
editMenu.addCommand("Label Connector", "labelConnector.labelConnector()", "A", shortcutContext=2)

"""
UI SHORTCUTS

Click:          Create connection
Shift-Click:    Jumps directly to Connector
Alt-Click:      Opens Connector Settings (same like having the parent selected while hitting the shortcut)
Ctrl:           Creates Parent (same like the UI button, just to make it faster accessible)


INSTALLATION

just add

nuke.pluginAddPath('path_to_this_folder/LabelConnector')

to your menu.py in your users nuke folder.
If you put this folder right next to your menu.py, you can use

nuke.pluginAddPath('./LabelConnector')

"""
