"""
labelConnector v1.6 - 01/2025
Lukas Schwabe, Johannes Hezer
Big thanks also to Falk Hofmann

Provides context-based UI helpers to setup and navigate Node Connections in Nuke, namely "Connector" and "Connected".

UI SHORTCUTS

Click:          Create Connection
Ctrl-Click:     Jumps directly to Connector
Alt-Click:      Opens Connector Settings (same like having the parent selected while hitting the shortcut)
Right-Click:    Preview Connection

"""

__version__ = 1.6

import nuke

if nuke.NUKE_VERSION_MAJOR < 16:
    import PySide2.QtCore as QtCore
    import PySide2.QtGui as QtGui
    import PySide2.QtWidgets as QtGuiWidgets
else:
    import PySide6.QtCore as QtCore
    import PySide6.QtGui as QtGui
    import PySide6.QtWidgets as QtGuiWidgets

import logging
import math
import fnmatch
import textwrap


_log = logging.getLogger("Label Connector")

BUTTON = "border-radius: 5px; font: 13px; padding: 4px 7px;"
BUTTON_BORDER_DEFAULT = "border: 1px solid #212121;"
BUTTON_BORDER_HIGHLIGHT = "border: 1px solid #AAAAAA;"
BUTTON_BORDER_SELECTED = "border: 1px solid #C6710C;"
BUTTON_REGULAR_COLOR = 673720575
BUTTON_REGULARDARK_COLOR = 471802623
BUTTON_HIGHLIGHT_COLOR = 3329297663

CONNECTOR_DEFAULT_COLOR = 1347440895


SEARCHFIELD = "border-radius: 5px; font: 13px; border: 1px solid #212121;"
RENAMEFIELD = "border-radius: 5px; font: 13px; border: 1px solid #212121;"

CONNECTOR_KEY = "Connector"
CONNECTED_KEY = "Connected"

UNDO = nuke.Undo()
UNDO_EVENT_TEXT = "Label Connector"

BOLD_LABELS = True  # set typo of Connectors to Bold
COLORIZE_CONNECTED = True

MAX_CHARS_CONNECTOR_BUTTONS = 16  # linebreak after this amount of characters
CONNECTORMINIMUMWIDTH = 500  # UI minimun height in px


_usePostageStamps = False
_labelConnectorUI = None


COLOR_LIST = {
    "Red": 1277436927,
    "Orange": 2017657087,
    "Yellow": 2154504703,
    "Green": 793519103,
    "Dark Green": 304619007,
    "Cyan": 592071935,
    "Blue": 556482559,
    "Dark Blue": 320482047,
    "Purple": 975388415,
    "Default": BUTTON_REGULAR_COLOR,
}

# you can add more Classes that you don't want to create Connections on.
# Classes with no Inputs like Reads, Backdrops,... will already be ignored
IGNORECLASSES = ["Viewer"]


class UIType:
    UI_DEFAULT = 1
    UI_CONNECTORONLY = 2
    UI_CHILDRENONLY = 3
    UI_COLOR = 4
    UI_NAMING = 5


class ConnectorButton(QtGuiWidgets.QPushButton):
    """Custom QPushButton to change colors when hovering above."""

    rightClicked = QtCore.Signal()

    def __init__(self, parent, connector, node):
        super(ConnectorButton, self).__init__(parent)
        self.setMouseTracking(True)
        self.label = connector.knob("label").getValue()
        self.wrapped_label = "\n".join(textwrap.wrap(self.label, width=MAX_CHARS_CONNECTOR_BUTTONS))
        self.connector = connector
        self.node = node
        self.entered = False
        self.selected = False
        self.is_highlighted = False  # stores highlight state in case of being selected, to revert correctly

        self.color = rgb2hex(interface2rgb(getTileColor(connector)))
        self.highlight = rgb2hex(interface2rgb(BUTTON_HIGHLIGHT_COLOR))
        self.highlighted_style = f"QPushButton{{background-color:{self.color};{BUTTON}{BUTTON_BORDER_HIGHLIGHT}}} QPushButton:hover{{background-color:{self.highlight};{BUTTON}{BUTTON_BORDER_HIGHLIGHT}}}"
        self.default_style = f"QPushButton{{background-color:{self.color};{BUTTON}{BUTTON_BORDER_DEFAULT}}} QPushButton:hover{{background-color:{self.highlight};{BUTTON}{BUTTON_BORDER_DEFAULT}}}"
        self.selected_style = f"QPushButton{{background-color:{self.color};{BUTTON}{BUTTON_BORDER_SELECTED}}} QPushButton:hover{{background-color:{self.highlight};{BUTTON}{BUTTON_BORDER_SELECTED}}}"

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
            self.setTextSelect()

        elif keyModifier == QtCore.Qt.AltModifier:
            self.setTextModify()

        elif keyModifier == QtCore.Qt.ControlModifier:
            self.setTextJumpConnector()

        self.entered = True

    def leaveEvent(self, event):
        """Change reset name when mouse leaves button."""

        self.setTextDefault()
        self.entered = False

    def mousePressEvent(self, event):
        """Emits a signal when right clicked."""

        if event.button() == QtCore.Qt.RightButton:
            self.rightClicked.emit()
        super(ConnectorButton, self).mousePressEvent(event)

    # Texts for different states

    def setTextJumpConnector(self):
        self.setText("Jump to Connector\n-\n" + self.wrapped_label)

    def setTextModify(self):
        self.setText("Options...\n-\n" + self.wrapped_label)

    def setTextSelect(self):
        self.setText("Create multiple\n-\n" + self.wrapped_label)

    def setTextDefault(self):
        self.setText(self.wrapped_label)

    # Styles for different states

    def setStyleHighlighted(self):
        """In case of a search pattern match."""

        self.setStyleSheet(self.highlighted_style)
        self.is_highlighted = True

    def setStyleDefault(self):
        """Default style."""

        self.setStyleSheet(self.default_style)
        self.is_highlighted = False

    def setStyleSelected(self):
        """In case of being selected to create multiple stamps."""

        self.setStyleSheet(self.selected_style)


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
        self.setStyleSheet(f"QPushButton{{background-color:{self.color};{BUTTON}}} QPushButton:hover{{background-color:{self.highlight};{BUTTON}}}")


