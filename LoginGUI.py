"""This file will be removed soon"""

from Login import Ui_MainWindow
from PyQt5 import QtCore, QtGui, QtWidgets
import sys
import time
import Datal
import SettingGUIFunc


class MyActions(Ui_MainWindow):
    def __init__(self, title=" "):
        self.title = title
        self.left = 250
        self.top = 250
        self.width = 200
        self.height = 150
        self.user = "1"
        self.psw = "1"

    # update setupUi
    def setupUi(self, MainWindow):
        super().setupUi(MainWindow)
        # MainWindow.resize(400, 300) # do not modify it
        MainWindow.move(self.left, self.top)  # set location for window
        MainWindow.setWindowTitle(self.title)  # change title
        self.label_2.setStyleSheet("color:white")
        self.pushButton.clicked.connect(self.on_click1)
        self.pushButton_2.clicked.connect(self.on_click2)

    def on_click1(self):
        if Datal.NextPass == 0:
            Datal.user = self.lineEdit.text()
            self.lineEdit.clear()
            self.label_2.setText("enter the password")
            Datal.NextPass = 1

        elif Datal.NextPass == 1:
            Datal.passw = self.lineEdit.text()
            self.lineEdit.clear()
            self.password(Datal.user, Datal.passw)
            Datal.NextPass = 0

    def on_click2(self):
        self.lineEdit.clear()

    def password(self, user, passw):
        if user == self.user and passw == self.psw:
            self.label_2.setText("Login successful!")
            Datal.login = True
            self.logged()

        else:
            self.label_2.setText("user name or Password  did not match! Enter the Username")

    def closeMyApp_OpenNewApp(self):
        login.close()
        self.SettingsFormer = QtWidgets.QMainWindow()
        self.open = SettingGUIFunc.SettingsForm("Intruder detector Settings")
        self.open.setupUi(self.SettingsFormer)
        self.SettingsFormer.show()

    def logged(self):
        time.sleep(1)
        print("login successful!----")
        self.closeMyApp_OpenNewApp()


if __name__ == '__main__':
    app = QtWidgets.QApplication(sys.argv)
    login = QtWidgets.QMainWindow()
    ui = MyActions("Login System")
    ui.setupUi(login)
    login.show()

    sys.exit(app.exec_())
