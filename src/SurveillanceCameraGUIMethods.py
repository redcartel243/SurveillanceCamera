import cv2

from src.device import list_capture_devices, get_device_info
import sys
from PyQt5.QtCore import QTimer, QThread, pyqtSignal, QEvent, Qt
from PyQt5.QtWidgets import QApplication, QMainWindow, QMenu, QAction, QMessageBox, QLabel, QDialog, QSizePolicy, QScrollArea
from PyQt5.QtGui import QPixmap, QImage, QPalette
from PyQt5.QtMultimedia import QCamera, QCameraInfo, QMediaPlayer, QMediaContent
from PyQt5.QtMultimediaWidgets import QVideoWidget
from CaptureIpCameraFramesWorker import CaptureIpCameraFramesWorker
from GUI.SurveillanceCameraGUI import Ui_MainWindow
from ip_address_dialog import IPAddressDialog
from face_recognition_service import FaceRecognitionService
import logging

logging.basicConfig(level=logging.INFO)

class MethodMapping(Ui_MainWindow, QMainWindow):
    def __init__(self, title=""):
        QMainWindow.__init__(self)
        self.title = title
        self.context_actions = ['Change Camera', 'Change Mapping', 'Show', 'Properties', 'Turn Off']
        self.available_cameras = list_capture_devices()
        self.selected_camera_id = None
        self.context_button = None

        self.camera = None
        self.cap = None
        self.ip_camera_thread = None
        self.face_recognition_thread = None

        self.view_camera_1_id = None
        self.view_camera_2_id = None
        self.ip_cameras = []

        self.use_face_recognition = False

    def setupUi(self, MainWindow):
        super().setupUi(MainWindow)
        MainWindow.setWindowTitle(self.title)
        self.context_button_1.clicked.connect(self.show_context_menu)
        self.context_button_2.clicked.connect(self.show_context_menu)
        self.context_button_3.clicked.connect(self.show_context_menu)
        self.context_button_4.clicked.connect(self.show_context_menu)
        self.view_camera_1.clicked.connect(lambda: self.view_camera(self.view_camera_1_id))
        self.view_camera_2.clicked.connect(lambda: self.view_camera(self.view_camera_2_id))
        self.view_camera_3.clicked.connect(lambda: self.view_camera(self.view_camera_3_id))
        self.view_camera_4.clicked.connect(lambda: self.view_camera(self.view_camera_4_id))
        self.vision_button.clicked.connect(self.toggle_face_recognition)

        # Initialize QLabel for displaying video
        self.video_label = QLabel(self.scrollAreaWidgetContents)
        self.video_label.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Ignored)
        self.video_label.setScaledContents(True)
        self.video_label.setObjectName("video_label")
        self.gridLayout_2.addWidget(self.video_label, 0, 0, 1, 1)

    def toggle_face_recognition(self):
        self.use_face_recognition = not self.use_face_recognition
        if self.use_face_recognition:
            logging.info("Turning on face recognition.")
            self.turn_on_face_recognition(self.selected_camera_id)
        else:
            logging.info("Turning off face recognition.")
            self.turn_on_camera(self.selected_camera_id)

    def turn_on_face_recognition(self, camera_id):
        try:
            if self.cap:
                self.cap.release()
            if self.camera:
                self.camera.stop()
                self.camera = None
            if self.ip_camera_thread:
                self.ip_camera_thread.stop()
                self.ip_camera_thread = None
            if self.face_recognition_thread:
                self.face_recognition_thread.stop()
                self.face_recognition_thread = None

            self.face_recognition_thread = FaceRecognitionService(camera_id)
            self.face_recognition_thread.ImageUpdated.connect(self.update_face_recognition_image)
            self.face_recognition_thread.start()
        except Exception as e:
            logging.error(f"Exception in turn_on_face_recognition: {e}")

    def turn_on_camera(self, camera_id):
        try:
            if self.cap:
                self.cap.release()
            if self.camera:
                self.camera.stop()
                self.camera = None
            if self.ip_camera_thread:
                self.ip_camera_thread.stop()
                self.ip_camera_thread = None
            if self.face_recognition_thread:
                self.face_recognition_thread.stop()
                self.face_recognition_thread = None

            if camera_id is not None:
                if isinstance(camera_id, str):
                    self.video_widget.setVisible(False)
                    self.video_label.setVisible(True)
                    print(f"Trying to connect to IP camera at {camera_id}")
                    self.ip_camera_thread = CaptureIpCameraFramesWorker(camera_id)
                    self.ip_camera_thread.ImageUpdated.connect(self.update_image)
                    self.ip_camera_thread.start()
                    print(f"Connected to IP camera at {camera_id}")
                else:
                    self.video_label.setVisible(False)
                    self.video_widget.setVisible(True)
                    camera_info = QCameraInfo.availableCameras()[camera_id]
                    self.camera = QCamera(camera_info)
                    self.camera.setViewfinder(self.video_widget)
                    self.camera.start()

            self.selected_camera_id = camera_id
        except Exception as e:
            logging.error(f"Exception in turn_on_camera: {e}")

    def update_image(self, image: QImage):
        self.video_label.setPixmap(QPixmap.fromImage(image))
        if self.use_face_recognition:
            self.capture_image_from_label()

    def update_face_recognition_image(self, frame):
        try:
            frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            image = QImage(frame_rgb.data, frame_rgb.shape[1], frame_rgb.shape[0], frame_rgb.strides[0], QImage.Format_RGB888)
            self.video_label.setPixmap(QPixmap.fromImage(image))
        except Exception as e:
            logging.error(f"Exception in update_face_recognition_image: {e}")

    def show_context_menu(self):
        self.context_button = self.sender()
        contextMenu = QMenu(self)
        for action_name in self.context_actions:
            action = QAction(action_name, self)
            contextMenu.addAction(action)
            action.triggered.connect(lambda checked, name=action_name: self.on_action_triggered(name))
        contextMenu.exec_(self.context_button.mapToGlobal(self.context_button.rect().bottomLeft()))

    def show_camera_menu(self):
        try:
            print(self.available_cameras)
            cameraMenu = QMenu(self)
            add_ip_action = QAction("Add IP Address", self)
            add_ip_action.triggered.connect(self.show_ip_address_dialog)
            cameraMenu.addAction(add_ip_action)
            cameraMenu.addSeparator()
            for camera_id in self.available_cameras + self.ip_cameras:
                action = QAction(f'Camera {camera_id}', self)
                cameraMenu.addAction(action)
                action.triggered.connect(lambda checked, cam_id=camera_id: self.assign_camera_to_button(cam_id))
            cameraMenu.exec_(self.context_button.mapToGlobal(self.context_button.rect().bottomLeft()))
        except Exception as e:
            logging.error(f"Exception in show_camera_menu: {e}")

    def show_ip_address_dialog(self):
        dialog = IPAddressDialog(self)
        if dialog.exec_() == QDialog.Accepted:
            ip_address = str(dialog.get_ip_address())
            self.ip_cameras.append(ip_address)
            self.show_message(f'IP Camera {ip_address} added')

    def assign_camera_to_button(self, camera_id):
        if self.context_button == self.context_button_1:
            self.view_camera_1_id = camera_id
        elif self.context_button == self.context_button_2:
            self.view_camera_2_id = camera_id
        elif self.context_button == self.context_button_3:
            self.view_camera_3_id = camera_id
        elif self.context_button == self.context_button_4:
            self.view_camera_4_id = camera_id
        self.show_message(f'Camera {camera_id} assigned')

    def view_camera(self, camera_id):
        self.turn_on_camera(camera_id)
        self.show_message(f'Viewing camera {camera_id}')

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
