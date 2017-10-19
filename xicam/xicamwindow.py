# -*- coding: UTF-8 -*-

# TODO: Make experiment save/load
### TODO: Add peak marking
## TODO: Add mask clear



import os

from PySide.QtUiTools import QUiLoader
from PySide import QtGui
from PySide import QtCore

from xicam import config
import watcher
#import daemon
import pipeline
import qdarkstyle
import plugins
from xicam import xglobals
import numpy as np

#import client.workflow

import threads
from pipeline import msg

class MyMainWindow(QtCore.QObject):
    def __init__(self, app):
        QtCore.QObject.__init__(self, app)
        print 'Gui:\t\t\t', QtGui.QApplication.instance().thread()
        QtGui.QFontDatabase.addApplicationFont("xicam/gui/zerothre.ttf")

        import plugins

        config.activate()

        self._pool = None
        # Load the gui from file
        self.app = app
        guiloader = QUiLoader()
        f = QtCore.QFile("xicam/gui/mainwindow.ui")
        f.open(QtCore.QFile.ReadOnly)
        self.ui = guiloader.load(f)
        f.close()

        # STYLE
        with open('xicam/gui/style.stylesheet', 'r') as f:
            style = f.read()
        app.setStyleSheet(qdarkstyle.load_stylesheet() + style)
        app.setAttribute(QtCore.Qt.AA_DontShowIconsInMenus, False)

        # INITIAL GLOBALS
        self.viewerprevioustab = -1
        self.timelineprevioustab = -1
        self.experiment = config.experiment()
        self.folderwatcher = watcher.newfilewatcher()
        self.plugins = []

        # ACTIONS
        # Wire up action buttons
        self.ui.findChild(QtGui.QAction, 'actionOpen').triggered.connect(self.dialogopen)
        self.ui.findChild(QtGui.QAction, 'actionSettings').triggered.connect(self.settingsopen)
        self.ui.findChild(QtGui.QAction, 'actionQuit').triggered.connect(QtGui.QApplication.instance().quit)

        self.ui.actionExport_Image.triggered.connect(self.exportimage)

        # Grab status bar
        msg.statusbar = self.ui.statusbar
        pb = QtGui.QProgressBar()
        pb.setSizePolicy(QtGui.QSizePolicy.Expanding, QtGui.QSizePolicy.Ignored)
        msg.progressbar = pb
        pb.setAccessibleName('progressbar')
        msg.statusbar.addPermanentWidget(pb)
        pb.hide()
        msg.showMessage('Ready...')
        xglobals.statusbar = self.ui.statusbar  # TODO: Deprecate this by replacing all statusbar calls with msg module

        # PLUG-INS

        placeholders = [self.ui.viewmode, self.ui.sidemode, self.ui.bottommode, self.ui.toolbarmode, self.ui.leftmode]

        plugins.initplugins(placeholders)

        plugins.plugins['MOTD'].instance.activate()

        plugins.base.fileexplorer.sigOpen.connect(self.openfiles)
        plugins.base.fileexplorer.sigFolderOpen.connect(self.openfolder)
        plugins.base.booltoolbar.actionTimeline.triggered.connect(plugins.base.filetree.handleOpenAction)

        pluginmode = plugins.widgets.pluginModeWidget(plugins.plugins)
        self.ui.modemenu.addWidget(pluginmode)

        self.ui.menubar.addMenu(plugins.buildactivatemenu(pluginmode))

        # TESTING
        ##
        # self.openimages(['../samples/AgB_00016.edf'])
        # self.openimages(['/Users/rp/Data/LaB6_Ant1_dc002p.mar3450'])

        # self.calibrate()
        # self.updatepreprocessing()
        ##
        testmenu = QtGui.QMenu('Testing')
        testmenu.addAction('Single frame').triggered.connect(self.singletest)
        testmenu.addAction('Image stack').triggered.connect(self.stacktest)
        testmenu.addAction('Timeline').triggered.connect(self.timelinetest)
        testmenu.addAction('Tilt').triggered.connect(self.tilttest)

        self.ui.menubar.addMenu(testmenu)

        #self.wfmanager = client.workflow.XicamWorkflow()
        #self.wfmanager.setup(self.ui.menubar)

        # START PYSIDE MAIN LOOP
        # Show UI and end app when it closes
        self.ui.installEventFilter(self)

    def eventFilter(self, obj, ev):
        if obj is self.ui:  # if the object is from the MainWindow
            if ev.type() == QtCore.QEvent.Close:
                # self.closeAllConnections()
                QtGui.QApplication.quit()
                threads.worker.stop()  # ask worker to stop nicely
                #threads.worker.wait()

                return True
            else:
                return False
        return QtCore.QObject.eventFilter(self, obj, ev)

    def singletest(self):
        self.openfiles(['/home/rp/data/3pt8m_gisaxs/26_pt10_30s_hi_2m.edf'])

    def stacktest(self):
        self.openfiles(['/tmp/20140905_191647_YL1031_.h5'])

    def timelinetest(self):
        import glob
        self.openfiles(sorted(glob.glob('/home/rp/data/YL1031/YL1031*.edf')))

    def tilttest(self):
        config.activeExperiment.setvalue('Detector Distance', 2.46269726489 * 79 * .001)
        config.activeExperiment.setvalue('Detector Rotation', 4.69729438873 * 360. / (2. * np.pi) - 180.)
        config.activeExperiment.setvalue('Detector Tilt', 0.503226642865 / (2. * np.pi) * 360.)
        config.activeExperiment.setvalue('Wavelength', 0.97621599151 * 1.e-10)
        config.activeExperiment.setvalue('Center X', 969.878684978)
        config.activeExperiment.setvalue('Center Y', 2048 - 2237.93277884)
        self.openfiles(['/home/rp/Downloads/lab6_041016_rct5_0001.tif'])

    def changetimelineoperation(self, index):
        self.currentTimelineTab().tab.setvariationmode(index)

    @staticmethod
    def load_image(path):
        """
        load an image with fabio
        """
        # Load an image path with fabio
        return pipeline.loader.loadpath(path)[0]

    def dialogopen(self):
        """
        Open a file dialog then open that image
        """
        filename, ok = QtGui.QFileDialog.getOpenFileName(self.ui, 'Open file', os.curdir,
                                                         '*' + ' *'.join(pipeline.loader.acceptableexts))
        if filename and ok:
            self.openfiles([filename])

    def openfiles(self, filenames):
        """
        when a file is opened, check if there is calibration and offer to use the image as calibrant
        """
        if filenames is not u'':
            if config.activeExperiment.iscalibrated or len(filenames) > 1:
                self.openimages(filenames)
            else:
                msgBox = QtGui.QMessageBox()
                msgBox.setText("The current experiment has not yet been calibrated. ")
                msgBox.setInformativeText("Use this image as a calibrant (AgBe)?")
                msgBox.setStandardButtons(QtGui.QMessageBox.Yes | QtGui.QMessageBox.No | QtGui.QMessageBox.Cancel)
                msgBox.setDefaultButton(QtGui.QMessageBox.Yes)

                response = msgBox.exec_()

                if response == QtGui.QMessageBox.Yes:
                    self.openimages(filenames)

                    self.calibrate()
                elif response == QtGui.QMessageBox.No:
                    self.openimages(filenames)
                elif response == QtGui.QMessageBox.Cancel:
                    return None

    def openfolder(self, filenames):
        """
        build a new tab from the folder path, add it to the tab view, and display it
        """

        if filenames is not u'':
            if config.activeExperiment.iscalibrated or len(filenames) > 1:
                import plugins

                self.ui.statusbar.showMessage('Loading images from folder...')
                self.app.processEvents()
                plugins.base.activeplugin.opendirectory(filenames)

                self.ui.statusbar.showMessage('Ready...')

    def exportimage(self):
        plugins.base.activeplugin.exportimage()

    def calibrate(self):

        """
        Calibrate using the currently active tab
        """
        # self.currentImageTab().load()
        plugins.base.activeplugin.calibrate()

    def openimages(self, paths):
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
        plugins.base.activeplugin.openfiles(paths)

        self.ui.statusbar.showMessage('Ready...')

    def loadexperiment(self):
        """
        replot the current tab (tab plotting checks if this is active)
        """
        path, _ = QtGui.QFileDialog.getOpenFileName(self.ui, 'Open file', os.curdir, "*.exp")
        self.experiment = config.experiment(path)

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
                msg.logMessage(path,msg.INFO)
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

    def settingsopen(self):
        config.settings.showEditor()
