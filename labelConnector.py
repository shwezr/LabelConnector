# labelConnector v1.0
# Lukas Schwabe & Johannes Hezer
# UI based on ChannelHotbox - Falk Hofmann

import logging
import math

import nuke
import PySide2.QtCore as QtCore
import PySide2.QtGui as QtGui
import PySide2.QtWidgets as QtGuiWidgets

LOG = logging.getLogger("labelMatcher")

BUTTON = "border-radius: 8px; font: 13px;"
BUTTON_REGULAR_COLOR = 673720575
BUTTON_HIGHLIGHT_COLOR = 3261606143

CONNECTOR_KEY = "Connector"
CONNECTED_KEY = "Connected"

UNDO = nuke.Undo()
UNDO_EVENT_TEXT = "Label Connector"

# Node classes for NoOps instead of PostageStamps
threeD_deep_nodes = ["DeepColorCorrect",
                     "DeepColorCorrect2",
                     "DeepCrop",
                     "DeepExpression",
                     "DeepFromFrames",
                     "DeepFromImage",
                     "DeepMerge",
                     "DeepRead",
                     "DeepRecolor",
                     "DeepReformat",
                     "DeepTransform",
                     "DeepWrite",
                     "ApplyMaterial"
                     "Axis2",
                     "Axis3",
                     "Card2",
                     "Camera",
                     "Camera2",
                     "Camera3",
                     "Cube",
                     "Cylinder",
                     "EditGeo",
                     "DisplaceGeo",
                     "Light",
                     "Light2",
                     "Light3",
                     "DirectLight",
                     "Spotlight",
                     "Environment",
                     "MergeGeo",
                     "Normals",
                     "Project3D",
                     "Project3D2",
                     "ReadGeo",
                     "Scene",
                     "Sphere",
                     "TransformGeo",
                     "WriteGeo"]

# ignore these classes to determine 2D or 3D tree
ignore_nodes = ["Dot",
                "NoOp",
                "TimeOffset",
                "TimeWarp",
                "Retime",
                "FrameHold"]


class ConnectorButton(QtGuiWidgets.QPushButton):
    """Custom QPushButton to change colors when hovering above."""

    def __init__(self, dot, node, button_width, parent=None):
        super(ConnectorButton, self).__init__(parent)
        self.setMouseTracking(True)
        self.setText(dot.knob('label').getValue())
        self.dot = dot
        self.node = node

        self.setMinimumWidth(button_width / 2)
        self.setSizePolicy(QtGuiWidgets.QSizePolicy.Preferred,
                           QtGuiWidgets.QSizePolicy.Expanding)
        self.color = rgb2hex(interface2rgb(getTileColor(dot)))
        self.highlight = rgb2hex(interface2rgb(BUTTON_HIGHLIGHT_COLOR))
        self.setStyleSheet("background-color:"+self.color + ";" + BUTTON)

    def enterEvent(self, event):
        """Change color to orange when mouse enters button."""
        self.setStyleSheet("background-color:"+self.highlight + ";" + BUTTON)

    def leaveEvent(self, event):
        """Change color to grey when mouse leaves button."""
        self.setStyleSheet("background-color:"+self.color + ";" + BUTTON)


class LineEdit(QtGuiWidgets.QLineEdit):
    """Custom QLineEdit with combined auto completion."""

    def __init__(self, parent, dots, node):
        super(LineEdit, self).__init__(parent)
        self.parent = parent
        self.node = node
        self.dots = dots
        self.setStyleSheet(BUTTON)

        dot_list = []
        for dot in dots:
            dot_list.append(dot.knob('label').getValue())

        self.setSizePolicy(QtGuiWidgets.QSizePolicy.Preferred,
                           QtGuiWidgets.QSizePolicy.Expanding)

        self.completer = QtGuiWidgets.QCompleter(dot_list, self)
        self.completer.setCaseSensitivity(
            QtCore.Qt.CaseSensitivity.CaseInsensitive)
        self.setCompleter(self.completer)
        self.completer.activated.connect(self.returnPressed)


class LabelConnector(QtGuiWidgets.QWidget):
    """User Interface class to provide buttons for each found ConnectorDot."""

    def __init__(self, node, dots):

        self.node = node

        super(LabelConnector, self).__init__()

        length = math.ceil(math.sqrt(len(dots) + 1))
        width, height = length * 200, length * 50
        self.setFixedSize(width, height)
        offset = QtCore.QPoint(width * 0.5, height * 0.5)
        self.move(QtGui.QCursor.pos() - offset)

        grid = QtGuiWidgets.QGridLayout()
        self.setLayout(grid)

        column_counter, row_counter = 0, 0
        button_width = width / length

        for dot in dots:
            button = ConnectorButton(dot, node, button_width)
            button.clicked.connect(self.clicked)
            grid.addWidget(button, row_counter, column_counter)

            if column_counter > length:
                row_counter += 1
                column_counter = 0

            else:
                column_counter += 1

        self.input = LineEdit(self, dots, node)
        grid.addWidget(self.input, row_counter, column_counter)
        self.input.returnPressed.connect(self.lineEnter)

        self.set_window_properties()

    def set_window_properties(self):
        """Set window falgs and focused widget."""

        self.setWindowFlags(QtCore.Qt.FramelessWindowHint |
                            QtCore.Qt.WindowStaysOnTopHint)

        self.setAttribute(QtCore.Qt.WA_TranslucentBackground)
        self.setAttribute(QtCore.Qt.WA_NoSystemBackground)

        # make sure the widgets closes when it loses focus
        self.installEventFilter(self)
        self.input.setFocus()

    def keyPressEvent(self, event):
        if event.key() == QtCore.Qt.Key_Escape:
            self.close()

    def clicked(self):
        UNDO.begin(UNDO_EVENT_TEXT)

        # create destination Node if none exists yet
        if not self.node:
            self.node = createConnectingNode(self.sender().dot)

        connectNodeToDot(self.node, self.sender().dot)

        UNDO.end()
        self.close()

    def lineEnter(self):
        UNDO.begin(UNDO_EVENT_TEXT)

        for dot in self.sender().dots:
            if self.input.text() == dot.knob('label').getValue():

                # create destination Node if none exists yet
                if not self.node:
                    self.node = createConnectingNode(dot)

                connectNodeToDot(self.node, dot)

                UNDO.end()
                self.close()
                break

        UNDO.end()

    def eventFilter(self, object, event):
        if event.type() in [QtCore.QEvent.WindowDeactivate, QtCore.QEvent.FocusOut]:
            self.close()
            return True
        return False


