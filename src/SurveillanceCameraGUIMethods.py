from src import db_func, Data
import sys
from PyQt5.QtWidgets import QApplication
from face_recognition_service import FaceRecognitionService
from GUI.SurveillanceCameraGUI import Ui_MainWindow
from PyQt5 import QtWidgets
from PyQt5.QtWidgets import *
class MethodMapping(Ui_MainWindow, QMainWindow):
    def __init__(self, title=""):
        QMainWindow.__init__(self)
        self.title = title



    def setupUi(self, MainWindow):
        super().setupUi(MainWindow)
        MainWindow.setWindowTitle(self.title)
        #Here map buttons with methods