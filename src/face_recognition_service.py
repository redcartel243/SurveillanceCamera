import os
import beepy
import cv2
import numpy as np
import face_recognition
from threading import Thread
import time
from queue import Queue, Empty
try:
    from dataloader import load_config
except ImportError:
    try:
        from .dataloader import load_config
    except ImportError:
        from src.dataloader import load_config
from src.emailer import send_email
from src.tts import speak
import logging
from PyQt5.QtCore import pyqtSignal, QObject, QThread
from src import Data

config = load_config()

logging.basicConfig(level=logging.INFO)



class FaceRecognitionService(QThread):
    ImageUpdated = pyqtSignal(np.ndarray)
    FaceRecognized = pyqtSignal(list, list)

    def __init__(self, camera_id, known_faces_dir='datasets/known_faces', captures_dir='datasets/Captures'):
        super().__init__()
        self.camera_id = camera_id
        self.running = True
        self.face_recognition_worker = FaceRecognitionWorker(known_faces_dir, captures_dir)
        self.frame_queue = Queue(maxsize=30)  # Limit queue size to avoid memory issues
        logging.info(f"FaceRecognitionService initialized for camera {camera_id}")

    def run(self):
        print(type(self.camera_id))
        cap = cv2.VideoCapture(self.camera_id)
        if not cap.isOpened():
            logging.error(f"Failed to open camera {self.camera_id}")
            return
        logging.info(f"Camera {self.camera_id} opened successfully")
        
        while self.running:
            ret, frame = cap.read()
            if ret:
                frame, face_locations, face_names = self.face_recognition_worker.recognize_faces(frame)
                frame_with_faces = self.face_recognition_worker.draw_faces(frame, face_locations, face_names)
                self.ImageUpdated.emit(frame_with_faces)
                self.FaceRecognized.emit(face_locations, face_names)
                print("Frame processed and emitted")
            else:
                print("Failed to read frame from camera")
            
            time.sleep(0.03)  # Limit to about 30 fps
        
        cap.release()
        print(f"Camera {self.camera_id} released")

    def stop(self):
        self.running = False
        logging.info("Face recognition service stopping...")


class FaceRecognitionWorker:
    def __init__(self, known_faces_dir='datasets/known_faces', captures_dir='datasets/Captures'):
        self.known_faces_dir = known_faces_dir
        self.captures_dir = captures_dir
        self.known_face_encodings = []
        self.known_face_names = []
        self.unknown_count_threshold = 6
        self.recognized_count_threshold = 20
        self.load_known_faces()
        logging.info("FaceRecognitionWorker initialized")
    
    def load_known_faces(self):
        for filename in os.listdir(self.known_faces_dir):
            filepath = os.path.join(self.known_faces_dir, filename)
            image = face_recognition.load_image_file(filepath)
            encodings = face_recognition.face_encodings(image)
            if encodings:
                self.known_face_encodings.append(encodings[0])
                self.known_face_names.append(os.path.splitext(filename)[0])

    def recognize_faces(self, frame):
        try:
            # Ensure the frame is in RGB format
            rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            
            # Resize the frame
            small_frame = cv2.resize(rgb_frame, (0, 0), fx=0.25, fy=0.25)
            
            # Find face locations and encodings
            face_locations = face_recognition.face_locations(small_frame, model="hog")
            face_encodings = face_recognition.face_encodings(small_frame, face_locations)

            face_names = []
            for face_encoding in face_encodings:
                matches = face_recognition.compare_faces(self.known_face_encodings, face_encoding)
                name = "Unknown"

                face_distances = face_recognition.face_distance(self.known_face_encodings, face_encoding)
                best_match_index = np.argmin(face_distances)
                if matches[best_match_index]:
                    name = self.known_face_names[best_match_index]

                face_names.append(name)

            print(f"Recognized {len(face_names)} faces")
            # Scale back up face locations since the frame we detected in was scaled to 1/4 size
            face_locations = [(top * 4, right * 4, bottom * 4, left * 4) for (top, right, bottom, left) in face_locations]

            return frame, face_locations, face_names
        except Exception as e:
            print(f"Exception in recognize_faces: {e}")
            return [], []
        

    def draw_faces(self, frame, face_locations, face_names):
        for (top, right, bottom, left), name in zip(face_locations, face_names):
            cv2.rectangle(frame, (left, top), (right, bottom), (0, 0, 255), 2)
            cv2.rectangle(frame, (left, bottom - 35), (right, bottom), (0, 0, 255), cv2.FILLED)
            font = cv2.FONT_HERSHEY_DUPLEX
            cv2.putText(frame, name, (left + 6, bottom - 6), font, 1.0, (255, 255, 255), 1)
        return frame