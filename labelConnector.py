# labelConnector v1.4
# Lukas Schwabe & Johannes Hezer
# UI based on ChannelHotbox - Falk Hofmann


import nuke
import PySide2.QtCore as QtCore
import PySide2.QtGui as QtGui
import PySide2.QtWidgets as QtGuiWidgets
import logging
import math
from enum import Enum

LOGGER = logging.getLogger("labelMatcher")

BUTTON = "border-radius: 8px; font: 13px;"
BUTTON_REGULAR_COLOR = 673720575
BUTTON_REGULARDARK_COLOR = 471802623
BUTTON_HIGHLIGHT_COLOR = 3261606143

SEARCHFIELD = "border-radius: 8px; font: 13px; border: 1px solid #212121;"
RENAMEFIELD = "border-radius: 3px; font: 13px; border: 1px solid #212121;"

CONNECTOR_KEY = "Connector"
CONNECTED_KEY = "Connected"

UNDO = nuke.Undo()
UNDO_EVENT_TEXT = "Label Connector"

USE_POSTAGESTAMPS = True
LABELCONNECTORUI = ""

COLORLIST = {
    'Red': 1277436927,
    'Orange': 2202599679,
    'Yellow': 2154504703,
    'Green': 793519103,
    'Dark Green': 304619007,
    'Cyan': 592071935,
    'Blue': 556482559,
    'Dark Blue': 320482047,
    'Purple': 975388415,
    'Default': BUTTON_REGULAR_COLOR
}

# you can add more Classes, that you don't want to connect. 
# Classes with no Inputs like Reads, Backdrops,... will already be ignored
IGNORECLASSES = ["Viewer"]


class UIType(Enum):
    UI_DEFAULT = 1
    UI_CONNECTORONLY = 2
    UI_CHILDRENONLY = 3
    UI_COLOR = 4
    UI_NAMING = 5


class ConnectorButton(QtGuiWidgets.QPushButton):
    """Custom QPushButton to change colors when hovering above."""

    def __init__(self, parent, dot, node):
        super(ConnectorButton, self).__init__(parent)
        self.setMouseTracking(True)
        self.setText(dot.knob('label').getValue())
        self.dot = dot
        self.node = node

        self.setMinimumWidth(100)
        self.setSizePolicy(QtGuiWidgets.QSizePolicy.Preferred,
                           QtGuiWidgets.QSizePolicy.Expanding)
        self.color = rgb2hex(interface2rgb(getTileColor(dot)))
        self.highlight = rgb2hex(interface2rgb(BUTTON_HIGHLIGHT_COLOR))
        self.setStyleSheet("background-color:" + self.color + ";" + BUTTON)

    def enterEvent(self, event):
        """Change color to orange when mouse enters button."""
        self.setStyleSheet("background-color:" + self.highlight + ";" + BUTTON)

    def leaveEvent(self, event):
        """Change color to grey when mouse leaves button."""
        self.setStyleSheet("background-color:" + self.color + ";" + BUTTON)


class StandardButton(QtGuiWidgets.QPushButton):
    """Custom QPushButton to change colors when hovering above."""

    def __init__(self, parent, text, color=BUTTON_REGULAR_COLOR):
        super(StandardButton, self).__init__(parent)
        self.setMouseTracking(True)
        self.setText(text)

        self.setMinimumWidth(100)

        self.setSizePolicy(QtGuiWidgets.QSizePolicy.Preferred,
                           QtGuiWidgets.QSizePolicy.Expanding)

        self.interfaceColor = color

        self.color = rgb2hex(interface2rgb(color))
        self.highlight = rgb2hex(interface2rgb(BUTTON_HIGHLIGHT_COLOR))
        self.setStyleSheet("background-color:"+self.color + ";"
                           + BUTTON
                           #    + "font-style: italic;"
                           )

    def enterEvent(self, event):
        """Change color to orange when mouse enters button."""
        self.setStyleSheet("background-color:"+self.highlight + ";"
                           + BUTTON
                           #    + "font-style: italic;"
                           )

    def leaveEvent(self, event):
        """Change color to  grey when mouse leaves button."""
        self.setStyleSheet("background-color:"+self.color + ";"
                           + BUTTON
                           #    + "font-style: italic;"
                           )

