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



is_partial_expanded = False
full_screen_active = False

class FullScreenWindow(QMainWindow):
    def __init__(self, parent=None, label_indices=None):
        super().__init__(parent)
        self.setWindowFlags(Qt.Window | Qt.WindowMinimizeButtonHint | Qt.WindowCloseButtonHint)
        self.showMaximized()
        self.central_widget = QWidget(self)
        self.setCentralWidget(self.central_widget)
        self.layout = QGridLayout(self.central_widget)
        self.labels = {}

        if label_indices is not None:
            for i, idx in enumerate(label_indices):
                label = QLabel(self)
                label.setScaledContents(True)
                label.setAlignment(Qt.AlignCenter)
                label.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
                row = i // 2
                col = i % 2
                self.layout.addWidget(label, row, col)
                self.labels[idx] = label

        # Make the video labels expand to fill the window
        for i in range(self.layout.rowCount()):
            self.layout.setRowStretch(i, 1)
        for i in range(self.layout.columnCount()):
            self.layout.setColumnStretch(i, 1)

    def closeEvent(self, event):
        global full_screen_active
        parent = self.parent()
        if parent:
            full_screen_active = False
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
        self.icon_button.setIcon(QIcon("GUI/resources/image_2024_07_08T14_12_00_872Z.png"))
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

        self.is_expanded = False

    def icon_clicked(self):
        print(f"Icon clicked on label {self.index}")
        self.main_window.enter_partial_expand(self.index)

    def adjust_for_expansion(self, is_expanded):
        """Adjust info size and position based on expansion state."""
        self.is_expanded = is_expanded
        


