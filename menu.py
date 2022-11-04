import nuke
import labelConnector

editMenu = nuke.menu('Nuke').findItem('Edit')

editMenu.addCommand('LabelConnector', "labelConnector.labelConnector()",
                    'A', shortcutContext=2)