# for later use, to overwrite autocompletion, nuke style,maybe
# class Completer(QtGuiWidgets.QCompleter):
#     """Custom QLineEdit with combined auto completion."""

#     def __init__(self, dot_list, parent):
#         super(Completer, self).__init__(dot_list, parent)


class LineEditConnectSelection(QtGuiWidgets.QLineEdit):
    """Custom QLineEdit with combined auto completion."""

    def __init__(self, parent, dots, node):
        super(LineEditConnectSelection, self).__init__(parent)
        # self.parent = parent
        self.node = node
        self.dots = dots
        self.setStyleSheet(SEARCHFIELD)

        dot_list = []
        for dot in dots:
            dot_list.append(dot.knob('label').getValue())

        self.setMinimumWidth(100)

        self.setSizePolicy(QtGuiWidgets.QSizePolicy.Preferred,
                           QtGuiWidgets.QSizePolicy.Expanding)

        self.completer = QtGuiWidgets.QCompleter(dot_list, self)
        self.completer.setCaseSensitivity(
            QtCore.Qt.CaseSensitivity.CaseInsensitive)
        self.completer.setFilterMode(QtCore.Qt.MatchFlag.MatchContains)
        # self.completer.setModelSorting(QtGuiWidgets.QCompleter.CaseInsensitivelySortedModel)

        self.setCompleter(self.completer)

    def keyPressEvent(self, event):
        """bounce back event to main ui to catch and overwrite TAB behaviour"""

        super(LineEditConnectSelection, self).keyPressEvent(event)
        self.parent().keyPressEvent(event)


class LineEditNaming(QtGuiWidgets.QLineEdit):
    """Custom QLineEdit with different style."""

    def __init__(self, parent):
        super(LineEditNaming, self).__init__(parent)
        self.parent = parent
        self.setStyleSheet(RENAMEFIELD)
        self.setSizePolicy(QtGuiWidgets.QSizePolicy.Preferred,
                           QtGuiWidgets.QSizePolicy.Expanding)


