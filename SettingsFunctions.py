"""this file contains the methods that are called in the GUI , we can call them slots"""

import os
from pathlib import Path
import cv2
import pickle
import json

import pyttsx3

import Data
import beepy
import os



def check_path(path):            #function to confirm whether the given path exists or not
    dir = os.path.dirname(path)  #if it doesn't exist this function will create
    if not os.path.exists(dir):
        os.makedirs(dir)
def checkLimit():#this method verify on the directory if there is not more than two user
    directory = r'C:\Users\appli\PycharmProjects\IntruderFaceDetection\DataSet'
    if len(os.listdir(directory))==2:
        beepy.beep(3)
        datasave=Data.load()
        datasave["LimitReached"]=True
        Data.save(datasave)
    else:
        print("ok")
def Speak(audio):#this method is used for text to speech
    datasave = Data.load()
    engine = pyttsx3.init('sapi5')
    voices = engine.getProperty('voices')
    engine.setProperty('voice', voices[datasave["voice"]].id)
    engine.say(audio)
    engine.runAndWait()
def AddFace(name):#this method is used to add the user's face on the system
    checkLimit()
    datasave = Data.load()
    if datasave["LimitReached"] == False:
        datasave = Data.load()
        vid_cam = cv2.VideoCapture(0)  # Start video capturing
        face_cascade = cv2.CascadeClassifier(
            'haarcascade_frontalface_default.xml')  # Detect object in video stream using Haarcascade Frontal Face

        face_id = 1  # For each person,there will be one face id
        n = face_id
        count = 0  # Initialize sample face image

        check_path("DataSet/")

        if datasave["ID"] == n:
            face_id = datasave["ID"] + 1
            datasave["ID"] = face_id
            datasave["user2"] = name
        else:
            datasave["ID"] = face_id
            datasave["user1"] = name
        Data.save(datasave)

        print("camera activation")
        while (True):
            checkLimit()
            datasave = Data.load()
            if datasave["LimitReached"] == True:#to stop the program if the users limit numbe ris reached
                break
            # Capture video frame _, is used to ignored first value because vid_cam.read() is returning 2 values
            _, image_frame = vid_cam.read()  # Capture video frame _, is used to ignored first value because vid_cam.read() is returning 2 values

            gray = cv2.cvtColor(image_frame, cv2.COLOR_BGR2GRAY)  # Convert frame to grayscale

            faces = face_cascade.detectMultiScale(gray, 1.4, 5)  # Detect faces using Cascade Classifier(xml file)

            for (x, y, w, h) in faces:
                cv2.rectangle(image_frame, (x, y), (x + w, y + h), (255, 0, 0),
                              2)  # Crop the image frame into rectangle
                count += 1
                red = list(datasave.keys())[list(datasave.values()).index(name)]
                cv2.imwrite("DataSet/" + str(name) + "." + str(red) + "." + str(count) + ".jpg",
                            image_frame[y:y + h, x:x + w])  # Save the captured image into the datasets folder

                cv2.imshow('Creating Dataset!!!',
                           image_frame)

            if cv2.waitKey(100) & 0xFF == 27:  # To stop taking video, press 'Esc'
                break

            elif count == 1:  # If image taken reach 1, stop taking video
                break

        vid_cam.release()  # Stop video

        cv2.destroyAllWindows()  # Close all windows





def DeleteUser(name):#this method is used to delete a user from the system
    ok=True
    directory = r'C:\Users\appli\PycharmProjects\IntruderFaceDetection\DataSet'
    datasave = Data.load()
    if datasave["user1"] == "" and datasave["user2"] == "":#if there is no user
        print("There is no User!")
        datasave["promptNotF"] = True
        Data.save(datasave)
    else:##if there is a user
        if len(os.listdir(directory)) > 0:#add an extra security to check if there is a user
            for filename in os.listdir(directory):#iterate trough the files in the folder
                red = list(datasave.keys())[list(datasave.values()).index(name)]
                print(name + "." + str(red))
                if filename.startswith(str(name) + "." + str(red)):#to check if the file correspond to the request

                    print("found file!")
                    datasave["promptNotF"] = False
                    os.remove("C:/Users/appli/PycharmProjects/IntruderFaceDetection/DataSet/" + str(filename))
                    Data.save(datasave)
                    ok = False
                    if len(os.listdir(directory)) == 0:
                        datasave["user1"]=""
                        datasave["user2"]=""
                        Data.save(datasave)
                        datasave=Data.load()


            if ok == True:
                    print("file not found")
                    datasave["promptNotF"] = True
                    Data.save(datasave)

        else:
            Data.promptNotF = True
            Data.save(datasave)




