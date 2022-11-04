import nuke
import labelConnector

editMenu = nuke.menu('Nuke').findItem('Edit')

editMenu.addCommand('LabelConnector', "labelConnector.labelConnector(useNoOpNodesOnly=False)",'A', shortcutContext=2)
