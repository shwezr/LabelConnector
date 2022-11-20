"""
labelConnector v1.5 - 11/2022
Lukas Schwabe & Johannes Hezer
UI based on ChannelHotbox - Falk Hofmann

Provides context-based UI helpers to setup and navigate Node Connections in Nuke.

Click:          Build connection / Choose option.
Shift-Click:    Jumps directly to Connector. 
Alt-Click:      Opens Connector Settings, same like having the parent selected.

"""

__version__ = 1.5

import nuke
import PySide2.QtCore as QtCore
import PySide2.QtGui as QtGui
import PySide2.QtWidgets as QtGuiWidgets
import logging
import math
import fnmatch
from enum import Enum

_log = logging.getLogger("Label Connector")

BUTTON = "border-radius: 5px; font: 13px; padding: 4px 7px;"
BUTTON_BORDERDEFAULT = "border: 1px solid #212121;"
BUTTON_BORDERHIGHLIGHT = "border: 1px solid #AAAAAA;"
BUTTON_REGULAR_COLOR = 673720575
BUTTON_REGULARDARK_COLOR = 471802623
BUTTON_HIGHLIGHT_COLOR = 3329297663

SEARCHFIELD = "border-radius: 5px; font: 13px; border: 1px solid #212121;"
RENAMEFIELD = "border-radius: 5px; font: 13px; border: 1px solid #212121;"

CONNECTOR_KEY = "Connector"
CONNECTED_KEY = "Connected"

UNDO = nuke.Undo()
UNDO_EVENT_TEXT = "Label Connector"

_usePostageStamps = True
_labelConnectorUI = ""


COLORLIST = {
    'Red': 1277436927,
    'Orange': 2017657087,
    'Yellow': 2154504703,
    'Green': 793519103,
    'Dark Green': 304619007,
    'Cyan': 592071935,
    'Blue': 556482559,
    'Dark Blue': 320482047,
    'Purple': 975388415,
    'Default': BUTTON_REGULAR_COLOR
}

# you can add more Classes that you don't want to create Connections on.
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
        self.label = dot.knob('label').getValue()
        self.dot = dot
        self.node = node
        self.entered = False
        self.color = rgb2hex(interface2rgb(getTileColor(dot)))
        self.highlight = rgb2hex(interface2rgb(BUTTON_HIGHLIGHT_COLOR))

        self.setTextDefault()
        self.setStyleDefault()

        self.setMinimumWidth(100)
        self.setMaximumWidth(250)
        self.setFixedHeight(65)
        self.setSizePolicy(QtGuiWidgets.QSizePolicy.Fixed, QtGuiWidgets.QSizePolicy.Expanding)

    def enterEvent(self, event):
        """Change name with modifiers when mouse enters button."""
        keyModifier = QtGuiWidgets.QApplication.keyboardModifiers()

        if keyModifier == QtCore.Qt.ShiftModifier:
            self.setTextJump()

        elif keyModifier == QtCore.Qt.AltModifier:
            self.setTextModify()

        self.entered = True

    def leaveEvent(self, event):
        """Change reset name when mouse leaves button."""
        self.setTextDefault()
        self.entered = False

    def setTextJump(self):
        self.setText("Jump to\n-\n" + self.label)

    def setTextModify(self):
        self.setText("Options...\n-\n" + self.label)

    def setTextDefault(self):
        self.setText(self.label)

    def setStyleHighlighted(self):
        self.setStyleSheet("QPushButton{background-color:" + self.color + ";" + BUTTON + BUTTON_BORDERHIGHLIGHT + "} " +
                           "QPushButton:hover{background-color:" + self.highlight + ";" + BUTTON + BUTTON_BORDERHIGHLIGHT + "}")

    def setStyleDefault(self):
        self.setStyleSheet("QPushButton{background-color:" + self.color + ";" + BUTTON + BUTTON_BORDERDEFAULT + "} " +
                           "QPushButton:hover{background-color:" + self.highlight + ";" + BUTTON + BUTTON_BORDERDEFAULT + "}")


