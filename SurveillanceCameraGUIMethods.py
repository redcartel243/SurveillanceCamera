import cv2
import numpy as np
import logging
import sys
from PyQt5.QtCore import QTimer, Qt, pyqtSignal, pyqtSlot
from PyQt5.QtWidgets import QApplication, QMainWindow, QMessageBox, QLabel, QWidget, QGridLayout, \
    QDialog, QSizePolicy, QFileDialog, QMenu, QAction, QInputDialog, QPushButton, QVBoxLayout, QHBoxLayout
from PyQt5.QtGui import QPixmap, QImage, QIcon
from src.CaptureIpCameraFramesWorker import CaptureIpCameraFramesWorker
from GUI.SurveillanceCameraGUI import Ui_MainWindow
from src.ip_address_dialog import IPAddressDialog
from src.face_recognition_service import FaceRecognitionService
from src import db_func


class FullScreenWindow(QMainWindow):
    def __init__(self, parent=None, label_indices=None, show_shrink_button=False):
        super().__init__(parent)
        self.setWindowFlags(Qt.Window)
        self.setWindowState(Qt.WindowFullScreen)  # Make the window full screen
        self.central_widget = QWidget(self)
        self.setCentralWidget(self.central_widget)
        self.layout = QGridLayout(self.central_widget)
        self.labels = {}  # Dictionary to hold new QLabel widgets

        if label_indices is not None:
            for i, idx in enumerate(label_indices):
                label = QLabel(self)
                label.setScaledContents(True)
                row = i // 2
                col = i % 2
                self.layout.addWidget(label, row, col)
                self.labels[idx] = label

        # Create a shrink button if needed
        if show_shrink_button:
            self.shrink_button = QPushButton("Shrink", self)
            self.shrink_button.setStyleSheet("background-color: white; padding: 5px;")
            self.shrink_button.setFixedSize(100, 40)
            self.shrink_button.clicked.connect(self.close_fullscreen)
            self.layout.addWidget(self.shrink_button, 0, 0)

        # Make the video labels expand to fill the window
        for i in range(self.layout.rowCount()):
            self.layout.setRowStretch(i, 1)
        for i in range(self.layout.columnCount()):
            self.layout.setColumnStretch(i, 1)

    def close_fullscreen(self):
        """Close the full-screen window."""
        self.close()

    def closeEvent(self, event):
        """Handle the closing of the full-screen window."""
        parent = self.parent()
        if parent:
            parent.full_screen_active = False
        event.accept()



class VideoLabel(QWidget):
    def __init__(self, index, main_window, parent=None):
        super().__init__(parent)
        self.index = index
        self.main_window = main_window
        self.label = QLabel(self)
        self.label.setScaledContents(True)
        self.label.setAlignment(Qt.AlignCenter)
        self.label.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

        # Create the icon button with a white background
        self.icon_button = QPushButton(self)
        self.icon_button.setIcon(QIcon("image_2024_07_08T14_12_00_872Z.png"))  # Set custom image icon
        self.icon_button.setFixedSize(24, 24)
        self.icon_button.setStyleSheet("background-color: white; padding: 2px; border: none;")
        self.icon_button.clicked.connect(self.icon_clicked)

        # Layout for positioning
        layout = QVBoxLayout(self)
        layout.addWidget(self.label)

        # Position the button in the bottom-left corner over the label
        button_layout = QHBoxLayout()
        button_layout.addWidget(self.icon_button)
        button_layout.addStretch()
        layout.addLayout(button_layout)
        layout.setContentsMargins(0, 0, 0, 0)

    def icon_clicked(self):
        print(f"Icon clicked on label {self.index}")
        self.main_window.enter_partial_expand(self.index)


