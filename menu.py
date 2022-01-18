import nuke
import labelConnector

# create a new ConnectorDot. Also renames existing ones alongside all dependent nodes.
nuke.menu('Nuke').addCommand('Luke/Make connector', "labelConnector.makeConnector()",
                             'alt+shift+A', shortcutContext=2)

# run label match search and connect matches. With one or none node, it shows the UI to set up new connections if applicable
nuke.menu('Nuke').addCommand('Luke/Connect connectors', "labelConnector.runLabelMatch()",
                             'A', shortcutContext=2)
# force show UI to make new connection when a single Node is selected
nuke.menu('Nuke').addCommand('Luke/Force Connect connectors', "labelConnector.runLabelMatch(forceShowUi = True)",
                             'alt+A', shortcutContext=2)
