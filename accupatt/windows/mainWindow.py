from datetime import datetime
import os
from pathlib import Path
import subprocess

import accupatt.config as cfg
from accupatt.helpers.cardPlotter import CardPlotter
from accupatt.helpers.dataFileImporter import convert_xlsx_to_db, load_from_accupatt_1_file
from accupatt.helpers.dBBridge import load_from_db, save_to_db
from accupatt.helpers.exportExcel import export_all_to_excel, safe_report
from accupatt.helpers.reportMaker import ReportMaker
from accupatt.models.appInfo import AppInfo
from accupatt.models.passData import Pass
from accupatt.models.seriesData import SeriesData
from accupatt.models.sprayCard import SprayCard
from accupatt.windows.cardManager import CardManager
from accupatt.windows.editSpreadFactors import EditSpreadFactors
from accupatt.windows.editThreshold import EditThreshold
from accupatt.windows.passManager import PassManager
from accupatt.windows.readString import ReadString
from accupatt.widgets import mplwidget, seriesinfowidget, singleCVImageWidget, splitcardwidget
from PyQt6 import uic
from PyQt6.QtCore import QSignalBlocker, Qt, pyqtSlot
from PyQt6.QtGui import QAction, QActionGroup
from PyQt6.QtWidgets import (QComboBox, QFileDialog, QLabel,
                             QListWidgetItem, QMenu, QMessageBox, QProgressDialog)

from accupatt.windows.reportManager import ReportManager
from accupatt.windows.stringAdvancedOptions import StringAdvancedOptions