class StandardButton(QtGuiWidgets.QPushButton):
    """Custom QPushButton to change colors when hovering above."""

    def __init__(self, parent, text, color=BUTTON_REGULAR_COLOR):
        super(StandardButton, self).__init__(parent)
        self.setMouseTracking(True)
        self.setText(text)

        self.setMinimumWidth(100)
        self.setMaximumWidth(150)
        self.setFixedHeight(65)
        self.setSizePolicy(QtGuiWidgets.QSizePolicy.Expanding, QtGuiWidgets.QSizePolicy.Fixed)

        self.interfaceColor = color

        self.color = rgb2hex(interface2rgb(color))
        self.highlight = rgb2hex(interface2rgb(BUTTON_HIGHLIGHT_COLOR))
        self.setStyleSheet("QPushButton{background-color:" + self.color + ";" + BUTTON + "} " +
                           "QPushButton:hover{background-color:" + self.highlight + ";" + BUTTON + "}")


class LineEditConnectSelection(QtGuiWidgets.QLineEdit):
    """Custom QLineEdit with combined auto completion."""

    def __init__(self, parent, dots, node):
        super(LineEditConnectSelection, self).__init__(parent)

        self.node = node
        self.dots = dots
        self.setStyleSheet(SEARCHFIELD)

        self.dotNameList = []
        for dot in dots:
            self.dotNameList.append(dot.knob('label').getValue())

        self.filteredDotNameList = []

        self.setFixedSize(150, 65)
        self.setSizePolicy(QtGuiWidgets.QSizePolicy.Fixed, QtGuiWidgets.QSizePolicy.Fixed)

        self.itemDelegate = QtGuiWidgets.QStyledItemDelegate(self)

        self.listWidget = QtGuiWidgets.QListView(parent)
        self.listWidget.hide()
        self.model = QtCore.QStringListModel(self.filteredDotNameList)
        self.listWidget.setModel(self.model)

        self.completer = QtGuiWidgets.QCompleter(self.filteredDotNameList, self)
        self.completer.setCompletionMode(QtGuiWidgets.QCompleter.UnfilteredPopupCompletion)

        self.completer.popup().setMouseTracking(True)
        self.completer.popup().setStyleSheet("QAbstractItemView:item:hover{background-color:#484848;}")
        self.completer.popup().setItemDelegate(self.itemDelegate)

        self.completer.popup().setMinimumHeight(65)
        self.completer.popup().setMinimumWidth(100)
        self.completer.popup().setMaximumWidth(150)
        self.completer.popup().setSizePolicy(QtGuiWidgets.QSizePolicy.Expanding, QtGuiWidgets.QSizePolicy.Expanding)

        self.setCompleter(self.completer)

    def updateCompleterList(self):
        self.completer.model().setStringList(self.filteredDotNameList)


class LineEditNaming(QtGuiWidgets.QLineEdit):
    """Custom QLineEdit with different style."""

    def __init__(self, parent):
        super(LineEditNaming, self).__init__(parent)
        self.parent = parent
        self.setFixedHeight(65)
        self.setMinimumWidth(200)
        self.setMaximumWidth(250)

        self.setStyleSheet(RENAMEFIELD)
        self.setSizePolicy(QtGuiWidgets.QSizePolicy.Expanding, QtGuiWidgets.QSizePolicy.Fixed)