class ConnectorListModel(QtCore.QStringListModel):
    """Class to extend the QAbstractListModel to store the Connector full name in the model."""

    ConnectorRole = QtCore.Qt.UserRole + 1

    def __init__(self, data, parent=None):
        """Class to extend the QAbstractListModel to store the Connector node in the model.

        Args:
            data (dict): Dict containing {"name": "connector_title", "connector": "connector_name"}
            parent (QObject, optional): parent widget. Defaults to None.
        """
        super(ConnectorListModel, self).__init__(parent)
        self.setStringList(data)

    def setStringList(self, data):
        """Update the model with the data.

        Args:
            data (dict): Dict containing {"name": "connector_title", "connector": "connector_name"}
        """

        self._data = data

        connector_names = [d["name"] for d in data]
        super(ConnectorListModel, self).setStringList(connector_names)

    def data(self, index, role=QtCore.Qt.DisplayRole):
        """Extend the data method to return the Connector node.

        Args:
            index (PySide2.QtCore.QModelIndex): Index of requested data.
            role (int, optional): Requested data role. Defaults to QtCore.Qt.DisplayRole.

        Returns:
            Any
        """

        if not self._data:
            return super(ConnectorListModel, self).data(index, role)

        if role == self.ConnectorRole:
            return self._data[index.row()]["connector"]

        return super(ConnectorListModel, self).data(index, role)

    def roleNames(self):
        roles = super(ConnectorListModel, self).roleNames()
        roles[self.ConnectorRole] = b"connector"
        return roles


class ConnectorAbstractView(QtGuiWidgets.QListView):
    """Extend the QListView to emit a signal when the current index changes."""

    currentIndexChanged = QtCore.Signal()

    def currentChanged(self, current, previous):
        ret = super(ConnectorAbstractView, self).currentChanged(current, previous)
        self.currentIndexChanged.emit()
        return ret