Ui_Form, baseclass = uic.loadUiType(os.path.join(os.getcwd(), 'resources', 'mainWindow.ui'))
Ui_Form_About, baseclass_about = uic.loadUiType(os.path.join(os.getcwd(), 'resources', 'about.ui'))
testing = False
class MainWindow(baseclass):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.ui = Ui_Form()
        self.ui.setupUi(self)

        self.setWindowTitle(f'AccuPatt {cfg.VERSION_MAJOR}.{cfg.VERSION_MINOR}.{cfg.VERSION_RELEASE}')

        self.currentDirectory = cfg.get_datafile_dir()

        # Setup MenuBar
        # --> Setup File Menu
        self.ui.action_new_series_new_aircraft.triggered.connect(self.newSeriesNewAircraft)
        self.ui.menu_file_aircraft.aboutToShow.connect(self.aboutToShowFileAircraftMenu)
        self.ui.menu_file_aircraft.triggered.connect(self.newSeriesFileAircraftMenuAction)
        self.ui.action_save.triggered.connect(self.saveFile)
        self.ui.action_open.triggered.connect(self.openFile)
        # --> Setup Options Menu
        self.ui.action_pass_manager.triggered.connect(self.openPassManager)
        self.ui.action_reset_defaults.triggered.connect(self.resetDefaults)
        # --> Setup Export to Excel Menu
        self.ui.action_safe_report.triggered.connect(self.exportSAFEAttendeeLog)
        self.ui.action_detailed_report.triggered.connect(self.exportAllRawData)
        # --> Setup Report Menu
        self.ui.actionCreate_Report.triggered.connect(self.makeReport)
        self.ui.actionReportManager.triggered.connect(self.reportManager)
        # --> # --> Report Options
        self.ui.actionInclude_Card_Images.setChecked(cfg.get_report_card_include_images())
        self.ui.actionInclude_Card_Images.toggled[bool].connect(self.reportCardImageChanged)
        # --> # --> # --> SprayCard Image Type
        self.ui.actionOriginal.setChecked(cfg.get_report_card_image_type() == cfg.REPORT_CARD_IMAGE_TYPE_ORIGINAL)
        self.ui.actionOutline.setChecked(cfg.get_report_card_image_type() == cfg.REPORT_CARD_IMAGE_TYPE_OUTLINE)
        self.ui.actionMask.setChecked(cfg.get_report_card_image_type() == cfg.REPORT_CARD_IMAGE_TYPE_MASK)
        ag_image_type = QActionGroup(self.ui.menuCard_Image_Type)
        for action in self.ui.menuCard_Image_Type.actions():
            ag_image_type.addAction(action)
        ag_image_type.triggered[QAction].connect(self.reportCardImageTypeChanged)
        # --> # --> # --> SprayCard Image Quantity per Page
        self.ui.action5.setChecked(cfg.get_report_card_image_per_page() == 5)
        self.ui.action7.setChecked(cfg.get_report_card_image_per_page() == 7)
        self.ui.action9.setChecked(cfg.get_report_card_image_per_page() == 9)
        ag_image_per_page = QActionGroup(self.ui.menuCard_Images_per_Page)
        for action in self.ui.menuCard_Images_per_Page.actions():
            ag_image_per_page.addAction(action)
        ag_image_per_page.triggered[QAction].connect(self.reportCardImagePerPageChanged)
        # --> Setup Help Menu
        self.ui.actionAbout.triggered.connect(self.about)
        self.ui.actionUserManual.triggered.connect(self.openResourceUserManual)
        self.ui.actionWorksheetWRK.triggered.connect(self.openResourceWSWRK)
        self.ui.actionWorksheetGillColor.triggered.connect(self.openResourceWSGillColor)
        self.ui.actionWorksheetGillBW.triggered.connect(self.openResourceWSGillBW)
        self.ui.actionCPCatalog.triggered.connect(self.openResourceCPCatalog)
        
        # Setup Tab Widget
        self.ui.tabWidget.setEnabled(False)
        # --> Setup AppInfo Tab
        self.ui.widgetSeriesInfo.target_swath_changed.connect(self.swathTargetChanged)
        # --> Setup String Analysis Tab
        self.ui.listWidgetStringPass.itemSelectionChanged.connect(self.stringPassSelectionChanged)
        self.ui.listWidgetStringPass.itemChanged[QListWidgetItem].connect(self.stringPassItemChanged)
        self.ui.buttonReadString.clicked.connect(self.readString)
        self.ui.checkBoxStringPassCenter.stateChanged[int].connect(self.stringPassCenterChanged)
        self.ui.checkBoxStringPassSmooth.stateChanged[int].connect(self.stringPassSmoothChanged)
        self.ui.checkBoxStringPassRebase.stateChanged[int].connect(self.stringPassRebaseChanged)
        self.ui.stringAdvancedOptionsPass.clicked.connect(self.stringAdvancedOptionsPass)
        self.ui.checkBoxStringSeriesCenter.stateChanged[int].connect(self.stringSeriesCenterChanged)
        self.ui.checkBoxStringSeriesSmooth.stateChanged[int].connect(self.stringSeriesSmoothChanged)
        self.ui.checkBoxStringSeriesEqualize.stateChanged[int].connect(self.stringSeriesEqualizeChanged)
        self.ui.stringAdvancedOptionsSeries.clicked.connect(self.stringAdvancedOptionsSeries)
        self.ui.spinBoxSwathAdjusted.valueChanged[int].connect(self.swathAdjustedChanged)
        self.ui.horizontalSliderSimulatedSwath.valueChanged[int].connect(self.swathAdjustedChanged)
        # --> | --> Setup Individual Passes Tab
        # --> | --> Setup Composite Tab
        # --> | --> Setup Simulations Tab
        self.ui.spinBoxSimulatedSwathPasses.valueChanged[int].connect(self.simulatedSwathPassesChanged)
        self.ui.radioButtonSimulationOne.toggled[bool].connect(self.simulationViewWindowChanged)

        # --> Setup Card Analysis Tab
        self.ui.listWidgetSprayCardPass.itemSelectionChanged.connect(self.sprayCardPassSelectionChanged)
        self.ui.listWidgetSprayCard.itemSelectionChanged.connect(self.sprayCardSelectionChanged)
        self.ui.listWidgetSprayCard.itemChanged[QListWidgetItem].connect(self.sprayCardItemChanged)
        self.ui.buttonEditCards.clicked.connect(self.editSprayCardList)
        self.ui.buttonEditThreshold.clicked.connect(self.editThreshold)
        self.ui.buttonEditSpreadFactors.clicked.connect(self.editSpreadFactors)
        # --> | --> Setup Add/Edit Cards Tab
        self.ui.radioButtonSprayCardFitH.toggled[bool].connect(self.updateSprayCardFitMode)
        self.ui.radioButtonSprayCardFitV.toggled[bool].connect(self.updateSprayCardFitMode)
        # --> | --> Stup Droplet Distribution Tab
        self.ui.comboBoxSprayCardDist.currentIndexChanged[int].connect(self.sprayCardDistModeChanged)
        # --> | --> Setup Spatial Tab
        self.ui.radioButtonSpatialFt.toggled[bool].connect(self.spatialUnitsChanged)
        self.ui.checkBoxColorByDSC.stateChanged[int].connect(self.colorByDSCChanged)
        # --> | --> Setup Simulations Tab 
        
        # Setup Statusbar
        self.status_label_file = QLabel('No Current Datafile')
        self.status_label_modified = QLabel()
        self.ui.statusbar.addWidget(self.status_label_file)
        self.ui.statusbar.addPermanentWidget(self.status_label_modified)
        self.show()
        # Testing
        if testing:
            self.openFile()

    '''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''
    Menubar
    '''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''

    @pyqtSlot()
    def newSeriesNewAircraft(self):
        self.newSeries()

    @pyqtSlot()
    def aboutToShowFileAircraftMenu(self):
        m: QMenu = self.ui.menu_file_aircraft
        m.clear()
        m.addAction('Select File Aircraft')
        m.addSeparator()
        for file in [f for f in os.listdir(self.currentDirectory) if f.endswith('.db')]:
            m.addAction(str(file))

    @pyqtSlot()
    def newSeriesFileAircraftMenuAction(self, action):
        if action.text() == 'Select File Aircraft':
            self.newSeries(useFileAircraft=True)
        else:
            file = os.path.join(self.currentDirectory,action.text())
            self.newSeries(useFileAircraft=True, fileAircraft=file)
        
    def newSeries(self, useFileAircraft=False, fileAircraft=''):
        # Dissociate from any currently in-use data file
        self.currentFile = ''
        # Declare/clear SeriesData Container
        self.seriesData = SeriesData()
        # Load in Fly-In Info from saved settings
        info = self.seriesData.info
        info.flyin_name = cfg.get_flyin_name()
        info.flyin_location = cfg.get_flyin_location()
        info.flyin_date = cfg.get_flyin_date()
        info.flyin_analyst = cfg.get_flyin_analyst()
        # Create empty passes based (# of passes from saved settings)
        for i in range(cfg.get_number_of_passes()):
            self.seriesData.passes.append(Pass(number=i+1))
        # File Aircraft
        if useFileAircraft:
            if fileAircraft == '':
                fileAircraft, _ = QFileDialog.getOpenFileName(parent=self, 
                                            caption='Open File',
                                            directory=self.currentDirectory,
                                            filter='AccuPatt (*.db)')
            # Load in series info from file
            load_from_db(file=fileAircraft, s=self.seriesData,load_only_info=True)
            # Increment series number
            info.series = info.series + 1
        # Clear/Update all ui elements
        self.update_all_ui()
        self.status_label_file.setText('No Current Data File')
        self.status_label_modified.setText('')
        self.ui.tabWidget.setEnabled(True)
        self.ui.tabWidget.setCurrentIndex(0)

    @pyqtSlot()
    def saveFile(self):
        # If viewing from XLSX, Prompt to convert
        if self.currentFile != '' and self.currentFile[-1] == 'x':
            msg = QMessageBox.question(self, 'Unable to Edit Datafile',
                                       'Current File is of type: AccuPatt 1 (.xlsx). Would you like to create an edit-compatible (.db) copy?')
            if msg == QMessageBox.StandardButton.Yes:
                self.currentFile = convert_xlsx_to_db(self.currentFile, self.seriesData)
                self.status_label_file.setText(f'Current File: {self.currentFile}')
                self.status_label_modified.setText(f'Last Save: {datetime.fromtimestamp(self.seriesData.info.modified)}')
                return True
            return False
        # If db file doesn't exist, lets create one
        if self.currentFile == '':
            # Have user create a new file
            initialFileName = self.seriesData.info.string_reg_series()
            initialDirectory = os.path.join(self.currentDirectory,initialFileName)
            fname, _ = QFileDialog.getSaveFileName(parent=self, 
                                                        caption='Create Data File for Series',
                                                        directory=initialDirectory,
                                                        filter='AccuPatt (*.db)')
            if fname is None or fname == '':
                return False
            self.currentFile = fname
            self.currentDirectory = os.path.dirname(self.currentFile)
            cfg.set_datafile_dir(self.currentDirectory)
        # If db file exists, or a new one has been created, update persistent vals for Flyin
        cfg.set_flyin_name(self.seriesData.info.flyin_name)
        cfg.set_flyin_location(self.seriesData.info.flyin_location)
        cfg.set_flyin_date(self.seriesData.info.flyin_date)
        cfg.set_flyin_analyst(self.seriesData.info.flyin_analyst)
        # If db file exists, or a new one has been created, save all SeriesData to the db
        save_to_db(file=self.currentFile, s=self.seriesData)
        self.status_label_file.setText(f'Current File: {self.currentFile}')
        self.status_label_modified.setText(f'Last Save: {datetime.fromtimestamp(self.seriesData.info.modified)}')
        return True

    @pyqtSlot()
    def openFile(self):
        try:
            self.currentDirectory
        except NameError:
            self.currentDirectory = Path.home()
        if testing:
            file = '/Users/gill14/Library/Mobile Documents/com~apple~CloudDocs/Projects/AccuPatt/testing/N802BK 01.db'
            #file = '/Users/gill14/Library/Mobile Documents/com~apple~CloudDocs/Projects/AccuPatt/testing/N802BK 01.xlsx'
        else:
            file, _ = QFileDialog.getOpenFileName(parent=self, 
                                            caption='Open File',
                                            directory=self.currentDirectory,
                                            filter='AccuPatt (*.db *.xlsx)')
        if file == '':
            return
        if file[-1]=='x':
            msg = QMessageBox(QMessageBox.Icon.Question,
                              'Convert to Compatible Version?',
                              'Would you like to open this file in View-Only mode or create a compatible (*.db) copy?')
            button_read_only = msg.addButton('View-Only',QMessageBox.ButtonRole.ActionRole)
            button_convert = msg.addButton('Create Compatible Copy',QMessageBox.ButtonRole.ActionRole)
            msg.exec()
            if msg.clickedButton() == button_read_only:
                self.seriesData = load_from_accupatt_1_file(file=file)
            elif msg.clickedButton() == button_convert:
                prog = QProgressDialog(self)
                prog.setMinimumDuration(0)
                prog.setWindowModality(Qt.WindowModality.WindowModal)
                file = convert_xlsx_to_db(file, prog=prog)
            else:
                return 
        self.currentFile = file
        self.currentDirectory = os.path.dirname(self.currentFile)
        cfg.set_datafile_dir(self.currentDirectory)
        last_modified = 'View-Only Mode'
        if self.currentFile[-1]=='b':
            self.seriesData = SeriesData()
            load_from_db(file=self.currentFile, s=self.seriesData)
            last_modified = f'Last Save: {datetime.fromtimestamp(self.seriesData.info.modified)}'
        self.update_all_ui()
        self.status_label_file.setText(f'Current File: {self.currentFile}')
        self.status_label_modified.setText(last_modified)
        self.ui.tabWidget.setEnabled(True)
        self.ui.tabWidget.setCurrentIndex(0)
                
    def update_all_ui(self):
        #Populate AppInfo tab
        self.ui.widgetSeriesInfo.fill_from_info(self.seriesData.info)

        #Update Controls
        with QSignalBlocker(self.ui.checkBoxStringSeriesCenter):
            self.ui.checkBoxStringSeriesCenter.setChecked(self.seriesData.string.center)
        with QSignalBlocker(self.ui.checkBoxStringSeriesSmooth):
            self.ui.checkBoxStringSeriesSmooth.setChecked(self.seriesData.string.smooth)
        with QSignalBlocker(self.ui.checkBoxStringSeriesEqualize):
            self.ui.checkBoxStringSeriesEqualize.setChecked(self.seriesData.string.equalize_integrals)
        with QSignalBlocker(self.ui.spinBoxSimulatedSwathPasses):
            self.ui.spinBoxSimulatedSwathPasses.setValue(self.seriesData.string.simulated_adjascent_passes)
        if cfg.get_string_simulation_view_window() == cfg.STRING_SIMULATION_VIEW_WINDOW_ONE:
            with QSignalBlocker(self.ui.radioButtonSimulationOne):
                self.ui.radioButtonSimulationOne.setChecked(True)
        else:
            with QSignalBlocker(self.ui.radioButtonSimulationAll):
                self.ui.radioButtonSimulationAll.setChecked(True)
        with QSignalBlocker(self.ui.radioButtonSimulationOne):
            self.ui.radioButtonSimulationOne.setChecked(cfg.get_string_simulation_view_window() == cfg.STRING_SIMULATION_VIEW_WINDOW_ONE)
        with QSignalBlocker(self.ui.radioButtonSpatialFt):
            self.ui.radioButtonSpatialFt.setChecked(self.seriesData.info.swath_units == cfg.UNIT_FT)

        #Refresh ListWidgets
        self.updatePassListWidgets(string=True, cards=True)

        # Set swath adjust UI, plot loc unit labels and replot
        self.swathTargetChanged()
        
        # Updates spray card views based on potentially new pass list
        self.sprayCardPassSelectionChanged()

    @pyqtSlot()
    def openPassManager(self):
        #Create popup and send current appInfo vals to popup
        e = PassManager(self.seriesData.passes, self)
        #Connect Slot to retrieve Vals back from popup
        e.pass_list_updated[list].connect(self.updateFromPassManager)
        #Start Loop
        e.exec()
      
    @pyqtSlot(list)  
    def updateFromPassManager(self, passes):
        self.seriesData.passes = passes
        self.update_all_ui()
        self.saveFile()
        
    def updatePassListWidgets(self, string = False, string_index = -1, cards = False, cards_index = -1):
        # ListWidget String Pass
        if string:
            with QSignalBlocker(lwps := self.ui.listWidgetStringPass):
                lwps.clear()
                for p in self.seriesData.passes:
                    item = QListWidgetItem(p.name, lwps)
                    item.setFlags(Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsSelectable)
                    item.setCheckState(Qt.CheckState.Unchecked)
                    if not p.string.data.empty:
                        item.setFlags(Qt.ItemFlag.ItemIsEnabled|Qt.ItemFlag.ItemIsSelectable|Qt.ItemFlag.ItemIsUserCheckable)
                        if p.include_in_composite:
                            item.setCheckState(Qt.CheckState.Checked)
                        else:
                            item.setCheckState(Qt.CheckState.PartiallyChecked)
                    lwps.setCurrentItem(item)
                if string_index != -1:
                    lwps.setCurrentRow(string_index)
        # ListWidget Cards Pass
        if cards:
            with QSignalBlocker(lwpc := self.ui.listWidgetSprayCardPass):
                lwpc.clear()
                for p in self.seriesData.passes:
                    item = QListWidgetItem(p.name, lwpc)
                    item.setFlags(Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsSelectable)
                    item.setCheckState(Qt.CheckState.Unchecked)
                    if p.spray_cards:
                        item.setCheckState(Qt.CheckState.Checked)
                    lwpc.setCurrentItem(item)
                if cards_index != -1:
                    lwpc.setCurrentRow(cards_index)
    
    @pyqtSlot()
    def resetDefaults(self):
        cfg.clear_all_settings()
    
    @pyqtSlot()
    def exportSAFEAttendeeLog(self):
        files, _ = QFileDialog.getOpenFileNames(parent=self,
                                            caption='Select Files to Include',
                                            directory=self.currentDirectory,
                                            filter='AccuPatt (*.db)')
        if files:
            dir = os.path.dirname(files[0])
            savefile, _ = QFileDialog.getSaveFileName(parent=self,
                                                   caption='Save S.A.F.E. Attendee Log As',
                                                   directory=dir + os.path.sep + 'Operation SAFE Attendee Log.xlsx',
                                                   filter='Excel Files (*.xlsx)')
        if files and savefile:
            safe_report(files, savefile)

    @pyqtSlot()
    def exportAllRawData(self):
        savefile, _ = QFileDialog.getSaveFileName(parent=self,
                                                   caption='Save As',
                                                   directory=self.currentDirectory + os.path.sep + f'{self.seriesData.info.string_reg_series()} Raw Data.xlsx',
                                                   filter='Excel Files (*.xlsx)')
        if savefile:
            export_all_to_excel(series=self.seriesData, saveFile=savefile)

    @pyqtSlot()
    def makeReport(self):
        savefile, _ = QFileDialog.getSaveFileName(parent=self,
                                                   caption='Save As',
                                                   directory=self.currentDirectory + os.path.sep + f'{self.seriesData.info.string_reg_series()}.pdf',
                                                   filter='PDF Files (*.pdf)')
        if savefile:
            reportMaker = ReportMaker(file=savefile, seriesData=self.seriesData)
            reportMaker.report_safe_string(
                overlayWidget=self.ui.plotWidgetOverlay,
                averageWidget=self.ui.plotWidgetAverage,
                racetrackWidget=self.ui.plotWidgetRacetrack,
                backAndForthWidget=self.ui.plotWidgetBackAndForth,
                tableView=self.ui.tableWidgetCV)
            for row, p in enumerate(self.seriesData.passes):
                if p.spray_cards and any([sc.include_in_composite for sc in p.spray_cards]):
                    # Select the pass to update plots
                    self.ui.listWidgetSprayCardPass.setCurrentRow(row)
                    # Select the pass for droplet dist
                    self.ui.comboBoxSprayCardDist.setCurrentIndex(1)
                    reportMaker.report_safe_card_summary(
                        spatialDVWidget=self.ui.mplWidgetCardSpatial1,
                        spatialCoverageWidget=self.ui.mplWidgetCardSpatial2,
                        histogramNumberWidget=self.ui.plotWidgetDropDist1,
                        histogramCoverageWidget=self.ui.plotWidgetDropDist2,
                        tableView=self.ui.tableWidgetSprayCardStats,
                        passData=p
                    )
                    # Print cards for pass
                    if cfg.get_report_card_include_images():
                        reportMaker.report_card_individuals_concise(passData=p) 
            reportMaker.save()
            subprocess.call(["open", savefile])
            # Redraw plots with defaults
            self.update_all_ui()
    
    @pyqtSlot(bool)
    def reportCardImageChanged(self, checked: bool):
        cfg.set_report_card_include_images(checked)
    
    @pyqtSlot(QAction)
    def reportCardImageTypeChanged(self, action: QAction):
        if action == self.ui.actionOutline:
            cfg.set_report_card_image_type(cfg.REPORT_CARD_IMAGE_TYPE_OUTLINE)
        elif action == self.ui.actionMask:
            cfg.set_report_card_image_type(cfg.REPORT_CARD_IMAGE_TYPE_MASK)
        else:
            cfg.set_report_card_image_type(cfg.REPORT_CARD_IMAGE_TYPE_ORIGINAL)
    
    @pyqtSlot(QAction)
    def reportCardImagePerPageChanged(self, action: QAction):
        if action == self.ui.action5:
            cfg.set_report_card_image_per_page(5)
        elif action == self.ui.action7:
            cfg.set_report_card_image_per_page(7)
        else:
            cfg.set_report_card_image_per_page(9)
    
    @pyqtSlot()
    def reportManager(self):
        #Create popup and send current appInfo vals to popup
        e = ReportManager(self)
        #Connect Slot to retrieve Vals back from popup
        #e.pass_list_updated[list].connect(self.updateFromPassManager)
        #Start Loop
        e.exec()
        
    @pyqtSlot()
    def about(self):
        About(parent=self).exec()
    
    @pyqtSlot()
    def openResourceUserManual(self):
        self.openResourceDocument('accupatt_2_user_manual.pdf')
    
    @pyqtSlot()
    def openResourceWSWRK(self):
        self.openResourceDocument('WRK_SpraySheet_V3.pdf')
        
    @pyqtSlot()
    def openResourceWSGillColor(self):
        self.openResourceDocument('Gill_SpraySheet_Color.pdf')
        
    @pyqtSlot()
    def openResourceWSGillBW(self):
        self.openResourceDocument('Gill_SpraySheet_BW.pdf')
        
    @pyqtSlot()
    def openResourceCPCatalog(self):
        self.openResourceDocument('CP_Catalog.pdf')
    
    def openResourceDocument(self, file):
        file = os.path.join(os.getcwd(), 'resources', 'documents', file)
        subprocess.call(["open", file])
    
    '''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''
    String Analysis
    '''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''
    
    @pyqtSlot()    
    def stringPassSelectionChanged(self):
        if (passData := self.getCurrentStringPass()):
            self.ui.checkBoxStringPassCenter.setChecked(passData.string.center)
            self.ui.checkBoxStringPassSmooth.setChecked(passData.string.smooth)
            self.ui.checkBoxStringPassRebase.setChecked(passData.string.rebase)
            self.ui.checkBoxStringPassCenter.setEnabled(not passData.string.rebase)
            self.updateStringPlots(individuals=True)
            #Update the info labels on the individual pass tab
            if passData.string.data.empty:
                self.ui.buttonReadString.setText(f'Capture {passData.name}')
            else:
                self.ui.buttonReadString.setText(f'Edit {passData.name}')
        
    @pyqtSlot(QListWidgetItem)
    def stringPassItemChanged(self, item: QListWidgetItem):
        # Checkstate on item changed
        # If new state is unchecked, make it partial
        if item.checkState() == Qt.CheckState.Unchecked:
            item.setCheckState(Qt.CheckState.PartiallyChecked)
        # Update SeriesData -> Pass object
        p = self.seriesData.passes[self.ui.listWidgetStringPass.row(item)]
        p.include_in_composite = (item.checkState() == Qt.CheckState.Checked)
        # Replot composites, simulations
        self.updateStringPlots(modify=True, composites=True, simulations=True)

    @pyqtSlot()
    def readString(self):
        if (passData := self.getCurrentStringPass()):
            #Create popup and send current appInfo vals to popup
            e = ReadString(passData=passData, parent=self)
            #Connect Slot to retrieve Vals back from popup
            e.accepted.connect(self.readStringFinished)
            #Start Loop
            e.show()
        
    @pyqtSlot()
    def readStringFinished(self):
        # Handles checking of string pass list widget
        self.updatePassListWidgets(string=True, string_index=self.ui.listWidgetStringPass.currentRow())
        # Replot all but individuals
        self.updateStringPlots(modify=True, individuals=False, composites=True, simulations=True)
        # Plot individuals and update capture button text
        self.stringPassSelectionChanged()

    @pyqtSlot(int)
    def stringPassCenterChanged(self, checkstate):
        if (passData := self.getCurrentStringPass()):
            passData.string.center = (Qt.CheckState(checkstate) == Qt.CheckState.Checked)
            self.updateStringPlots(modify=True, composites=True, simulations=True)
    
    @pyqtSlot(int) 
    def stringPassSmoothChanged(self, checkstate):
        if (passData := self.getCurrentStringPass()):
            passData.string.smooth = (Qt.CheckState(checkstate) == Qt.CheckState.Checked)
            self.updateStringPlots(modify=True, individuals=True, composites=True, simulations=True)
    
    @pyqtSlot(int)
    def stringPassRebaseChanged(self, checkstate):
        if (passData := self.getCurrentStringPass()):
            passData.string.rebase = (Qt.CheckState(checkstate) == Qt.CheckState.Checked)
            if passData.string.rebase:
                passData.string.center = True
                self.ui.checkBoxStringPassCenter.setChecked(passData.string.center)
            self.ui.checkBoxStringPassCenter.setEnabled(not passData.string.rebase)
            self.updateStringPlots(modify=True, individuals=True, composites=True, simulations=True)
    
    @pyqtSlot(int)
    def stringSeriesCenterChanged(self, checkstate):
        self.seriesData.string.center = (Qt.CheckState(checkstate) == Qt.CheckState.Checked)
        self.updateStringPlots(modify=True, composites=True, simulations=True)
        
    @pyqtSlot(int)
    def stringSeriesSmoothChanged(self, checkstate):
        self.seriesData.string.smooth = (Qt.CheckState(checkstate) == Qt.CheckState.Checked)
        self.updateStringPlots(modify=True, composites=True, simulations=True)
        
    @pyqtSlot(int)
    def stringSeriesEqualizeChanged(self, checkstate):
        self.seriesData.string.equalize_integrals = (Qt.CheckState(checkstate) == Qt.CheckState.Checked)
        self.updateStringPlots(modify = True, composites = True, simulations = True)
    
    @pyqtSlot()
    def stringAdvancedOptionsPass(self):
        if (passData := self.getCurrentStringPass()):
            e = StringAdvancedOptions(
                passData=passData,
                parent=self
            )
            e.accepted.connect(self.stringAdvancedOptionsPassUpdated)
            e.exec()
    
    def stringAdvancedOptionsPassUpdated(self):
        self.updateStringPlots(modify=True, individuals=False, composites=True, simulations=True)
    
    @pyqtSlot()
    def stringAdvancedOptionsSeries(self):
        e = StringAdvancedOptions(
            seriesData=self.seriesData,
            parent=self
        )
        e.accepted.connect(self.stringAdvancedOptionsSeriesUpdated)
        e.exec()
        
    def stringAdvancedOptionsSeriesUpdated(self):
        self.updateStringPlots(modify=True, composites=True, simulations=True)
    
    @pyqtSlot(int)
    def swathAdjustedChanged(self, swath):
        self.seriesData.info.swath_adjusted = swath
        with QSignalBlocker(self.ui.spinBoxSwathAdjusted):
            self.ui.spinBoxSwathAdjusted.setValue(swath)
        with QSignalBlocker(self.ui.horizontalSliderSimulatedSwath):
            self.ui.horizontalSliderSimulatedSwath.setValue(swath)
        self.updateStringPlots(composites=True, simulations=True)
    
    def swathTargetChanged(self):
        #Update the swath adjustment slider
        sw = self.seriesData.info.swath
        if sw == 0:
            sw = self.seriesData.info.swath_adjusted
        minn = float(sw) * 0.5
        maxx = float(sw) * 1.5
        with QSignalBlocker(self.ui.horizontalSliderSimulatedSwath):
            self.ui.horizontalSliderSimulatedSwath.setValue(self.seriesData.info.swath_adjusted)
            self.ui.horizontalSliderSimulatedSwath.setMinimum(round(minn))
            self.ui.horizontalSliderSimulatedSwath.setMaximum(round(maxx))
        with QSignalBlocker(self.ui.spinBoxSwathAdjusted):
            self.ui.spinBoxSwathAdjusted.setValue(self.seriesData.info.swath_adjusted)
            self.ui.spinBoxSwathAdjusted.setSuffix(' ' + self.seriesData.info.swath_units)
        # Must update all string plots for new labels and potential new adjusted swath
        self.updateStringPlots(modify=True, individuals=True, composites=True, simulations=True)
    
    def updateStringPlots(self, modify = False, individuals = False, composites = False, simulations = False):
        if modify:
            self.seriesData.string.modifyPatterns()
        if individuals:
            if (passData := self.getCurrentStringPass()) != None:
                # Plot Individual
                line_left, line_right, line_vertical = passData.string.plotIndividual(self.ui.plotWidgetIndividual)
                # Connect Individual trim handle signals to slots for updating
                if line_left is not None and line_right is not None and line_vertical is not None:
                    line_left.sigPositionChangeFinished.connect(self._updateTrimL)
                    line_right.sigPositionChangeFinished.connect(self._updateTrimR)
                    line_vertical.sigPositionChangeFinished.connect(self._updateTrimFloor)
                # Plot Individual Trim
                passData.string.plotIndividualTrim(self.ui.plotWidgetIndividualTrim)
        if composites:
            self.seriesData.string.plotOverlay(self.ui.plotWidgetOverlay)
            self.seriesData.string.plotAverage(self.ui.plotWidgetAverage, self.seriesData.info.swath_adjusted)
        if simulations:
            self.seriesData.string.plotRacetrack(
                mplWidget=self.ui.plotWidgetRacetrack, 
                swath_width=self.seriesData.info.swath_adjusted, 
                showEntireWindow=self.ui.radioButtonSimulationAll.isChecked())
            self.seriesData.string.plotBackAndForth(
                mplWidget = self.ui.plotWidgetBackAndForth, 
                swath_width = self.seriesData.info.swath_adjusted, 
                showEntireWindow=self.ui.radioButtonSimulationAll.isChecked())
            self.seriesData.string.plotCVTable(self.ui.tableWidgetCV, self.seriesData.info.swath_adjusted)

    @pyqtSlot(object)
    def _updateTrimL(self, object):
        self.getCurrentStringPass().string.user_set_trim_left(object.value())
        self.updateStringPlots(modify=True, individuals=True, composites=True, simulations=True)
    
    @pyqtSlot(object)
    def _updateTrimR(self, object):
        self.getCurrentStringPass().string.user_set_trim_right(object.value())
        self.updateStringPlots(modify=True, individuals=True, composites=True, simulations=True)
       
    @pyqtSlot(object) 
    def _updateTrimFloor(self, object):
        self.getCurrentStringPass().string.user_set_trim_floor(object.value())
        self.updateStringPlots(modify=True, individuals=True, composites=True, simulations=True)

    @pyqtSlot(int)
    def simulatedSwathPassesChanged(self, numAdjascentPasses):
       self.seriesData.string.simulated_adjascent_passes = numAdjascentPasses
       self.updateStringPlots(simulations=True)
       
    @pyqtSlot(bool)
    def simulationViewWindowChanged(self, viewOneIsChecked):
        cfg.set_String_simulation_view_window(cfg.STRING_SIMULATION_VIEW_WINDOW_ONE if viewOneIsChecked else cfg.STRING_SIMULATINO_VIEW_WINDOW_ALL)
        self.updateStringPlots(simulations=True)
       
    def getCurrentStringPass(self):
        passData: Pass = None
        # Check if a pass is selected
        if (passIndex := self.ui.listWidgetStringPass.currentRow()) != -1:
            passData = self.seriesData.passes[passIndex]
        return passData

    '''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''
    Spray Card Analysis
    '''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''

    @pyqtSlot()
    def sprayCardPassSelectionChanged(self):
        with QSignalBlocker(self.ui.listWidgetSprayCard):
            # Clear Spray Card List
            self.ui.listWidgetSprayCard.clear()
            passData, _ = self.getCurrentCardPassAndCard()
            if passData:
                # Repopulate Spray Card List
                for card in passData.spray_cards:
                    item = QListWidgetItem(card.name,self.ui.listWidgetSprayCard)
                    if card.has_image:
                        if card.include_in_composite: 
                            item.setCheckState(Qt.CheckState.Checked)
                        else:
                            item.setCheckState(Qt.CheckState.PartiallyChecked)
                        item.setFlags(Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsSelectable | Qt.ItemFlag.ItemIsUserCheckable)
                    else:
                        item.setCheckState(Qt.CheckState.Unchecked)
                        item.setFlags(Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsSelectable)
        self.sprayCardSelectionChanged()
        self.updateCardPlots(spatial=True)

    @pyqtSlot()
    def sprayCardSelectionChanged(self):
        passData, sprayCard = self.getCurrentCardPassAndCard()
        # Update dist input ui
        cb_dist: QComboBox = self.ui.comboBoxSprayCardDist
        with QSignalBlocker(cb_dist):
            cb_dist.clear()
            cb_dist.addItem((sprayCard.name if sprayCard else ''))
            cb_dist.addItem((passData.name if passData else ''))
            cb_dist.addItem(('Series'))
        # Processing Buttons visibility
        self.setSprayCardProcessingButtonsEnable(bool(sprayCard and sprayCard.has_image))
        # Update plot/image ui
        self.updateCardPlots(images=True, distributions=True)

    @pyqtSlot(QListWidgetItem)
    def sprayCardItemChanged(self, item: QListWidgetItem):
        # Checkstate on item changed
        # If new state is unchecked, make it partial
        if item.checkState() == Qt.CheckState.Unchecked:
            with QSignalBlocker(self.ui.listWidgetSprayCard):
                item.setCheckState(Qt.CheckState.PartiallyChecked)
        # Update Card Object
        passData, _ = self.getCurrentCardPassAndCard()
        sprayCard: SprayCard = passData.spray_cards[self.ui.listWidgetSprayCard.row(item)]
        sprayCard.include_in_composite = (item.checkState() == Qt.CheckState.Checked)
        # Replot
        self.updateCardPlots(distributions=True, spatial=True)

    @pyqtSlot()
    def editSprayCardList(self):
        #Get a handle on the currently selected pass
        passData, _ = self.getCurrentCardPassAndCard()
        #Trigger file save if filapath needed
        if self.currentFile == None or self.currentFile == '':
            if not self.saveFile():
                return
        #Open the Edit Card List window for currently selected pass
        e = CardManager(passData=passData, filepath=self.currentFile, parent=self)
        #Connect Slot to retrieve Vals back from popup
        e.accepted.connect(self.editSprayCardListFinished)
        e.passDataChanged.connect(self.saveFile)
        #Start Loop
        e.exec()
        
    @pyqtSlot()
    def editSprayCardListFinished(self):
        # Save all changes
        self.saveFile()
        # Handles checking of card pass list widget
        self.updatePassListWidgets(cards=True, cards_index=self.ui.listWidgetSprayCardPass.currentRow())
        # Repopulates card list widget, updates rest of ui
        self.sprayCardPassSelectionChanged()

    @pyqtSlot()
    def editThreshold(self):
        passData, sprayCard = self.getCurrentCardPassAndCard()
        if sprayCard and sprayCard.has_image:
            #Open the Edit SF window for currently selected card
            e = EditThreshold(sprayCard=sprayCard, passData=passData, seriesData=self.seriesData, parent=self)
            #Connect Slot to retrieve Vals back from popup
            e.accepted.connect(self.saveAndUpdateSprayCardView)
            #Start Loop
            e.exec()
    
    @pyqtSlot()
    def editSpreadFactors(self):
        passData, sprayCard = self.getCurrentCardPassAndCard()
        if sprayCard and sprayCard.has_image:
            #Open the Edit SF window for currently selected card
            e = EditSpreadFactors(sprayCard=sprayCard, passData=passData, seriesData=self.seriesData, parent=self)
            #Connect Slot to retrieve Vals back from popup
            e.accepted.connect(self.saveAndUpdateSprayCardView)
            #Start Loop
            e.exec()

    @pyqtSlot(bool)
    def updateSprayCardFitMode(self, newBool):
        self.updateCardPlots(images=True)

    @pyqtSlot(int)
    def sprayCardDistModeChanged(self, mode):
        self.updateCardPlots(distributions=True)
    
    @pyqtSlot(bool)
    def spatialUnitsChanged(self, newBool):
        self.updateCardPlots(spatial=True)
    
    @pyqtSlot(int)
    def colorByDSCChanged(self, checkstate):
        self.updateCardPlots(spatial=True)
    
    @pyqtSlot()
    def saveAndUpdateSprayCardView(self):
        self.saveFile()
        self.updateCardPlots(images = True, distributions = True, spatial = True)

    def updateCardPlots(self, images = False, distributions = False, spatial = False):
        passData, sprayCard, cvImg1, cvImg2 = [None] * 4
        passData, sprayCard = self.getCurrentCardPassAndCard()
        if images:
            if sprayCard and sprayCard.has_image:
                cvImg1, cvImg2 = sprayCard.images_processed()
            fitMode = 'horizontal' if self.ui.radioButtonSprayCardFitH.isChecked() else 'vertical'
            self.ui.splitCardWidget.updateSprayCardView(cvImg1, cvImg2, fitMode)
        if distributions:
            spc = [sprayCard, passData, self.seriesData]
            spc = [spc[i] if i == self.ui.comboBoxSprayCardDist.currentIndex() else None for i in range(len(spc))]
            CardPlotter.plotDistribution(mplWidget1=self.ui.plotWidgetDropDist1,
                                         mplWidget2=self.ui.plotWidgetDropDist2,
                                         tableWidget=self.ui.tableWidgetSprayCardStats,
                                         sprayCard=spc[0],
                                         passData=spc[1],
                                         seriesData=spc[2])
        if spatial:
            self.ui.labelCardSpatialPass.setText(passData.name if passData else '')
            spray_cards = passData.spray_cards if passData else []
            loc_units = cfg.UNIT_FT if self.ui.radioButtonSpatialFt.isChecked() else cfg.UNIT_M
            CardPlotter.plotSpatial(mplWidget1=self.ui.mplWidgetCardSpatial1,
                                    mplWidget2=self.ui.mplWidgetCardSpatial2,
                                    sprayCards=spray_cards,
                                    loc_units=loc_units,
                                    colorize=self.ui.checkBoxColorByDSC.isChecked())
        
    def getCurrentCardPassAndCard(self) -> tuple:
        passData, sprayCard = [None] * 2
         # Check if a pass is selected
        if (passIndex := self.ui.listWidgetSprayCardPass.currentRow()) != -1:
            passData: Pass = self.seriesData.passes[passIndex]
            # Check if a card is selected
            if (cardIndex := self.ui.listWidgetSprayCard.currentRow()) != -1:
                sprayCard: SprayCard = passData.spray_cards[cardIndex]
        return passData, sprayCard
    
    def setSprayCardProcessingButtonsEnable(self, enable = False):
        self.ui.buttonEditThreshold.setEnabled(enable)
        self.ui.buttonEditSpreadFactors.setEnabled(enable)
        
class About(baseclass_about):
    def __init__(self, parent = None):
        super().__init__(parent = parent)
        # Your code will go here
        self.ui = Ui_Form_About()
        self.ui.setupUi(self)
        self.ui.label_version.setText(f'AccuPatt Version:  {cfg.VERSION_MAJOR}.{cfg.VERSION_MINOR}.{cfg.VERSION_RELEASE}')
        self.show()