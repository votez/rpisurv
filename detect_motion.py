# import the necessary packages
from threading import Thread
import threading
from imutils.video import VideoStream
from imutils.video import FPS
# import PiVideoStream
import argparse
import datetime
import imutils
import time
import cv2
import collections
import os
import numpy

MAX_BUFFER_LEN = 1000
CLASSES = ["background", "aeroplane", "bicycle", "bird", "boat",
           "bottle", "bus", "car", "cat", "chair", "cow", "diningtable",
           "dog", "horse", "motorbike", "person", "pottedplant", "sheep",
           "sofa", "train", "tvmonitor"]
INTERESTING_CLASSES = {"bicycle", "car", "cat", "cow", "dog", "horse", "motorbike", "person", "sheep"}

COLORS = numpy.random.uniform(0, 255, size=(len(CLASSES), 3))


def process_file(video):
    global height, width, top, bottom, left, right, scale, avg, st, motion, display
    counter = 0
    while True:
        counter += 1
        frame = video.read()
        if frame is None:
            break
        frame = frame[1]
        if frame is None:
            break

        if motion == 0:
            buffer.append(frame)

        if height is None:
            height = len(frame)
            width = len(frame[0])
            top = args.get("top")
            bottom = height - args.get("bottom")
            left = args.get("left")
            right = width - args.get("right")
            scale = right - left / 500
            scale = 1 if scale < 1 else scale
            print(
                f"t:{top} b:{bottom} l:{left} r:{right}, HxW: {height}x{width}, area of interest {right - left}x{bottom - top}")
        disp = frame.copy()
        copy = frame[top:bottom, left:right]
        if right - left > 500:
            copy = imutils.resize(copy, width=500)
        else:
            copy = copy.copy()
        diff = 0
        if counter % QUANTISATION == 0:
            gray = cv2.cvtColor(copy, cv2.COLOR_BGR2GRAY)
            gray = cv2.GaussianBlur(gray, (21, 21), 0)
            # if the average frame is None, initialize it
            if avg is None:
                print("[INFO] starting background model...")
                avg = gray.copy().astype("float")
                continue
            # accumulate the weighted average between the current frame and
            # previous frames, then compute the difference between the current
            # frame and running average
            cv2.accumulateWeighted(gray, avg, WEIGHT)
            frameDelta = cv2.absdiff(gray, cv2.convertScaleAbs(avg))
            # threshold the delta image, dilate the thresholded image to fill
            # in holes, then find contours on thresholded image
            thresh = cv2.threshold(frameDelta, THRESHOLD, 255, cv2.THRESH_BINARY)[1]
            thresh = cv2.dilate(thresh, None, iterations=2)
            st = sum(sum(thresh))
            cnts = imutils.grab_contours(
                cv2.findContours(thresh.copy(), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)) if st > area_limit else []
            fs = 0
            for c in cnts:
                # if the contour is too small, ignore it
                ca = cv2.contourArea(c)
                if ca < contour_limit_low:
                    #                print(f"Contour is too small: {ca}")
                    continue
                if ca > contour_limit_high:
                    #                print(f"Contour is too big: {ca}")
                    continue
                fs = fs + ca
                diff = max(diff, ca)
                # compute the bounding box for the contour, draw it on the frame,
                # and update the text
                (x, y, w, h) = cv2.boundingRect(c)
            #            cv2.rectangle(copy, (x, y), (x + w, y + h), (0, 255, 0), 2)
            #            cv2.putText(copy, str(ca),org=(x, y - 20), fontFace=cv2.FONT_HERSHEY_SIMPLEX, color=(0,255,0),thickness=1, fontScale=1)

            #            cv2.rectangle(disp, (left + int(x*scale), top + int(y*scale)), (left+int( scale*(x + w)), top+int( scale*(y + h))), (0, 255, 0), 2)
            #            cv2.putText(disp, str(ca),org=(left+int(x*scale), top+int( scale*y) - 20), fontFace=cv2.FONT_HERSHEY_SIMPLEX, color=(0,255,0),thickness=1, fontScale=1)

            cv2.rectangle(disp, (left, top), (right, bottom), (255, 0, 0), 2)
            cv2.putText(disp, f"Sum: {int(st)}", org=(20, 50), fontFace=cv2.FONT_HERSHEY_SIMPLEX, color=(0, 0, 255),
                        thickness=3, fontScale=1.5)
            cv2.putText(disp, f"Filtered: {int(fs)}", org=(20, 100), fontFace=cv2.FONT_HERSHEY_SIMPLEX,
                        color=(0, 0, 255),
                        thickness=3, fontScale=1.5)
            cv2.putText(disp, f"max contour: {int(diff)}", org=(20, 130), fontFace=cv2.FONT_HERSHEY_SIMPLEX,
                        color=(0, 0, 255), thickness=3, fontScale=1.5)
            #        if args.get("display") :
            #             cv2.imshow("TEST", disp)
            #            cv2.imshow("DIFF", frameDelta)
            #            cv2.imshow("THRESHOLD", thresh)

            detected = False
            if st < area_limit:
                cv2.putText(disp, f"Area low {st} < {area_limit}", org=(20, 600), fontFace=cv2.FONT_HERSHEY_SIMPLEX,
                            color=(255, 0, 0), thickness=3, fontScale=1.5)
            if st > area_limit and fs < filtered_limit:
                cv2.putText(disp, f"Filtered {filtered_limit}", org=(20, 600), fontFace=cv2.FONT_HERSHEY_SIMPLEX,
                            color=(255, 0, 0), thickness=3, fontScale=1.5)

            if st > area_limit and fs > filtered_limit:
                cv2.putText(disp, f"Ahtung! {filtered_limit}", org=(20, 600), fontFace=cv2.FONT_HERSHEY_SIMPLEX,
                            color=(255, 255, 0), thickness=3, fontScale=1.5)
                #            (h, w) = disp.shape[:2]
                (h, w) = (len(copy), len(copy[0]))
                blob = cv2.dnn.blobFromImage(copy, 0.007843, (len(copy), len(copy[0])), 127.5)
                net.setInput(blob)
                detections = net.forward()
                # loop over the detections
                for i in numpy.arange(0, detections.shape[2]):
                    # extract the confidence (i.e., probability) associated with the
                    # prediction
                    confidence = detections[0, 0, i, 2]
                    # filter out weak detections by ensuring the `confidence` is
                    # greater than the minimum confidence
                    if confidence > args["confidence"]:
                        # extract the index of the class label from the `detections`,
                        # then compute the (x, y)-coordinates of the bounding box for
                        # the object
                        idx = int(detections[0, 0, i, 1])
                        box = detections[0, 0, i, 3:7] * numpy.array([w, h, w, h])
                        (startX, startY, endX, endY) = box.astype("int")
                        # display the prediction
                        if CLASSES[idx] not in INTERESTING_CLASSES:
                            continue
                        label = "{}: {:.2f}%".format(CLASSES[idx], confidence * 100)
                        print("[INFO] {}".format(label))
                        cv2.rectangle(copy, (startX, startY), (endX, endY), COLORS[idx], 2)
                        y = startY - 15 if startY - 15 > 15 else startY + 15
                        cv2.putText(copy, label, (int(startX * scale) + left, int(y * scale) + top),
                                    cv2.FONT_HERSHEY_SIMPLEX, 1, COLORS[idx], 2)
                        detected = True
            if detected:
                if motion == 0 and out is not None:
                    while len(buffer) > 0:
                        out.write(buffer.popleft())
                #                cv2.waitKey(0)
                motion = bufferSize  # record X more seconds

            if motion > 0:
                cv2.putText(disp, f"Recording {motion}", org=(20, 500), fontFace=cv2.FONT_HERSHEY_SIMPLEX,
                            color=(0, 0, 255), thickness=3, fontScale=2)

            if display:
                cv2.imshow("TEST", disp)

        if out is not None and motion > 0:
            #        cv2.putText(copy, "WRITING", (10, 140), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 255), 2)
            out.write(frame)

        if motion > 0:
            motion = motion - 1

        fps.update()
        if display and counter % QUANTISATION == 0:
            #        cv2.putText(copy, "Contour: {}".format(diff), (10, 20), cv2.FONT_HERSHEY_SIMPLEX, 1.5, (0, 0, 255), 2)
            #        cv2.putText(copy, "Area: {}".format(st), (10, 70), cv2.FONT_HERSHEY_SIMPLEX, 1.5, (0, 0, 255), 2)
            #        cv2.putText(copy, "FPS: {}".format(fps), (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 1.5, (0, 0, 255), 2)
            #    cv2.imshow("Stream",frame)
            #        cv2.imshow("Area", copy)
            key = cv2.waitKey(1) & 0xFF
            # 81
            # 83
            # 82
            # 84
            # 81

            if key == ord('q'):
                print("Exit")
                break
            elif key == ord('l'):
                left = left + 10
                avg = None
                print(f"-l {left} -r {width - right} -t {top} -b {height - bottom}")
            elif key == 81:
                # left arrow
                left = left - 10
                avg = None
                print(f"-l {left} -r {width - right} -t {top} -b {height - bottom}")
            elif key == ord('r'):
                right = right - 10
                avg = None
                print(f"-l {left} -r {width - right} -t {top} -b {height - bottom}")
            elif key == 83:
                # right arrow
                right = right + 10
                avg = None
                print(f"-l {left} -r {width - right} -t {top} -b {height - bottom}")
            elif key == ord('t'):
                top = top + 10
                avg = None
                print(f"-l {left} -r {width - right} -t {top} -b {height - bottom}")
            elif key == 82:
                # up arrow
                top = top - 10
                avg = None
                print(f"-l {left} -r {width - right} -t {top} -b {height - bottom}")
            elif key == ord('b'):
                bottom = bottom - 10
                avg = None
                print(f"-l {left} -r {width - right} -t {top} -b {height - bottom}")
            elif key == 84:
                # down arrow
                bottom = bottom + 10
                avg = None
                print(f"-l {left} -r {width - right} -t {top} -b {height - bottom}")
            elif key == ord(' '):
                print("Pause")
                cv2.waitKey(0)
            elif key == ord('d'):
                display = False