class LineEditConnectSelection(QtGuiWidgets.QLineEdit):
    """Custom QLineEdit with combined auto completion."""

    def __init__(self, parent, dots, node):
        super(LineEditConnectSelection, self).__init__(parent)

        self.node = node
        self.dots = dots
        self.setStyleSheet(SEARCHFIELD)

        self.dotNameList = []
        for dot in dots:
            self.dotNameList.append(dot.knob("label").getValue())

        self.filteredDotNameList = []

        self.setFixedSize(150, 65)
        self.setSizePolicy(QtGuiWidgets.QSizePolicy.Fixed, QtGuiWidgets.QSizePolicy.Fixed)

        self.itemDelegate = QtGuiWidgets.QStyledItemDelegate(self)

        # self.listWidget = ConnectorAbstractView(parent)
        # self.listWidget.hide()
        # self.model = ConnectorListModel(self.filteredDotNameList)
        # self.listWidget.setModel(self.model)

        self.completer = QtGuiWidgets.QCompleter(self.filteredDotNameList, self)
        self.completer.setCompletionMode(QtGuiWidgets.QCompleter.UnfilteredPopupCompletion)

        self.completer.setPopup(ConnectorAbstractView())
        self.completer.setModel(ConnectorListModel(self.filteredDotNameList))

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

    def __init__(
        self,
        node=None,
        connectors=None,
        selectedConnectors=None,
        uitype=UIType.UI_DEFAULT,
        namingText="",
    ):
        super(LabelConnector, self).__init__()

        self.node = node
        self.selectedConnectors = selectedConnectors
        self.connectors = connectors
        self.uiType = uitype
        self.shiftPressed = False
        self.ctrlPressed = False
        self.altPressed = False
        self.centered_ui = False
        self.textOld = namingText

        try:  # we have to try this in case no viewer exists or no active input is used
            self.current_viewed_node = nuke.activeViewer().node().input(nuke.activeViewer().activeInput())
        except Exception:
            self.current_viewed_node = None

        try:
            self.active_viewer_input = nuke.activeViewer().activeInput()  # returns None if nothing is connected
        except Exception:
            # if there was no input, we set it to 1 (which equals to Num2 in Nuke, to avoid the first input)
            self.active_viewer_input = None

        if self.active_viewer_input is None:
            self.active_viewer_input = 1

        if uitype == UIType.UI_DEFAULT:
            self.buttons = list()
            self.clicked_connectors_list = list()

        # add a main widget in between to have transparent background

        self.main_widget = QtGuiWidgets.QWidget()
        self.main_widget.setObjectName("label_connector_widget")
        self.main_widget.setStyleSheet("QWidget#label_connector_widget{background-color: rgba(45, 45, 45, 0.9);}")

        self.main_layout = QtGuiWidgets.QVBoxLayout()
        self.main_layout.addWidget(self.main_widget)
        self.setLayout(self.main_layout)

        self.content_layout = QtGuiWidgets.QVBoxLayout()
        self.main_widget.setLayout(self.content_layout)

        button_grid = QtGuiWidgets.QGridLayout()
        self.content_layout.addLayout(button_grid)

        # populate the UI based on the UIType

        column_counter, row_counter = 0, 0
        self.hasInputField = False

        if uitype == UIType.UI_CHILDRENONLY:
            new_btn = StandardButton(self, "Jump to Parent")
            new_btn.clicked.connect(self.clickedJump)
            button_grid.addWidget(new_btn, row_counter, column_counter)

            column_counter += 1

            new_btn = StandardButton(self, "Re-Connect to...")
            new_btn.clicked.connect(self.forceConnect)
            button_grid.addWidget(new_btn, row_counter, column_counter)

        elif uitype == UIType.UI_CONNECTORONLY:
            len_selected_equals_one = len(selectedConnectors) == 1

            self.clicked_connectors_list = selectedConnectors

            new_btn = StandardButton(self, "create Connected")
            new_btn.clicked.connect(self.make_connectors_btn_clicked)
            new_btn.setSizePolicy(QtGuiWidgets.QSizePolicy.Expanding, QtGuiWidgets.QSizePolicy.Expanding)
            new_btn.setMaximumWidth(self.width())
            button_grid.addWidget(new_btn, row_counter, column_counter, 1, 2 + len_selected_equals_one)
            row_counter += 1

            if len_selected_equals_one:
                new_btn = StandardButton(self, "Rename...")
                new_btn.clicked.connect(self.setupConnector)
                button_grid.addWidget(new_btn, row_counter, column_counter)

                column_counter += 1

            new_btn = StandardButton(self, "Colorize...")
            new_btn.clicked.connect(self.selectColor)
            button_grid.addWidget(new_btn, row_counter, column_counter)

            column_counter += 1

            new_btn = StandardButton(self, "Select All Children")
            new_btn.clicked.connect(self.selectChildren)
            button_grid.addWidget(new_btn, row_counter, column_counter)

        elif uitype == UIType.UI_COLOR:
            length = int(len(COLOR_LIST) / 2) - 1

            for color in COLOR_LIST:
                new_btn = StandardButton(self, color, COLOR_LIST[color])
                new_btn.clicked.connect(self.setColor)
                button_grid.addWidget(new_btn, row_counter, column_counter)

                column_counter += 1
                if column_counter > length:
                    row_counter += 1
                    column_counter = 0

            self.hasInputField = False

        elif uitype == UIType.UI_NAMING:
            self.title = QtGuiWidgets.QLabel(self)

            if self.textOld:
                self.title.setText("Rename Connector")
            else:
                self.title.setText("Create New Connector")

            self.title.setStyleSheet("color: #AAAAAA; font: 13px; margin-top: 10px;")
            self.title.setAlignment(QtCore.Qt.AlignLeft)
            button_grid.addWidget(self.title, 0, 0)

            self.input = LineEditNaming(self)

            self.input.setText(self.textOld)
            self.input.selectAll()

            button_grid.addWidget(self.input, 1, 0)
            self.input.returnPressed.connect(self.lineEnter)
            self.hasInputField = True

        else:  # uitype == UIType.UI_DEFAULT
            lenGrid = len(connectors)

            length = math.ceil(math.sqrt(lenGrid))

            for dot in connectors:
                new_btn = ConnectorButton(self, dot, node)
                new_btn.clicked.connect(self.connector_button_left_clicked)
                new_btn.rightClicked.connect(self.connector_button_right_clicked)

                button_grid.addWidget(new_btn, row_counter, column_counter)
                self.buttons.append(new_btn)

                column_counter += 1
                if column_counter > length:
                    row_counter += 1
                    column_counter = 0

            if connectors:
                self.input = LineEditConnectSelection(self, connectors, node)
                button_grid.addWidget(self.input, 1, length + 2)

                self.input.textEdited.connect(self.updateSearchMatches)
                self.input.textChanged.connect(self.highlightButtonsMatchingResults)
                self.input.returnPressed.connect(self.lineEnter)
                self.input.completer.popup().pressed.connect(self.lineEnter)
                self.input.completer.popup().currentIndexChanged.connect(self.highlightButtonsMatchingResults)

                self.hasInputField = True
                button_grid.addWidget(
                    self.input.completer.popup(),
                    2,
                    length + 2,
                    max(1, button_grid.rowCount() - 2),
                    1,
                )

                if button_grid.rowCount() < 4:  # makes the popup smaller on smaller grids
                    self.input.completer.popup().setMaximumHeight(65)
                    button_grid.setRowStretch(2, 1)

                button_grid.setColumnMinimumWidth(length + 1, 10)  # adds a little spacer

            # create Parent Button
            new_btn = StandardButton(self, "Create New\nParent...", BUTTON_REGULARDARK_COLOR)
            new_btn.clicked.connect(self.setupConnector)
            button_grid.addWidget(new_btn, 0, length + 2)

            # explanation label at the bottom
            explanation_label = QtGuiWidgets.QLabel(self)
            explanation_label.setText("shift - multiple | alt - options | ctrl - jump to connector | right-click - preview")
            explanation_label.setStyleSheet("color: #AAAAAA; font: 10px; margin-top: 10px;")
            explanation_label.setWordWrap(True)
            explanation_label.setAlignment(QtCore.Qt.AlignCenter)

            self.content_layout.addWidget(explanation_label)

        self.setSizePolicy(QtGuiWidgets.QSizePolicy.Expanding, QtGuiWidgets.QSizePolicy.Expanding)

        self.setWindowFlags(QtCore.Qt.FramelessWindowHint | QtCore.Qt.WindowStaysOnTopHint)
        # self.setAttribute(QtCore.Qt.WA_NoSystemBackground)
        self.setAttribute(QtCore.Qt.WA_TranslucentBackground)

        self.installEventFilter(self)

        if self.hasInputField:
            self.input.setFocus()

    def resizeEvent(self, event):
        """Gui size is now known, so lets position it beneath the Mouse Cursor."""

        # the setMinimumHeight method seems to do weird stuff, so lest just do it manually

        if self.uiType == UIType.UI_DEFAULT:
            if event.size().width() < CONNECTORMINIMUMWIDTH:
                self.resize(CONNECTORMINIMUMWIDTH, event.size().height())

        super(LabelConnector, self).resizeEvent(event)

        if not self.centered_ui:  # set position only once in the beginning
            geo = self.frameGeometry()

            if self.uiType == UIType.UI_DEFAULT:
                centerTo = QtGui.QGuiApplication.screenAt(QtGui.QCursor.pos()).geometry().center()
            else:
                centerTo = QtGui.QCursor.pos()

            if self.uiType == UIType.UI_DEFAULT and self.connectors:  # slight offset here feels better
                centerTo -= QtCore.QPoint(-int(geo.width() * 0.05), int(geo.height() * 0.2))

            if self.uiType == UIType.UI_CONNECTORONLY:
                centerTo += QtCore.QPoint(0, int(geo.height() * 0.2))

            geo.moveCenter(centerTo)
            self.move(geo.topLeft())

            self.centered_ui = True

    def updateSearchMatches(self):
        """
        Searches for matches, filling the list for the completer as well as the highlighting.
        This won't update when stepping through the completer list via up/down arrow keys.
        """

        inputText = self.input.text().upper()

        self.input.filteredDotNameList = []
        self.highlightButtons = []

        if inputText:
            query = "*" + "*".join([inputText[j : j + 1] for j in range(len(inputText))]) + "*"

            tempListUnsorted = []

            for button in self.buttons:
                if fnmatch.fnmatch(button.text(), query):
                    self.highlightButtons.append(button)
                    if button.text() not in tempListUnsorted:
                        tempListUnsorted.append({"name": button.label, "connector": button.connector.name()})

            for n in list(tempListUnsorted):
                if n["name"].startswith(inputText):
                    self.input.filteredDotNameList.append(n)
                    tempListUnsorted.remove(n)

            for n in list(tempListUnsorted):
                if inputText in n["name"]:
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
            selected_entry = self.input.completer.popup().currentIndex()

            if selected_entry.row() != -1:
                connector_name = self.input.completer.model().data(selected_entry, QtCore.Qt.UserRole + 1)
            else:
                connector_name = ""

            for button in self.highlightButtons:
                if connector_name == button.connector.name() and button.label == inputText:
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
                self.ctrlPressed = True

            elif event.key() == QtCore.Qt.Key_Shift:
                self.shiftPressed = True

            elif event.key() == QtCore.Qt.Key_Alt:
                self.altPressed = True

            elif event.key() in [QtCore.Qt.Key_Up, QtCore.Qt.Key_Down]:
                self.input.completer.popup().keyPressEvent(event)

            # handle GUI changes for modifier keys
            if event.key() in [QtCore.Qt.Key_Alt, QtCore.Qt.Key_Shift, QtCore.Qt.Key_Control]:
                self.update_connector_button_text()

    def keyReleaseEvent(self, event):
        """Catch key strokes, also to update highlighting of buttons."""

        if self.uiType == UIType.UI_DEFAULT:
            if event.key() == QtCore.Qt.Key_Control:
                self.ctrlPressed = False

            elif event.key() == QtCore.Qt.Key_Shift:
                self.shiftPressed = False

                if self.clicked_connectors_list:
                    self.create_multiple_connectors()
                    self.close()

            elif event.key() == QtCore.Qt.Key_Alt:
                self.altPressed = False

            # handle GUI changes for modifier keys
            if event.key() in [QtCore.Qt.Key_Alt, QtCore.Qt.Key_Shift, QtCore.Qt.Key_Control]:
                self.update_connector_button_text()

    def update_connector_button_text(self):
        """Set connector button text based on pressed Modifier Keys."""

        if self.shiftPressed and not (self.altPressed or self.ctrlPressed):
            for button in self.buttons:
                if button.entered:
                    button.setTextSelect()
                    break

        elif self.altPressed and not (self.shiftPressed or self.ctrlPressed):
            for button in self.buttons:
                if button.entered:
                    button.setTextModify()
                    break

        elif self.ctrlPressed and not (self.shiftPressed or self.altPressed):
            for button in self.buttons:
                if button.entered:
                    button.setTextJumpConnector()
                    break

        else:
            for button in self.buttons:
                button.setTextDefault()

    def create_multiple_connectors(self):
        """Create multiple connectors based on selected buttons."""

        if not self.clicked_connectors_list:
            return
        UNDO.begin(UNDO_EVENT_TEXT)

        created_nodes = []
        for connector in self.clicked_connectors_list:
            n = createConnectingNodeAndConnect(connector)
            created_nodes.append(n)

        xPosFirst = created_nodes[0].xpos()
        yPosFirst = created_nodes[0].ypos()

        for i, node in enumerate(created_nodes):
            node.setXpos(xPosFirst + 120 * i)
            node.setYpos(yPosFirst)
            node.setSelected(True)

        self.clicked_connectors_list = []

        UNDO.end()

    QtCore.Slot()

    def make_connectors_btn_clicked(self):
        UNDO.begin(UNDO_EVENT_TEXT)

        for n in nuke.selectedNodes():
            n.setSelected(False)

        created_nodes = []

        for connector in self.clicked_connectors_list:
            n = createConnectingNodeAndConnect(connector)

            n.setXYpos(connector.xpos(), connector.ypos() + 100)

            created_nodes.append(n)

        for node in created_nodes:
            node.setSelected(True)

        self.clicked_connectors_list = []

        UNDO.end()

        self.close()

    QtCore.Slot()

    def connector_button_left_clicked(self):
        """Clicking actions based on pressed Modifier Keys"""

        keyModifier = QtGuiWidgets.QApplication.keyboardModifiers()

        if keyModifier == QtCore.Qt.ControlModifier:
            jumpKeepingPreviousSelection(self.sender().connector)

        elif keyModifier == QtCore.Qt.AltModifier:
            _showConnectorUI(self.sender().connector)
            self.close()

        elif keyModifier == QtCore.Qt.ShiftModifier:
            clicked_button = self.sender()
            if clicked_button not in self.clicked_connectors_list:
                self.clicked_connectors_list.append(clicked_button.connector)
                clicked_button.setStyleSelected()
            else:
                self.clicked_connectors_list.remove(clicked_button.connector)
                if clicked_button.is_highlighted:
                    clicked_button.setStyleHighlighted()
                else:
                    clicked_button.setStyleDefault()

        else:
            UNDO.begin(UNDO_EVENT_TEXT)
            createConnectingNodeAndConnect(self.sender().connector, self.node)
            UNDO.end()
            self.close()

    QtCore.Slot()

    def connector_button_right_clicked(self):
        """Set Viewer Input to the clicked Connector."""

        try:
            if nuke.activeViewer().node().input(self.active_viewer_input) == self.sender().connector:
                nuke.activeViewer().node().setInput(self.active_viewer_input, self.current_viewed_node)
            else:
                nuke.activeViewer().node().setInput(self.active_viewer_input, self.sender().connector)
                nuke.activeViewer().activateInput(self.active_viewer_input)

            self.changed_viewed_node = True

        except Exception as e:
            # nuke.tprint("Error setting Viewer Input: ", e)
            pass

    def clickedJump(self):
        """Click on Jump To Parent"""

        jumpKeepingPreviousSelection(self.node.input(0))
        self.close()

    def forceConnect(self):
        """Click on Re-Connect"""

        self.close()
        _forceShowUI(self.node, self.connectors)

    def setColor(self):
        """Click on Color Button"""

        color = self.sender().interfaceColor

        if color == BUTTON_REGULAR_COLOR:
            color = nuke.defaultNodeColor("Dot")

        UNDO.begin("Colorize Connector")

        if self.selectedConnectors:
            for node in self.selectedConnectors:
                node.knob("tile_color").setValue(color)

                if COLORIZE_CONNECTED:
                    color = node.knob("tile_color").value()
                    for x in node.dependent(nuke.INPUTS | nuke.HIDDEN_INPUTS, forceEvaluate=False):
                        if color not in [BUTTON_REGULAR_COLOR, 0]:
                            x.knob("tile_color").setValue(color)
                        else:
                            x.knob("tile_color").setValue(CONNECTOR_DEFAULT_COLOR)

        else:
            self.node.knob("tile_color").setValue(color)

            if COLORIZE_CONNECTED:
                color = self.node.knob("tile_color").value()
                for x in self.node.dependent(nuke.INPUTS | nuke.HIDDEN_INPUTS, forceEvaluate=False):
                    if color not in [BUTTON_REGULAR_COLOR, 0]:
                        x.knob("tile_color").setValue(color)
                    else:
                        x.knob("tile_color").setValue(CONNECTOR_DEFAULT_COLOR)

        UNDO.end()

        self.close()

    def setupConnector(self):
        """Click on create or rename Parent"""

        self.close()
        if self.uiType == UIType.UI_DEFAULT:
            if self.hasInputFieldAndText():
                makeConnector(self.node, self.input.text())

            else:
                _showNamingUI(self.node)

        elif self.uiType == UIType.UI_CONNECTORONLY:
            _showNamingUI(self.node, self.node.knob("label").getValue())

    def hasInputFieldAndText(self):
        """Returns bool if current UI has a textinput and some userinput is provided"""

        if self.hasInputField:
            if self.input.text().strip(" "):
                return True

        return False

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

        else:  # uitype == UIType.UI_DEFAULT
            if self.input.text() == "":
                self.close()
                return

            else:
                input_text = self.input.text().upper()

            selected_entry = self.input.completer.popup().currentIndex()
            connect_to = ""

            if selected_entry.row() != -1:
                connector_name = self.input.completer.model().data(selected_entry, QtCore.Qt.UserRole + 1)
                for connector in self.connectors:
                    if connector_name == connector.name():
                        connect_to = connector
                        break
            else:
                for connector in self.connectors:
                    if input_text == connector.knob("label").getValue().upper():
                        connect_to = connector
                        break

            if not connect_to and self.input.filteredDotNameList:
                name_list = [d["name"] for d in self.input.filteredDotNameList]
                for connector in self.connectors:
                    if name_list[0].upper() == connector.knob("label").getValue().upper():
                        connect_to = connector
                        break

            if connect_to:
                keyModifier = QtGuiWidgets.QApplication.keyboardModifiers()

                if keyModifier == QtCore.Qt.ControlModifier:
                    jumpKeepingPreviousSelection(connect_to)

                else:
                    UNDO.begin(UNDO_EVENT_TEXT)
                    createConnectingNodeAndConnect(connect_to, self.node)
                    UNDO.end()

        self.close()

    def mousePressEvent(self, event):
        """Close if there was a left click within the UIs geo, but no Button was triggered."""

        if event.button() == QtCore.Qt.LeftButton:
            if self.uiType == UIType.UI_DEFAULT:
                self.create_multiple_connectors()
            self.close()

    def eventFilter(self, object, event):
        if object == self and event.type() in [
            QtCore.QEvent.WindowDeactivate,
            QtCore.QEvent.FocusOut,
        ]:
            if self.uiType == UIType.UI_DEFAULT:
                self.create_multiple_connectors()

            self.close()
            return True

        return False

    def focusNextPrevChild(self, next):
        """overriding this, to be able to use TAB as ENTER, like the Nuke Node Menu"""

        return False

    def close(self):
        """Close the UI, reset the viewer to original state if it was altered."""

        try:
            # if viewer input was changed, we set it back to the original input
            if self.changed_viewed_node:
                nuke.activeViewer().node().setInput(self.active_viewer_input, self.current_viewed_node)
        except Exception:
            pass

        super(LabelConnector, self).close()


