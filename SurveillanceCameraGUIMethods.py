import cv2
import numpy as np
import logging
import sys
from PyQt5.QtCore import QTimer, Qt
from PyQt5.QtWidgets import QApplication, QMainWindow, QMenu, QAction, QMessageBox, QLabel, QWidget, QGridLayout, \
    QInputDialog, QSizePolicy, QDialog, QFileDialog, QVBoxLayout
from PyQt5.QtGui import QPixmap, QImage
from src.CaptureIpCameraFramesWorker import CaptureIpCameraFramesWorker
from GUI.SurveillanceCameraGUI import Ui_MainWindow
from src.ip_address_dialog import IPAddressDialog
from src.face_recognition_service import FaceRecognitionService
from src import db_func

logging.basicConfig(level=logging.INFO)


class MethodMapping(QMainWindow, Ui_MainWindow):
    def __init__(self, title="", user_id=None):
        super().__init__()
        self.title = title
        self.user_id = user_id  # Set the user_id from the login window
        self.context_actions = ['Change Camera', 'Change Mapping', 'Show', 'Properties', 'Turn Off']
        self.available_cameras = None
        self.selected_camera_id = None
        self.context_button = None
        self.camera = None
        self.cap = None
        self.ip_camera_thread = None
        self.face_recognition_thread = None
        self.is_expanded = False  # Track the expanded state
        self.ip_cameras = []
        self.video_gif = None  # QMovie for displaying the GIF
        self.placeholder_image = QPixmap("Black Image.png")
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
        self.expand_Button.clicked.connect(self.toggle_expand_video)
        self.refresh_button.clicked.connect(self.refreshbutton)
        self.edit_mapping.clicked.connect(self.open_mapping_tab)
        self.add_room_button.clicked.connect(self.add_room)

        # Additional button and label for map change
        self.change_map_button.clicked.connect(self.change_map)

        # Get the central widget of the MainWindow
        central_widget = MainWindow.centralWidget()

        # Initialize QLabel for displaying video
        self.video_label = QLabel(central_widget)
        self.video_label.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.video_label.setScaledContents(True)
        self.video_label.setObjectName("video_label")
        self.video_label.setMinimumSize(700, 700)  # Set a reasonable minimum size
        self.video_label.setAlignment(Qt.AlignCenter)
        self.video_label.setContentsMargins(10, 10, 10, 10)  # Optional, for better padding

        # Create a widget to hold the video and button
        self.video_widget_container = QWidget(central_widget)
        self.video_widget_container.setLayout(QGridLayout())
        self.video_widget_container.layout().addWidget(self.video_label, 0, 0)
        self.video_widget_container.layout().addWidget(self.expand_Button, 0, 0, Qt.AlignBottom | Qt.AlignRight)
        self.video_widget_container.layout().addWidget(self.vision_button, 0, 0, Qt.AlignTop | Qt.AlignLeft)

        # Ensure the container expands to fill the space
        self.video_widget_container.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

        self.gridLayout_2.addWidget(self.video_widget_container, 0, 0, 1, 1)
        self.gridLayout_2.setContentsMargins(0, 0, 0, 0)  # Remove margins around the grid

        # Populate the combobox with rooms and cameras
        self.populate_rooms_combobox()
        self.populate_mapping_list()
        self.rooms_list_combobox.activated.connect(self.show_combobox_context_menu)

        # Show the placeholder image when the video is off
        self.show_placeholder_image()

    def change_map(self):
        # Open a file dialog to select an image file
        file_path, _ = QFileDialog.getOpenFileName(self, "Select Map Image", "", "Image Files (*.png *.jpg *.bmp)")

        if file_path:  # Check if a file was selected
            # Load the selected image into a QPixmap
            map_image = QPixmap(file_path)

            if not map_image.isNull():  # Check if the image loaded successfully
                # Scale the image to fit the label size, keeping the aspect ratio
                scaled_image = map_image.scaled(self.map_display.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation)

                # Set the scaled image to the map_display label
                self.map_display.setPixmap(map_image)
            else:
                print("Failed to load the image. Check the file format and path.")
        else:
            print("No file selected.")

    def refreshbutton(self):
        new_camera_count = db_func.add_new_cameras()
        print(new_camera_count)
        self.populate_mapping_list()
        self.show_message(f"Loading cameras finished. {new_camera_count} new cameras added.")

    def refresh(self):
        self.available_cameras = db_func.get_available_cameras()
        self.populate_rooms_combobox()

    def populate_mapping_list(self):
        self.mapping_list.clear()
        rooms_with_cameras = db_func.get_all_rooms_with_cameras()

        for room_name, cameras in rooms_with_cameras.items():
            for camera in cameras:
                if camera == "No cameras assigned":
                    list_item_text = f"{room_name}: {camera}"  # Because here no camera assigned
                else:
                    list_item_text = f"{room_name}: Camera {camera}"
                self.mapping_list.addItem(list_item_text)

    def populate_rooms_combobox(self):
        self.rooms_list_combobox.clear()
        rooms = db_func.get_all_rooms_with_cameras()
        for room_name, cameras in rooms.items():
            camera_list = ', '.join(cameras)
            display_text = f"{room_name}: {camera_list}"
            self.rooms_list_combobox.addItem(display_text)
        self.available_cameras = db_func.get_available_cameras()

    def show_combobox_context_menu(self, index):
        if index < 0:
            return

        room_text = self.rooms_list_combobox.itemText(index)
        room_name, camera_list = room_text.split(': ')

        contextMenu = QMenu(self)

        delete_room_action = QAction("Delete Room", self)
        delete_assignment_action = QAction("Delete Assignment", self)
        modify_assignment_action = QAction("Modify Assignment", self)

        contextMenu.addAction(delete_room_action)
        contextMenu.addAction(delete_assignment_action)
        contextMenu.addAction(modify_assignment_action)

        room_id = db_func.get_room_id_by_name(room_name)

        delete_room_action.triggered.connect(lambda: self.delete_room(room_id))
        delete_assignment_action.triggered.connect(lambda: self.delete_assignment(room_id, camera_list))
        modify_assignment_action.triggered.connect(lambda: self.modify_assignment(room_id))

        # Show the context menu
        contextMenu.exec_(self.rooms_list_combobox.mapToGlobal(self.rooms_list_combobox.rect().bottomLeft()))

    def add_room(self):
        room_name, ok = QInputDialog.getText(self, "Add Room", "Enter room name:")
        if ok and room_name:
            rooms = db_func.get_rooms(self.user_id)
            if any(room_name == existing_name for _, existing_name in rooms):
                self.show_message(f"Room '{room_name}' already exists.")
            else:
                db_func.add_room(self.user_id, room_name)
                self.populate_rooms_combobox()
                self.show_message(f"Room '{room_name}' added successfully.")

    def delete_room(self, room_id):
        db_func.delete_room(room_id)
        self.populate_rooms_combobox()
        self.show_message(f"Room ID '{room_id}' and its assignments deleted.")

    def delete_assignment(self, room_id, camera_list):
        camera_ids = camera_list.split(', ')
        for camera_id in camera_ids:
            db_func.delete_assignment(room_id, camera_id)
        self.populate_rooms_combobox()
        self.show_message(f"Assignments for Room ID '{room_id}' deleted.")

    def modify_assignment(self, room_id):
        available_cameras = db_func.get_available_cameras()
        cameraMenu = QMenu(self)
        for camera_id in available_cameras:
            print(camera_id)
            action = QAction(f'Camera {camera_id}', self)
            cameraMenu.addAction(action)
            action.triggered.connect(lambda checked, cam_id=camera_id: self.assign_camera_to_room(room_id, cam_id))
        cameraMenu.exec_(self.rooms_list_combobox.mapToGlobal(self.rooms_list_combobox.rect().bottomLeft()))

    def assign_camera_to_room(self, room_id, camera_id):
        room_name = db_func.get_room_name_by_id(room_id)
        db_func.assign_camera_to_room(room_id, camera_id)
        self.populate_rooms_combobox()
        self.show_message(f"Camera {camera_id} assigned to room '{room_name}' (ID: {room_id}).")

    def open_mapping_tab(self):
        self.tabWidget.setCurrentIndex(self.tabWidget.indexOf(self.mapping_tab))

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
            self.saved_geometry = self.video_widget_container.geometry()
            self.video_label.setParent(None)
            self.expand_Button.setParent(None)

            self.fullscreen_layout = QGridLayout()
            self.fullscreen_container = QWidget()
            self.fullscreen_container.setLayout(self.fullscreen_layout)

            self.fullscreen_layout.addWidget(self.video_label, 0, 0)
            self.fullscreen_layout.addWidget(self.expand_Button, 0, 0)
            self.fullscreen_layout.setAlignment(self.expand_Button, Qt.AlignBottom | Qt.AlignRight)

            self.fullscreen_container.showFullScreen()
            self.is_expanded = True
        else:
            self.video_label.setParent(self.video_widget_container)
            self.expand_Button.setParent(self.video_widget_container)

            self.video_widget_container.setGeometry(self.saved_geometry)

            self.fullscreen_container.hide()

            self.video_widget_container.layout().addWidget(self.video_label)
            self.video_widget_container.layout().addWidget(self.expand_Button)
            self.video_widget_container.layout().setAlignment(self.expand_Button, Qt.AlignBottom | Qt.AlignRight)

            self.video_label.setScaledContents(True)
            self.video_label.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
            self.video_widget_container.resize(self.video_widget_container.size())
            self.video_label.update()

            self.is_expanded = False
    
    def turn_on_face_recognition(self, camera_id):
        try:
            self.stop_all_threads()
            self.video_label.setVisible(True)
            if camera_id is not None:
                self.face_recognition_thread = FaceRecognitionService(camera_id)
                self.face_recognition_thread.ImageUpdated.connect(self.update_face_recognition_image)
                self.face_recognition_thread.start()
                print(f"Face recognition started for camera {camera_id}")
            self.selected_camera_id = camera_id
        except Exception as e:
            logging.error(f"Exception in turn_on_face_recognition: {e}")

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
        # Show the placeholder image when the video is off
        self.show_placeholder_image()

    # Method to display a placeholder image when the video is off
    def show_placeholder_image(self):
        # Load the placeholder image
        self.placeholder_image = QPixmap("Black Image.png")

        # Debug: Check if the image is loaded
        if self.placeholder_image.isNull():
            print("Failed to load the image. Check the path and format.")
            return

        # Scale the image to fit the QLabel size while maintaining aspect ratio
        scaled_placeholder = self.placeholder_image.scaled(
            self.video_label.size(),
            Qt.KeepAspectRatio,
            Qt.SmoothTransformation
        )

        # Set the scaled image to the QLabel
        self.video_label.setPixmap(scaled_placeholder)
        self.video_label.setAlignment(Qt.AlignCenter)  # Center the image within the QLabel

        # Debug: Print sizes to understand scaling issues
        print("Label size:", self.video_label.size())
        print("Image size before scaling:", self.placeholder_image.size())
        print("Image size after scaling:", scaled_placeholder.size())

    def display_frame(self):
        ret, frame = self.cap.read()
        if ret:
            frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            height, width, channel = frame.shape
            bytes_per_line = 3 * width
            q_img = QImage(frame.data, width, height, bytes_per_line, QImage.Format_RGB888)
            scaled_q_img = q_img.scaled(self.video_label.size(), Qt.KeepAspectRatio)
            self.video_label.setPixmap(QPixmap.fromImage(scaled_q_img))

    def update_image(self, image: QImage):
        self.video_label.setPixmap(QPixmap.fromImage(image))
        if self.use_face_recognition:
            self.capture_image_from_label()

    def update_face_recognition_image(self, frame):
        try:
            frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            image = QImage(frame_rgb.data, frame_rgb.shape[1], frame_rgb.shape[0], frame_rgb.strides[0],
                           QImage.Format_RGB888)
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
        return QImage(rgb_frame.data, rgb_frame.shape[1], rgb_frame.shape[0], rgb_frame.strides[0],
                      QImage.Format_RGB888)

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
            self.free_cameras = db_func.get_cameras()
            self.free_cameras = [int(x) for x in self.free_cameras]
            cameraMenu = QMenu(self)
            add_ip_action = QAction("Add IP Address", self)
            add_ip_action.triggered.connect(self.show_ip_address_dialog)
            cameraMenu.addAction(add_ip_action)
            cameraMenu.addSeparator()
            for camera_id in self.free_cameras + self.ip_cameras:
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
            info = db_func.get_device_info(self.selected_camera_id)
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
    from GUI.LoginGUI import LoginWindow

    db_func.init_db()

    app = QApplication(sys.argv)
    login_window = LoginWindow()

    if login_window.exec_() == QDialog.Accepted:
        user_id = login_window.get_user_id()
        MainWindow = QMainWindow()
        ui = MethodMapping("Surveillance Camera", user_id=user_id)
        ui.setupUi(MainWindow)
        MainWindow.show()

    sys.exit(app.exec_())