class MethodMapping(QMainWindow, Ui_MainWindow):
    frame_updated = pyqtSignal(QImage, int)

    def __init__(self, title="", user_id=None):
        try:
            super().__init__()
            self.full_screen_window = None
            self.title = title
            self.user_id = user_id
            self.available_cameras = []
            self.context_actions = ['Change Camera', 'Change Mapping', 'Show', 'Properties', 'Turn Off']
            self.selected_camera_id = None
            self.ip_camera_threads = {}
            self.face_recognition_thread = None
            self.ip_cameras = []
            self.placeholder_image = QPixmap("GUI/resources/Black Image.png")
            self.view_camera_ids = []
            self.current_page = 0
            self.max_cameras_per_page = 4
            self.video_labels = []
            self.caps = {}
            self.current_camera_ids = {}
            self.timers = {}
            self.label_valid_flags = {}
            self.setupUi()
            print("MethodMapping initialized")

            self.frame_updated.connect(self.on_frame_updated)

            # Populate combo boxes and camera views after UI is set up
            self.populate_rooms_combobox()
            self.rooms_list_combobox.currentIndexChanged.connect(self.show_combobox_context_menu)
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
            self.label_valid_flags[i] = False

            # Fetch camera info and update label with room and camera ID
            camera_id = self.view_camera_ids[i] if i < len(self.view_camera_ids) else None
            room_name = db_func.get_room_name_by_camera_id(camera_id) if camera_id else "Unknown Room"

        self.show_placeholder_image()

    def resize_based_on_tab(self, index):
        if index == self.tabWidget.indexOf(self.alarm_tab):
            self.setFixedSize(600, 600)
        elif index == self.tabWidget.indexOf(self.mapping_tab):
            self.setFixedSize(646, 618)
        elif index == self.tabWidget.indexOf(self.camera_tab):
            self.setFixedSize(987, 607)

    def next_page(self):
        if (self.current_page + 1) * self.max_cameras_per_page < len(self.view_camera_ids):
            self.current_page += 1
            self.update_video_display()

    def previous_page(self):
        if self.current_page > 0:
            self.current_page -= 1
            self.update_video_display()

    def update_video_display(self):
        try:
            self.stop_all_threads()

            while self.video_layout.count():
                item = self.video_layout.takeAt(0)
                widget = item.widget()
                if widget:
                    self.video_layout.removeWidget(widget)

            self.label_valid_flags = {}

            start_index = self.current_page * self.max_cameras_per_page
            end_index = min(start_index + self.max_cameras_per_page, len(self.view_camera_ids))
            current_cameras = self.view_camera_ids[start_index:end_index]

            for i in range(self.max_cameras_per_page):
                if i < len(current_cameras):
                    camera_id = current_cameras[i]
                    video_label = self.video_labels[i]
                    self.video_layout.addWidget(video_label, i // 2, i % 2)
                    self.label_valid_flags[i] = True

                    self.turn_on_camera(camera_id, i)
                else:
                    video_label = self.video_labels[i]
                    self.video_layout.addWidget(video_label, i // 2, i % 2)
                    video_label.label.setPixmap(self.placeholder_image)
                    self.label_valid_flags[i] = False

            total_pages = (len(self.view_camera_ids) - 1) // self.max_cameras_per_page
            self.next_button.setEnabled(self.current_page < total_pages)
            self.previous_button.setEnabled(self.current_page > 0)
        except Exception as e:
            print(f"Exception in update_video_display: {e}")

    def toggle_expand_all(self):
        global full_screen_active 
        if full_screen_active:
            self.full_screen_window.close()
            full_screen_active = False
        
        else:
            self.full_screen_window = FullScreenWindow(self, label_indices=[0, 1, 2, 3])
            self.full_screen_window.show()
            full_screen_active = True

    def enter_partial_expand(self, index):
        global is_partial_expanded
        if is_partial_expanded:
            for video_label in self.video_labels:
                video_label.setVisible(True)
                video_label.adjust_for_expansion(False)
            is_partial_expanded = False
        else:
            for i, video_label in enumerate(self.video_labels):
                if i != index:
                    video_label.setVisible(False)
                video_label.adjust_for_expansion(i == index)
            is_partial_expanded = True
        self.adjust_layouts()

    def adjust_layouts(self):
        global is_partial_expanded
        if is_partial_expanded:
            for i, video_label in enumerate(self.video_labels):
                if video_label.isVisible():
                    self.video_layout.addWidget(video_label, 0, 0, 1, 1)
        else:
            for i, video_label in enumerate(self.video_labels):
                row = i // 2
                col = i % 2
                self.video_layout.addWidget(video_label, row, col)

    @pyqtSlot(QImage, int)
    def on_frame_updated(self, image, label_index):
        global full_screen_active
        try:
            if self.label_valid_flags.get(label_index, True):
                if 0 <= label_index < len(self.video_labels):
                    main_label = self.video_labels[label_index].label
                    main_label.setPixmap(QPixmap.fromImage(image))

                    if full_screen_active and self.full_screen_window:
                        fs_label = self.full_screen_window.labels.get(label_index)
                        if fs_label:
                            fs_label.setPixmap(QPixmap.fromImage(image))
                else:
                    print(f"Invalid label index in on_frame_updated: {label_index}")
            else:
                print(f"Label at index {label_index} is no longer valid.")
        except Exception as e:
            print(f"Exception in on_frame_updated: {e}")
            logging.exception("Exception in on_frame_updated")

    def turn_on_camera(self, camera_id, label_index):
        try:
            print(f"Attempting to turn on camera {camera_id} for label {label_index}")
            if self.current_camera_ids.get(label_index) == camera_id:
                print(f"Camera {camera_id} is already running on label {label_index}, no need to restart.")
                return

            self.stop_camera_feed(label_index)
            self.current_camera_ids[label_index] = camera_id
            video_label = self.video_labels[label_index].label
            video_label.setVisible(True)

            room_name = db_func.get_room_name_by_camera_id(camera_id)

            if camera_id:
                if isinstance(camera_id, str) and len(camera_id) > 16:
                    print(f"Trying to connect to IP camera at {camera_id}")
                    ip_thread = CaptureIpCameraFramesWorker(camera_id)
                    ip_thread.ImageUpdated.connect(lambda image, idx=label_index: self.frame_updated.emit(image, idx))
                    ip_thread.start()
                    self.ip_camera_threads[label_index] = ip_thread

                    print(f"Connected to IP camera at {camera_id}")
                else:
                    cap = cv2.VideoCapture(int(camera_id))
                    if cap.isOpened():
                        self.caps[label_index] = cap
                        print(f"Camera {camera_id} opened successfully")

                        timer = QTimer()
                        timer.timeout.connect(lambda cp=cap, idx=label_index: self.capture_frame(cp, idx))
                        timer.start(30)
                        self.timers[label_index] = timer
                    else:
                        print(f"Failed to open camera {camera_id}")
        except Exception as e:
            print(f"Exception in turn_on_camera: {e}")

    def capture_frame(self, cap, label_index):
        global is_partial_expanded
        global full_screen_active
        try:
            if not cap.isOpened():
                print(f"Error: Camera for label_index {label_index} is not opened")
                return

            ret, frame = cap.read()
            if not ret:
                print(f"Failed to capture frame from camera {self.current_camera_ids.get(label_index)} at label {label_index}")
                return

            room_name = db_func.get_room_name_by_camera_id(self.current_camera_ids[label_index])
            camera_id = self.current_camera_ids[label_index]
            state = "ON"

            overlay_text = f"{room_name} | Camera ID: {camera_id} | {state}"

            font = cv2.FONT_HERSHEY_SIMPLEX
            if full_screen_active:
                font_scale = 1.5
                thickness = 2
            elif is_partial_expanded:
                font_scale = 1.2
                thickness = 2
            else:
                font_scale = 1
                thickness = 1

            color = (255, 255, 255)
            text_size = cv2.getTextSize(overlay_text, font, font_scale, thickness)[0]

            text_x = (frame.shape[1] - text_size[0]) // 2
            text_y = frame.shape[0] - 10

            cv2.putText(frame, overlay_text, (text_x, text_y), font, font_scale, color, thickness, cv2.LINE_AA)

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

    def stop_camera_feed(self, label_index):
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
        """
        Populate the combobox with rooms and their associated cameras.
        """
        self.rooms_list_combobox.clear()
        rooms_with_cameras = db_func.get_all_rooms_with_cameras()
        for room_name, cameras in rooms_with_cameras.items():
            camera_list = ', '.join(cameras)
            display_text = f"{room_name}: {camera_list}"
            self.rooms_list_combobox.addItem(display_text)

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
        except Exception as e:
            print(f"Exception in turn_on_face_recognition: {e}")

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
            return  # No item selected

        room_text = self.rooms_list_combobox.itemText(index)
        room_name = room_text.split(': ')[0]

        contextMenu = QMenu(self)

        delete_room_action = QAction("Delete Room", self)
        delete_assignment_action = QAction("Delete Assignment", self)
        modify_assignment_action = QAction("Modify Assignment", self)

        contextMenu.addAction(delete_room_action)
        contextMenu.addAction(delete_assignment_action)
        contextMenu.addAction(modify_assignment_action)

        delete_room_action.triggered.connect(lambda: self.delete_room(room_name))
        delete_assignment_action.triggered.connect(lambda: self.delete_assignment(room_name))
        modify_assignment_action.triggered.connect(lambda: self.modify_assignment(room_name))

        contextMenu.exec_(self.rooms_list_combobox.mapToGlobal(self.rooms_list_combobox.rect().bottomLeft()))

    def add_room(self):
        room_name, ok = QInputDialog.getText(self, "Add Room", "Enter room name:")
        if ok and room_name:
            rooms = db_func.get_rooms_by_user_id(self.user_id)
            if any(room_name == existing_name for existing_name in rooms):
                self.show_message(f"Room '{room_name}' already exists.")
            else:
                db_func.add_room(self.user_id, room_name)
                self.populate_rooms_combobox()
                self.show_message(f"Room '{room_name}' added successfully.")

    def delete_room(self, room_name):
        """
        Delete a room and unassign its cameras. This ensures that the room's cameras are no longer
        linked to the room and can be reassigned elsewhere.
        """
        try:
            db_func.delete_room(room_name)
            self.populate_rooms_combobox()
            self.show_message(f"Room '{room_name}' and its camera assignments deleted.")
        except Exception as e:
            self.show_message(f"Failed to delete room '{room_name}': {str(e)}")

    def delete_assignment(self, room_name, camera_id):
        """
        Unassign a camera from a room. The camera will no longer be linked to the room
        and can be reassigned.
        """
        try:
            db_func.unassign_camera_from_room(room_name, camera_id)
            self.populate_rooms_combobox()
            self.show_message(f"Camera {camera_id} unassigned from room '{room_name}' successfully.")
        except Exception as e:
            self.show_message(f"Failed to unassign camera {camera_id} from room '{room_name}': {str(e)}")

    def modify_assignment(self, room_name, camera_id):
        """
        Modify the camera assignment for a room. This allows you to change the cameras
        associated with a room.
        """
        try:
            db_func.assign_camera_to_room(room_name, camera_id)
            self.populate_rooms_combobox()
            self.show_message(f"Camera {camera_id} assigned to room '{room_name}' successfully.")
        except Exception as e:
            self.show_message(f"Failed to modify camera assignment: {str(e)}")

    def assign_camera_to_room(self, room_name, camera_id):
        """
        Assign a camera to a room, considering that a camera can only be in one room at a time
        but a room can have multiple cameras.
        """
        try:
            db_func.assign_camera_to_room(room_name, camera_id)
            self.populate_rooms_combobox()
            self.show_message(f"Camera {camera_id} assigned to room '{room_name}' successfully.")
        except Exception as e:
            self.show_message(f"Failed to assign camera {camera_id}: {str(e)}")

    def open_mapping_tab(self):
        self.tabWidget.setCurrentIndex(self.tabWidget.indexOf(self.mapping_tab))

    def show_message(self, message):
        QMessageBox.information(self, "Information", message)


if __name__ == "__main__":
    from GUI.LoginGUI import LoginWindow

    db_func.init_db()
    db_func.add_new_cameras()

    app = QApplication(sys.argv)
    login_window = LoginWindow()

    if login_window.exec_() == QDialog.Accepted:
        user_id = login_window.get_user_id()
        ui = MethodMapping("Surveillance Camera", user_id=user_id)
        ui.show()

    sys.exit(app.exec_())