class MethodMapping(QMainWindow, Ui_MainWindow):
    frame_updated = pyqtSignal(QImage, int)  # Signal with image and label index

    def __init__(self, title="", user_id=None):
        try:
            super().__init__()
            self.title = title
            self.user_id = user_id
            self.available_cameras = []  # List of available cameras
            self.context_actions = ['Change Camera', 'Change Mapping', 'Show', 'Properties', 'Turn Off']
            self.selected_camera_id = None
            self.ip_camera_threads = {}  # Dictionary to handle multiple IP camera threads
            self.face_recognition_thread = None
            self.ip_cameras = []
            self.placeholder_image = QPixmap("Black Image.png")
            self.view_camera_ids = []  # Store camera IDs for all video labels
            self.current_page = 0  # Track the current page of cameras
            self.max_cameras_per_page = 4  # Max cameras to display per page
            self.video_labels = []  # List to hold video labels
            self.caps = {}  # Dictionary to hold VideoCapture objects for each camera
            self.timers = {}  # Dictionary to hold QTimer objects for each camera
            self.label_valid_flags = {}  # Dictionary to track if a label is valid
            self.current_camera_ids = {}  # New dictionary to track current camera IDs per label index
            self.full_screen_active = False
            self.setupUi()
            print("MethodMapping initialized")

            self.frame_updated.connect(self.on_frame_updated)  # Connect the signal to the slot

            # Populate combo boxes and camera views after UI is set up
            self.populate_rooms_combobox()
            self.populate_mapping_list_and_camera_view()
        except Exception as e:
            print(f"Exception during initialization: {e}")

    def setupUi(self):
        super().setupUi(self)
        self.setWindowTitle(self.title)

        self.vision_button.clicked.connect(self.toggle_face_recognition)
        self.refresh_button.clicked.connect(self.refreshbutton)
        self.edit_mapping.clicked.connect(self.open_mapping_tab)
        self.add_room_button.clicked.connect(self.add_room)
        self.change_map_button.clicked.connect(self.change_map)
        self.all_camera_off_button.clicked.connect(self.stop_all_threads)
        self.expand_all_button.clicked.connect(self.toggle_expand_all)
        self.tabWidget.currentChanged.connect(self.resize_based_on_tab)

        self.next_button.clicked.connect(self.next_page)
        self.previous_button.clicked.connect(self.previous_page)

        # Initialize video display layout dynamically
        self.video_widget_container = QWidget(self)
        self.video_layout = QGridLayout(self.video_widget_container)
        self.gridLayout.addWidget(self.video_widget_container, 0, 0, 1, 1)

        # Initialize video labels and add to layout
        for i in range(self.max_cameras_per_page):
            video_label = VideoLabel(i, self)
            video_label.label.setPixmap(self.placeholder_image)
            self.video_layout.addWidget(video_label, i // 2, i % 2)
            self.video_labels.append(video_label)
            self.label_valid_flags[i] = False  # Initially no active feed

        

        self.show_placeholder_image()

    def resize_based_on_tab(self, index):
        """Resize the window based on the selected tab."""
        if index == self.tabWidget.indexOf(self.alarm_tab):
            self.setFixedSize(600, 600)  # Alarm tab size
        elif index == self.tabWidget.indexOf(self.camera_tab):
            self.setFixedSize(1054, 643)  # Camera tab size
        elif index == self.tabWidget.indexOf(self.mapping_tab):
            self.setFixedSize(646, 618)  # Mapping tab size

    def next_page(self):
        """Move to the next page of camera feeds."""
        if (self.current_page + 1) * self.max_cameras_per_page < len(self.view_camera_ids):
            self.current_page += 1
            self.update_video_display()

    def previous_page(self):
        """Move to the previous page of camera feeds."""
        if self.current_page > 0:
            self.current_page -= 1
            self.update_video_display()

    def update_video_display(self):
        """Update the video display based on the current page of cameras."""
        try:
            # Stop all camera feeds before updating
            self.stop_all_threads()

            # Remove existing labels from the layout but do not delete them
            while self.video_layout.count():
                item = self.video_layout.takeAt(0)
                widget = item.widget()
                if widget is not None:
                    self.video_layout.removeWidget(widget)

            # Reset label valid flags
            self.label_valid_flags = {}

            # Display video labels for the current page
            start_index = self.current_page * self.max_cameras_per_page
            end_index = min(start_index + self.max_cameras_per_page, len(self.view_camera_ids))
            current_cameras = self.view_camera_ids[start_index:end_index]

            for i in range(self.max_cameras_per_page):
                if i < len(current_cameras):
                    camera_id = current_cameras[i]
                    video_label = self.video_labels[i]
                    self.video_layout.addWidget(video_label, i // 2, i % 2)
                    self.label_valid_flags[i] = True  # Mark label as valid

                    # Turn on camera and display the feed
                    self.turn_on_camera(camera_id, i)
                else:
                    # No camera for this label, show placeholder
                    video_label = self.video_labels[i]
                    self.video_layout.addWidget(video_label, i // 2, i % 2)
                    video_label.label.setPixmap(self.placeholder_image)
                    self.label_valid_flags[i] = False  # No active feed

            # Handle pagination buttons
            total_pages = (len(self.view_camera_ids) - 1) // self.max_cameras_per_page
            self.next_button.setEnabled(self.current_page < total_pages)
            self.previous_button.setEnabled(self.current_page > 0)
        except Exception as e:
            print(f"Exception in update_video_display: {e}")

    def toggle_expand_all(self):
        """Opens a full-screen window with all video feeds in a 2x2 grid, with a shrink button."""
        label_indices = [i for i in range(len(self.video_labels))]
        self.full_screen_window = FullScreenWindow(parent=self, label_indices=label_indices, show_shrink_button=True)
        self.full_screen_window.show()
        self.full_screen_active = True

    def enter_partial_expand(self, index):
        """Opens a full-screen window with a single video feed and a shrink button."""
        self.full_screen_window = FullScreenWindow(parent=self, label_indices=[index], show_shrink_button=True)
        self.full_screen_window.show()
        self.full_screen_active = True


    @pyqtSlot(QImage, int)
    def on_frame_updated(self, image, label_index):
        """Updates the video label with the new frame in the main GUI thread."""
        try:
            if self.label_valid_flags.get(label_index, True):
                if 0 <= label_index < len(self.video_labels):
                    # Update main window label
                    main_label = self.video_labels[label_index].label
                    main_label.setPixmap(QPixmap.fromImage(image))

                    # Update full-mscreen label if active
                    if self.full_screen_active and self.full_screen_window:
                        fs_label = self.full_screen_window.labels.get(label_index)
                        if fs_label:
                            fs_label.setPixmap(QPixap.fromImage(image))
                else:
                    print(f"Invalid label index in on_frame_updated: {label_index}")
            else:
                print(f"Label at index {label_index} is no longer valid.")
        except Exception as e:
            print(f"Exception in on_frame_updated: {e}")
            logging.exception("Exception in on_frame_updated")

    def turn_on_camera(self, camera_id, label_index):
        """Turns on the specified camera and displays the feed in the corresponding video label."""
        try:
            print(f"Attempting to turn on camera {camera_id} for label {label_index}")
            if self.current_camera_ids.get(label_index) == camera_id:
                print(f"Camera {camera_id} is already running on label {label_index}, no need to restart.")
                return  # No need to restart the camera feed

            # Ensure previous feed on this label is stopped before turning on a new feed
            self.stop_camera_feed(label_index)

            # Update the current camera ID for this label
            self.current_camera_ids[label_index] = camera_id

            video_label = self.video_labels[label_index].label
            video_label.setVisible(True)

            if camera_id:
                if isinstance(camera_id, str) and len(camera_id) > 16:  # IP camera case
                    print(f"Trying to connect to IP camera at {camera_id}")
                    ip_thread = CaptureIpCameraFramesWorker(camera_id)
                    ip_thread.ImageUpdated.connect(lambda image, idx=label_index: self.frame_updated.emit(image, idx))
                    ip_thread.start()
                    self.ip_camera_threads[label_index] = ip_thread
                    print(f"Connected to IP camera at {camera_id}")
                else:
                    print(f"Attempting to open local camera {camera_id}")
                    cap = cv2.VideoCapture(int(camera_id))
                    if cap.isOpened():
                        self.caps[label_index] = cap
                        print(f"Camera {camera_id} opened successfully")

                        timer = QTimer()
                        timer.timeout.connect(lambda cp=cap, idx=label_index: self.capture_frame(cp, idx))
                        timer.start(30)  # Refresh rate in milliseconds (30 ms = ~33 fps)
                        self.timers[label_index] = timer
                    else:
                        print(f"Failed to open camera {camera_id}")

            self.selected_camera_id = camera_id
            self.label_valid_flags[label_index] = True  # Mark this label as valid

        except Exception as e:
            print(f"Exception in turn_on_camera: {e}")
            logging.exception("Exception in turn_on_camera")

    def capture_frame(self, cap, label_index):
        """Captures a frame from the camera and emits a signal to update the GUI."""
        try:
            if not cap.isOpened():
                print(f"Error: Camera for label_index {label_index} is not opened")
                return

            ret, frame = cap.read()
            if not ret:
                print(f"Failed to capture frame from camera {self.current_camera_ids.get(label_index)} at label {label_index}")
                return
            
            frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            h, w, ch = frame_rgb.shape
            bytes_per_line = ch * w
            qimg = QImage(frame_rgb.data, w, h, bytes_per_line, QImage.Format_RGB888)
            self.frame_updated.emit(qimg, label_index)
        except Exception as e:
            print(f"Exception in capture_frame: {e}")
            logging.exception("Exception in capture_frame")

    def stop_all_threads(self):
        try:
            if self.face_recognition_thread and self.face_recognition_thread.isRunning():
                self.face_recognition_thread.stop()
                self.face_recognition_thread.wait()
                print("Face recognition thread stopped")
                self.face_recognition_thread = None

            for label_index in range(self.max_cameras_per_page):
                self.stop_camera_feed(label_index)

            self.label_valid_flags = {}
            self.current_camera_ids = {}
        except Exception as e:
            print(f"Exception in stop_all_threads: {e}")
            logging.exception("Exception in stop_all_threads")

    def stop_camera_feed(self, label_index):
        """Stops the camera feed for the specified label index."""
        if label_index in self.caps:
            cap = self.caps.pop(label_index)
            cap.release()

        if label_index in self.timers:
            timer = self.timers.pop(label_index)
            timer.stop()

        if label_index in self.ip_camera_threads:
            thread = self.ip_camera_threads.pop(label_index)
            thread.stop()
            thread.wait()

        if label_index in self.current_camera_ids:
            del self.current_camera_ids[label_index]

    def show_placeholder_image(self):
        """Show placeholder image on all labels."""
        for label_index in range(self.max_cameras_per_page):
            self.video_labels[label_index].label.setPixmap(self.placeholder_image)
            self.label_valid_flags[label_index] = False  # No active feed
            self.stop_camera_feed(label_index)

    def populate_mapping_list_and_camera_view(self):
        self.mapping_list.clear()
        rooms_with_cameras = db_func.get_all_rooms_with_cameras()
        db_func.add_new_cameras()  # Add new cameras

        available_cameras = db_func.get_available_cameras()
        all_cameras = set()
        for cameras in rooms_with_cameras.values():
            all_cameras.update(cameras)
        all_cameras.update(available_cameras)
        all_cameras.update(self.ip_cameras)

        sorted_cameras = sorted(all_cameras, key=lambda x: str(x))

        for room_name, cameras in rooms_with_cameras.items():
            for camera in cameras:
                list_item_text = f"{room_name}: Camera {camera}"
                self.mapping_list.addItem(list_item_text)

        self.view_camera_ids = sorted_cameras
        self.update_video_display()

    def populate_rooms_combobox(self):
        self.rooms_list_combobox.clear()
        rooms = db_func.get_all_rooms_with_cameras()
        for room_name, cameras in rooms.items():
            camera_list = ', '.join(cameras)
            display_text = f"{room_name}: {camera_list}"
            self.rooms_list_combobox.addItem(display_text)
        self.available_cameras = db_func.get_available_cameras()

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
                self.face_recognition_thread.ImageUpdated.connect(lambda image: self.update_image(image, self.video_labels[0].label))
                self.face_recognition_thread.FaceRecognized.connect(self.handle_face_recognition)
                self.face_recognition_thread.start()
                print(f"Face recognition started for camera {camera_id}")
                self.selected_camera_id = camera_id
            else:
                print("No camera selected for face recognition.")
        except Exception as e:
            print(f"Exception in turn_on_face_recognition: {e}")
            logging.exception("Exception in turn_on_face_recognition")

    def handle_face_recognition(self, face_locations, face_names):
        try:
            print(f"Faces recognized: {face_names}")
        except Exception as e:
            print(f"Exception in handle_face_recognition: {e}")
            logging.exception("Exception in handle_face_recognition")

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

    def show_camera(self, button):
        camera_id = self.get_camera_id(button)
        if camera_id is not None:
            self.selected_camera_id = camera_id
            self.update_video_display()

    def get_camera_id(self, button):
        text = button.text()
        if text.startswith("IP Camera"):
            index = int(text.split()[-1]) - 1
            return self.ip_cameras[index]
        elif text.startswith("Camera"):
            return int(text.split()[-1])
        return None

    def show_camera_properties(self, button):
        pass

    def turn_off_camera(self, button):
        self.update_button_text(button, "Camera Off")
        self.stop_all_threads()
        self.show_placeholder_image()

    def update_button_text(self, button, text):
        button.setText(text)

    def show_message(self, message):
        QMessageBox.information(self, "Information", message)


if __name__ == "__main__":
    from GUI.LoginGUI import LoginWindow

    # Initialize the database
    db_func.init_db()
    db_func.add_new_cameras()  # Add this line if new cameras need to be added at startup

    app = QApplication(sys.argv)
    login_window = LoginWindow()

    if login_window.exec_() == QDialog.Accepted:
        user_id = login_window.get_user_id()
        ui = MethodMapping("Surveillance Camera", user_id=user_id)
        ui.show()

    sys.exit(app.exec_())
