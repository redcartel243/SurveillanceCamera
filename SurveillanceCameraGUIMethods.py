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
import time

class MethodMapping(QMainWindow, Ui_MainWindow):
    def __init__(self, title="", user_id=None):
        super().__init__()
        self.title = title
        self.user_id = user_id
        self.context_actions = ['Change Camera', 'Change Mapping', 'Show', 'Properties', 'Turn Off']
        self.available_cameras = []  # List of available cameras
        self.selected_camera_id = None
        self.context_button = None
        self.camera = None
        self.cap = None
        self.ip_camera_thread = None
        self.face_recognition_thread = None
        self.is_expanded = False
        self.ip_cameras = []
        self.video_gif = None
        self.placeholder_image = QPixmap("Black Image.png")
        self.use_face_recognition = False
        self.view_camera_ids = []  # Store camera IDs for all video labels
        self.current_page = 0  # Track the current page of cameras
        self.max_cameras_per_page = 4  # Max cameras to display per page
        self.video_labels = []  # List to hold video labels

        print("MethodMapping initialized")

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
        self.change_map_button.clicked.connect(self.change_map)
        self.next_button.clicked.connect(self.next_page)
        self.previous_button.clicked.connect(self.previous_page)

        central_widget = MainWindow.centralWidget()

        self.video_label = QLabel(central_widget)
        self.video_label.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.video_label.setScaledContents(True)
        self.video_label.setObjectName("video_label")
        self.video_label.setMinimumSize(700, 700)
        self.video_label.setAlignment(Qt.AlignCenter)
        self.video_label.setContentsMargins(10, 10, 10, 10)

        self.video_widget_container = QWidget(self)
        self.video_layout = QGridLayout(self.video_widget_container)
        self.video_widget_container.setLayout(self.video_layout)
        self.video_widget_container.layout().addWidget(self.video_label, 0, 0)
        self.video_widget_container.layout().addWidget(self.expand_Button, 0, 0, Qt.AlignBottom | Qt.AlignRight)
        self.video_widget_container.layout().addWidget(self.vision_button, 0, 0, Qt.AlignTop | Qt.AlignLeft)

        self.video_widget_container.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

        self.gridLayout_2.addWidget(self.video_widget_container, 0, 0, 1, 1)
        self.gridLayout_2.setContentsMargins(0, 0, 0, 0)

        self.populate_rooms_combobox()
        self.populate_mapping_list()
        self.rooms_list_combobox.activated.connect(self.show_combobox_context_menu)

        self.show_placeholder_image()



    def next_page(self):
        """Move to the next page of camera feeds."""
        if (self.current_page + 1) * self.max_cameras_per_page < len(self.available_cameras):
            self.current_page += 1
            self.update_video_display()

    def previous_page(self):
        """Move to the previous page of camera feeds."""
        if self.current_page > 0:
            self.current_page -= 1
            self.update_video_display()

    
    def update_video_display(self):
        """Update the video display based on the current page of cameras."""
        # Clear existing layout
        for i in reversed(range(self.video_layout.count())): 
            self.video_layout.itemAt(i).widget().setParent(None)

        # Display video labels for the current page
        start_index = self.current_page * self.max_cameras_per_page
        end_index = start_index + self.max_cameras_per_page
        current_cameras = self.available_cameras[start_index:end_index]

        self.video_labels = []  # Clear the video labels list

        for i, camera_id in enumerate(current_cameras):
            video_label = QLabel(self)
            video_label.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
            video_label.setScaledContents(True)
            video_label.setObjectName(f"video_label_{i}")
            video_label.setMinimumSize(300, 300)
            video_label.setPixmap(self.placeholder_image)  # Placeholder until video feed starts
            self.video_layout.addWidget(video_label, i // 2, i % 2)
            self.video_labels.append(video_label)


    def toggle_face_recognition(self):
        self.use_face_recognition = not self.use_face_recognition
        if self.use_face_recognition:
            print("Turning on face recognition.")
            self.turn_on_face_recognition(self.selected_camera_id)
        else:
            print("Turning off face recognition.")
            self.turn_on_camera(self.selected_camera_id)

    def turn_on_face_recognition(self, camera_id):
        try:
            self.stop_all_threads()
            self.video_label.setVisible(True)
            if camera_id is not None:
                self.face_recognition_thread = FaceRecognitionService(camera_id,'datasets/known_faces', 'datasets/Captures')
                self.face_recognition_thread.ImageUpdated.connect(self.update_image)
                self.face_recognition_thread.FaceRecognized.connect(self.handle_face_recognition)
                self.face_recognition_thread.start()
                print(f"Face recognition started for camera {camera_id}")
            self.selected_camera_id = camera_id
        except Exception as e:
            print(f"Exception in turn_on_face_recognition: {e}")

    def update_image(self, frame):
        try:
            frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            image = QImage(frame_rgb.data, frame_rgb.shape[1], frame_rgb.shape[0], frame_rgb.strides[0],
                           QImage.Format_RGB888)
            if self.video_labels:
                self.video_labels[0].setPixmap(QPixmap.fromImage(image))  # Display on the first video label
        except Exception as e:
            print(f"Exception in update_image: {e}")

    def handle_face_recognition(self, face_locations, face_names):
        try:
            print(f"Faces recognized: {face_names}")
            # Here you can add code to handle the recognized faces
            # For example, update the UI or trigger other actions
        except Exception as e:
            print(f"Exception in handle_face_recognition: {e}")

    def stop_all_threads(self):
        try:
            if hasattr(self, 'face_recognition_thread') and self.face_recognition_thread.isRunning():
                self.face_recognition_thread.stop()
                self.face_recognition_thread.wait()
                print("Face recognition thread stopped")
            if self.cap:
                self.cap.release()
            if self.camera:
                self.camera.stop()
                self.camera = None
            if self.ip_camera_thread:
                self.ip_camera_thread.stop()
                self.ip_camera_thread = None
        except Exception as e:
            print(f"Exception in stop_all_threads: {e}")
        self.show_placeholder_image()

    def turn_on_camera(self, camera_id):
        """Turn on the camera feed for a specific camera ID."""
        if camera_id is None:
            self.show_message("No camera assigned to this slot.")
            return
        try:
            self.stop_all_threads()
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

    def show_placeholder_image(self):
        """Show placeholder image on all labels."""
        for i in range(self.max_cameras_per_page):
            label = QLabel(self)
            label.setPixmap(self.placeholder_image)
            self.video_layout.addWidget(label, i // 2, i % 2)

    def change_map(self):
        file_path, _ = QFileDialog.getOpenFileName(self, "Select Map Image", "", "Image Files (*.png *.jpg *.bmp)")
        if file_path:
            map_image = QPixmap(file_path)
            if not map_image.isNull():
                scaled_image = map_image.scaled(self.map_display.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation)
                self.map_display.setPixmap(map_image)
            else:
                print("Failed to load the image. Check the file format and path.")
        else:
            print("No file selected.")

    def refreshbutton(self):
        new_camera_count = db_func.add_new_cameras()
        self.populate_mapping_list()
        self.show_message(f"Loading cameras finished. {new_camera_count} new cameras added.")

    def populate_mapping_list(self):
        self.mapping_list.clear()
        rooms_with_cameras = db_func.get_all_rooms_with_cameras()
        for room_name, cameras in rooms_with_cameras.items():
            for camera in cameras:
                list_item_text = f"{room_name}: {'Camera ' + camera if camera != 'No cameras assigned' else camera}"
                self.mapping_list.addItem(list_item_text)

    def populate_rooms_combobox(self):
        self.rooms_list_combobox.clear()
        rooms = db_func.get_all_rooms_with_cameras()
        for room_name, cameras in rooms.items():
            camera_list = ', '.join(cameras)
            display_text = f"{room_name}: {camera_list}"
            self.rooms_list_combobox.addItem(display_text)
        self.available_cameras = db_func.get_available_cameras()
        self.update_video_display()

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

    def show_context_menu(self):
        sender = self.sender()
        contextMenu = QMenu(self)
        for action in self.context_actions:
            contextMenu.addAction(action)
        action = contextMenu.exec_(sender.mapToGlobal(sender.rect().bottomLeft()))
        if action:
            self.handle_context_action(action.text(), sender)

    def handle_context_action(self, action, button):
        if action == 'Change Camera':
            self.change_camera(button)
        elif action == 'Change Mapping':
            self.change_mapping(button)
        elif action == 'Show':
            self.show_camera(button)
        elif action == 'Properties':
            self.show_properties(button)
        elif action == 'Turn Off':
            self.turn_off_camera(button)

    def change_camera(self, button):
        try:
            self.free_cameras = db_func.get_cameras()
            self.free_cameras = [int(x) for x in self.free_cameras]
            cameraMenu = QMenu(self)
        
            add_ip_action = QAction("Add IP Address", self)
            add_ip_action.triggered.connect(lambda: self.show_ip_address_dialog(button))
            cameraMenu.addAction(add_ip_action)
            cameraMenu.addSeparator()
        
            for camera_id in self.free_cameras + self.ip_cameras:
                action = QAction(f'Camera {camera_id}', self)
                cameraMenu.addAction(action)
                action.triggered.connect(lambda checked, cam_id=camera_id, btn=button: self.assign_camera_to_button(btn, cam_id))
            
            cameraMenu.exec_(button.mapToGlobal(button.rect().bottomLeft()))
        except Exception as e:
            logging.error(f"Exception in change_camera: {e}")

    
    def show_ip_address_dialog(self, button):
        dialog = IPAddressDialog(self)
        if dialog.exec_():
            ip_address = dialog.get_ip_address()
            self.ip_cameras.append(ip_address)
            self.assign_camera_to_button(button, ip_address)

    def assign_camera_to_button(self, button, camera_id):
        button_to_attribute = {
            self.context_button_1: 'view_camera_1_id',
            self.context_button_2: 'view_camera_2_id',
            self.context_button_3: 'view_camera_3_id',
            self.context_button_4: 'view_camera_4_id'
        }
        
        attribute_name = button_to_attribute.get(button)
        if attribute_name:
            setattr(self, attribute_name, camera_id)
            self.update_button_text(button, f"Camera {camera_id}")
            self.show_message(f'Camera {camera_id} assigned')
        else:
            logging.warning(f"Unrecognized button for camera assignment: {button}")
    
    

    def change_mapping(self, button):
        # Implement change mapping functionality
        pass

    def show_camera(self, button):
        camera_id = self.get_camera_id(button)
        if camera_id is not None:
            self.turn_on_camera(camera_id)

    def show_properties(self, button):
        # Implement show properties functionality
        pass

    def turn_off_camera(self, button):
        self.update_button_text(button, "Camera Off")
        self.stop_all_threads()
        self.show_placeholder_image()

    def update_button_text(self, button, text):
        button.setText(text)

    def get_camera_id(self, button):
        text = button.text()
        if text.startswith("IP Camera"):
            index = int(text.split()[-1]) - 1
            return self.ip_cameras[index]
        elif text.startswith("Camera"):
            return int(text.split()[-1])
        return None

    def view_camera(self, camera_id):
        if camera_id is None:
            self.show_message("No camera assigned to this Button. Please assign a camera first.")
            return

        self.turn_on_camera(camera_id)
        self.show_message(f"Viewing camera {camera_id}")
        

    def show_message(self, message):
        QMessageBox.information(self, "Message", message)

    def display_frame(self):
        ret, frame = self.cap.read()
        if ret:
            self.update_image(frame)

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