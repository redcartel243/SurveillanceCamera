import sys
from PyQt5.QtWidgets import QApplication
from face_recognition_service import FaceRecognitionService
from motion_detection import detect_motion

if __name__ == "__main__":
    face_recognition_service = FaceRecognitionService()
    face_recognition_service.start()
    #detect_motion()