# def store_connector_name_on_node(node, connector):
#     """
#     Store the connector name on the node as a knob.

#     Args:
#         node (node): Nuke Node
#         connector (node): Connector Node
#     """

#     if not node.knob("connectorName"):
#         knob = nuke.String_Knob("connectorName", "Connector Name")
#         knob.setValue(connector.name())
#         knob.setVisible(False)
#         node.addKnob(knob)
#     else:
#         node.knob("connectorName").setValue(connector.name())


def addConnectingNodeButtons(connecting, connector):
    """
    Adds "jump to source" and "open source settings" buttons to a node.
    """

    if not connecting.knob("connected"):
        tab = nuke.Tab_Knob("connected", "Connected")
        connecting.addKnob(tab)

    if not connecting.knob("jumpToSource"):
        jump_button = nuke.PyScript_Knob("jumpToSource", "Jump to Source")
        jump_button.setCommand(
            "n = nuke.thisNode()\n"
            "input = n.input(0)\n"
            "\n"
            "if input:\n"
            "    prevNodes = nuke.selectedNodes()\n"
            "    for i in prevNodes:\n"
            "        i.setSelected(False)\n"
            "    input.setSelected(True)\n"
            "    nuke.zoomToFitSelected()\n"
            "    input.setSelected(False)\n"
            "    for i in prevNodes:\n"
            "        i.setSelected(True)\n"
        )
        connecting.addKnob(jump_button)

    if not connecting.knob("connectorName"):
        knob = nuke.String_Knob("connectorName", "Connector Name")
        knob.setValue(connector.name())
        knob.setVisible(False)
        connecting.addKnob(knob)
    else:
        connecting.knob("connectorName").setValue(connector.name())


