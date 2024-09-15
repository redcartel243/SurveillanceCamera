import cv2
import numpy as np
import logging
import sys
from PyQt5.QtCore import QTimer, Qt
from PyQt5.QtWidgets import QApplication, QMainWindow, QMenu, QAction, QMessageBox, QLabel, QWidget, QGridLayout, \
    QInputDialog, QSizePolicy, QDialog, QFileDialog, QVBoxLayout, QPushButton
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
        self.ip_camera_threads = {}  # Use a dictionary to handle multiple IP camera threads
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
        self.caps = {}  # Dictionary to hold VideoCapture objects for each camera
        self.timers = {}  # Dictionary to hold QTimer objects for each camera

        print("MethodMapping initialized")

    def setupUi(self, MainWindow):
        super().setupUi(MainWindow)
        MainWindow.setWindowTitle(self.title)
        self.context_button_1.clicked.connect(self.show_context_menu)
        self.context_button_2.clicked.connect(self.show_context_menu)
        self.context_button_3.clicked.connect(self.show_context_menu)
        self.context_button_4.clicked.connect(self.show_context_menu)
        self.vision_button.clicked.connect(self.toggle_face_recognition)
        self.expand_Button.clicked.connect(self.toggle_expand_video)
        self.refresh_button.clicked.connect(self.refreshbutton)
        self.edit_mapping.clicked.connect(self.open_mapping_tab)
        self.add_room_button.clicked.connect(self.add_room)
        self.change_map_button.clicked.connect(self.change_map)
        self.next_button.clicked.connect(self.next_page)
        self.previous_button.clicked.connect(self.previous_page)

        # Initialize video display layout dynamically
        self.video_widget_container = QWidget(self)
        self.video_layout = QGridLayout(self.video_widget_container)
        self.video_widget_container.setLayout(self.video_layout)
        self.gridLayout_2.addWidget(self.video_widget_container, 0, 0, 1, 1)

        # Populate combo boxes, and display video feeds
        self.populate_rooms_combobox()
        self.populate_mapping_list_and_camera_view()
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
    "Modifying this"
    def update_video_display(self):
        """Update the video display based on the current page of cameras."""
        try:
                # Stop all camera feeds before updating
            self.stop_all_threads()

            # Clear existing layout
            while self.video_layout.count():
                item = self.video_layout.takeAt(0)
                widget = item.widget()
                if widget is not None:
                    widget.setParent(None)

            # Display video labels for the current page
            start_index = self.current_page * self.max_cameras_per_page
            end_index = min(start_index + self.max_cameras_per_page, len(self.view_camera_ids))
            current_cameras = self.view_camera_ids[start_index:end_index]
            print("Current cameras: {cm}".format(cm=current_cameras))

            self.video_labels = []  # Clear the video labels list

            for i, camera_id in enumerate(current_cameras):
                video_label = QLabel(self)
                video_label.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
                video_label.setScaledContents(True)
                video_label.setObjectName(f"video_label_{i}")
                video_label.setMinimumSize(300, 300)
                video_label.setPixmap(self.placeholder_image)  # Placeholder until video feed starts
                self.video_layout.addWidget(video_label, i // 2, i % 2)
                #print(video_label.size,camera_id,current_cameras)
                self.video_labels.append(video_label)

                # Turn on camera and display the feed
                self.turn_on_camera(camera_id, i)
            

            # If fewer cameras than slots, fill with placeholders
            for i in range(len(current_cameras), self.max_cameras_per_page):
                placeholder_label = QLabel(self)
                placeholder_label.setPixmap(self.placeholder_image)
                self.video_layout.addWidget(placeholder_label, i // 2, i % 2)

            # Handle pagination buttons
            total_pages = (len(self.view_camera_ids) - 1) // self.max_cameras_per_page
            self.next_button.setEnabled(self.current_page < total_pages)
            self.previous_button.setEnabled(self.current_page > 0)
        except Exception as e:
            print(e)

    def toggle_face_recognition(self):
        self.use_face_recognition = not self.use_face_recognition
        if self.use_face_recognition:
            print("Turning on face recognition.")
            self.turn_on_face_recognition(self.selected_camera_id)
        else:
            print("Turning off face recognition.")
            self.update_video_display()

    def turn_on_face_recognition(self, camera_id):
        try:
            self.stop_all_threads()
            if camera_id is not None:
                self.face_recognition_thread = FaceRecognitionService(camera_id, 'datasets/known_faces', 'datasets/Captures')
                self.face_recognition_thread.ImageUpdated.connect(lambda image: self.update_image(image, self.video_labels[0]))
                self.face_recognition_thread.FaceRecognized.connect(self.handle_face_recognition)
                self.face_recognition_thread.start()
                print(f"Face recognition started for camera {camera_id}")
                self.selected_camera_id = camera_id
            else:
                print("No camera selected for face recognition.")
        except Exception as e:
            print(f"Exception in turn_on_face_recognition: {e}")

    def update_image(self, image: QImage, video_label: QLabel):
        """Updates the specified video label with the new image."""
        
        video_label.setPixmap(QPixmap.fromImage(image))
        video_label.setScaledContents(True)

    def display_frame(self, video_label: QLabel, cap):
        """Displays the current frame from the camera in the specified video label."""
        try:
            ret, frame = cap.read()
            if not ret:
                print("Failed to capture frame from camera")
                return

            # Convert frame to RGB and then QImage
            frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            height, width, channel = frame_rgb.shape
            print(height, width, channel)
            bytes_per_line = 3 * frame_rgb.strides[0]

            q_img = QImage(frame_rgb.data, frame_rgb.shape[1], frame_rgb.shape[0],frame_rgb.strides[0] , QImage.Format_RGB888)

            # Set the QLabel to show the new frame
            video_label.setPixmap(QPixmap.fromImage(q_img))

        except Exception as e:
            print(f"Exception in display_frame: {e}")

    def handle_face_recognition(self, face_locations, face_names):
        try:
            print(f"Faces recognized: {face_names}")
        except Exception as e:
            print(f"Exception in handle_face_recognition: {e}")

    def stop_all_threads(self):
        try:
            # Stop face recognition thread
            if self.face_recognition_thread and self.face_recognition_thread.isRunning():
                self.face_recognition_thread.stop()
                self.face_recognition_thread.wait()
                print("Face recognition thread stopped")
                self.face_recognition_thread = None

            # Stop all camera feeds
            for cap in self.caps.values():
                cap.release()
            self.caps.clear()

            for timer in self.timers.values():
                timer.stop()
            self.timers.clear()

            for thread in self.ip_camera_threads.values():
                thread.stop()
            self.ip_camera_threads.clear()

        except Exception as e:
            print(f"Exception in stop_all_threads: {e}")

    def turn_on_camera(self, camera_id, label_index):
        """Turns on the specified camera and displays the feed in the corresponding video label."""
        try:
            # Ensure all previous threads and feeds are stopped
            self.stop_all_threads()

            if not (0 <= label_index < len(self.video_labels)):
                print(f"Invalid label index: {label_index}")
                return

            video_label = self.video_labels[label_index]
            video_label.setVisible(True)

            if camera_id:
                if isinstance(camera_id, str) and len(camera_id)>16:  # IP camera case
                    print(f"Trying to connect to IP camera at {camera_id}")
                    ip_thread = CaptureIpCameraFramesWorker(camera_id)
                    ip_thread.ImageUpdated.connect(lambda image: self.update_image(image, video_label))
                    ip_thread.start()
                    self.ip_camera_threads[label_index] = ip_thread
                    print(f"Connected to IP camera at {camera_id}")
                else:
                    print(f"Trying to connect to local camera {camera_id}")
                    cap = cv2.VideoCapture(int(camera_id))
                    if cap.isOpened():
                        self.caps[label_index] = cap
                        print(f"Camera {camera_id} opened successfully")
                        timer = QTimer()
                        timer.timeout.connect(lambda: self.display_frame(video_label, cap))
                        timer.start(30)  # Refresh rate in milliseconds (30 ms = ~33 fps)
                        self.timers[label_index] = timer
                    else:
                        print(f"Failed to open camera {camera_id}")
            self.selected_camera_id = camera_id

        except Exception as e:
            print(f"Exception in turn_on_camera: {e}")

    def show_placeholder_image(self):
        """Show placeholder image on all labels."""
        while self.video_layout.count():
            item = self.video_layout.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.setParent(None)

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
                self.map_display.setPixmap(scaled_image)
            else:
                print("Failed to load the image. Check the file format and path.")
        else:
            print("No file selected.")

    def refreshbutton(self):
        new_camera_count = db_func.add_new_cameras()
        self.populate_mapping_list_and_camera_view()
        self.show_message(f"Loading cameras finished. {new_camera_count} new cameras added.")

    def populate_mapping_list_and_camera_view(self):
        self.mapping_list.clear()
        rooms_with_cameras = db_func.get_all_rooms_with_cameras()
        print(rooms_with_cameras)

        # Create a list of all cameras, assigned and unassigned, sorted alphabetically
        all_cameras = set()
        for cameras in rooms_with_cameras.values():
            all_cameras.update(cameras)
        available_cameras = db_func.get_available_cameras()  # Get unassigned cameras
        all_cameras.update(available_cameras)
        all_cameras.update(self.ip_cameras)  # Include IP cameras
        # Sort all cameras alphabetically (handling IP cameras with potential numbers in their names)
        sorted_cameras = sorted(all_cameras, key=lambda x: str(x))

        # Populate the mapping list (with room names for assigned cameras)
        for room_name, cameras in rooms_with_cameras.items():
            for camera in cameras:
                list_item_text = f"{room_name}: Camera {camera}"
                self.mapping_list.addItem(list_item_text)

        # Update the video labels to display camera feeds for all cameras (up to 4 per page)
        self.view_camera_ids = sorted_cameras

        # Start and display the camera feeds automatically on app startup
        self.update_video_display()

        print(f"All cameras (alphabetically sorted): {sorted_cameras}")

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
        # Implement the logic to expand the video to full screen
        pass

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
        pass

    def show_camera(self, button):
        camera_id = self.get_camera_id(button)
        if camera_id is not None:
            self.selected_camera_id = camera_id
            self.update_video_display()

    def show_properties(self, button):
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

    def show_message(self, message):
        QMessageBox.information(self, "Information", message)

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