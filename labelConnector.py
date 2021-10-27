# labelConnector v0.16
# Lukas Schwabe & Johannes Hezer
# UI based on ChannelHotbox - Falk Hofmann

import math
import logging
import nuke
try:
    # < Nuke 11
    import PySide.QtCore as QtCore
    import PySide.QtGui as QtGui
    import PySide.QtGui as QtGuiWidgets
except ImportError:
    # >= Nuke 11
    import PySide2.QtCore as QtCore
    import PySide2.QtGui as QtGui
    import PySide2.QtWidgets as QtGuiWidgets


log = logging.getLogger("labelMatcher")

undo = nuke.Undo()
undoEventText = "Label Connector"

BUTTON = "border-radius: 8px; font: 13px;"

button_regular_color = 673720575
button_highlight_color = 3261606143

threeD_deep_nodes = [   "DeepColorCorrect",
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
                        "WriteGeo" ]
                        
ignore_nodes = [        "Dot", 
                        "NoOp", 
                        "TimeOffset", 
                        "TimeWarp", 
                        "Retime", 
                        "FrameHold" ]

class LayerButton(QtGuiWidgets.QPushButton):
    """Custom QPushButton to change colors when hovering above."""
    def __init__(self, dot, node, button_width, parent=None):
        super(LayerButton, self).__init__(parent)
        self.setMouseTracking(True)
        self.setText(dot.knob('label').getValue())
        self.dot = dot
        self.node = node

        self.setMinimumWidth(button_width / 2)
        self.setSizePolicy(QtGuiWidgets.QSizePolicy.Preferred,
                           QtGuiWidgets.QSizePolicy.Expanding)
        self.color = rgb2hex(interface2rgb(getTileColor(dot)))
        self.highlight = rgb2hex(interface2rgb(button_highlight_color))
        self.setStyleSheet("background-color:"+self.color + ";" + BUTTON)

    def enterEvent(self, event):  # pylint: disable=invalid-name,unused-argument
        """Change color to orange when mouse enters button."""
        self.setStyleSheet("background-color:"+self.highlight + ";" + BUTTON)

    def leaveEvent(self, event):  # pylint: disable=invalid-name,unused-argument
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
        # self.completer.setCompletionMode(QtGuiWidgets.QCompleter.InlineCompletion)
        self.completer.setCaseSensitivity(QtCore.Qt.CaseSensitivity.CaseInsensitive)
        self.setCompleter(self.completer)
        self.completer.activated.connect(self.returnPressed)


class labelConnector(QtGuiWidgets.QWidget):
    """User Interface class to provide buttons for each channel layer."""

    def __init__(self, node, dots):

        self.node = node

        super(labelConnector, self).__init__()

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
            button = LayerButton(dot, node, button_width)
            button.clicked.connect(self.clicked)
            grid.addWidget(button, row_counter, column_counter)

            if column_counter > length:
                row_counter += 1
                column_counter = 0

            else:
                column_counter += 1

        self.input = LineEdit(self, dots, node)
        grid.addWidget(self.input, row_counter, column_counter)
        self.input.returnPressed.connect(self.line_enter)

        self.set_window_properties()

    def set_window_properties(self):
        """Set window falgs and focused widget."""

        self.setWindowFlags(QtCore.Qt.FramelessWindowHint |  QtCore.Qt.WindowStaysOnTopHint)

        self.setAttribute(QtCore.Qt.WA_TranslucentBackground)
        self.setAttribute(QtCore.Qt.WA_NoSystemBackground)

        # make sure the widgets closes when it loses focus
        self.installEventFilter(self)
        self.input.setFocus()

    def keyPressEvent(self, event):  # pylint: disable=invalid-name
        if event.key() == QtCore.Qt.Key_Escape:                
            self.close()

    def clicked(self):
        undo.begin(undoEventText)
        if self.node == "":
            self.node = createConnectingNode(self.sender().dot)

        connectNodeToDot(self.node, self.sender().dot)
        undo.end()
        self.close()


    def line_enter(self):
        undo.begin(undoEventText)

        for dot in self.sender().dots:
            if self.input.text() == dot.knob('label').getValue():

                if self.node == "":
                    self.node = createConnectingNode(dot)

                connectNodeToDot(self.node, dot)

                undo.end()
                self.close()

        undo.end()

    def eventFilter(self, object, event):
        if event.type() in [QtCore.QEvent.WindowDeactivate, QtCore.QEvent.FocusOut]:
            self.close()
            return True
        return False

def isPreviousNodeDeepOrThreeD(node):

    dependencies = node.dependencies(nuke.INPUTS | nuke.HIDDEN_INPUTS)

    if dependencies:
        previousNode = dependencies[0]

        if previousNode.Class() in ignore_nodes:
            return isPreviousNodeDeepOrThreeD(previousNode)
        elif previousNode.Class() in threeD_deep_nodes:
            return True

    return False

def createConnectingNode(dot):

    node = ""

    if isPreviousNodeDeepOrThreeD(dot):
        node = nuke.createNode("NoOp", inpanel = False)
    else:
        node = nuke.createNode("PostageStamp", inpanel = False)

    node.knob('tile_color').setValue(rgb2interface((80,80,80)))
    node.setName("Connected")

    return node

def connectNodeToDot(node,dot):
    undo.begin(undoEventText)

    if node.setInput(0,dot):
        node['label'].setValue(dot['label'].getValue())
        node["hide_input"].setValue(True)

        undo.end()
        return True

    undo.end()
    return False


