import cv2
from src.device import list_capture_devices, get_device_info
import numpy as np
import logging
import sys
from PyQt5.QtCore import QTimer, QThread, pyqtSignal, Qt
from PyQt5.QtWidgets import QApplication, QMainWindow, QMenu, QAction, QMessageBox, QLabel, QDialog, QSizePolicy, QScrollArea, QVBoxLayout, QGridLayout, QWidget, QPushButton
from PyQt5.QtGui import QPixmap, QImage, QPalette
from PyQt5.QtMultimedia import QCamera, QCameraInfo
from CaptureIpCameraFramesWorker import CaptureIpCameraFramesWorker
from GUI.SurveillanceCameraGUI import Ui_MainWindow
from ip_address_dialog import IPAddressDialog
from face_recognition_service import FaceRecognitionService

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
        self.view_camera_3_id = None
        self.view_camera_4_id = None
        self.ip_cameras = []

        self.use_face_recognition = False
        self.is_expanded = False  # Track the expanded state

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
        self.expand_Button.clicked.connect(self.toggle_expand_video)

        # Initialize QLabel for displaying video
        self.video_label = QLabel(self.scrollAreaWidgetContents)
        self.video_label.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.video_label.setScaledContents(True)
        self.video_label.setObjectName("video_label")

        # Create a widget to hold the video and button
        self.video_widget_container = QWidget(self.scrollAreaWidgetContents)
        self.video_widget_container.setLayout(QGridLayout())
        self.video_widget_container.layout().addWidget(self.video_label, 0, 0)
        self.video_widget_container.layout().addWidget(self.expand_Button, 0, 0, Qt.AlignBottom | Qt.AlignRight)

        self.gridLayout_2.addWidget(self.video_widget_container, 0, 0, 1, 1)

    def toggle_face_recognition(self):
        self.use_face_recognition = not self.use_face_recognition
        if self.use_face_recognition:
            logging.info("Turning on face recognition.")
            self.turn_on_face_recognition(self.selected_camera_id)
        else:
            logging.info("Turning off face recognition.")
            self.turn_on_camera(self.selected_camera_id)

    def toggle_expand_video(self):
        if not self.is_expanded:
            # Save the current geometry before expanding
            self.saved_geometry = self.video_widget_container.geometry()

            # Set the video label and button as a new window
            self.video_label.setParent(None)
            self.expand_Button.setParent(None)

            # Create a new layout for the full-screen view
            self.fullscreen_layout = QGridLayout()
            self.fullscreen_container = QWidget()
            self.fullscreen_container.setLayout(self.fullscreen_layout)

            # Add video label and button to the full-screen layout
            self.fullscreen_layout.addWidget(self.video_label, 0, 0)
            self.fullscreen_layout.addWidget(self.expand_Button, 0, 0)
            self.fullscreen_layout.setAlignment(self.expand_Button, Qt.AlignBottom | Qt.AlignRight)

            self.fullscreen_container.showFullScreen()
            self.is_expanded = True
        else:
            # Restore the original state
            self.video_label.setParent(self.video_widget_container)
            self.expand_Button.setParent(self.video_widget_container)

            # Restore the geometry of the original container
            self.video_widget_container.setGeometry(self.saved_geometry)

            # Hide the full-screen container
            self.fullscreen_container.hide()

            # Re-add video label and expand button back to the layout
            self.video_widget_container.layout().addWidget(self.video_label)
            self.video_widget_container.layout().addWidget(self.expand_Button)
            self.video_widget_container.layout().setAlignment(self.expand_Button, Qt.AlignBottom | Qt.AlignRight)

            self.is_expanded = False

    def turn_on_camera(self, camera_id):
        try:
            self.stop_all_threads()
            self.video_label.setVisible(True)
            if camera_id is not None:
                if isinstance(camera_id, str):
                    print(f"Trying to connect to IP camera at {camera_id}")
                    self.ip_camera_thread = CaptureIpCameraFramesWorker(camera_id)
                    self.ip_camera_thread.ImageUpdated.connect(self.update_image)
                    self.ip_camera_thread.start()
                    print(f"Connected to IP camera at {camera_id}")
                else:
                    self.cap = cv2.VideoCapture(camera_id)
                    self.timer = QTimer()
                    self.timer.timeout.connect(self.display_frame)
                    self.timer.start(30)
            self.selected_camera_id = camera_id
        except Exception as e:
            logging.error(f"Exception in turn_on_camera: {e}")

    def stop_all_threads(self):
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

    def display_frame(self):
        ret, frame = self.cap.read()
        if ret:
            image = self.convert_frame_to_qimage(frame)
            self.update_image(image)

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

    def capture_image_from_label(self):
        pixmap = self.video_label.pixmap()
        if pixmap:
            image = pixmap.toImage()
            frame = self.convert_qimage_to_frame(image)
            self.face_recognition_thread.face_recognition_worker.recognize_faces(frame)

    @staticmethod
    def convert_frame_to_qimage(frame):
        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        return QImage(rgb_frame.data, rgb_frame.shape[1], rgb_frame.shape[0], rgb_frame.strides[0], QImage.Format_RGB888)

    @staticmethod
    def convert_qimage_to_frame(image):
        image = image.convertToFormat(QImage.Format_RGB888)
        width, height = image.width(), image.height()
        ptr = image.bits()
        ptr.setsize(image.byteCount())
        return np.array(ptr).reshape(height, width, 3)

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
