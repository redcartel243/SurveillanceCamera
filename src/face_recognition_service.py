import os
import beepy
import cv2
import numpy as np
import face_recognition
from threading import Thread
from dataloader import load_config
from emailer import send_email
from tts import speak
import logging
from PyQt5.QtCore import pyqtSignal, QObject, QThread
import Data

config = load_config()

logging.basicConfig(level=logging.INFO)

class FaceRecognitionWorker(QObject):
    ImageUpdated = pyqtSignal(np.ndarray)

    def __init__(self, known_faces_dir='C:/Users/Red/PycharmProjects/SurveillanceCamera/datasets/known_faces', captures_dir='C:/Users/Red/PycharmProjects/SurveillanceCamera/datasets/Captures'):
        super().__init__()
        self.known_faces_dir = known_faces_dir
        self.captures_dir = captures_dir
        self.unknown_count_threshold = 6
        self.recognized_count_threshold = 20

    def load_known_faces(self):
        known_face_encodings = []
        known_face_names = []

        for filename in os.listdir(self.known_faces_dir):
            filepath = os.path.join(self.known_faces_dir, filename)
            image = face_recognition.load_image_file(filepath)
            encodings = face_recognition.face_encodings(image)[0]
            if encodings.any():
                known_face_encodings.append(encodings)
                known_face_names.append(os.path.splitext(filename)[0])

        return known_face_encodings, known_face_names

    def recognize_faces(self, frame):
        known_face_encodings, known_face_names = self.load_known_faces()
        rgb_frame = np.ascontiguousarray(frame[:, :, ::-1])
        face_locations = face_recognition.face_locations(rgb_frame)
        face_encodings = face_recognition.face_encodings(rgb_frame, face_locations)

        face_names = []
        for face_encoding in face_encodings:
            matches = face_recognition.compare_faces(known_face_encodings, face_encoding)
            name = "Unknown"
            face_distances = face_recognition.face_distance(known_face_encodings, face_encoding)
            best_match_index = np.argmin(face_distances)
            if matches[best_match_index]:
                name = known_face_names[best_match_index]
            face_names.append(name)
            self.handle_detection(name, frame)

        self.draw_faces(frame, face_locations, face_names)
        self.ImageUpdated.emit(frame)

    def handle_detection(self, name, frame):
        datasave = Data.load()
        if name == "Unknown":
            self.handle_unknown_detection(frame, datasave)
        else:
            self.handle_recognized_detection(name, datasave)
        Data.save(datasave)

    def handle_unknown_detection(self, frame, datasave):
        datasave["countWrongf"] += 1
        if datasave["countWrongf"] >= self.unknown_count_threshold:
            logging.warning("Unknown face detected.")
            for _ in range(config['alarm']['repetitions']):
                speak(config['alarm']['text'])
                beepy.beep(config['alarm']['sound'])
            intruder_image_path = os.path.join(self.captures_dir, 'intruder.jpg')
            cv2.imwrite(intruder_image_path, frame)
            #send_email(intruder_image_path, 'C:/Users/Red/PycharmProjects/SurveillanceCamera/datasets/Time_of_movements.csv')
            datasave["countWrongf"] = 0  # Reset counter

    def handle_recognized_detection(self, name, datasave):
        datasave["countRightf"] += 1
        if datasave["countRightf"] >= self.recognized_count_threshold:
            logging.info(f"User {name} recognized.")
            datasave["countRightf"] = 0  # Reset counter

    def draw_faces(self, frame, face_locations, face_names):
        for (top, right, bottom, left), name in zip(face_locations, face_names):
            top *= 4
            right *= 4
            bottom *= 4
            left *= 4

            cv2.rectangle(frame, (left, top), (right, bottom), (0, 0, 255), 2)
            cv2.rectangle(frame, (left, bottom - 35), (right, bottom), (0, 0, 255), cv2.FILLED)
            font = cv2.FONT_HERSHEY_DUPLEX
            cv2.putText(frame, name, (left + 6, bottom - 6), font, 1.0, (255, 255, 255), 1)

class FaceRecognitionService(QThread):
    ImageUpdated = pyqtSignal(np.ndarray)

    def __init__(self, camera_id):
        super().__init__()
        self.face_recognition_worker = FaceRecognitionWorker()
        self.camera_id = camera_id
        self.running = False

    def run(self):
        try:
            logging.info("Starting face recognition service.")
            known_face_encodings, known_face_names = self.face_recognition_worker.load_known_faces()
            video_capture = cv2.VideoCapture(self.camera_id)
            self.running = True

            while self.running:
                ret, frame = video_capture.read()
                if not ret:
                    logging.error("Failed to capture image from camera.")
                    break

                rgb_frame = np.ascontiguousarray(frame[:, :, ::-1])
                face_locations = face_recognition.face_locations(rgb_frame)
                face_encodings = face_recognition.face_encodings(rgb_frame, face_locations)

                face_names = []
                for face_encoding in face_encodings:
                    matches = face_recognition.compare_faces(known_face_encodings, face_encoding)
                    name = "Unknown"
                    face_distances = face_recognition.face_distance(known_face_encodings, face_encoding)
                    best_match_index = np.argmin(face_distances)
                    if matches[best_match_index]:
                        name = known_face_names[best_match_index]
                    face_names.append(name)
                    self.face_recognition_worker.handle_detection(name, frame)

                self.face_recognition_worker.draw_faces(frame, face_locations, face_names)
                self.ImageUpdated.emit(frame)

            video_capture.release()
            logging.info("Stopped face recognition service.")
        except Exception as e:
            logging.error(f"Exception in face recognition service: {e}")

    def stop(self):
        self.running = False
