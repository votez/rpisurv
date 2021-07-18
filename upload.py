from __future__ import print_function
import os.path
import os

import numpy
from googleapiclient.discovery import build
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
import base64

import imutils
import time
import cv2

from PIL import Image

from picamera import PiCamera
from picamera.color import Color
from time import sleep
from datetime import datetime
from apiclient.http import MediaFileUpload

# If modifying these scopes, delete the file token.json.
SCOPES = ['https://www.googleapis.com/auth/drive']
THRESHOLD = 900
#rpiFolder = '1bMnujx42DmxmhT2U-cXjuSijkvqLSxde'
#changesFolder = '1B4ZgTFazv5My3gSWAsjYg0dlLjaqy12a'
changesFolder = '1tFNJX8-JuZqFQyKWkD_nfzW7c1RKNi-v'
rpiFolder = '1RoB8bBSurOYf23zFTjA92VWDGOB_rwBj'
debugFolder = '1eNIxIXKW0SpvprChaOO4boodHahsnaiE'

def calcDiff(original, test):
    height, width, _ = original.shape
    scaled = 500
    half=scaled/2
    scale = width / scaled
    # initialize the first frame in the video stream
    firstFrame = imutils.resize(original, width=scaled)
    firstFrame[:150,:] = [0,0,0]
    firstFrame = cv2.cvtColor(firstFrame, cv2.COLOR_BGR2GRAY)
    firstFrame = cv2.GaussianBlur(firstFrame, (21, 21), 0)
    # loop over the frames of the video
    frame = imutils.resize(test, width=scaled)
    frame[:150,:] = [0,0,0]
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    gray = cv2.GaussianBlur(gray, (21, 21), 0)
    frameDelta = cv2.absdiff(firstFrame, gray)
    thresh = cv2.threshold(frameDelta, 25, 255, cv2.THRESH_BINARY)[1]
    # dilate the thresholded image to fill in holes, then find contours
    # on thresholded image
    thresh = cv2.dilate(thresh, None, iterations=2)
    cnts = cv2.findContours(thresh.copy(), cv2.RETR_EXTERNAL,
    	cv2.CHAIN_APPROX_SIMPLE)
    cnts = imutils.grab_contours(cnts)
    diff = 0
    # loop over the contours
    for c in cnts:
        # if the contour is too small, ignore it
        if cv2.contourArea(c) > diff:
            diff = cv2.contourArea(c)
    	# compute the bounding box for the contour, draw it on the frame,
    	# and update the text
        (x, y, w, h) = cv2.boundingRect(c)
        (xs,ys,ws,hs) = (int(x*scale), int(y*scale), int(w * scale), int(h * scale))
#        cv2.rectangle(frame, (x, y), (x + w, y + h), (0, 255, 0), 2)
        cv2.putText(test,str(cv2.contourArea(c)),org=(xs,ys),fontFace=cv2.FONT_HERSHEY_PLAIN,color=(255,255,255), fontScale=1)
        cv2.rectangle(test, (xs, ys), (xs + ws, ys + hs), (0, 255, 0), 2)
    return diff


def main():
    creds = None
    # The file token.json stores the user's access and refresh tokens, and is
    # created automatically when the authorization flow completes for the first
    # time.
    if os.path.exists('/home/pi/opt/token.json'):
        creds = Credentials.from_authorized_user_file('/home/pi/opt/token.json', SCOPES)
    # If there are no (valid) credentials available, let the user log in.
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            print("Credentials not valid")
            exit(-5)
            flow = InstalledAppFlow.from_client_secrets_file(
                'credentials.json', SCOPES)
            creds = flow.run_local_server(port=0)
        # Save the credentials for the next run
        with open('token.json', 'w') as token:
            token.write(creds.to_json())

    service = build('drive', 'v3', credentials=creds)


    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    with PiCamera() as camera:
# Original 2592, 1944
#        camera.resolution = (2592, 1944)  
        camera.resolution = (1280, 720)
        camera.annotate_text = timestamp
        camera.annotate_background = Color('blue')
        camera.rotation = 180
        sleep(5)
        camera.capture('/var/lib/ramdisk/image.jpg')
    

    test = cv2.imread('/var/lib/ramdisk/image.jpg', cv2.IMREAD_COLOR)
    original = cv2.imread('/var/lib/ramdisk/previous.jpg', cv2.IMREAD_COLOR)

    if original is None:
        original = numpy.zeros((720,1280,3), numpy.uint8)

    if calcDiff(original, test) > THRESHOLD:
        print("Changes detected")
        cv2.imwrite('/var/lib/ramdisk/contour.jpg',test)
        file_metadata = {
            'name': datetime.now().strftime("contour_%Y%m%d-%H%M.jpg"),
            'parents': [debugFolder]
        }
        media = MediaFileUpload('/var/lib/ramdisk/contour.jpg',
                            mimetype='image/jpeg',
                            resumable=False)
        file = service.files().create(body=file_metadata,
                                        media_body=media,
                                        fields='id').execute()
        print(f"Uploaded debug {file}")
        file_metadata = {
            'name': datetime.now().strftime("%Y%m%d-%H%M.jpg"),
            'parents': [changesFolder]
        }
        media = MediaFileUpload('/var/lib/ramdisk/image.jpg',
                            mimetype='image/jpeg',
                            resumable=False)
        file = service.files().create(body=file_metadata,
                                        media_body=media,
                                        fields='id').execute()
        print(f"Uploaded original {file}")

    img = Image.open('/var/lib/ramdisk/image.jpg')
    new_width  = 746
    new_height = 420
    img = img.resize((new_width, new_height), Image.ANTIALIAS)
    img.save('/var/lib/ramdisk/scaled.jpg')

    file_metadata = {
        'name': datetime.now().strftime("komnata_%Y%m%d-%H%M.jpg"),
        'parents': [rpiFolder]
    }
    media = MediaFileUpload('/var/lib/ramdisk/scaled.jpg',
                        mimetype='image/jpeg',

                         resumable=False)
    service.files().create(body=file_metadata,
                                    media_body=media,
                                    fields='id').execute()

    os.rename(r'/var/lib/ramdisk/image.jpg',r'/var/lib/ramdisk/previous.jpg')

if __name__ == '__main__':
    main()