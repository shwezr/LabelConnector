import nuke
import labelConnector

# create a new ConnectorDot. Also renames existing ones alongside all dependent nodes.
nuke.menu("Nuke").addCommand("LabelConnector/Make connector",
                             "labelConnector.makeConnector()", "F9")

# run label match search and connect matches. With one or none node, it shows the UI to set up new connections if applicable
nuke.menu("Nuke").addCommand("LabelConnector/Connect connectors",
                             "labelConnector.runLabelMatch()",
                             "F8")

# force show UI to make new connection when a single Node is selected
nuke.menu("Nuke").addCommand("LabelConnector/Force Connect connectors",
                             "labelConnector.runLabelMatch(forceShowUi = True)", "ctrl+F8")