class LabelConnector(QtGuiWidgets.QWidget):
    """Core LabelConnector UI."""

    def __init__(self, node=None, dots=None, selectedConnectors=None, uitype=UIType.UI_DEFAULT):
        super(LabelConnector, self).__init__()

        self.node = node
        self.selectedConnectors = selectedConnectors
        self.dots = dots
        self.uiType = uitype
        self.shiftPressed = False
        self.altPressed = False
        self.placed = False

        if uitype == UIType.UI_DEFAULT:
            self.buttons = list()

        grid = QtGuiWidgets.QGridLayout()
        self.setLayout(grid)

        column_counter, row_counter = 0, 0
        self.hasInputField = False

        if uitype == UIType.UI_CHILDRENONLY:
            button = StandardButton(self, "Jump to Parent")
            button.clicked.connect(self.clickedJump)
            grid.addWidget(button, row_counter, column_counter)

            column_counter += 1

            button = StandardButton(self, "Re-Connect to...")
            button.clicked.connect(self.forceConnect)
            grid.addWidget(button, row_counter, column_counter)

        elif uitype == UIType.UI_CONNECTORONLY:
            if len(selectedConnectors) == 1:

                button = StandardButton(self, "Rename...")
                button.clicked.connect(self.setupConnector)
                grid.addWidget(button, row_counter, column_counter)

                column_counter += 1

            button = StandardButton(self, "Colorize...")
            button.clicked.connect(self.selectColor)
            grid.addWidget(button, row_counter, column_counter)

            column_counter += 1

            button = StandardButton(self, "Select All Children")
            button.clicked.connect(self.selectChildren)
            grid.addWidget(button, row_counter, column_counter)

        elif uitype == UIType.UI_COLOR:
            length = int(len(COLORLIST) / 2) - 1

            for color in COLORLIST:
                button = StandardButton(self, color, COLORLIST[color])
                button.clicked.connect(self.setColor)
                grid.addWidget(button, row_counter, column_counter)

                column_counter += 1
                if column_counter > length:
                    row_counter += 1
                    column_counter = 0

            self.hasInputField = False

        elif uitype == UIType.UI_NAMING:
            self.input = LineEditNaming(self)

            self.textOld = ""
            if self.node:
                if isConnector(self.node):
                    self.textOld = node.knob('label').getValue()
                    self.input.setText(self.textOld)
                    self.input.selectAll()

            grid.addWidget(self.input)
            self.input.returnPressed.connect(self.lineEnter)
            self.hasInputField = True

        else:  # uitype == UIType.UI_DEFAULT
            lenGrid = len(dots)

            length = math.ceil(math.sqrt(lenGrid))

            for dot in dots:
                button = ConnectorButton(self, dot, node)
                button.clicked.connect(self.clicked)
                grid.addWidget(button, row_counter, column_counter)
                self.buttons.append(button)

                column_counter += 1
                if column_counter > length:
                    row_counter += 1
                    column_counter = 0

            if dots:
                self.input = LineEditConnectSelection(self, dots, node)
                grid.addWidget(self.input, 1, length + 2)

                self.input.textEdited.connect(self.updateSearchMatches)
                self.input.textChanged.connect(self.highlightButtonsMatchingResults)
                self.input.returnPressed.connect(self.lineEnter)
                self.input.completer.popup().pressed.connect(self.lineEnter)

                self.hasInputField = True
                grid.addWidget(self.input.completer.popup(), 2, length + 2,  max(1, grid.rowCount() - 2), 1)

                if grid.rowCount() < 4:  # makes the popup smaller on smaller grids
                    self.input.completer.popup().setMaximumHeight(65)
                    grid.setRowStretch(2, 1)

                grid.setColumnMinimumWidth(length + 1, 10)  # adds a little spacer

            # create Parent Button
            button = StandardButton(self, "Create New\nParent...", BUTTON_REGULARDARK_COLOR)
            button.clicked.connect(self.setupConnector)
            grid.addWidget(button, 0, length + 2)

        self.setSizePolicy(QtGuiWidgets.QSizePolicy.Expanding, QtGuiWidgets.QSizePolicy.Expanding)

        self.setWindowFlags(QtCore.Qt.FramelessWindowHint | QtCore.Qt.WindowStaysOnTopHint)
        self.setAttribute(QtCore.Qt.WA_NoSystemBackground)
        self.setAttribute(QtCore.Qt.WA_TranslucentBackground)

        self.installEventFilter(self)

        if self.hasInputField:
            self.input.setFocus()

    def resizeEvent(self, event):
        super(LabelConnector, self).resizeEvent(event)

        if not self.placed:  # set position only once in the beginning

            geo = self.frameGeometry()
            centerTo = QtGui.QCursor.pos()

            if self.uiType == UIType.UI_DEFAULT:  # slight offset here feels better
                centerTo -= QtCore.QPoint(-int(geo.width()*0.05), int(geo.height()*0.2))

            geo.moveCenter(centerTo)
            self.move(geo.topLeft())

            self.placed = True

    def updateSearchMatches(self):
        """
        Searches for matches, filling the list for the completer as well as the highlighting. 
        This won't update when stepping through the completer list via up/down arrow keys.
        """

        inputText = self.input.text().upper()

        self.input.filteredDotNameList = []
        self.highlightButtons = []

        if inputText:

            query = '*' + '*'.join([inputText[j:j+1] for j in range(len(inputText))]) + '*'

            tempListUnsorted = []

            for button in self.buttons:
                if fnmatch.fnmatch(button.text(), query):
                    self.highlightButtons.append(button)
                    tempListUnsorted.append(button.text())

            for n in list(tempListUnsorted):
                if n.startswith(inputText):
                    self.input.filteredDotNameList.append(n)
                    tempListUnsorted.remove(n)

            for n in list(tempListUnsorted):
                if inputText in n:
                    self.input.filteredDotNameList.append(n)
                    tempListUnsorted.remove(n)

            self.input.filteredDotNameList.extend(tempListUnsorted)

        self.input.updateCompleterList()

    def highlightButtonsMatchingResults(self):
        """Highlights all Buttons matching the search result. Except there is a perfect match, then just this one."""

        inputText = self.input.text().upper()

        for button in self.buttons:
            button.setStyleDefault()

        if inputText:
            for button in self.highlightButtons:
                if inputText == button.text():
                    button.setStyleHighlighted()
                    return

            for button in self.highlightButtons:
                button.setStyleHighlighted()

    def keyPressEvent(self, event):
        """Catch key strokes, also to update highlighting of buttons."""
        if event.key() == QtCore.Qt.Key_Escape:
            self.close()
            return

        elif event.key() == QtCore.Qt.Key_Tab:
            self.lineEnter()
            return

        if self.uiType == UIType.UI_DEFAULT:
            if event.key() == QtCore.Qt.Key_Control:
                self.setupConnector()
                return

            elif event.key() == QtCore.Qt.Key_Shift:
                self.shiftPressed = True

            elif event.key() == QtCore.Qt.Key_Alt:
                self.altPressed = True

            elif event.key() in [QtCore.Qt.Key_Up, QtCore.Qt.Key_Down]:
                self.input.completer.popup().keyPressEvent(event)

            # handle GUI changes for modifier keys
            if event.key() == QtCore.Qt.Key_Shift and not self.altPressed:
                for button in self.buttons:
                    if button.entered:
                        button.setTextJump()
                        break

            elif event.key() == QtCore.Qt.Key_Alt and not self.shiftPressed:
                for button in self.buttons:
                    if button.entered:
                        button.setTextModify()
                        break

            elif event.key() in [QtCore.Qt.Key_Alt, QtCore.Qt.Key_Shift]:
                for button in self.buttons:
                    button.setTextDefault()

    def keyReleaseEvent(self, event):
        """Catch key strokes, also to update highlighting of buttons."""

        if self.uiType == UIType.UI_DEFAULT:
            if event.key() == QtCore.Qt.Key_Shift:
                self.shiftPressed = False

            elif event.key() == QtCore.Qt.Key_Alt:
                self.altPressed = False

            # handle GUI changes for modifier keys
            if event.key() == QtCore.Qt.Key_Shift and self.altPressed:
                for button in self.buttons:
                    if button.entered:
                        button.setTextModify()
                        break

            elif event.key() == QtCore.Qt.Key_Alt and self.shiftPressed:
                for button in self.buttons:
                    if button.entered:
                        button.setTextJump()
                        break

            elif event.key() in [QtCore.Qt.Key_Alt, QtCore.Qt.Key_Shift]:
                for button in self.buttons:
                    button.setTextDefault()

    def clicked(self):
        """Clicking actions based on pressed Modifier Keys"""
        keyModifier = QtGuiWidgets.QApplication.keyboardModifiers()

        if keyModifier == QtCore.Qt.ShiftModifier:
            jumpKeepingPreviousSelection(self.sender().dot)
            self.close()

        elif keyModifier == QtCore.Qt.AltModifier:
            _showConnectorUI(self.sender().dot)

        else:
            UNDO.begin(UNDO_EVENT_TEXT)
            if self.node:
                createConnectingNodeAndConnect(self.sender().dot, self.node)
            else:
                createConnectingNodeAndConnect(self.sender().dot)

            UNDO.end()

        self.close()

    def clickedJump(self):
        """Click on Jump To Parent"""
        jumpKeepingPreviousSelection(self.node.input(0))
        self.close()

    def forceConnect(self):
        """Click on Re-Connect"""
        self.close()
        _forceShowUI(self.node, self.dots)

    def setColor(self):
        """Click on Color Button"""
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
        """Click on create or rename Parent"""
        self.close()
        _showNamingUI(self.node)

    def selectColor(self):
        """Click on Color Menu"""
        self.close()
        _showColorSelectionUI(self.selectedConnectors)

    def selectChildren(self):
        """Click on Show all Connections"""
        for i in nuke.selectedNodes():
            i.setSelected(False)

        for node in self.selectedConnectors:
            for x in node.dependent(nuke.INPUTS | nuke.HIDDEN_INPUTS, forceEvaluate=False):
                x.setSelected(True)

        self.close()

    def lineEnter(self):
        """After pressing Enter or Tab"""
        if not self.hasInputField:
            return

        if self.uiType == UIType.UI_NAMING:
            if self.input.text():
                makeConnector(self.node, self.input.text(), self.textOld)

        else:  # uitype == UIType.UI_NAMING
            if self.input.text() == '':
                self.close()
                return

            connectDot = ''

            for dot in self.dots:
                if self.input.text().upper() == dot.knob('label').getValue().upper():
                    connectDot = dot
                    break

            if not connectDot:
                for dot in self.dots:
                    if self.input.filteredDotNameList[0] == dot.knob('label').getValue().upper():
                        connectDot = dot
                        break

            if connectDot:
                keyModifier = QtGuiWidgets.QApplication.keyboardModifiers()

                if keyModifier == QtCore.Qt.ShiftModifier:
                    jumpKeepingPreviousSelection(connectDot)

                else:
                    UNDO.begin(UNDO_EVENT_TEXT)
                    # create destination Node if none exists yet
                    if self.node:
                        createConnectingNodeAndConnect(connectDot, self.node)
                    else:
                        createConnectingNodeAndConnect(connectDot)
                    UNDO.end()

        self.close()

    def eventFilter(self, object, event):
        if object == self and event.type() in [QtCore.QEvent.WindowDeactivate, QtCore.QEvent.FocusOut]:
            self.close()
            return True

        return False

    def focusNextPrevChild(self, next):
        """overriding this, to be able to use TAB as ENTER, like the Nuke Node Menu"""
        return False


