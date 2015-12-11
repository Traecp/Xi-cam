# -*- coding: UTF-8 -*-

### TODO: Add calibrant selection
# TODO: Add calibration button
# TODO: Make experiment save/load
### TODO: Add peak marking
### TODO: Add q trace
# TODO: Confirm q calibration
### TODO: Add caking
# TODO: Synchronize tabs
## TODO: Add mask clear
### TODO: Clean tab names
### TODO: Add arc ROI
## TODO: Use detector mask in centerfinder


import sys
import os


# print os.getcwd()

# import loader

from PySide.QtUiTools import QUiLoader
from PySide import QtGui
from PySide import QtCore


from pyqtgraph.parametertree import \
    ParameterTree  # IF THIS IS LOADED BEFORE PYSIDE, BAD THINGS HAPPEN; pycharm insists I'm wrong...
import pyqtgraph as pg
import models
import config
import viewer
import library
import timeline
import watcher
import numpy as np
import daemon
import pipeline
import toolbar
import rmc
import multiprocessing
import qdarkstyle



class MyMainWindow():
    def __init__(self,app):

        import plugins


        self._pool = None
        # Load the gui from file
        self.app = app
        guiloader = QUiLoader()
        #print os.getcwd()
        f = QtCore.QFile("gui/mainwindow.ui")
        f.open(QtCore.QFile.ReadOnly)
        self.ui = guiloader.load(f)
        f.close()


        # STYLE
        # self.app.setStyle('Plastique')
        with open('gui/style.stylesheet', 'r') as f:
            style = f.read()
        app.setStyleSheet(qdarkstyle.load_stylesheet() + style)



        # INITIAL GLOBALS
        self.viewerprevioustab = -1
        self.timelineprevioustab = -1
        self.experiment = config.experiment()
        self.folderwatcher = watcher.newfilewatcher()
        self.plugins = []




        # ACTIONS
        # Wire up action buttons
        self.ui.findChild(QtGui.QAction, 'actionOpen').triggered.connect(self.dialogopen)
        # self.ui.findChild(QtGui.QAction, 'actionCenterFind').triggered.connect(self.centerfind)
        # self.ui.findChild(QtGui.QAction, 'actionPolyMask').triggered.connect(self.polymask)
        # self.ui.findChild(QtGui.QAction, 'actionLog_Intensity').triggered.connect(self.redrawcurrent)
        # self.ui.findChild(QtGui.QAction, 'actionRemove_Cosmics').triggered.connect(self.removecosmics)
        # self.ui.findChild(QtGui.QAction, 'actionMultiPlot').triggered.connect(self.multiplottoggle)
        # self.ui.findChild(QtGui.QAction, 'actionMaskLoad').triggered.connect(self.maskload)
        # self.ui.findChild(QtGui.QAction, 'actionSaveExperiment').triggered.connect(self.experiment.save)
        # self.ui.findChild(QtGui.QAction, 'actionLoadExperiment').triggered.connect(self.loadexperiment)
        # self.ui.findChild(QtGui.QAction, 'actionRadial_Symmetry').triggered.connect(self.redrawcurrent)
        # self.ui.findChild(QtGui.QAction, 'actionMirror_Symmetry').triggered.connect(self.redrawcurrent)
        # self.ui.findChild(QtGui.QAction, 'actionShow_Mask').triggered.connect(self.redrawcurrent)
        # self.ui.findChild(QtGui.QAction, 'actionCake').triggered.connect(self.redrawcurrent)
        # self.ui.findChild(QtGui.QAction, 'actionLine_Cut').triggered.connect(self.linecut)
        # self.ui.findChild(QtGui.QAction, 'actionTimeline').triggered.connect(self.opentimeline)
        # self.ui.findChild(QtGui.QAction, 'actionAdd').triggered.connect(self.addmode)
        # self.ui.findChild(QtGui.QAction, 'actionSubtract').triggered.connect(self.subtractmode)
        # self.ui.findChild(QtGui.QAction, 'actionAdd_with_coefficient').triggered.connect(self.addwithcoefmode)
        # self.ui.findChild(QtGui.QAction, 'actionSubtract_with_coefficient').triggered.connect(self.subtractwithcoefmode)
        # self.ui.findChild(QtGui.QAction, 'actionDivide').triggered.connect(self.dividemode)
        # self.ui.findChild(QtGui.QAction, 'actionAverage').triggered.connect(self.averagemode)
        # self.ui.findChild(QtGui.QAction, 'actionVertical_Cut').triggered.connect(self.vertcut)
        # self.ui.findChild(QtGui.QAction, 'actionHorizontal_Cut').triggered.connect(self.horzcut)
        # self.ui.findChild(QtGui.QAction, 'actionRemeshing').triggered.connect(self.remeshmode)
        # self.ui.findChild(QtGui.QAction, 'actionExport_Image').triggered.connect(self.exportimage)
        # self.ui.findChild(QtGui.QAction, 'actionCalibrate_AgB').triggered.connect(self.calibrate)
        # self.ui.findChild(QtGui.QAction, 'actionRefine_Center').triggered.connect(self.refinecenter)

        # set inital state
        # self.ui.findChild(QtGui.QAction, 'actionLog_Intensity').setChecked(True)

        # WIDGETS
        # Setup experiment tree
        # self.experimentTree = ParameterTree()
        # settingsList = self.ui.findChild(QtGui.QVBoxLayout, 'propertiesBox')
        # settingsList.addWidget(self.experimentTree)

        # Setup Image Properties
        # self.imagePropModel = models.imagePropModel(self.currentImageTab)
        #self.ui.propertytable.setModel(self.imagePropModel)
        # self.ui.openfileslist.hide()
        #self.ui.openfilescheck.hide()




        # Setup file tree
        # self.filetreemodel = QtGui.QFileSystemModel()
        # self.filetree = self.ui.findChild(QtGui.QTreeView, 'treebrowser')
        # self.filetree.setModel(self.filetreemodel)
        # self.filetreepath = pipeline.pathtools.getRoot()
        # self.treerefresh(self.filetreepath)
        # header = self.filetree.header()
        # self.filetree.setHeaderHidden(True)
        # for i in range(1, 4):
        # header.hideSection(i)
        # filefilter = ["*.tif", "*.edf", "*.fits", "*.nxs", "*.hdf", "*.cbf"]
        # self.filetreemodel.setNameFilters(filefilter)
        # self.filetreemodel.setNameFilterDisables(False)
        # self.filetreemodel.setResolveSymlinks(True)
        # self.filetree.expandAll()
        # self.filetree.sortByColumn(0,QtCore.Qt.AscendingOrder)


        # Setup preview
        # self.preview = viewer.previewwidget(self.filetreemodel)
        # self.ui.findChild(QtGui.QVBoxLayout, 'smallimageview').addWidget(self.preview)

        # Setup library view
        # if sys.platform == 'win32':
        # self.libraryview = library.librarylayout(self, 'C://')
        # else:
        #     self.libraryview = library.librarylayout(self, pipeline.pathtools.getRoot())
        # self.ui.findChild(QtGui.QWidget, 'thumbbox').setLayout(self.libraryview)

        # Setup open files list
        # self.openfileslistview = self.ui.findChild(QtGui.QListView, 'openfileslist')
        # self.listmodel = models.openfilesmodel(self.ui.findChild(QtGui.QTabWidget, 'tabWidget'))
        # self.openfileslistview.setModel(self.listmodel)

        # Setup folding toolboxes
        # self.ui.findChild(QtGui.QCheckBox, 'filebrowsercheck').stateChanged.connect(self.filebrowserpanetoggle)
        # self.ui.findChild(QtGui.QCheckBox, 'openfilescheck').stateChanged.connect(self.openfilestoggle)
        # self.ui.findChild(QtGui.QCheckBox, 'watchfold').stateChanged.connect(self.watchfoldtoggle)
        # self.ui.findChild(QtGui.QCheckBox, 'experimentfold').stateChanged.connect(self.experimentfoldtoggle)
        # self.ui.findChild(QtGui.QCheckBox, 'propertiesfold').stateChanged.connect(self.propertiesfoldtoggle)

        # Setup integration plot widget
        # qintegrationwidget = pg.PlotWidget()
        # self.qintegration = qintegrationwidget.getPlotItem()
        # self.qintegration.setLabel('bottom', u'q (\u212B\u207B\u00B9)', '')
        # self.qLine = pg.InfiniteLine(angle=90, movable=False, pen=pg.mkPen('#FFA500'))
        # self.qLine.setVisible(False)
        # self.qintegration.addItem(self.qLine)
        # self.ui.qplotslot.addWidget(qintegrationwidget)
        # chiintegrationwidget = pg.PlotWidget()
        # self.chiintegration = chiintegrationwidget.getPlotItem()
        # self.chiintegration.setLabel('bottom', u'χ (Degrees)')
        # self.chiLine = pg.InfiniteLine(angle=90, movable=False, pen=pg.mkPen('#FFA500'))
        # self.chiLine.setVisible(False)
        # self.chiintegration.addItem(self.chiLine)
        # self.ui.chiplotslot.addWidget(chiintegrationwidget)
        #
        # self.ui.plotTabs.currentChanged.connect(self.replotviewer)


        # Setup timeline plot widget
        # timelineplot = pg.PlotWidget()
        # self.timeline = timelineplot.getPlotItem()
        # self.timeline.showAxis('left', False)
        # self.timeline.showAxis('bottom', False)
        # self.timeline.showAxis('top', True)
        # self.timeline.showGrid(x=True)
        #
        # self.timeline.getViewBox().setMouseEnabled(x=False, y=True)
        #self.timeline.setLabel('bottom', u'Frame #', '')

        # self.timeline.getViewBox().buildMenu()
        # menu = self.timeline.getViewBox().menu
        # operationcombo = QtGui.QComboBox()
        # operationcombo.setObjectName('operationcombo')
        # operationcombo.addItems(
        # ['Chi Squared', 'Abs. difference', 'Norm. Abs. difference', 'Sum intensity', 'Norm. Abs. Diff. derivative'])
        # operationcombo.currentIndexChanged.connect(self.changetimelineoperation)
        # opwidgetaction = QtGui.QWidgetAction(menu)
        # opwidgetaction.setDefaultWidget(operationcombo)
        # #need to connect it
        # menu.addAction(opwidgetaction)





        # Timeline toolbar
        # self.timelinetoolbar = toolbar.difftoolbar()
        # self.timelinetoolbar.connecttriggers(self.calibrate, self.centerfind, self.refinecenter, self.redrawcurrent,
        # self.redrawcurrent, self.redrawcurrent, self.linecut, self.vertcut,
        #                                      self.horzcut, self.redrawcurrent, self.redrawcurrent, self.redrawcurrent,
        #                                      self.roi, self.arccut, self.polymask, self.process)
        # self.ui.timelinebox.insertWidget(0, self.timelinetoolbar)

        # Viewer toolbar
        # self.difftoolbar = toolbar.difftoolbar()
        # self.difftoolbar.connecttriggers(self.calibrate, self.centerfind, self.refinecenter, self.redrawcurrent,
        # self.redrawcurrent, self.remeshmode, self.linecut, self.vertcut,
        #                                  self.horzcut, self.redrawcurrent, self.redrawcurrent, self.redrawcurrent,
        #                                  self.roi, self.arccut, self.polymask)
        # self.ui.diffbox.insertWidget(0, self.difftoolbar)

        # Setup file operation toolbox
        # self.booltoolbar = QtGui.QToolBar()
        # self.booltoolbar.addAction(self.ui.findChild(QtGui.QAction, 'actionTimeline'))
        # self.booltoolbar.addAction(self.ui.findChild(QtGui.QAction, 'actionAdd'))
        # self.booltoolbar.addAction(self.ui.findChild(QtGui.QAction, 'actionSubtract'))
        # self.booltoolbar.addAction(self.ui.findChild(QtGui.QAction, 'actionAdd_with_coefficient'))
        # self.booltoolbar.addAction(self.ui.findChild(QtGui.QAction, 'actionSubtract_with_coefficient'))
        # self.booltoolbar.addAction(self.ui.findChild(QtGui.QAction, 'actionDivide'))
        # self.booltoolbar.addAction(self.ui.findChild(QtGui.QAction, 'actionAverage'))
        # self.booltoolbar.setIconSize(QtCore.QSize(32, 32))
        # self.ui.findChild(QtGui.QVBoxLayout, 'leftpanelayout').addWidget(self.booltoolbar)


        # Adjust splitter position (not working?)
        # self.ui.findChild(QtGui.QSplitter, 'splitter').setSizes([500, 1])
        # self.ui.findChild(QtGui.QSplitter, 'splitter_3').setSizes([200, 1, 200])
        # self.ui.findChild(QtGui.QSplitter, 'splitter_2').setSizes([150, 1])
        # self.ui.findChild(QtGui.QSplitter, 'splitter_4').setSizes([500, 1])

        # Grab status bar
        #self.statusbar = self.ui.statusbar
        self.ui.statusbar.showMessage('Ready...')
        self.app.processEvents()


        # SIGNALS
        # self.ui.findChild(QtGui.QTabWidget, 'tabWidget').tabCloseRequested.connect(self.tabCloseRequested)
        # self.ui.findChild(QtGui.QTabWidget, 'tabWidget').currentChanged.connect(self.currentchanged)
        # self.ui.findChild(QtGui.QTabWidget, 'timelinetabwidget').currentChanged.connect(self.currentchangedtimeline)
        # self.ui.findChild(QtGui.QTabWidget, 'timelinetabwidget').tabCloseRequested.connect(
        # self.timelinetabCloseRequested)
        # self.filetree.clicked.connect(self.preview.loaditem)
        # self.filetree.doubleClicked.connect(self.itemopen)
        # self.openfileslistview.doubleClicked.connect(self.switchtotab)
        # self.ui.findChild(QtGui.QDialogButtonBox, 'watchbuttons').button(QtGui.QDialogButtonBox.Open).clicked.connect(
        # self.openwatchfolder)
        # self.ui.findChild(QtGui.QDialogButtonBox, 'watchbuttons').button(QtGui.QDialogButtonBox.Reset).clicked.connect(
        #     self.resetwatchfolder)
        # self.folderwatcher.newFilesDetected.connect(self.newfilesdetected)
        #self.ui.findChild(QtGui.QCheckBox, 'autoPreprocess').stateChanged.connect(self.updatepreprocessing)

        # Connect top menu
        # self.ui.librarybutton.clicked.connect(self.showlibrary)
        #self.ui.viewerbutton.clicked.connect(self.showviewer)
        #self.ui.timelinebutton.clicked.connect(self.showtimeline)


        # PLUG-INS
        self.rmcpugin = rmc.gui(self.ui)
        placeholders = [self.ui.viewmode, self.ui.sidemode, self.ui.bottommode, self.ui.toolbarmode, self.ui.leftmode]

        plugins.loadplugins(placeholders)
        plugins.plugins['Viewer'].activate()

        plugins.base.filetree.sigOpenFile.connect(self.openfile)

        self.ui.modemenu.addWidget(plugins.widgets.pluginModeWidget(plugins.plugins))



        # CONFIG
        # Bind experiment tree to parameter
        # self.bindexperiment()

        # TESTING
        ##
        # self.openimage('../samples/AgB_00016.edf')

        #self.calibrate()
        # self.updatepreprocessing()
        ##

        # START PYSIDE MAIN LOOP
        # Show UI and end app when it closes
        self.ui.show()
        self.ui.raise_()
        self.ui.activateWindow()

    def replotviewer(self):
        if hasattr(self.currentImageTab(), 'tab'):
            if self.currentImageTab().tab is not None:
                self.currentImageTab().tab.replot()


                # def process(self):
                # self.currentTimelineTab().tab.processtimeline()
                #
                #
                # def treerefresh(self, path=None):
                #     """
                #     Refresh the file tree, or switch directories and refresh
                #     """
                #     if path is None:
                #         path = self.filetreepath
                #
                #     root = QtCore.QDir(path)
                #     self.filetreemodel.setRootPath(root.absolutePath())
                #     self.filetree.setRootIndex(self.filetreemodel.index(root.absolutePath()))
                #     self.filetree.show()

                # def switchtotab(self, index):
                # """
                #     Set the current viewer tab
                #     """
                #     self.ui.findChild(QtGui.QTabWidget, 'tabWidget').setCurrentIndex(index.row())

                # def linecut(self):
                # """
                #     Connect linecut to current tab's linecut
                #     """
                #     self.currentImageTab().tab.linecut()
                #
                # def arccut(self):
                #     self.currentImageTab().tab.arccut()
                #
                # def roi(self):
                #     self.currentImageTab().tab.roi()

                # def opentimeline(self):
                # """
                #     Open a tab in Timeline mode
                #     """
                #     import plugins
                #     indices = self.ui.findChild(QtGui.QTreeView, 'treebrowser').selectedIndexes()
                #     paths = [self.filetreemodel.filePath(index) for index in indices]
                #
                #     plugins.plugins['Timeline'].openfiles(files=paths)
                # newtimelinetab = timeline.timelinetabtracker(paths, self.experiment, self)
        # filenames = [path.split('/')[-1] for path in paths]
        #
        # timelinetabwidget = self.ui.findChild(QtGui.QTabWidget, 'timelinetabwidget')
        # timelinetabwidget.setCurrentIndex(timelinetabwidget.addTab(newtimelinetab, 'Timeline: ' + ', '.join(filenames)))

    def changetimelineoperation(self, index):
        self.currentTimelineTab().tab.setvariationmode(index)

    # def addmode(self):
    # """
    #     Launch a tab as an add operation
    #     """
    #     operation = lambda m: np.sum(m, 0)
    #     self.launchmultimode(operation, 'Addition')
    #
    # def subtractmode(self):
    #     """
    #     Launch a tab as an sub operation
    #     """
    #     operation = lambda m: m[0] - np.sum(m[1:], 0)
    #     self.launchmultimode(operation, 'Subtraction')
    #
    # def addwithcoefmode(self):
    #     """
    #     Launch a tab as an add with coef operation
    #     """
    #     coef, ok = QtGui.QInputDialog.getDouble(self.ui, u'Enter scaling coefficient x (A+xB):', u'Enter coefficient')
    #
    #     if coef and ok:
    #         operation = lambda m: m[0] + coef * np.sum(m[1:], 0)
    #         self.launchmultimode(operation, 'Addition with coef (x=' + coef + ')')
    #
    # def subtractwithcoefmode(self):
    #     """
    #     Launch a tab as a sub with coef operation
    #     """
    #     coef, ok = QtGui.QInputDialog.getDouble(self.ui, u'Enter scaling coefficient x (A-xB):', u'Enter coefficient')
    #
    #     if coef and ok:
    #         operation = lambda m: m[0] - coef * np.sum(m[1:], 0)
    #         self.launchmultimode(operation, 'Subtraction with coef (x=' + str(coef))
    #
    # def dividemode(self):
    #     """
    #     Launch a tab as a div operation
    #     """
    #     operation = lambda m: m[0] / m[1]
    #     self.launchmultimode(operation, 'Division')
    #
    # def averagemode(self):
    #     """
    #     Launch a tab as an avg operation
    #     """
    #     operation = lambda m: np.mean(m, 0)
    #     self.launchmultimode(operation, 'Average')
    #
    #
    #
    # def launchmultimode(self, operation, operationname):
    #     """
    #     Launch a tab in multi-image operation mode
    #     """
    #     import plugins
    #     indices = self.ui.findChild(QtGui.QTreeView, 'treebrowser').selectedIndexes()
    #     paths = [self.filetreemodel.filePath(index) for index in indices]
    #     plugins.plugins['Viewer'].openfiles(paths=paths, operation=operation, operationname=operationname)

    def vertcut(self):
        """
        Connect vertical cut to current tab
        """
        self.currentImageTab().tab.verticalcut()

    def horzcut(self):
        """
        Connect horizontal cut to current tab
        """
        self.currentImageTab().tab.horizontalcut()

    def remeshmode(self):
        """
        Connect remesh mode to current tab
        """
        self.redrawcurrent()
        if self.currentImageTab() is not None:
            self.currentImageTab().tab.replot()

    def currentchanged(self, index):
        """
        When the active tab changes, load/unload tabs
        """
        # print('Changing from', self.viewerprevioustab, 'to', index)
        if index > -1:
            tabwidget = self.ui.findChild(QtGui.QTabWidget, 'tabWidget')

            # try:
            if self.viewerprevioustab > -1 and tabwidget.widget(self.viewerprevioustab) is not None:
                tabwidget.widget(self.viewerprevioustab).unload()
            # except AttributeError:
            #    print('AttributeError intercepted in currentchanged()')
            tabwidget.widget(index).load()
        self.viewerprevioustab = index

    def currentchangedtimeline(self, index):
        """
        When the active tab changes, load/unload tabs
        """
        # print('Changing from', self.timelineprevioustab, 'to', index)
        if index > -1:
            timelinetabwidget = self.ui.findChild(QtGui.QTabWidget, 'timelinetabwidget')
            # try:
            if self.viewerprevioustab > -1 and timelinetabwidget.widget(self.timelineprevioustab) is not None:
                timelinetabwidget.widget(self.timelineprevioustab).unload()
            # except AttributeError:
            #    print('AttributeError intercepted in currentchanged()')
            timelinetabwidget.widget(index).load()
        self.timelineprevioustab = index

        self.ui.findChild(QtGui.QStackedWidget, 'viewmode').setCurrentIndex(2)


    @staticmethod
    def load_image(path):
        """
        load an image with fabio
        """
        # Load an image path with fabio
        return pipeline.loader.loadpath(path)[0]


    def currentImageTab(self):
        """
        Get the currently shown image tab
        """
        if self.ui.viewmode.currentIndex() == 1:
            tabwidget = self.ui.tabWidget
        elif self.ui.viewmode.currentIndex() == 2:
            tabwidget = self.ui.timelinetabwidget
        return tabwidget.widget(tabwidget.currentIndex())


    def currentTimelineTab(self):
        """
        Get the currently shown image tab
        """
        tabwidget = self.ui.findChild(QtGui.QTabWidget, 'timelinetabwidget')
        if tabwidget.currentIndex() > -1:
            return tabwidget.widget(tabwidget.currentIndex())
        else:
            return None

    def viewmask(self):
        """
        Connect mask toggling to the current tab
        """
        # Show the mask overlay
        self.currentImageTab().viewmask()

    def tabCloseRequested(self, index):
        """
        Delete a tab from the tab view upon request
        """
        self.ui.findChild(QtGui.QTabWidget, 'tabWidget').widget(index).deleteLater()
        self.listmodel.widgetchanged()
        self.imagePropModel.widgetchanged()
        self.ui.filenamelabel.setText('')

    def timelinetabCloseRequested(self, index):
        self.ui.findChild(QtGui.QTabWidget, 'timelinetabwidget').widget(index).deleteLater()
        self.listmodel.widgetchanged()
        self.imagePropModel.widgetchanged()
        self.ui.filenamelabel.setText('')

    def polymask(self):
        """
        Add a polygon mask ROI to the tab
        """
        self.currentImageTab().tab.polymask()

    def dialogopen(self):
        """
        Open a file dialog then open that image
        """
        filename, ok = QtGui.QFileDialog.getOpenFileName(self.ui, 'Open file', os.curdir,
                                                         "*.tif *.edf *.fits *.tif *.cdf")
        if filename and ok:
            self.openfile(filename)

    def itemopen(self, index):
        """
        Open the item selected in the file tree
        """
        path = self.filetreemodel.filePath(index)

        if os.path.isfile(path):
            self.openfile(path)
        elif os.path.isdir(path):
            self.libraryview.chdir(path)
            self.showlibrary()


    def openfile(self, filename):
        """
        when a file is opened, check if there is calibration and offer to use the image as calibrant
        """
        print(filename)
        if filename is not u'':
            if config.activeExperiment.iscalibrated:
                self.openimage(filename)
            else:
                msgBox = QtGui.QMessageBox()
                msgBox.setText("The current experiment has not yet been calibrated. ")
                msgBox.setInformativeText("Use this image as a calibrant (AgBe)?")
                msgBox.setStandardButtons(QtGui.QMessageBox.Yes | QtGui.QMessageBox.No | QtGui.QMessageBox.Cancel)
                msgBox.setDefaultButton(QtGui.QMessageBox.Yes)

                response = msgBox.exec_()

                if response == QtGui.QMessageBox.Yes:
                    self.openimage(filename)

                    self.calibrate()
                elif response == QtGui.QMessageBox.No:
                    self.openimage(filename)
                elif response == QtGui.QMessageBox.Cancel:
                    return None

    def exportimage(self):
        self.currentImageTab().tab.exportimage()

    def calibrate(self):
        import plugins

        """
        Calibrate using the currently active tab
        """
        #self.currentImageTab().load()
        plugins.base.activeplugin.calibrate()

    def openimage(self, path):
        """
        build a new tab, add it to the tab view, and display it
        """

        import plugins

        self.ui.statusbar.showMessage('Loading image...')
        self.app.processEvents()
        # Make an image tab for that file and add it to the tab view
        # newimagetab = viewer.imageTabTracker([path], self.experiment, self)
        #tabwidget = self.ui.findChild(QtGui.QTabWidget, 'tabWidget')
        #tabwidget.setCurrentIndex(tabwidget.addTab(newimagetab, path.split('/')[-1]))
        plugins.plugins['Viewer'].openfiles(path)

        self.ui.statusbar.showMessage('Ready...')

    def centerfind(self):
        """
        find the center using the current tab image
        """
        self.ui.statusbar.showMessage('Finding center...')
        self.app.processEvents()
        # find the center of the current tab
        self.currentImageTab().tab.findcenter()
        self.ui.statusbar.showMessage('Ready...')

    def refinecenter(self):
        """
        Refine the center using the current tab image
        """
        self.ui.statusbar.showMessage('Refining center...')
        self.app.processEvents()
        # find the center of the current tab
        self.currentImageTab().tab.refinecenter()
        self.ui.statusbar.showMessage('Ready...')

    def redrawcurrent(self):
        """
        redraw the current tab's view
        """
        if self.currentImageTab() is not None:
            self.currentImageTab().tab.redrawimage()


    def removecosmics(self):
        """
        mask cosmic background on current tab
        """
        self.ui.statusbar.showMessage('Removing cosmic rays...')
        self.app.processEvents()
        self.currentImageTab().tab.removecosmics()
        self.ui.statusbar.showMessage('Ready...')

    def multiplottoggle(self):
        """
        replot the current tab (tab plotting checks if this is active)
        """
        self.currentImageTab().tab.replot()

    def maskload(self):
        """
        load a file as a mask
        """
        path, _ = QtGui.QFileDialog.getOpenFileName(self.ui, 'Open file', os.curdir, "*.tif *.edf *.fits")
        mask = self.load_image(path)
        self.experiment.addtomask(mask)

    def loadexperiment(self):
        """
        replot the current tab (tab plotting checks if this is active)
        """
        path, _ = QtGui.QFileDialog.getOpenFileName(self.ui, 'Open file', os.curdir, "*.exp")
        self.experiment = config.experiment(path)

    def bindexperiment(self):
        """
        connect the current experiment to the parameter tree gui
        """
        if self.experiment is None:
            self.experiment = config.experiment()
        self.experimentTree.setParameters(self.experiment, showTop=False)
        self.experiment.sigTreeStateChanged.connect(self.updateexperiment)

    def updateexperiment(self):
        self.experiment.save()
        if hasattr(self.currentImageTab(), 'tab'):
            if self.currentImageTab().tab is not None:
                self.currentImageTab().tab.redrawimage()
                self.currentImageTab().tab.drawcenter()
                self.currentImageTab().tab.replot()
                self.currentImageTab().tab.dimg.invalidatecache()

    def filebrowserpanetoggle(self):
        """
        toggle this pane as visible/hidden
        """
        pane = self.ui.findChild(QtGui.QTreeView, 'treebrowser')
        pane.setHidden(not pane.isHidden())

    def openfilestoggle(self):
        """
        toggle this pane as visible/hidden
        """
        pane = self.ui.findChild(QtGui.QListView, 'openfileslist')
        pane.setHidden(not pane.isHidden())

    def watchfoldtoggle(self):
        """
        toggle this pane as visible/hidden
        """
        pane = self.ui.findChild(QtGui.QFrame, 'watchframe')
        pane.setVisible(not pane.isVisible())

    def experimentfoldtoggle(self):
        """
        toggle this pane as visible/hidden
        """
        pane = self.experimentTree
        pane.setHidden(not pane.isHidden())

    def propertiesfoldtoggle(self):
        """
        toggle this pane as visible/hidden
        """
        pane = self.ui.propertytable
        pane.setHidden(not pane.isHidden())

    def showlibrary(self):
        """
        switch to library view
        """
        self.ui.viewmode.setCurrentIndex(0)
        self.ui.sidemode.setCurrentIndex(0)

    def showviewer(self):
        """
        switch to viewer view
        """
        self.ui.viewmode.setCurrentIndex(1)
        self.ui.sidemode.setCurrentIndex(0)

    def showtimeline(self):
        """
        switch to timeline view
        """
        self.ui.viewmode.setCurrentIndex(2)
        self.ui.sidemode.setCurrentIndex(0)



    def openwatchfolder(self):
        """
        Start a daemon thread watching the selected folder
        """
        dialog = QtGui.QFileDialog(self.ui, 'Choose a folder to watch', os.curdir,
                                   options=QtGui.QFileDialog.ShowDirsOnly)
        d = dialog.getExistingDirectory()
        if d:
            self.ui.findChild(QtGui.QLabel, 'watchfolderpath').setText(d)
            self.folderwatcher.addPath(d)
            if self.ui.findChild(QtGui.QCheckBox, 'autoPreprocess').isChecked():
                self.daemonthread = daemon.daemon(d, self.experiment, procold=True)
                self.daemonthread.start()

    def resetwatchfolder(self):
        """
        Resets the watch folder gui and ends current daemon
        """
        self.folderwatcher.removePaths(self.folderwatcher.directories())
        self.ui.findChild(QtGui.QLabel, 'watchfolderpath').setText('')
        self.daemonthread.stop()

    def newfilesdetected(self, d, paths):
        """
        When new files are detected, auto view/timeline them
        """
        # TODO: receive data from daemon thread instead of additional watcher object.
        if self.ui.findChild(QtGui.QCheckBox, 'autoView').isChecked():
            for path in paths:
                print(path)
                self.openfile(os.path.join(d, path))
        if self.ui.findChild(QtGui.QCheckBox, 'autoTimeline').isChecked():
            self.showtimeline()
            if self.currentTimelineTab() is None:
                newtimelinetab = timeline.timelinetabtracker([], self.experiment, self)
                timelinetabwidget = self.ui.findChild(QtGui.QTabWidget, 'timelinetabwidget')

                timelinetabwidget.setCurrentIndex(timelinetabwidget.addTab(newtimelinetab, 'Watched timeline'))
                self.currentTimelineTab().load()
            self.currentTimelineTab().tab.appendimage(d, paths)

            # def loadhiprmc(self):
            #     self.loadplugin(hiprmc)
            #
            # def loadplugin(self,module):
