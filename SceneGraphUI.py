#!/X/tools/binlinux/xpython
from PyQt4 import QtCore, QtGui
from functools import partial
import os

from . import logger
from . import config
from . import graph
from . import ui
reload(config)
reload(graph)
reload(ui)


class SceneGraph(QtGui.QMainWindow):
    
    def __init__(self, parent=None):
        super(SceneGraph, self).__init__(parent)
        
        self._current_file  = None              # current save file name (if any)
        self._startdir      = os.getenv('HOME')
        
        self.settings       = QtCore.QSettings('SceneGraphc.ini', QtCore.QSettings.IniFormat)
        self.settings.setFallbacksEnabled(False)
        self.menubar = QtGui.QMenuBar(self)
        self.centralwidget = QtGui.QWidget(self)
        self.gridLayout = QtGui.QGridLayout(self.centralwidget)
        self.tabWidget = QtGui.QTabWidget(self.centralwidget)
        self.graphTab = QtGui.QWidget()
        self.tabGridLayout = QtGui.QGridLayout(self.graphTab)
        self.main_splitter = QtGui.QSplitter(self.graphTab)
        self.main_splitter.setOrientation(QtCore.Qt.Horizontal)
        
        # Node view
        self.graphicsView = graph.GraphicsView(self.main_splitter, gui=self)
        self.right_splitter = QtGui.QSplitter(self.main_splitter)
        self.right_splitter.setOrientation(QtCore.Qt.Vertical)
        
        # Node Attributes
        self.detailGroup = QtGui.QGroupBox(self.right_splitter)
        self.detailGroupLayout = QtGui.QVBoxLayout(self.detailGroup)
        # add widgets here
        self.optionsBox = QtGui.QGroupBox(self.right_splitter)
        self.tabGridLayout.addWidget(self.main_splitter, 0, 0, 1, 1)
        
        self.tabWidget.addTab(self.graphTab, "Scene View")
        self.gridLayout.addWidget(self.tabWidget, 0, 0, 1, 1)
        self.setCentralWidget(self.centralwidget)
        self.menubar = QtGui.QMenuBar(self)
        self.menubar.setGeometry(QtCore.QRect(0, 0, 978, 22))
        self.setMenuBar(self.menubar)
        self.statusbar = QtGui.QStatusBar(self)
        self.setStatusBar(self.statusbar)
        
        self.setupUI()
        self.connect(self.graphicsView, QtCore.SIGNAL("tabPressed"), partial(self.createTabMenu, self.graphicsView))
        
        # load saved settings
        self.resize(self.settings.value('size').toSize())
        self.move(self.settings.value('pos').toPoint())
        self.setMenuBar(self.menubar)
        
        
    def setupUI(self):
        """
        Set up the main UI
        """
        # event filter
        self.eventFilter = MouseEventFilter(self)        
        self.installEventFilter(self.eventFilter)
        
        self.setWindowTitle('Scene Graph - v%s' % config.VERSION_AS_STRING)
        self.main_splitter.setStretchFactor(0, 1)
        self.main_splitter.setStretchFactor(1, 0)
        self.main_splitter.setSizes([770, 300])
        self.setStyleSheet("QTabWidget {background-color:rgb(68, 68, 68)}")
        
        self._setupGraphicsView()
        self._setupNodeAttributes()
        self._setupOptions()
        
        self._buildMenuBar()
    
    def setupConnections(self):
        pass
    
    def _setupGraphicsView(self, filter=False):        
        # scene view
        self.graphicsScene = graph.GraphicsScene()
        self.graphicsView.setScene(self.graphicsScene)
        self.graphicsView.setSceneRect(0, 0, 1000, 1000)
        #self.graphicsView.setSceneRect(-10000, -10000, 20000, 20000)

        # graphics View
        self.graphicsView.wheelEvent = self.graphicsView_wheelEvent
        self.graphicsView.resizeEvent = self.graphicsView_resizeEvent
        self.graphicsView.setBackgroundBrush(QtGui.QBrush(QtGui.QColor(60, 60, 60, 255), QtCore.Qt.SolidPattern))
        
        self.graphicsView.setContextMenuPolicy(QtCore.Qt.CustomContextMenu) 
        # event filter
        if filter:
            self.viewEventFilter = MouseEventFilter(self.graphicsView)
            self.graphicsView.viewport().installEventFilter(self.viewEventFilter)
            
        self.graphicsScene.selectionChanged.connect(self.nodesSelectedAction)          
        
    def _setupNodeAttributes(self):
        self.detailGroup.setTitle('Node Attributes')

    def _setupOptions(self):
        self.optionsBox.setTitle('Options')
    
    def _buildMenuBar(self):
        """
        Build the main menubar
        """
        # FILE MENU
        self.menuFile = QtGui.QMenu(self.menubar)
        self.menuFile.setTitle("File")

        self.action_saveAs = QtGui.QAction(self)
        self.action_save = QtGui.QAction(self)
        self.action_read = QtGui.QAction(self)
        self.action_reset = QtGui.QAction(self)
        
        self.menuFile.addAction(self.action_saveAs)
        self.menuFile.addAction(self.action_save)
        self.menuFile.addAction(self.action_read)
        self.menuFile.addAction(self.action_reset)
        
        
        self.action_saveAs.setText("Save Graph As...")
        self.action_save.setText("Save Graph...")
        self.action_read.setText("Read Graph...")
        self.action_reset.setText("Reset Graph")
        
        self.action_saveAs.triggered.connect(self.saveGraph)
        self.action_save.triggered.connect(partial(self.saveGraph, filename=self._current_file))
        self.action_read.triggered.connect(self.readGraph)
        self.action_reset.triggered.connect(self.resetGraph)
        
        if not self._current_file:
            self.action_save.setEnabled(False)
        self.menubar.addAction(self.menuFile.menuAction())
        
        # GRAPH MENU
        self.menuGraph = QtGui.QMenu(self.menubar)
        self.menuGraph.setTitle("Graph")
        self.action_add_generic = QtGui.QAction(self)
        self.menuGraph.addAction(self.action_add_generic)
        self.action_add_generic.setText("Add Generic node...")
        self.action_add_generic.triggered.connect(partial(self.graphicsScene.nodeManager.createNode, 'generic'))
        self.menubar.addAction(self.menuGraph.menuAction())
        
    #- SAVING/LOADING ------
    def saveGraph(self, filename=None):
        """
        Save the current graph to a json file
        """
        import os
        if not filename:
            filename = QtGui.QFileDialog.getSaveFileName(self, "Save graph file", self._startdir, "JSON files (*.json)")
            if filename == "":
                return          

        logger.getLogger().info('saving current graph "%s"' % filename)
        self.graphicsScene.nodeManager.write(filename)
        self._current_file = filename
        self.action_save.setEnabled(True)

    def readGraph(self):
        """
        Read the current graph from a json file
        """
        import os
        filename = QtGui.QFileDialog.getOpenFileName(self, "Open graph file", self._startdir, "JSON files (*.json)")
        if filename == "":
            return
        
        self.resetGraph()
        logger.getLogger().info('reading graph "%s"' % filename)
        self.graphicsScene.nodeManager.read(filename)
        self._current_file = filename
        self.action_save.setEnabled(True)

    def resetGraph(self):
        """
        Reset the current graph
        """
        self.graphicsScene.nodeManager.reset()
        self._current_file = None
        self.action_save.setEnabled(False)
        
    def sizeHint(self):
        return QtCore.QSize(1070, 800)
    
    def removeDetailWidgets(self):
        """
        Remove a widget from the detailGroup box
        """
        for i in reversed(range(self.detailGroupLayout.count())):
            widget = self.detailGroupLayout.takeAt(i).widget()
            if widget is not None: 
                widget.deleteLater()
    
    #- ACTIONS ----
    def nodesSelectedAction(self):
        self.removeDetailWidgets()
        nodes = self.graphicsScene.selectedItems()
        if len(nodes) == 1:
            node = nodes[0]
            if node._is_node:
                nodeAttrWidget = ui.NodeAttributesWidget(self.detailGroup, manager=self.graphicsScene.nodeManager)                
                nodeAttrWidget.setNode(node)
                self.detailGroupLayout.addWidget(nodeAttrWidget)     
    
    #- EVENTS ----
    def graphicsView_wheelEvent(self, event):
        factor = 1.41 ** ((event.delta()*.5) / 240.0)
        self.graphicsView.scale(factor, factor)

    def graphicsView_resizeEvent(self, event):
        self.graphicsScene.setSceneRect(0, 0, self.graphicsView.width(), self.graphicsView.height())
       
    #- MENUS -----
    def createTabMenu(self, parent):
        """ build a context menu for the lights list """
        print '# Creating tab menu...'
        menu=QtGui.QMenu(parent)
        menu.clear()
        reset_action = menu.addAction('Reset options to default')
        menu.exec_(parent.scenePos())

    def closeEvent(self, event):
        """ 
        Write window prefs when UI is closed
        """
        self.settings.setValue('size', self.size())
        self.settings.setValue('pos', self.pos())
        event.accept()

class MouseEventFilter(QtCore.QObject):
    def eventFilter(self, obj, event):
        if event.type() == QtCore.QEvent.MouseButtonPress:
            # call a function here..
            # obj.doSomething()
            return True
        return False
    