class LabelConnector(QtGuiWidgets.QWidget):
    """User Interface class to provide buttons for each found ConnectorDot."""

    def __init__(self, node=None, dots=None, selectedConnectors=None, uitype=UIType.UI_DEFAULT):

        self.node = node
        self.selectedConnectors = selectedConnectors
        self.dots = dots
        self.uiType = uitype

        super(LabelConnector, self).__init__()

        self.setSizePolicy(QtGuiWidgets.QSizePolicy.Preferred,
                           QtGuiWidgets.QSizePolicy.Expanding)

        grid = QtGuiWidgets.QGridLayout()
        self.setLayout(grid)

        column_counter, row_counter = 0, 0
        self.hasInputField = False

        if uitype == UIType.UI_CHILDRENONLY:
            width, height = 300, 100

            button = StandardButton(self, "Jump to Parent")
            button.clicked.connect(self.clickedJump)
            grid.addWidget(button, row_counter, column_counter)

            column_counter += 1

            button = StandardButton(self, "Re-Connect to...")
            button.clicked.connect(self.forceConnect)
            grid.addWidget(button, row_counter, column_counter)

        elif uitype == UIType.UI_CONNECTORONLY:

            if len(selectedConnectors) == 1:
                width, height = 450, 100

                button = StandardButton(self, "Rename...")
                button.clicked.connect(self.setupConnector)
                grid.addWidget(button, row_counter, column_counter)

                column_counter += 1

            else:
                width, height = 300, 100

            button = StandardButton(self, "Select All Children")
            button.clicked.connect(self.selectChildren)
            grid.addWidget(button, row_counter, column_counter)

            column_counter += 1

            button = StandardButton(self, "Colorize...")
            button.clicked.connect(self.selectColor)
            grid.addWidget(button, row_counter, column_counter)

        elif uitype == UIType.UI_COLOR:

            length = math.ceil(len(COLORLIST) / 2)
            width, height = length * 150, 150

            for color in COLORLIST:
                button = StandardButton(self, color, COLORLIST[color])
                button.clicked.connect(self.setColor)
                grid.addWidget(button, row_counter, column_counter)

                if column_counter + 1 >= length:
                    row_counter += 1
                    column_counter = 0

                else:
                    column_counter += 1

            self.hasInputField = False

        elif uitype == UIType.UI_NAMING:
            self.input = LineEditNaming(self)

            self.textOld = ""
            if self.node:
                self.textOld = node.knob('label').getValue()
                self.input.setText(self.textOld)
                self.input.selectAll()

            width, height = 200, 75
            self.setFixedHeight(height)
            self.setMinimumWidth(width)
            self.setSizePolicy(QtGuiWidgets.QSizePolicy.Preferred,
                               QtGuiWidgets.QSizePolicy.Preferred)

            grid.addWidget(self.input)

            self.input.returnPressed.connect(self.lineEnter)

            self.hasInputField = True

        else:

            lenGrid = len(dots) + 1

            if dots:
                lenGrid += 1

            length = math.ceil(math.sqrt(lenGrid))
            width, height = length * 150, length * 50

            for dot in dots:
                button = ConnectorButton(self, dot, node)
                button.clicked.connect(self.clicked)
                grid.addWidget(button, row_counter, column_counter)

                if column_counter > length:
                    row_counter += 1
                    column_counter = 0

                else:
                    column_counter += 1

            if dots:
                self.input = LineEditConnectSelection(self, dots, node)
                grid.addWidget(self.input, row_counter, column_counter)
                self.input.returnPressed.connect(self.lineEnter)
                self.input.completer.popup().clicked.connect(self.lineEnter)
                self.hasInputField = True

                if column_counter > length:
                    row_counter += 1
                    column_counter = 0

                else:
                    column_counter += 1

            button = StandardButton(
                self, "Create New\nParent...", BUTTON_REGULARDARK_COLOR)
            button.clicked.connect(self.setupConnector)
            grid.addWidget(button, row_counter, column_counter)

        self.setMinimumSize(width, height)

        offset = QtCore.QPoint(width/2, height / 2)
        self.move(QtGui.QCursor.pos() - offset)
        self.set_window_properties(self.hasInputField)

    def set_window_properties(self, setFocus=False):
        """Set window falgs and focused widget."""

        self.setWindowFlags(QtCore.Qt.FramelessWindowHint |
                            QtCore.Qt.WindowStaysOnTopHint)

        self.setAttribute(QtCore.Qt.WA_TranslucentBackground)
        self.setAttribute(QtCore.Qt.WA_NoSystemBackground)

        # make sure the widgets closes when it loses focus
        self.installEventFilter(self)

        if setFocus:
            self.input.setFocus()

    def keyPressEvent(self, event):
        if event.key() == QtCore.Qt.Key_Escape:
            self.close()
        if event.key() == QtCore.Qt.Key_Tab:
            self.lineEnter()

    def clicked(self):
        UNDO.begin(UNDO_EVENT_TEXT)

        # create destination Node if none exists yet
        if not self.node:
            self.node = createConnectingNodeAndConnect(self.sender().dot)
        else:
            connectNodeToDot(self.node, self.sender().dot)

        UNDO.end()
        self.close()

    def clickedJump(self):
        for i in nuke.selectedNodes():
            i.setSelected(False)
        self.node.input(0).setSelected(True)
        nuke.zoomToFitSelected()
        self.close()

    def forceConnect(self):
        self.close()
        forceShowUI(self.node, self.dots)

    def setColor(self):
        color = self.sender().interfaceColor

        if color == BUTTON_REGULAR_COLOR:
            color = nuke.defaultNodeColor('Dot')

        UNDO.begin(UNDO_EVENT_TEXT)

        if self.selectedConnectors:
            for node in self.selectedConnectors:
                node.knob('tile_color').setValue(color)
        else:
            self.node.knob('tile_color').setValue(color)

        UNDO.end()

        self.close()

    def setupConnector(self):
        self.close()
        showNamingUI(self.node)

    def selectColor(self):
        self.close()
        showColorSelectionUI(self.selectedConnectors)

    def selectChildren(self):
        for i in nuke.selectedNodes():
            i.setSelected(False)

        for node in self.selectedConnectors:
            for x in node.dependent(nuke.INPUTS | nuke.HIDDEN_INPUTS, forceEvaluate=False):
                x.setSelected(True)

        self.close()

    def lineEnter(self):
        if not self.hasInputField:
            return

        if self.uiType == UIType.UI_NAMING:
            if self.input.text():
                makeConnector(self.node, self.input.text(), self.textOld)

        # standard UI
        else:
            if self.input.text() == '':
                self.close()
                return

            for dot in self.dots:
                if self.input.text().upper() in dot.knob('label').getValue().upper():

                    UNDO.begin(UNDO_EVENT_TEXT)
                    # create destination Node if none exists yet
                    if not self.node:
                        createConnectingNodeAndConnect(dot)
                    else:
                        connectNodeToDot(self.node, dot)

                    UNDO.end()
                    break

        self.close()

    def eventFilter(self, object, event):
        if event.type() in [QtCore.QEvent.WindowDeactivate, QtCore.QEvent.FocusOut]:
            self.close()
            return True

        return False

    def focusNextPrevChild(self, next):
        """override, to be able to use TAB as ENTER, like the Nuke Node Menu"""
        return False


