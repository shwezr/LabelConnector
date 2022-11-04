# LabelConnector
A Connector Tool for Nuke. Connect Nodes via label-matching. Super light-weight without callbacks. Uses simple ConnectorDots (Dot nodes named "Connector...") and node labels plus a handy UI to connect new nodes from anywhere in the DAG.

## Quick Manual

**alt+shift+A:** 
- **no ConnectorDot selected:** Creates new ConnectorDot
- **ConnectorDot selected:** Renames ConnectorDot alongside all dependent Nodes.

**A:** 
- **\>= 1 selected nodes:**  Connects all label matches. No ConnectorUI is shown.
- **1 selected node, no label:** Shows ConnectorUI.
- **0 selected nodes:** Will create a new PostageStamp/NoOp, showing the ConnectorUI.
 
**alt+A:** 
- **1 selected node, any label:** Will show the ConnectorUI instead of connecting the existing label match.

You can change these Shortcuts in the attached menu.py.

Feel free to color your ConnectorDots, these colors will then appear in the ConnectorUI.

Thanks to Falk Hofmann for helping with the UI and code clean up.

## Example

Select any node you want to attach a Connector Dot to, press **alt+shift+A**.

![Create Connector 01](./.pictures/LabelConnectorCreateConnector01.png)
![Create Connector 02](./.pictures/LabelConnectorCreateConnector02.png)

\
\
You can also colorize the Connector Dot - I use the super handy W_HotBox for this, but feel free to choose any Node Color. The color will be reflected in the Connector UI.

![Create Color 01](./.pictures/LabelConnectorColor01.png)

\
\
Click free DAG space, or any Node you want, and hit **A** to set a new connection.

![Create Connection 01](./.pictures/LabelConnectorConnection01.png)

\
\
You can type a Connector Name or click any button. With previously no Node selected, it will create a NoOp (3D) or PostageStamp (2D).

![Create Connection 02](./.pictures/LabelConnectorConnection02.png)

\
\
Selecting a Connector Dot and hitting **alt+shift+A** again renames the Connector Dot as well as all attached Nodes.

![Create Rename 01](./.pictures/LabelConnectorRename01.png)
![Create Rename 02](./.pictures/LabelConnectorRename02.png)

\
\
Buttons are sorted alphabetically.
![Create Connection 03](./.pictures/LabelConnectorConnection03.png)

\
\
After copy-pasting a group of Nodes, they're all selected. Just hit **A** to connect them all.

![Create Connect 01](./.pictures/LabelConnectorConnect01.png)
![Create Connect 02](./.pictures/LabelConnectorConnect02.png)



