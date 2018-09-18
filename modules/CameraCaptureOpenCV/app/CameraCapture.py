# To make python 2 and python 3 compatible code
from __future__ import division
from __future__ import absolute_import

# Imports
import sys
if sys.version_info[0] < 3:  # e.g python version <3
    import cv2
else:
    import cv2
    from cv2 import cv2
import numpy
import requests
import json
import time
import base64
import time
import ptvsd

import VideoStream
from VideoStream import VideoStream
import text2speech

jpgdata = []


def addImage(imageName):
    f = open(imageName, 'r+')
    jpgdata.append(f.read())
    f.close()


imageCount = len(jpgdata)
lastTagSpoken = ''

count = 0


class CameraCapture(object):

    def __IsInt(self, string):
        try:
            int(string)
            return True
        except ValueError:
            return False

    def __init__(
            self,
            videoPath,
            bingSpeechKey,
            predictThreshold,
            imageProcessingEndpoint,
            sendToHubCallback=None
    ):
        self.videoPath = videoPath
        self.tts = text2speech.TextToSpeech(bingSpeechKey)
        self.predictThreshold = predictThreshold
        self.imageProcessingEndpoint = imageProcessingEndpoint
        self.imageProcessingParams = ""
        self.sendToHubCallback = sendToHubCallback

        if self.__IsInt(videoPath):
            # case of a usb camera (usually mounted at /dev/video* where * is an int)
            self.isWebcam = True
        
        
        
        self.vs = None
        
        


    def __buildSentence(self, tag):
        vowels = ('a', 'e', 'i', 'o', 'u', 'A', 'E', 'I', 'O', 'U')
        sentence = 'You scanned '
        if tag.startswith(vowels):
            sentence = sentence + 'an '
        else:
            sentence = sentence + 'a '
        return sentence + tag

    def __sendFrameForProcessing(self, frame):
        global count, jpgdata, lastTagSpoken
        count = count + 1
        # time.sleep(0.5)
        print("send frame: " + str(count))

        headers = {'Content-Type': 'application/octet-stream'}
        response = requests.post(self.imageProcessingEndpoint, headers=headers,
                                 params=self.imageProcessingParams, data=frame)

        sortResponse = sorted(
            response.json(), key=lambda k: k['Probability'], reverse=True)[0]

        print(sortResponse)

        probability = sortResponse['Probability']

        if probability > self.predictThreshold and sortResponse['Tag'] != lastTagSpoken:
            lastTagSpoken = sortResponse['Tag']
            self.tts.Text2Speech(self.__buildSentence(sortResponse['Tag']))
            return json.dumps(response.json())
        else:
            return []

    def __displayTimeDifferenceInMs(self, endTime, startTime):
        return str(int((endTime-startTime) * 1000)) + " ms"

    def __enter__(self):
        self.vs = VideoStream(int(self.videoPath)).start()
        # needed to load at least one frame into the VideoStream class
        time.sleep(1.0)

        return self

    def start(self):
        frameCounter = 0
        while True:
            frameCounter += 1
            frame = self.vs.read()

            # Process externally
            if self.imageProcessingEndpoint != "":
                encodedFrame = cv2.imencode(".jpg", frame)[1].tostring()
                response = self.__sendFrameForProcessing(encodedFrame)

                # forwarding outcome of external processing to the EdgeHub
                if response != "[]" and self.sendToHubCallback is not None:
                    self.sendToHubCallback(response)

    def __exit__(self, exception_type, exception_value, traceback):
        pass