def getAllDots():
    #here we could filter for a dot nc like
    # if dot.name().startswith("Connector...") just to make it more bullet proof
    # we also return only set of dots with labels
    dots = list()
    compareList = list()
    doubleEntries = False
    doubleEntriesList = list()
    for dot in nuke.allNodes("Dot"):
        if dot.name().startswith("Connector"):
                if dot["label"].value():
                    if not dot["label"].value() in compareList:
                        dots.append(dot)
                        compareList.append(dot["label"].value())
                    else:
                        log.error("Double Label Entry found on Connector Dots, skipping dot: %s \"%s\" " % (dot.name(), dot["label"].value()))
                        doubleEntries = True
                        doubleEntriesList.append(dot)
    if doubleEntries:
        message = 'Skipped following Connector Dots (Label already used): \n \n'
        for doubleDot in doubleEntriesList:
            message += "%s \"%s\"\n" % (doubleDot.name(), doubleDot["label"].value())
        nuke.message(message)

    #dots.sort()
    dots.sort(key=lambda dot: dot.knob('label').value())
    return dots

def runLabelMatch(forceShowUi = False):

    uiCheck = False
    labelConnectorNodeCreated = False
    nodes = nuke.selectedNodes()
    dots = getAllDots()
    for node in nodes:
        if node["label"].value():

            if not node.name().startswith("Connector"):                   
                for dot in dots:
                    if node["label"].value() == dot["label"].value():
                        if not connectNodeToDot(node,dot):  
                            uiCheck = True
                    else:
                        uiCheck = True

        else:
            uiCheck = True

    
    global labelConnectorUi  # pylint: disable=global-statement

    # if the label is empty or not match could be found and the selection is just one node
    if (uiCheck or forceShowUi) and len(nodes) == 1 and dots:
        labelConnectorUi = labelConnector(node, dots)
        labelConnectorUi.show()

    # this will run and create a new node context based
    if len(nodes) == 0 and dots:
        node = ""
        labelConnectorUi = labelConnector(node, dots)
        labelConnectorUi.show()

def setConnectorDot(dot, txt):
    dot.setName("Connector")
    dot.knob('note_font_size').setValue(22)
    dot.knob('label').setValue(txt.upper())

def makeConnector():
    undo.begin(undoEventText)


    nodes = nuke.selectedNodes()
    if len(nodes) == 1:
        for n in nodes:
            if n.Class() == "Dot":        
                if "Connector" in n.name():
                    txtold = n['label'].getValue()
                    txtnew = nuke.getInput('Rename Label', txtold)

                    if txtnew:
                        txtnew = txtnew.upper()
                        n['label'].setValue(txtnew)
                        for x in n.dependent(nuke.INPUTS | nuke.HIDDEN_INPUTS, forceEvaluate = False):
                            if x['label'].getValue() == txtold:
                                x['label'].setValue(txtnew)

                else:
                    txt = nuke.getInput('Set label', 'new label')

                    if txt:
                        setConnectorDot(n, txt)
                    
            else:
                txt = nuke.getInput('Set label', 'new label')

                if txt:
                    n = nuke.createNode("Dot", inpanel = False)
                    setConnectorDot(n, txt)

                    n.setYpos(n.ypos()+50)

    if len(nodes) == 0:
        txt = nuke.getInput('Set label', 'new label')

        if txt:
            n = nuke.createNode("Dot", inpanel = False)
            setConnectorDot(n, txt)

    undo.end()
    



def interface2rgb(hexValue, normalize = True):
    '''
    Convert a color stored as a 32 bit value as used by nuke for interface colors to normalized rgb values.

    '''
    return [(0xFF & hexValue >>  i) / 255.0 for i in [24,16,8]]

def rgb2interface(rgb):
    '''
    Convert a color stored as rgb values to a 32 bit value as used by nuke for interface colors.
    '''
    if len(rgb) == 3:
        rgb = rgb + (255,)

    return int('%02x%02x%02x%02x'%rgb,16)


def getTileColor(node = None):
    '''
    If a node has it's color set automatically, the 'tile_color' knob will return 0.
    If so, this function will scan through the preferences to find the correct color value.
    '''

    if not node:
        node = nuke.selectedNode()

    interfaceColor = node.knob('tile_color').value()

    if interfaceColor == 0 or interfaceColor == nuke.defaultNodeColor(node.Class()) or interfaceColor == 3435973632:
        interfaceColor = button_regular_color;

    return interfaceColor


def rgb2hex(rgbaValues):
    '''
    Convert a color stored as normalized rgb values to a hex.
    '''
    if len(rgbaValues) < 3:
        return
    return '#%02x%02x%02x' % (int(rgbaValues[0]*255),int(rgbaValues[1]*255),int(rgbaValues[2]*255))

def hex2rgb(hexColor):
    '''
    Convert a color stored as hex to rgb values.
    '''
    hexColor = hexColor.lstrip('#')
    return tuple(int(hexColor[i:i+2], 16) for i in (0, 2 ,4))

def rgb2interface(rgb):
    '''
    Convert a color stored as rgb values to a 32 bit value as used by nuke for interface colors.
    '''
    if len(rgb) == 3:
        rgb = rgb + (255,)

    return int('%02x%02x%02x%02x'%rgb,16)