def isPreviousNodeDeepOrThreeD(node):
    """
    checks if the upstream Node is a 3D/deep or 3D type of node

    Args:
        node (node): Any nuke Node

    Returns:
        bool: True if the upstream node is 3D or Deep type
    """

    dependencies = node.dependencies(nuke.INPUTS | nuke.HIDDEN_INPUTS)

    if dependencies:
        previousNode = dependencies[0]

        if previousNode.Class() in ignore_nodes:
            return isPreviousNodeDeepOrThreeD(previousNode)
        elif previousNode.Class() in threeD_deep_nodes:
            return True

    return False


def createConnectingNode(dot):
    """
    Creates a to-be-connected Node based on 2D or 3D/Deep type node tree

    Args:
        dot (node): Nuke Dot Node

    Returns:
        node: New Node to be connected
    """

    nodeType = "PostageStamp"
    if isPreviousNodeDeepOrThreeD(dot):
        nodeType = "NoOp"

    node = nuke.createNode(nodeType, inpanel=False)

    node.knob('tile_color').setValue(rgb2interface((80, 80, 80)))
    node.setName(CONNECTED_KEY)

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
        if dot.name().startswith(CONNECTOR_KEY) and dot["label"].value():

            # check if ConnectorDot Label has already been used
            if not dot["label"].value() in compareList:
                connectorDots.append(dot)
                compareList.append(dot["label"].value())
            else:
                LOG.error("Double Label Entry found on Connector Dots, skipping dot: {} '{}' ".format(
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


def runLabelMatch(forceShowUi=False):
    """
    Entry function, determines if there are multiple nodes that shall be connected via label matching,
    or rather a single none-labeled or no node is selected so a new connection can be set up.

    Args:
        forceShowUi (bool, optional): Set true to force a new node connection on single and already labeled Node. Defaults to False.
    """
    uiCheck = False  # True if the ConnectorUI should be shown or not
    nodes = nuke.selectedNodes()
    connectorDots = getAllConnectorDots()

    if not forceShowUi:
        for node in nodes:
            if node["label"].value():  # only none labeled nodes show the UI
                if not node.name().startswith(CONNECTOR_KEY):
                    for dot in connectorDots:
                        if node["label"].value() == dot["label"].value():
                            # Label Match has been found, try to connect the two Nodes
                            uiCheck = False if connectNodeToDot(
                                node, dot) else True
                            break
                        else:
                            uiCheck = True
            else:
                uiCheck = True

    if len(nodes) > 1:
        # with more than one node, no new connections will be made, no UI shown.
        return

    global labelConnectorUi

    # if the label is empty or no match could be found and the selection is just one node
    if (uiCheck or forceShowUi) and nodes and connectorDots:
        if forceShowUi:
            node = nodes[0]
        labelConnectorUi = LabelConnector(node, connectorDots)
        labelConnectorUi.show()

    # this will run and create a new node context based
    if not nodes and connectorDots:
        node = ""
        labelConnectorUi = LabelConnector(node, connectorDots)
        labelConnectorUi.show()


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


def makeConnector():
    """
    Creates a new ConnectorDot (a Dot named "Connector..."), 
    or renames an existing selected one alongside all dependent nodes.
    """

    nodes = nuke.selectedNodes()

    if len(nodes) > 1:
        return

    UNDO.begin(UNDO_EVENT_TEXT)

    if nodes:
        node = nodes[0]
        if node.Class() == "Dot":
            if CONNECTOR_KEY in node.name():
                # rename existing ConnectorDot alongside dependent Nodes
                txtold = node['label'].getValue()
                txtnew = nuke.getInput('Rename Label', txtold)

                if txtnew:
                    txtnew = txtnew.upper()
                    node['label'].setValue(txtnew)
                    for x in node.dependent(nuke.INPUTS | nuke.HIDDEN_INPUTS, forceEvaluate=False):
                        if x['label'].getValue() == txtold:
                            x['label'].setValue(txtnew)

            else:
                # change existing Dot to ConnectorDot
                txt = nuke.getInput('Set label', 'new label')

                if txt:
                    setConnectorDot(node, txt)

        else:  # attach new ConnectorDot Node to any Node
            txt = nuke.getInput('Set label', 'new label')

            if txt:
                node = nuke.createNode("Dot", inpanel=False)
                setConnectorDot(node, txt)
                node.setYpos(node.ypos()+50)

    else:  # create new independent ConnectorDot
        txt = nuke.getInput('Set label', 'new label')

        if txt:
            node = nuke.createNode("Dot", inpanel=False)
            setConnectorDot(node, txt)

    UNDO.end()


def interface2rgb(hexValue, normalize=True):
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