def createConnectingNodeAndConnect(connector, node=None):
    """
    Creates a to-be-connected Node based on 2D or 3D/Deep type node tree

    Args:
        dot (node): Nuke Dot Node
        node (node): Optional Nuke Node, to prepend the created node

    Returns:
        node: New Node to be connected
    """

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

    connectSuccess = connectNodeToDot(connectingNode, connector)

    if not connectSuccess and _usePostageStamps and not connectorGiven:
        xpos, ypos = connectingNode.xpos(), connectingNode.ypos()
        nuke.delete(connectingNode)
        for n in nuke.selectedNodes():
            n.setSelected(False)
        connectingNode = nuke.createNode("NoOp", inpanel=False)
        connectingNode.setXYpos(xpos, ypos)
        connectNodeToDot(connectingNode, connector)

    elif not connectSuccess and _usePostageStamps and connectorGiven:
        return

    if node and not connectorGiven:
        connectingNode.setXpos((node.xpos() + int(node.screenWidth() / 2)) - int(connectingNode.screenWidth() / 2))
        if connectingNode.Class() == "NoOp":
            offset = 50
        else:
            offset = 100
        connectingNode.setYpos(node.ypos() - offset)

        if not node.setInput(0, connectingNode):
            nuke.delete(connectingNode)
            return

    connectingNode.setName(CONNECTED_KEY)
    connectingNode.knob("label").setValue(connector["label"].getValue())
    connectingNode.knob("tile_color").setValue(CONNECTOR_DEFAULT_COLOR)
    connectingNode.knob("hide_input").setValue(True)

    if COLORIZE_CONNECTED:
        color = connector.knob("tile_color").value()
        if color not in [BUTTON_REGULAR_COLOR, 0]:
            connectingNode.knob("tile_color").setValue(color)

    addConnectingNodeButtons(connectingNode, connector)

    return connectingNode