def createConnectingNodeAndConnect(dot, node=None):
    """
    Creates a to-be-connected Node based on 2D or 3D/Deep type node tree

    Args:
        dot (node): Nuke Dot Node
        node (node): Optional Nuke Node, to prepend the created node

    Returns:
        node: New Node to be connected
    """

    UNDO.begin(UNDO_EVENT_TEXT)

    nodeClass = "PostageStamp"

    global _usePostageStamps
    if not _usePostageStamps:
        nodeClass = "NoOp"

    connectingNode = None
    connectorGiven = False

    if node:
        if isConnectingNode(node):
            connectingNode = node
            connectorGiven = True

    if not connectingNode:
        for n in nuke.selectedNodes():
            n.setSelected(False)
        connectingNode = nuke.createNode(nodeClass, inpanel=False)

    connectSuccess = connectNodeToDot(connectingNode, dot)

    if not connectSuccess and _usePostageStamps and not connectorGiven:
        xpos, ypos = connectingNode.xpos(), connectingNode.ypos()
        nuke.delete(connectingNode)
        for n in nuke.selectedNodes():
            n.setSelected(False)
        connectingNode = nuke.createNode("NoOp", inpanel=False)
        connectingNode.setXYpos(xpos, ypos)
        connectNodeToDot(connectingNode, dot)

    elif not connectSuccess and _usePostageStamps and connectorGiven:
        UNDO.end()
        return

    if node and not connectorGiven:
        connectingNode.setXpos(
            (node.xpos() + int(node.screenWidth()/2)) - int(connectingNode.screenWidth()/2))
        if connectingNode.Class() == "NoOp":
            offset = 50
        else:
            offset = 100
        connectingNode.setYpos(node.ypos() - offset)

        if not node.setInput(0, connectingNode):
            nuke.delete(connectingNode)
            UNDO.end()
            return

    connectingNode.setName(CONNECTED_KEY)
    connectingNode.knob('label').setValue(dot['label'].getValue())
    connectingNode.knob('tile_color').setValue(rgb2interface((80, 80, 80)))
    connectingNode.knob("hide_input").setValue(True)

    UNDO.end()


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
        UNDO.end()
        return True
    UNDO.end()
    return False


