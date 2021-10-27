import labelConnector
nuke.menu( 'Nuke' ).addCommand( 'LabelConnector/Make connector', "labelConnector.makeConnector()", 'F7' ) # also renames an existing connector
nuke.menu( 'Nuke' ).addCommand( 'LabelConnector/Connect connectors', "labelConnector.runLabelMatch()", 'F8' ) # standard run to match labels, connect nodes, or make new connections
nuke.menu( 'Nuke' ).addCommand( 'LabelConnector/Force Connect connectors', "labelConnector.runLabelMatch(forceShowUi = True)", 'ctrl+F8' ) # force show UI to make new connection when a single Node is selected