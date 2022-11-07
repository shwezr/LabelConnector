import nuke
import labelConnector


editMenu = nuke.menu('Nuke').findItem('Edit')

# change your shortcut here, default = 'A'. 
# If you never want PostageStamps, but NoOps forever and ever, change to useNoOpNodesOnly=True
editMenu.addCommand('LabelConnector', 'labelConnector.labelConnector(useNoOpNodesOnly=False)', 'A', shortcutContext=2)

"""
just add

nuke.pluginAddPath('path_to_this_folder/LabelConnector')

to your menu.py in your users nuke folder.
If you put this folder right next to your menu.py, you can use

nuke.pluginAddPath('./LabelConnector')

"""