def jumpKeepingPreviousSelection(node):
    """
    Jump to node without destroyng previous selection of nodes

    Args:
        node (node): any nuke node
    """

    prevNodes = nuke.selectedNodes()

    for i in prevNodes:
        i.setSelected(False)

    node.setSelected(True)
    nuke.zoomToFitSelected()
    node.setSelected(False)

    for i in prevNodes:
        i.setSelected(True)


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
                _log.error("Double Label Entry found on Connector Dots, skipping dot: {} '{}' ".format(
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


def isConnectingAndConnectedCorrectly(node):
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


def _forceShowUI(node, dots):
    """
    force to show UI despite there is already a label in the node.
    Used to override existing connections.
    """

    global _labelConnectorUI

    _labelConnectorUI = LabelConnector(node, dots)
    _labelConnectorUI.show()


def _showColorSelectionUI(selectedConnectors):
    """
    force to show UI with color options
    """

    global _labelConnectorUI

    _labelConnectorUI = LabelConnector(
        selectedConnectors[0], selectedConnectors=selectedConnectors, uitype=UIType.UI_COLOR)
    _labelConnectorUI.show()


def _showNamingUI(node):
    """
    force to show UI with color options
    """

    global _labelConnectorUI

    _labelConnectorUI = LabelConnector(node, uitype=UIType.UI_NAMING)
    _labelConnectorUI.show()


def _showConnectorUI(node):
    """
    force to show UI with color options
    """

    global _labelConnectorUI

    _labelConnectorUI = LabelConnector(node, selectedConnectors=[
                                       node], uitype=UIType.UI_CONNECTORONLY)
    _labelConnectorUI.show()


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
    text = text.strip(" ").upper()

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
    Entry function. Determines, which UI to open based on context.
    """

    if useNoOpNodesOnly:
        global _usePostageStamps
        _usePostageStamps = False

    connectedSth = False
    onlyConnectorDotsSelected = True
    nodes = nuke.selectedNodes()
    connectorDots = getAllConnectorDots()

    for node in nodes:
        if not isConnector(node):
            onlyConnectorDotsSelected = False
            if node["label"].value() and not isConnectingAndConnectedCorrectly(node):
                for dot in connectorDots:
                    if node["label"].value() == dot["label"].value():
                        # Label Match has been found, try to connect the two Nodes
                        if connectNodeToDot(node, dot):
                            connectedSth = True
                        break

    if (len(nodes) > 1 or connectedSth) and not onlyConnectorDotsSelected:
        # with more than one node or when connections were made, no new Dots will be set up thus no UI shown.
        # except we have one or mulitple parents
        return

    global _labelConnectorUI

    if nodes:

        node = nodes[0]

        if onlyConnectorDotsSelected:
            _labelConnectorUI = LabelConnector(
                node, selectedConnectors=nodes, uitype=UIType.UI_CONNECTORONLY)
            _labelConnectorUI.show()
            return

        if isConnectingAndConnectedCorrectly(node):
            _labelConnectorUI = LabelConnector(
                node, connectorDots, uitype=UIType.UI_CHILDRENONLY)
            _labelConnectorUI.show()
            return

        if not hasPossibleInputs(node):
            _labelConnectorUI = LabelConnector(node, uitype=UIType.UI_NAMING)
            _labelConnectorUI.show()
            return

        # will create  a prepending connector
        _labelConnectorUI = LabelConnector(node, connectorDots)
        _labelConnectorUI.show()
        return

    # will create a standalone connector
    _labelConnectorUI = LabelConnector(dots=connectorDots)
    _labelConnectorUI.show()
    return
