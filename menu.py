import nuke
import labelConnector


editMenu = nuke.menu('Nuke').findItem('Edit')

# change your shortcut here, default = 'A'. 
# If you never want PostageStamps, but NoOps forever and ever, change to useNoOpNodesOnly=True
editMenu.addCommand('LabelConnector', 'labelConnector.labelConnector(useNoOpNodesOnly=False)', 'A', shortcutContext=2)

"""
UI Shortcuts

Click:          Create connection
Shift-Click:    Jumps directly to Connector
Alt-Click:      Opens Connector Settings (same like having the parent selected while hitting the shortcut)
Ctrl:           Creates Parent (same like the UI button, just to make it faster accessible)


Installation:

just add

nuke.pluginAddPath('path_to_this_folder/LabelConnector')

to your menu.py in your users nuke folder.
If you put this folder right next to your menu.py, you can use

nuke.pluginAddPath('./LabelConnector')

"""
