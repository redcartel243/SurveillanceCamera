from src import db_func, Data
from src.device import list_capture_devices, get_device_info
import sys
from PyQt5.QtWidgets import QApplication, QMainWindow, QMenu, QAction, QMessageBox, QPushButton, QVBoxLayout, QWidget
from PyQt5.QtMultimedia import QCamera, QCameraInfo
from PyQt5.QtMultimediaWidgets import QVideoWidget
from face_recognition_service import FaceRecognitionService
from GUI.SurveillanceCameraGUI import Ui_MainWindow
from PyQt5 import QtWidgets


class MethodMapping(Ui_MainWindow, QMainWindow):
    def __init__(self, title=""):
        QMainWindow.__init__(self)
        self.title = title
        self.context_actions = ['Change Camera', 'Change Mapping', 'Show', 'Properties', 'Turn Off']  # List of action names
        self.available_cameras = list_capture_devices()
        self.selected_camera_id = None
        self.context_button = None

        # Initialize camera and video widget
        self.camera = None
        self.video_widget = QVideoWidget()
        self.setCentralWidget(self.video_widget)

    def setupUi(self, MainWindow):
        super().setupUi(MainWindow)
        MainWindow.setWindowTitle(self.title)
        # Here map buttons with methods
        self.context_button_1.clicked.connect(self.show_context_menu)
        self.context_button_2.clicked.connect(self.show_context_menu)
        self.context_button_3.clicked.connect(self.show_context_menu)
        self.context_button_4.clicked.connect(self.show_context_menu)

    def turn_on_camera(self, camera_id):
        if self.camera:
            self.camera.stop()

        camera_info = QCameraInfo.availableCameras()[camera_id]
        self.camera = QCamera(camera_info)
        self.camera.setViewfinder(self.video_widget)
        self.camera.start()

        self.selected_camera_id = camera_id

    def show_context_menu(self):
        self.context_button = self.sender()
        contextMenu = QMenu(self)
        for action_name in self.context_actions:
            action = QAction(action_name, self)
            contextMenu.addAction(action)
            # Connect the action to a slot
            action.triggered.connect(lambda checked, name=action_name: self.on_action_triggered(name))
        # Display the context menu at the position of the button
        contextMenu.exec_(self.context_button.mapToGlobal(self.context_button.rect().bottomLeft()))

    def show_camera_menu(self):
        try:
            print(self.available_cameras)
            cameraMenu = QMenu(self)
            for camera_id in self.available_cameras:
                action = QAction(f'Camera {camera_id}', self)
                cameraMenu.addAction(action)
                # Connect the action to a slot
                action.triggered.connect(lambda checked, cam_id=camera_id: self.change_camera(cam_id))
            # Display the camera menu at the position of the original button
            cameraMenu.exec_(self.context_button.mapToGlobal(self.context_button.rect().bottomLeft()))
        except Exception as e:
            print(e)

    def change_camera(self, camera_id):
        self.turn_on_camera(camera_id)
        self.show_message(f'Camera {camera_id} selected')

    def show_camera_properties(self):
        if self.selected_camera_id is not None:
            info = get_device_info(self.selected_camera_id)
            if info:
                properties = "\n".join([f"{key}: {value}" for key, value in info.items()])
                self.show_message(f"Properties of Camera {self.selected_camera_id}:\n{properties}")
            else:
                self.show_message("Failed to retrieve camera properties.")
        else:
            self.show_message("No camera selected.")

    def on_action_triggered(self, action_name):
        if action_name == 'Change Camera':
            self.show_camera_menu()
        elif action_name == 'Properties':
            self.show_camera_properties()
        elif action_name == 'Turn Off':
            self.turn_on_camera(None)
            self.show_message("Camera turned off")
        else:
            self.show_message(f"{action_name} was clicked")

    def show_message(self, message):
        QMessageBox.information(self, "Message", message)


if __name__ == "__main__":
    app = QApplication(sys.argv)
    MainWindow = QMainWindow()
    ui = MethodMapping("Surveillance Camera")
    ui.setupUi(MainWindow)
    MainWindow.show()
    sys.exit(app.exec_())
