from PyQt5 import QtWidgets as qtw
from PyQt5 import QtCore as qtc
from PyQt5 import QtGui as qtg
from PyQt5 import uic

from appInfo import AppInfo

Ui_Form, baseclass = uic.loadUiType('editApplicatorInfo.ui')

class EditApplicatorInfo(baseclass):

    applied = qtc.pyqtSignal(AppInfo)

    def __init__(self, appInfo, parent = None):
        super().__init__()
        # Your code will go here
        self.ui = Ui_Form()
        self.ui.setupUi(self)

        self.appInfo = appInfo
        self.ui.pilotLineEdit.setText(self.appInfo.pilot)
        self.ui.businessLineEdit.setText(self.appInfo.business)
        self.ui.streetLineEdit.setText(self.appInfo.street)
        self.ui.cityLineEdit.setText(self.appInfo.city)
        self.ui.stateLineEdit.setText(self.appInfo.state)
        self.ui.zipLineEdit.setText(self.appInfo.strip_num(self.appInfo.zip))
        self.ui.phoneLineEdit.setText(self.appInfo.phone)
        self.ui.emailLineEdit.setText(self.appInfo.email)

        self.ui.buttonBox.accepted.connect(self.on_applied)
        self.ui.buttonBox.rejected.connect(self.reject)

        # Your code ends here
        self.show()

    def on_applied(self):
        #save to this appInfoInstance from fields
        self.appInfo.pilot = self.ui.pilotLineEdit.text()
        self.appInfo.business = self.ui.businessLineEdit.text()
        self.appInfo.street = self.ui.streetLineEdit.text()
        self.appInfo.city = self.ui.cityLineEdit.text()
        self.appInfo.state = self.ui.stateLineEdit.text()
        self.appInfo.zip = self.ui.zipLineEdit.text()
        self.appInfo.phone = self.ui.phoneLineEdit.text()
        self.appInfo.email = self.ui.emailLineEdit.text()

        self.applied.emit(self.appInfo)

        self.accept

if __name__ == '__main__':
    app = QtGui.QApplication([])
    gui = NewWindow()
    gui.show()
    app.exec_()