def connectNodeToDot(node, connector):
    """
    Connects a connecting-Node to a Connector

    Args:
        node (node): any nuke node
        dot (node): Connector

    Returns:
        bool: True if new node connection was successful
    """

    UNDO.begin(UNDO_EVENT_TEXT)
    if node.setInput(0, connector):
        if COLORIZE_CONNECTED:
            color = connector.knob("tile_color").value()
            if color not in [BUTTON_REGULAR_COLOR, 0]:
                node.knob("tile_color").setValue(color)
            else:
                node.knob("tile_color").setValue(CONNECTOR_DEFAULT_COLOR)

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

    prev_nodes = nuke.selectedNodes()

    for i in prev_nodes:
        i.setSelected(False)

    node.setSelected(True)
    nuke.zoomToFitSelected()
    node.setSelected(False)

    for i in prev_nodes:
        i.setSelected(True)


def getAllConnectors():
    """
    get all Connectors with a valid label, warn if there are double entries found.

    Returns:
        list: list containing all connectors
    """

    # filtered_connectors = list()
    # compare_list = list()
    # double_entries_bool = False
    # double_entries_list = list()

    # keep compatibility with older versions, so we also search for dots
    all_dots = [node for node in nuke.allNodes("Dot") if node["label"].value() and isConnector(node)]
    # all_postage_stamps = [
    #     node for node in nuke.allNodes("PostageStamp") if node.knob("disable").value() is False and node.knob("label").value() and isConnector(node)
    # ]

    all_noops = [node for node in nuke.allNodes("NoOp") if node["label"].value() and isConnector(node)]

    all_connectors = all_dots + all_noops

    # for connector in all_connectors:
    # check if ConnectorDot Label has already been used
    # if connector["label"].value() not in compare_list:
    # filtered_connectors.append(connector)
    # compare_list.append(connector["label"].value())
    # else:
    #     _log.error("Double Label Entry found on Connector Dots, skipping dot: {} '{}' ".format(connector.name(), connector["label"].value()))
    #     double_entries_bool = True
    #     double_entries_list.append(connector)

    # if double_entries_bool:
    #     message = "Skipped following Connector Dots (Label already used): \n \n"
    #     for doubleDot in double_entries_list:
    #         message += "{} '{}' \n".format(doubleDot.name(), doubleDot["label"].value())
    #     nuke.message(message)

    all_connectors.sort(key=lambda connector: connector.knob("label").value())
    return all_connectors


