#!/usr/bin/env python
#
# www.learnopencv.com/deep-learning-based-object-detection-using-yolov3-with-opencv-python-c/

import cv2
import numpy as np
import time
import zm_util

class Detector:

    def __init__(self, width, height, conf_threshold):
        # Width and height can be 320, 416, or 608. Lower is faster, higher is
        # more accurate.

        self._width = width
        self._height = height
        self._conf_threshold = conf_threshold
        self._names = []
        self._net = None
        self._detection_time = None
        self._matches = []

    def setup(self, config_file, weights_file, names_file):

        try:
            f1 = open(config_file)
            f2 = open(weights_file)
            f3 = open(names_file)
        except IOError:
            zm_util.debug("Unable to open one or more detection setup files",
                          "stderr")
            return False
        f1.close()
        f2.close()

        self._net = cv2.dnn.readNet(weights_file, config_file)
        for line in f3:
            self._names.append(line.rstrip('\n'))
        f3.close()

        return True

    def detect(self, image_file, checked_names):
        # Finds requested objects in image file

        self._detection_time = None
        start = time.time()
        cap = cv2.VideoCapture(image_file)
        hasFrame, frame = cap.read()
        if not hasFrame:
            zm_util.debug("No image frame found")
            return False

        blob = cv2.dnn.blobFromImage(frame, 1./255.,
                                    (self._width, self._height), [0,0,0], 1,
                                    crop=False)
        self._net.setInput(blob) 
        outs = self._net.forward(self._getOutputNames())
        detected_names, confidence = self._postprocess(outs)
        self._determineMatches(detected_names, confidence, checked_names)
        self._detection_time = time.time() - start

        return True

    def matches(self):
        # Returns names and confidence levels of detected objects in the list
        # of checked_names

        return self._matches

    def detectionTime(self):

        return self._detection_time

    def _getOutputNames(self):
        # Get the names of all the layers in the network

        layersNames = self._net.getLayerNames()
        return [layersNames[i[0] - 1] for i in \
                self._net.getUnconnectedOutLayers()]

    def _postprocess(self, outs):
        # Get names and scores of detected objects with high enough confidence

        names = []
        confidences = []

        for out in outs:
            for detection in out:
                scores = detection[5:]
                classId = np.argmax(scores)
                confidence = scores[classId]
                if confidence > self._conf_threshold:
                    names.append(self._names[classId])
                    confidences.append(float(confidence))

        return names, confidences

    def _determineMatches(self, detected_names, confidence, checked_names):

        ndetected = len(detected_names)
        self._matches = []
        for name in checked_names:
            for i in range(ndetected):
                if detected_names[i] == name:
                    self._matches.append({name: confidence[i]})
                    break