if __name__ == "__main__":
    net = cv2.dnn.readNetFromCaffe('/home/votez/opt/pivideo/mobilenet_ssd/MobileNetSSD_deploy.prototxt',
                                   '/home/votez/opt/pivideo/mobilenet_ssd/MobileNetSSD_deploy.caffemodel')

    # construct the argument parser and parse the arguments
    ap = argparse.ArgumentParser()
    ap.add_argument("-v", "--video", nargs="+", help="path to the video file")
    ap.add_argument("-l", "--left", type=int, default=0, help="cut from left")
    ap.add_argument("-r", "--right", type=int, default=0, help="cut from right")
    ap.add_argument("-t", "--top", type=int, default=0, help="cut from top")
    ap.add_argument("-b", "--bottom", type=int, default=0, help="cut from bottom")
    ap.add_argument("-cl", "--contour_low", type=int, default=300, help="minimum contour size")
    ap.add_argument("-ch", "--contour_high", type=int, default=25000, help="maximum contour size")
    ap.add_argument("-a", "--area", type=int, default=5000, help="minimum area size")
    ap.add_argument("-af", "--filtered", type=int, help="minimum area size")
    ap.add_argument("-s", "--slot", type=int, default=150, help="frames to preserve")
    ap.add_argument("-n", "--noop", action="store_true", help="just record sample frame and output area of interest")
    ap.add_argument("-o", "--output", type=str, required=True, help="output file")
    ap.add_argument("-q", "--quantization", type=int, default=10, help="How many frames to skip between checks")
    ap.add_argument("-w", "--weight", type=float, default=0.3, help="current frame weight")
    ap.add_argument("-d", "--display", action="store_true", help="Display imshow")
    ap.add_argument("-tr", "--threshold", type=int, default=25, help="image threshold")
    ap.add_argument("-c", "--confidence", type=float, default=0.3, help="confidence level")
    resolution = (1280, 720)

    args = vars(ap.parse_args())
    firstFrame = None
    # loop over the frames of the video
    avg = None
    motionCounter = 0
    WEIGHT = args.get("weight")
    THRESHOLD = args.get("threshold")
    QUANTISATION = args.get("quantization")
    bufferSize = args.get("slot")
    noop = args.get("noop")
    timestamp = datetime.datetime.now().second
    fps = 0.0
    st = 0
    files = args["video"]
    outputFile = args.get("output")

    height = None
    width = None
    top = 0
    bottom = 0
    left = 0
    right = 0
    buffer = collections.deque(maxlen=bufferSize)
    index = 0
    out = None
    scale = 1
    display = args.get("display")
    if not args.get("noop"):
        print(f"Write to {outputFile}")
        out = cv2.VideoWriter(outputFile, cv2.VideoWriter_fourcc('m', 'p', '4', 'v'), 30, resolution)

    motion = 100  # capture at least first 3 seconds to have a proper file
    contour_limit_low = args.get("contour_low")
    contour_limit_high = args.get("contour_high")
    area_limit = args.get("area")
    filtered_limit = args.get("filtered")
    # while not reader.stopped or len(reader.buffer) > 0:
    lastVideoTs = datetime.datetime.now()
    for file in files:
        print(f"Process file {file}")
        vs = cv2.VideoCapture(file)
        fps = FPS().start()
        process_file(vs)
        fps.stop()
        vs.release()
        print(f"FPS: {fps.fps()}")

    if out is not None:
        out.release()
    cv2.destroyAllWindows()