def getAllConnectorLabels():
    """returns a list with all currently used labels"""

    # keep compatibility with older versions, so we also search for dots

    all_dots = [node for node in nuke.allNodes("Dot") if node["label"].value() and isConnector(node)]
    # all_postage_stamps = [
    #     node for node in nuke.allNodes("PostageStamp") if node.knob("disable").value() is False and node.knob("label").value() and isConnector(node)
    # ]

    all_noops = [node for node in nuke.allNodes("NoOp") if node["label"].value() and isConnector(node)]

    all_connectors = all_dots + all_noops

    connector_dot_labels = [connector["label"].value() for connector in all_connectors]

    return connector_dot_labels


def isConnectingAndConnectedCorrectly(node):
    """returns if the node is connected to the correct parent."""

    if not node.input(0):
        return False
    return node.knob("label").getValue() == node.input(0).knob("label").getValue() and isConnectingNode(node)


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
        selectedConnectors[0],
        selectedConnectors=selectedConnectors,
        uitype=UIType.UI_COLOR,
    )
    _labelConnectorUI.show()


def _showNamingUI(node, oldText=""):
    """
    force to show UI with color options
    """

    global _labelConnectorUI

    _labelConnectorUI = LabelConnector(node, uitype=UIType.UI_NAMING, namingText=oldText)
    _labelConnectorUI.show()


def _showConnectorUI(node):
    """
    force to show UI with color options
    """

    global _labelConnectorUI

    _labelConnectorUI = LabelConnector(node, selectedConnectors=[node], uitype=UIType.UI_CONNECTORONLY)
    _labelConnectorUI.show()


def hasPossibleInputs(node):
    """
    workaround to find out if a node can have connections. Because the "inputs" are still there
    and could be forcefully connected to sth.
    Also ignore IGNORECLASSES.
    """
    return "hide_input" in node.knobs() and not node.Class() in IGNORECLASSES


