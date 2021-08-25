from __future__ import print_function
import os.path
import os

import numpy
from googleapiclient.discovery import build
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials

import imutils
import cv2
import argparse

from picamera import PiCamera
from picamera.color import Color
from time import sleep
from datetime import datetime
from googleapiclient.http import MediaFileUpload

# If modifying these scopes, delete the file token.json.
SCOPES = ['https://www.googleapis.com/auth/drive']
MIN_AREA = 150
SCALE = 720
# rpiFolder = '1bMnujx42DmxmhT2U-cXjuSijkvqLSxde'
# changesFolder = '1B4ZgTFazv5My3gSWAsjYg0dlLjaqy12a'
changesFolder = '1tFNJX8-JuZqFQyKWkD_nfzW7c1RKNi-v'
rpiFolder = '1RoB8bBSurOYf23zFTjA92VWDGOB_rwBj'
debugFolder = '1eNIxIXKW0SpvprChaOO4boodHahsnaiE'


def calc_diff(original, test, area_threshold, contour_threshold, top, bottom, left, right):
    height, width, _ = original.shape
    scaled = 500
    half = scaled / 2
    scale = width / scaled
    # initialize the first frame in the video stream
    first_frame = imutils.resize(original, width=scaled)
    first_frame[:top, :] = [0, 0, 0]
    first_frame[bottom:, :] = [0, 0, 0]
    first_frame[:, :left] = [0, 0, 0]
    first_frame[:, right:] = [0, 0, 0]
    first_frame = cv2.cvtColor(first_frame, cv2.COLOR_BGR2GRAY)
    first_frame = cv2.GaussianBlur(first_frame, (21, 21), 0)
    # loop over the frames of the video
    frame = imutils.resize(test, width=scaled)
    frame[:top, :] = [0, 0, 0]
    frame[bottom:, :] = [0, 0, 0]
    frame[:, :left] = [0, 0, 0]
    frame[:, right:] = [0, 0, 0]
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    gray = cv2.GaussianBlur(gray, (21, 21), 0)
    frame_delta = cv2.absdiff(first_frame, gray)
    thresh = cv2.threshold(frame_delta, 25, 255, cv2.THRESH_BINARY)[1]
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
        if cv2.contourArea(c) < MIN_AREA:
            continue
        if cv2.contourArea(c) > diff:
            diff = cv2.contourArea(c)
        # compute the bounding box for the contour, draw it on the frame,
        # and update the text
        (x, y, w, h) = cv2.boundingRect(c)
        (xs, ys, ws, hs) = (int(x * scale), int(y * scale), int(w * scale), int(h * scale))
        #        cv2.rectangle(frame, (x, y), (x + w, y + h), (0, 255, 0), 2)
        cv2.putText(test, str(cv2.contourArea(c)), org=(xs, ys), fontFace=cv2.FONT_HERSHEY_PLAIN, color=(255, 255, 255),
                    fontScale=1)
        cv2.rectangle(test, (xs, ys), (xs + ws, ys + hs), (0, 255, 0), 2)
        cv2.rectangle(test, (int(left * scale), int(top * scale)), (int(right * scale), int(bottom * scale)),
                      (255, 0, 0), 1)

    cv2.putText(test, f"Area {str(sum(sum(thresh)))}", org=(900, 20), fontFace=cv2.FONT_HERSHEY_PLAIN,
                color=(0, 100, 255), fontScale=1.5)
    cv2.putText(test, f"Contour: {diff}", org=(900, 45), fontFace=cv2.FONT_HERSHEY_PLAIN, color=(0, 100, 255),
                fontScale=1.5)
    return diff > contour_threshold or sum(sum(thresh)) > area_threshold


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("-f", "--force", type=bool, default=False, help="force full scale upload")
    ap.add_argument("-a", "--area", type=int, default=900, help="minimum area to consider")
    ap.add_argument("-l", "--left", type=int, default=0, help="cut from left")
    ap.add_argument("-r", "--right", type=int, default=500, help="cut from right")
    ap.add_argument("-t", "--top", type=int, default=150, help="cut from top")
    ap.add_argument("-b", "--bottom", type=int, default=281, help="cut from bottom")
    ap.add_argument("-c", "--contour", type=int, default=500, help="minimum contour size")
    args = vars(ap.parse_args())

    credentials = None
    # The file token.json stores the user's access and refresh tokens, and is
    # created automatically when the authorization flow completes for the first
    # time.
    if os.path.exists('/home/pi/opt/token.json'):
        credentials = Credentials.from_authorized_user_file('/home/pi/opt/token.json', SCOPES)
    # If there are no (valid) credentials available, let the user log in.
    if not credentials or not credentials.valid:
        if credentials and credentials.expired and credentials.refresh_token:
            credentials.refresh(Request())
        else:
            print("Credentials not valid")
            flow = InstalledAppFlow.from_client_secrets_file(
                'credentials.json', SCOPES)
            credentials = flow.run_local_server(port=0)
        # Save the credentials for the next run
        with open('token.json', 'w') as token:
            token.write(credentials.to_json())

    service = build('drive', 'v3', credentials=credentials)

    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    with PiCamera() as camera:
        # Original 2592, 1944
        #        camera.resolution = (2592, 1944)
        camera.resolution = (1280, 720)
        camera.annotate_text = timestamp
        camera.annotate_background = Color('blue')
        camera.rotation = 180
        sleep(5)
        camera.capture('/var/ramdisk/image.jpg')

    test = cv2.imread('/var/ramdisk/image.jpg', cv2.IMREAD_COLOR)
    original = cv2.imread('/var/ramdisk/previous.jpg', cv2.IMREAD_COLOR)

    if original is None:
        original = numpy.zeros((720, 1280, 3), numpy.uint8)

    is_different = calc_diff(original, test,
                             area_threshold=args.get("area"), contour_threshold=args.get("contour"),
                             top=args.get("top"), bottom=args.get("bottom"), left=args.get("left"),
                             right=args.get("right"))

    if is_different or args.get("force"):
        print("Changes detected")
        cv2.imwrite('/var/ramdisk/contour.jpg', test)
        file_metadata = {
            'name': datetime.now().strftime("contour_%Y%m%d-%H%M.jpg"),
            'parents': [debugFolder]
        }
        media = MediaFileUpload('/var/ramdisk/contour.jpg',
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
        media = MediaFileUpload('/var/ramdisk/image.jpg',
                                mimetype='image/jpeg',
                                resumable=False)
        file = service.files().create(body=file_metadata,
                                      media_body=media,
                                      fields='id').execute()
        print(f"Uploaded original {file}")

    img = cv2.imread('/var/ramdisk/image.jpg')
    img = imutils.resize(img, width=SCALE)
    cv2.imwrite('/var/ramdisk/scaled.jpg', img)

    file_metadata = {
        'name': datetime.now().strftime("komnata_%Y%m%d-%H%M.jpg"),
        'parents': [rpiFolder]
    }
    media = MediaFileUpload('/var/ramdisk/scaled.jpg',
                            mimetype='image/jpeg',

                            resumable=False)
    service.files().create(body=file_metadata,
                           media_body=media,
                           fields='id').execute()

    test = imutils.resize(test, width=SCALE)
    cv2.imwrite('/var/ramdisk/small_contour.jpg', test)
    file_metadata = {
        'name': datetime.now().strftime("small_contour_%Y%m%d-%H%M.jpg"),
        'parents': [rpiFolder]
    }
    media = MediaFileUpload('/var/ramdisk/small_contour.jpg',
                            mimetype='image/jpeg',
                            resumable=False)
    file = service.files().create(body=file_metadata,
                                  media_body=media,
                                  fields='id').execute()
    print(f"Uploaded small debug {file}")

    os.rename(r'/var/ramdisk/image.jpg', r'/var/ramdisk/previous.jpg')


if __name__ == '__main__':
    main()
