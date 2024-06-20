
import sys
from PyQt5 import QtCore, QtWidgets

from PyQt5.QtWidgets import *
from Settings import Ui_MainWindow
import SettingsFunctions

import Data
import  beepy
from Camsystem import face,motion
class SettingsForm(Ui_MainWindow,QMainWindow):
    def __init__(self, title=" "):
        QMainWindow.__init__(self)
        self.title = title
        self.left = 250
        self.top = 250
        self.width = 200
        self.height = 150


        # update setupUi

    def setupUi(self, MainWindow):
        super().setupUi(MainWindow)
        # MainWindow.resize(400, 300) # do not modify it
        MainWindow.move(self.left, self.top)  # set location for window
        MainWindow.setWindowTitle(self.title)  # change title
        self.pushButton.clicked.connect(self.AddUser)
        self.pushButton_3.clicked.connect(self.DelUser)
        self.pushButton_2.clicked.connect(self.getAlarm)
        self.pushButton_4.clicked.connect(self.getRep)
        self.pushButton_5.clicked.connect(self.playAlarm)
        self.pushButton_6.clicked.connect(self.changeVoice)
        self.pushButton_7.clicked.connect(self.ChangeAlarmText)
        self.pushButton_8.clicked.connect(self.playAlarmVoice)
        self.pushButton_9.clicked.connect(self.Default)
        self.pushButton_10.clicked.connect(self.ONclick)
        self.pushButton_11.clicked.connect(self.OFFclick)
        self.pushButton_12.clicked.connect(self.camclick)
        self.pushButton_12.clicked.connect(self.camclick)
        self.pushButton_13.clicked.connect(self.camclick)
        self.pushButton_14.clicked.connect(self.camclick)
    def camclick(self):
        datasave = Data.load()
        if datasave["ON"] == False:
            QMessageBox.about(self, "warning", "The system is turned off")
        else:
            self.thread1 = face()
            self.thread2 = motion()
            self.thread1.start()
            self.thread2.start()
            self.thread1.join()
            self.thread2.join()

    def ONclick(self):
        datasave = Data.load()
        datasave["ON"]=True
        datasave["OFF"]=False
        Data.save(datasave)
        QMessageBox.about(self, "warning", "The system is turned on")
    def OFFclick(self):
        datasave=Data.load()
        datasave["OFF"]=True
        datasave["ON"]=False
        Data.save(datasave)
        QMessageBox.about(self, "warning", "The system is turned off")
    def AddUser(self):#this function is used to check wheter the requested name is already in the system if not , we call the AddFace method from SettingFunctions
        datasave=Data.load()
        red = self.lineEdit.text()
        if red != "":
            if red == datasave["user1"] or red==datasave["user2"]:
                print("user in dataset")
                QMessageBox.about(self, "warning", "the user already exist")
            else:
                print("new user being added...")
                SettingsFunctions.AddFace(red)
                self.MessageMethod()






    def DelUser(self):#this method is used to delete a user from the system

        try:
            red = self.lineEdit_2.text()
            if red != "":
                SettingsFunctions.DeleteUser(red)
                datasave = Data.load()
                print(datasave["promptNotF"])
                if datasave["promptNotF"]==True:

                    QMessageBox.about(self, "Warning", "No User Found ")
                    datasave["promptNotF"] = False
                    Data.save(datasave)
                elif datasave["promptNotF"]==False:

                    QMessageBox.about(self, "Warning", "User Deleted! ")
        except Exception as e:
            print(e)
            print("an exception occurred")
            QMessageBox.about(self, "Warning", "No User Found ")


    def MessageMethod(self):
        datasave=Data.load()
        if datasave["LimitReached"]==True:
            QMessageBox.about(self, "warning", "Limit of user reached")
        else:
            QMessageBox.about(self, "Notice", "New User Added successfully ")

    def getAlarm(self):#method used to change the alarm
        datasave=Data.load()
        repo={}
        items = ("1:coin", "2:robot_error", "3:error","4:ping","5:ready","6:success","7:wilhelm")
        item, okPressed = QInputDialog.getItem(self, "Set Alarm", "sound:", items, 0, False)
        if okPressed and item:
            datasave["alarm"]=int(''.join(x for x in item if x.isdigit()))
            Data.save(datasave)

    def getRep(self):#method used to change the number of repetition
        datasave=Data.load()
        items = ("1","2","3","4","5")
        item, okPressed = QInputDialog.getItem(self, "Set Alarm", "sound:", items, 0, False)
        if okPressed and item:
            datasave["numberRep"] = int(item)
            Data.save(datasave)
    def playAlarm(self):#method used to play the alarm
        datasave=Data.load()
        beepy.beep(sound=datasave["alarm"])
    def changeVoice(self):#method used to change the voice
        datasave=Data.load()
        items = ("Male","Female")
        item, okPressed = QInputDialog.getItem(self, "Voice Settings", "Voice type:", items, 0, False)
        if okPressed and item:
            if item=="Male":
                datasave["voice"] = 0
            if item=="Female":
                datasave["voice"]=1
            Data.save(datasave)
    def ChangeAlarmText(self):
        datasave=Data.load()
        text, okPressed = QInputDialog.getText(self, "Change speech", "Speech:", QLineEdit.Normal, "")
        if okPressed and text != '':
            datasave["AlarmText"]=text
            Data.save(datasave)
    def playAlarmVoice(self):
        datasave=Data.load()
        SettingsFunctions.Speak(datasave["AlarmText"])

    def Default(self):
        Data.setToDefault()



if __name__ == "__main__":
    app = QtWidgets.QApplication(sys.argv)
    MainWindow = QtWidgets.QMainWindow()
    ui = SettingsForm("Intruder Detector")
    ui.setupUi(MainWindow)
    MainWindow.show()
    sys.exit(app.exec_())
