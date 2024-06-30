import sys
from PyQt5 import QtWidgets
from PyQt5.QtWidgets import *
from Settings import Ui_MainWindow
import beepy
from old.camsystem import face, motion
from src import user_db_func, Data


class SettingsForm(Ui_MainWindow, QMainWindow):
    def __init__(self, title=" "):
        QMainWindow.__init__(self)
        self.title = title
        self.left = 250
        self.top = 250
        self.width = 200
        self.height = 150

    def setupUi(self, MainWindow):
        super().setupUi(MainWindow)
        MainWindow.move(self.left, self.top)
        MainWindow.setWindowTitle(self.title)
        self.pushButton_2.clicked.connect(self.get_alarm)
        self.pushButton_4.clicked.connect(self.get_rep)
        self.pushButton_5.clicked.connect(self.play_alarm)
        self.pushButton_6.clicked.connect(self.change_voice)
        self.pushButton_7.clicked.connect(self.change_alarm_text)
        self.pushButton_8.clicked.connect(self.play_alarm_voice)
        self.pushButton_9.clicked.connect(self.set_default)
        self.pushButton_10.clicked.connect(self.on_click)
        self.pushButton_11.clicked.connect(self.off_click)
        self.pushButton_12.clicked.connect(self.cam_click)
        self.pushButton_13.clicked.connect(self.cam_click)
        self.pushButton_14.clicked.connect(self.cam_click)

    def cam_click(self):
        datasave = Data.load()
        if not datasave["ON"]:
            QMessageBox.warning(self, "Warning", "The system is turned off")
        else:
            self.thread1 = face()
            self.thread2 = motion()
            self.thread1.start()
            self.thread2.start()
            self.thread1.join()
            self.thread2.join()

    def on_click(self):
        datasave = Data.load()
        datasave["ON"] = True
        datasave["OFF"] = False
        Data.save(datasave)
        QMessageBox.information(self, "Information", "The system is turned on")

    def off_click(self):
        datasave = Data.load()
        datasave["OFF"] = True
        datasave["ON"] = False
        Data.save(datasave)
        QMessageBox.information(self, "Information", "The system is turned off")

    def get_alarm(self):
        datasave = Data.load()
        items = ("1:coin", "2:robot_error", "3:error", "4:ping", "5:ready", "6:success", "7:wilhelm")
        item, okPressed = QInputDialog.getItem(self, "Set Alarm", "Sound:", items, 0, False)
        if okPressed and item:
            datasave["alarm"] = int(''.join(filter(str.isdigit, item)))
            Data.save(datasave)

    def get_rep(self):
        datasave = Data.load()
        items = ("1", "2", "3", "4", "5")
        item, okPressed = QInputDialog.getItem(self, "Set Alarm", "Repetitions:", items, 0, False)
        if okPressed and item:
            datasave["numberRep"] = int(item)
            Data.save(datasave)

    def play_alarm(self):
        datasave = Data.load()
        beepy.beep(sound=datasave["alarm"])

    def change_voice(self):
        datasave = Data.load()
        items = ("Male", "Female")
        item, okPressed = QInputDialog.getItem(self, "Voice Settings", "Voice type:", items, 0, False)
        if okPressed and item:
            datasave["voice"] = 0 if item == "Male" else 1
            Data.save(datasave)

    def change_alarm_text(self):
        datasave = Data.load()
        text, okPressed = QInputDialog.getText(self, "Change Speech", "Speech:", QLineEdit.Normal, "")
        if okPressed and text:
            datasave["AlarmText"] = text
            Data.save(datasave)

    def play_alarm_voice(self):
        datasave = Data.load()
        SettingsFunctions.Speak(datasave["AlarmText"])

    def set_default(self):
        Data.setToDefault()

if __name__ == "__main__":
    db_func.init_db()  # Initialize the database
    app = QtWidgets.QApplication(sys.argv)
    MainWindow = QtWidgets.QMainWindow()
    ui = SettingsForm("Surveillance Camera")
    ui.setupUi(MainWindow)
    MainWindow.show()
    sys.exit(app.exec_())