def createConnectingNodeAndConnect(dot):
    """
    Creates a to-be-connected Node based on 2D or 3D/Deep type node tree

    Args:
        dot (node): Nuke Dot Node

    Returns:
        node: New Node to be connected
    """

    nodeClass = "PostageStamp"

    if not USE_POSTAGESTAMPS:
        nodeClass = "NoOp"

    node = nuke.createNode(nodeClass, inpanel=False)
    node.setName(CONNECTED_KEY)

    if not connectNodeToDot(node, dot) and USE_POSTAGESTAMPS:
        nuke.delete(node)
        node = nuke.createNode("NoOp", inpanel=False)
        node.setName(CONNECTED_KEY)
        connectNodeToDot(node, dot)

    node.knob('tile_color').setValue(rgb2interface((80, 80, 80)))

    return node


def connectNodeToDot(node, dot):
    """
    Connects a connecting-Node to a ConnectorDot

    Args:
        node (node): any nuke node
        dot (node): ConnectorDot

    Returns:
        bool: True if new node connection was successful
    """

    if not isConnectingNode(node):
        if not hasPossibleInputs(node):
            return True

        UNDO.begin(UNDO_EVENT_TEXT)

        connectingNode = createConnectingNodeAndConnect(dot)

        if node.setInput(0, connectingNode):
            connectingNode.setXpos(node.xpos())
            if connectingNode.Class() == "NoOp":
                offset = 50
            else:
                offset = 100
            connectingNode.setYpos(node.ypos() - offset)

            UNDO.end()
            return True

        else:
            nuke.delete(connectingNode)

        UNDO.end()
        return False

    else:

        UNDO.begin(UNDO_EVENT_TEXT)

        if node.setInput(0, dot):
            node['label'].setValue(dot['label'].getValue())
            node["hide_input"].setValue(True)

            UNDO.end()
            return True

        UNDO.end()
        return False