def setConnectorSettings(connector, txt):
    """
    sets defaults for connectorDots like font size and sets label.

    Args:
        dot (node): ConnectorDot
        txt (str): desired label text
    """
    connector.setName(CONNECTOR_KEY)
    # connector.knob("note_font_size").setValue(22)
    connector.knob("label").setValue(txt.upper())
    # connector.knob("postage_stamp").setValue(False)

    if BOLD_LABELS:
        current_font = connector.knob("note_font").value()
        connector.knob("note_font").setValue(f"{current_font} Bold")


def addConnectorNodeButtons(node):
    """Adds "Select all Children" button to a node."""

    tab = nuke.Tab_Knob("connector", "Connector")
    node.addKnob(tab)

    select_button = nuke.PyScript_Knob("selectChildren", "Select all Children")
    select_button.setCommand(
        "n = nuke.thisNode()\n"
        "for i in nuke.selectedNodes():\n"
        "    i.setSelected(False)\n"
        "\n"
        "for x in n.dependent(nuke.INPUTS | nuke.HIDDEN_INPUTS, forceEvaluate=False):\n"
        "    x.setSelected(True)\n"
    )
    node.addKnob(select_button)


def makeConnector(node, text, textOld=""):
    """
    Creates a new Connector, or renames an existing selected one alongside all dependent nodes.
    """
    text = text.strip(" ").upper()

    if not text:
        return

    # if text in getAllConnectorLabels():
    #     nuke.message("Label already in use")
    #     return

    UNDO.begin(UNDO_EVENT_TEXT)

    if node:
        if node.Class() in ["Dot", "NoOp"] and isConnector(node):
            # rename existing ConnectorDot alongside dependent Nodes
            node["label"].setValue(text)
            for x in node.dependent(nuke.INPUTS | nuke.HIDDEN_INPUTS, forceEvaluate=False):
                if x["label"].getValue() == textOld:
                    x["label"].setValue(text)

        else:  # attach new ConnectorDot Node to any Node
            node = nuke.createNode("NoOp", inpanel=False)
            setConnectorSettings(node, text)
            node.setYpos(node.ypos() + 50)
            addConnectorNodeButtons(node)

    else:  # create new independent ConnectorDot
        node = nuke.createNode("NoOp", inpanel=False)
        setConnectorSettings(node, text)
        addConnectorNodeButtons(node)

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

    return int("%02x%02x%02x%02x" % rgb, 16)


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
    interfaceColor = node.knob("tile_color").value()

    if interfaceColor == 0 or interfaceColor == nuke.defaultNodeColor(node.Class()) or interfaceColor == 3435973632:
        interfaceColor = BUTTON_REGULAR_COLOR

    return interfaceColor


def rgb2hex(rgbaValues):
    """
    Convert a color stored as normalized rgb values to a hex.

    Args:
        rgbaValues ([type]): [description]

    Returns:O
        [type]: [description]
    """
    if len(rgbaValues) < 3:
        return
    return "#%02x%02x%02x" % (
        int(rgbaValues[0] * 255),
        int(rgbaValues[1] * 255),
        int(rgbaValues[2] * 255),
    )


def hex2rgb(hexColor):
    """
    Convert a color stored as hex to rgb values.

    Args:
        hexColor ([type]): [description]

    Returns:
        [type]: [description]
    """
    hexColor = hexColor.lstrip("#")
    return tuple(int(hexColor[i : i + 2], 16) for i in (0, 2, 4))


def labelConnector():
    """
    Entry function. Determines, which UI to open based on context.
    """

    connectedSth = False
    onlyConnectorsSelected = True
    nodes = nuke.selectedNodes()
    all_connectors = getAllConnectors()

    for node in nodes:
        if not isConnector(node):
            onlyConnectorsSelected = False
            if node["label"].value() and not isConnectingAndConnectedCorrectly(node):
                if node.knob("connectorName"):
                    connectorName = node.knob("connectorName").value()
                    connector = nuke.toNode(connectorName)
                    if connector:
                        if connectNodeToDot(node, connector):
                            connectedSth = True
                        continue

                for connector in all_connectors:
                    if node["label"].value() == connector["label"].value():
                        # Label Match has been found, try to connect the two Nodes
                        if connectNodeToDot(node, connector):
                            connectedSth = True
                        break

    if (len(nodes) > 1 or connectedSth) and not onlyConnectorsSelected:
        # with more than one node or when connections were made, no new Dots will be set up thus no UI shown.
        # except we have one or mulitple parents
        return

    global _labelConnectorUI

    if nodes:
        node = nodes[0]

        if onlyConnectorsSelected:
            _labelConnectorUI = LabelConnector(node, selectedConnectors=nodes, uitype=UIType.UI_CONNECTORONLY)
            _labelConnectorUI.show()
            return

        if isConnectingAndConnectedCorrectly(node):
            _labelConnectorUI = LabelConnector(node, all_connectors, uitype=UIType.UI_CHILDRENONLY)
            _labelConnectorUI.show()
            return

        if not hasPossibleInputs(node):
            _labelConnectorUI = LabelConnector(node, uitype=UIType.UI_NAMING)
            _labelConnectorUI.show()
            return

        # will create  a prepending connector
        _labelConnectorUI = LabelConnector(node, all_connectors)
        _labelConnectorUI.show()
        return

    # will create a standalone connector
    _labelConnectorUI = LabelConnector(connectors=all_connectors)
    _labelConnectorUI.show()
    return
