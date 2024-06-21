import os

import beepy
import cv2
import numpy
import numpy as np
import face_recognition
from threading import Thread
from dataloader import load_config
from emailer import send_email
from tts import speak
import logging
from src import Data

config = load_config()

logging.basicConfig(level=logging.INFO)

class FaceRecognition(Thread):
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
            print(encodings)
            if encodings.any():
                known_face_encodings.append(encodings)
                known_face_names.append(os.path.splitext(filename)[0])

        return known_face_encodings, known_face_names

    def run(self):
        known_face_encodings, known_face_names = self.load_known_faces()
        video_capture = cv2.VideoCapture(0)
        process_this_frame = True

        while True:
            ret, frame = video_capture.read()
            if not ret:
                logging.error("Failed to capture image from camera.")
                break

            small_frame = cv2.resize(frame, (0, 0), fx=0.25, fy=0.25)
            rgb_small_frame = numpy.ascontiguousarray(small_frame[:, :, ::-1])

            face_locations = []
            face_names = []

            if process_this_frame:
                face_locations = face_recognition.face_locations(rgb_small_frame)
                face_encodings = face_recognition.face_encodings(rgb_small_frame, face_locations)

                for face_encoding in face_encodings:
                    matches = face_recognition.compare_faces(known_face_encodings, face_encoding)
                    name = "Unknown"
                    face_distances = face_recognition.face_distance(known_face_encodings, face_encoding)
                    best_match_index = np.argmin(face_distances)
                    if matches[best_match_index]:
                        name = known_face_names[best_match_index]

                    face_names.append(name)
                    self.handle_detection(name, frame)

            process_this_frame = not process_this_frame

            self.draw_faces(frame, face_locations, face_names)
            cv2.imshow('Video', frame)

            if cv2.waitKey(1) & 0xFF == ord('q'):
                break

        video_capture.release()
        cv2.destroyAllWindows()

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

class FaceRecognitionService:
    def __init__(self):
        self.face_recognition_thread = FaceRecognition()

    def start(self):
        self.face_recognition_thread.start()

    def stop(self):
        self.face_recognition_thread.join()