def getAllConnectorDots():
    """
    get all ConnectorDots with a valid label, warn if there are double entries found.

    Returns:
        list: list containing all connectorDots
    """

    connectorDots = list()
    compareList = list()
    doubleEntries = False
    doubleEntriesList = list()

    for dot in nuke.allNodes("Dot"):
        if isConnector(dot) and dot["label"].value():

            # check if ConnectorDot Label has already been used
            if not dot["label"].value() in compareList:
                connectorDots.append(dot)
                compareList.append(dot["label"].value())
            else:
                LOGGER.error("Double Label Entry found on Connector Dots, skipping dot: {} '{}' ".format(
                    dot.name(), dot["label"].value()))
                doubleEntries = True
                doubleEntriesList.append(dot)

    if doubleEntries:
        message = 'Skipped following Connector Dots (Label already used): \n \n'
        for doubleDot in doubleEntriesList:
            message += "{} '{}' \n".format(doubleDot.name(),
                                           doubleDot["label"].value())
        nuke.message(message)

    connectorDots.sort(key=lambda dot: dot.knob('label').value())
    return connectorDots


def getAllConnectorDotsLabels():
    """
    returns a list with all currently used labels
    """
    connectorDotsLabels = list()

    for dot in nuke.allNodes("Dot"):
        if isConnector(dot) and dot["label"].value():
            connectorDotsLabels.append(dot["label"].value())

    return connectorDotsLabels


def isConnectorAndConnectedCorrectly(node):
    """
    returns if the node is connected to the correct parent.
    """
    if not node.input(0):
        return False
    return node.knob('label').getValue() == node.input(0).knob('label').getValue() and isConnectingNode(node)


def isConnector(node):
    return node.name().startswith(CONNECTOR_KEY)


def isConnectingNode(node):
    return node.name().startswith(CONNECTED_KEY)


def forceShowUI(node, dots):
    """
    force to show UI despite there is already a label in the node.
    Used to override existing connections.
    """

    global LABELCONNECTORUI

    LABELCONNECTORUI = LabelConnector(node, dots)
    LABELCONNECTORUI.show()


def showColorSelectionUI(selectedConnectors):
    """
    force to show UI with color options
    """

    global LABELCONNECTORUI

    LABELCONNECTORUI = LabelConnector(selectedConnectors[0],
                                      selectedConnectors=selectedConnectors, uitype=UIType.UI_COLOR)
    LABELCONNECTORUI.show()


def showNamingUI(node):
    """
    force to show UI with color options
    """

    global LABELCONNECTORUI

    LABELCONNECTORUI = LabelConnector(node, uitype=UIType.UI_NAMING)
    LABELCONNECTORUI.show()


def hasPossibleInputs(node):
    """
    workaround to find out if a node can have connections. Because the "inputs" are still there
    and could be forcefully connected to sth.
    Also ignore IGNORECLASSES.
    """
    return "hide_input" in node.knobs() and not node.Class() in IGNORECLASSES


def setConnectorDot(dot, txt):
    """
    sets defaults for connectorDots like font size and sets label.

    Args:
        dot (node): ConnectorDot
        txt (str): desired label text
    """
    dot.setName(CONNECTOR_KEY)
    dot.knob('note_font_size').setValue(22)
    dot.knob('label').setValue(txt.upper())


def makeConnector(node, text, textOld):
    """
    Creates a new ConnectorDot (a Dot named "Connector..."), 
    or renames an existing selected one alongside all dependent nodes.
    """
    text = text.upper()

    if text in getAllConnectorDotsLabels():
        nuke.message("Label already in use")
        return

    UNDO.begin(UNDO_EVENT_TEXT)

    if node:
        if node.Class() == "Dot":
            if isConnector(node):
                # rename existing ConnectorDot alongside dependent Nodes
                node['label'].setValue(text)
                for x in node.dependent(nuke.INPUTS | nuke.HIDDEN_INPUTS, forceEvaluate=False):
                    if x['label'].getValue() == textOld:
                        x['label'].setValue(text)

            else:

                setConnectorDot(node, text)

        else:  # attach new ConnectorDot Node to any Node
            node = nuke.createNode("Dot", inpanel=False)
            setConnectorDot(node, text)
            node.setYpos(node.ypos()+50)

    else:  # create new independent ConnectorDot
        node = nuke.createNode("Dot", inpanel=False)
        setConnectorDot(node, text)

    UNDO.end()


