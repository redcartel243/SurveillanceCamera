import os
from email import encoders
from email.mime.base import MIMEBase

import beepy
import face_recognition
import cv2
import numpy
import numpy as np
from src import Data
#  running face recognition on live video from your webcam.
#   1. Process each video frame at 1/4 resolution (though still display it at full resolution)
#   2. Only detect faces in every other frame of video.

import pyttsx3
import smtplib
from email.mime.image import MIMEImage
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from threading import Thread
from src.MotionDetection import detectmot


def sendmail(image_frame, filename):
    img_data = open(image_frame, 'rb').read()
    msg = MIMEMultipart()
    msg['Subject'] = 'Intruder detected'
    msg['From'] = 'cfeshete97@outlook.com'
    msg['To'] = 'bukedidavid@gmail.com'

    text = MIMEText(
        "an intruder has been detected, please open this website to manage the camera:https://my.ivideon.com/cameras/groups/own")
    msg.attach(text)
    image = MIMEImage(img_data, name=os.path.basename(image_frame))
    # open the file to be sent

    attachment = open(filename, "rb")

    # instance of MIMEBase and named as p
    p = MIMEBase('application', 'octet-stream')

    # To change the payload into encoded form
    p.set_payload((attachment).read())

    # encode into base64
    encoders.encode_base64(p)

    p.add_header('Content-Disposition', "attachment; filename= %s" % filename)

    # attach the instance 'p' to instance 'msg'
    msg.attach(p)
    msg.attach(image)
    s = smtplib.SMTP('smtp-mail.outlook.com', '587')  # smtp.gmail.com for gmail
    s.ehlo()
    s.starttls()
    s.ehlo()
    s.login('cfeshete97@outlook.com', 'charles1997')
    s.sendmail('cfeshete97@outlook.com', 'bukedidavid@gmail.com', msg.as_string())
    s.quit()


# the function used to speak (text to speech)
def Speak(audio):
    datasave = Data.load()
    engine = pyttsx3.init('sapi5')
    voices = engine.getProperty('voices')
    engine.setProperty('voice', voices[datasave["voice"]].id)
    engine.say(audio)
    engine.runAndWait()


# thread for motion detection ,CAM1
class motion(Thread):
    def __init__(self):
        Thread.__init__(self)

    def run(self):
        detectmot()


# thread for face detection,CAM2
class face(Thread):
    def __init__(self):
        Thread.__init__(self)

    def run(self):
        while True:
            datasave = Data.load()
            directory = 'C:/Users/Red/PycharmProjects/SurveillanceCamera/DataSet'
            if len(os.listdir(directory)) != 0:  # to avoid error while the script is running on the background
                # we check if the Dataset file is empty or not
                # Get a reference to webcam #0 (the default one)
                video_capture = cv2.VideoCapture(0)  # here we input the ip address of cam2
                count = 0
                user1 = ""
                user2 = ""
                # Load a sample picture and learn how to recognize it.
                directory = 'C:/Users/Red/PycharmProjects/SurveillanceCamera/DataSet'
                for filename in os.listdir(directory):
                    User1 = face_recognition.load_image_file(
                        "C:/Users/Red/PycharmProjects/SurveillanceCamera/DataSet/" + str(filename))
                    user1 = str(filename)
                    break
                User1_face_encoding = face_recognition.face_encodings(User1)[0]
                # Load a second sample picture and learn how to recognize it.


                # Create arrays of known face encodings and their names
                known_face_encodings = [
                    User1_face_encoding
                ]
                known_face_names = [
                    user1
                ]
                countWrongf = 0
                countRightf = 0
                # Initialize some variables
                face_locations = []
                face_encodings = []
                face_names = []
                process_this_frame = True

                while True:
                    # Grab a single frame of video
                    ret, frame = video_capture.read()

                    # Resize frame of video to 1/4 size for faster face recognition processing
                    small_frame = cv2.resize(frame, (0, 0), fx=0.25, fy=0.25)

                    # Convert the image from BGR color (which OpenCV uses) to RGB color (which face_recognition uses)
                    rgb_small_frame = numpy.ascontiguousarray(small_frame[:, :, ::-1])
                    # Only process every other frame of video to save time
                    if process_this_frame:
                        # Find all the faces and face encodings in the current frame of video
                        face_locations = face_recognition.face_locations(rgb_small_frame)
                        face_encodings = face_recognition.face_encodings(rgb_small_frame, face_locations)

                        face_names = []

                        for face_encoding in face_encodings:
                            # See if the face is a match for the known face(s)
                            matches = face_recognition.compare_faces(known_face_encodings, face_encoding)
                            name = "Unknown"

                            # # If a match was found in known_face_encodings, just use the first one.
                            # if True in matches:
                            #     first_match_index = matches.index(True)
                            #     name = known_face_names[first_match_index]

                            # Or instead, use the known face with the smallest distance to the new face
                            face_distances = face_recognition.face_distance(known_face_encodings, face_encoding)

                            best_match_index = np.argmin(face_distances)
                            if matches[best_match_index]:
                                name = known_face_names[best_match_index]

                            face_names.append(name)
                            if name == "Unknown":
                                countWrongf += 1
                                print(countWrongf)
                                if countWrongf == 6:
                                    x = datasave["numberRep"]
                                    for l in range(0, x):
                                        Speak(datasave["AlarmText"])
                                    while x > 0:
                                        beepy.beep(datasave["alarm"])
                                        x -= 1
                                    cv2.imwrite('Captures/intruder.jpg',
                                                frame)
                                    sendmail('Captures/intruder.jpg', '../Time_of_movements.csv')

                            else:
                                countRightf += 1
                                print(countRightf)
                                if countRightf == 20:
                                    print("ok,continue")

                    process_this_frame = not process_this_frame

                    # Display the results
                    for (top, right, bottom, left), name in zip(face_locations, face_names):
                        # Scale back up face locations since the frame we detected in was scaled to 1/4 size
                        top *= 4
                        right *= 4
                        bottom *= 4
                        left *= 4

                        # Draw a box around the face
                        cv2.rectangle(frame, (left, top), (right, bottom), (0, 0, 255), 2)

                        # Draw a label with a name below the face
                        cv2.rectangle(frame, (left, bottom - 35), (right, bottom), (0, 0, 255), cv2.FILLED)
                        font = cv2.FONT_HERSHEY_DUPLEX
                        cv2.putText(frame, name, (left + 6, bottom - 6), font, 1.0, (255, 255, 255), 1)

                    # Display the resulting image hide because the user should not see the camera overview
                    cv2.imshow('Video', frame)

                    # Hit 'q' on the keyboard to quit!
                    if cv2.waitKey(1) & 0xFF == ord('q'):
                        break

                # Release handle to the webcam
                video_capture.release()
                cv2.destroyAllWindows()
                break

            else:
                print("no user found!")
        print("the system is off")

thread1 = face()
#thread2 = motion()
thread1.start()
#thread2.start()
thread1.join()
#thread2.join()
