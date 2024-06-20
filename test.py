import os
import smtplib
from email import encoders
from email.mime.base import MIMEBase
from email.mime.image import MIMEImage
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText


def SendMail(image_frame,filename):
    img_data = open(image_frame, 'rb').read()
    msg = MIMEMultipart()
    msg['Subject'] = 'Intruder detected'
    msg['From'] = 'cfeshete97@outlook.com'
    msg['To'] = 'bukedidavid@gmail.com'

    text = MIMEText("an intruder has been detected, please open this website to manage the camera:https://my.ivideon.com/cameras/groups/own")
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
SendMail('Captures/intruder.jpg','Time_of_movements.csv')