def interface2rgb(hexValue):
    """
    Convert a color stored as a 32 bit value as used by nuke for interface colors to normalized rgb values.

    Args:
        hexValue ([type]): [description]
        normalize (bool, optional): [description]. Defaults to True.

    Returns:
        [type]: [description]
    """
    return [(0xFF & hexValue >> i) / 255.0 for i in [24, 16, 8]]


def rgb2interface(rgb):
    """
    Convert a color stored as rgb values to a 32 bit value as used by nuke for interface colors.

    Args:
        rgb ([type]): [description]

    Returns:
        [type]: [description]
    """
    if len(rgb) == 3:
        rgb = rgb + (255,)

    return int('%02x%02x%02x%02x' % rgb, 16)


def getTileColor(node=None):
    """
    If a node has it's color set automatically, the 'tile_color' knob will return 0.
    If so, this function will scan through the preferences to find the correct color value.

    Args:
        node ([type], optional): [description]. Defaults to None.

    Returns:
        [type]: [description]
    """
    node = node or nuke.selectedNode()
    interfaceColor = node.knob('tile_color').value()

    if interfaceColor == 0 or interfaceColor == nuke.defaultNodeColor(node.Class()) or interfaceColor == 3435973632:
        interfaceColor = BUTTON_REGULAR_COLOR

    return interfaceColor


def rgb2hex(rgbaValues):
    """
    Convert a color stored as normalized rgb values to a hex.

    Args:
        rgbaValues ([type]): [description]

    Returns:
        [type]: [description]
    """
    if len(rgbaValues) < 3:
        return
    return '#%02x%02x%02x' % (int(rgbaValues[0]*255), int(rgbaValues[1]*255), int(rgbaValues[2]*255))


def hex2rgb(hexColor):
    """
    Convert a color stored as hex to rgb values.

    Args:
        hexColor ([type]): [description]

    Returns:
        [type]: [description]
    """
    hexColor = hexColor.lstrip('#')
    return tuple(int(hexColor[i:i+2], 16) for i in (0, 2, 4))


def labelConnector(useNoOpNodesOnly=True):
    """
    Entry function. Determines, which UI to open.
    """

    if useNoOpNodesOnly:
        global USE_POSTAGESTAMPS
        USE_POSTAGESTAMPS = False

    connectedSth = False
    onlyConnectorDotsSelected = True
    nodes = nuke.selectedNodes()
    connectorDots = getAllConnectorDots()

    for node in nodes:
        if not isConnector(node):
            onlyConnectorDotsSelected = False
            if node["label"].value() and not isConnectorAndConnectedCorrectly(node):
                for dot in connectorDots:
                    if node["label"].value() == dot["label"].value():
                        # Label Match has been found, try to connect the two Nodes
                        if connectNodeToDot(node, dot):
                            connectedSth = True
                        break

    if (len(nodes) > 1 or connectedSth) and not onlyConnectorDotsSelected:
        # with more than one node or when connections were made, no new Dots will be set up thus no UI shown.
        return

    global LABELCONNECTORUI

    if nodes:

        node = nodes[0]

        if not hasPossibleInputs(node):
            # clear list, so no possible connections are shown, as there are none possible
            connectorDots = []

        if isConnectorAndConnectedCorrectly(node):
            LABELCONNECTORUI = LabelConnector(
                node, connectorDots, uitype=UIType.UI_CHILDRENONLY)
            LABELCONNECTORUI.show()
            return

        if onlyConnectorDotsSelected:
            LABELCONNECTORUI = LabelConnector(node,
                                              selectedConnectors=nodes, uitype=UIType.UI_CONNECTORONLY)
            LABELCONNECTORUI.show()
            return

        # will create  a prepending connector
        LABELCONNECTORUI = LabelConnector(node, connectorDots)
        LABELCONNECTORUI.show()
        return

    # will create a standalone connector
    LABELCONNECTORUI = LabelConnector(dots=connectorDots)
    LABELCONNECTORUI.show()
    return
