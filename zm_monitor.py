import sys
import os
from cv2 import imread
from zm_util import debug

class Monitor:
    def __init__(self, monitor_name, monitor_id, zmapi, detector=None, detect_objects=True,
                 detect_in="image"):
        '''Initialize monitor with name, id, pointers to ZMAPI and detector instances, and detection
           settings'''
        self.name = monitor_name
        self.id = monitor_id
        self.api = zmapi
        self.detector = detector
        self.detect_objects = detect_objects
        self.detect_in = detect_in

        # Sanity checks
        if self.detect_objects:
            if detector is None:
                self.debug("Must pass a detector to detect objects.", "stderr")
                sys.exit(1)
            if not detect_in in ["image", "video"]:
                self.debug("detect_in must be 'image' or 'video'.", "stderr")
                sys.exit(1)

        # Get latest event
        self.latest_event = self.api.getMonitorLatestEvent(self.id)

        # Save active state
        self.checkActive()

    def debug(self, message, pipename='stdout'):
        debug("{:s}: {:s}".format(self.name, message), pipename)

    def checkActive(self):
        '''Checks if monitor is active'''
        self.active = self.api.getMonitorDaemonStatus(self.id)
        return self.active

    def eventImage(self, event, imgfile="snapshot.jpg"):
        '''Returns the path to the latest event image'''
        if event['id'] == -1:
            return None
        return os.path.join(event['path'], imgfile)

    def eventVideo(self, event):
        '''Returns the path to the latest event video'''
        if event['id'] == -1:
            return None
        return os.path.join(event['path'], event['video_name'])

    def getNewEvent(self):
        '''Gets a new event from the API. Returns True if there is a new event to process, False
           if not. An event is considered ready to be processed if:
           1. It is different from the one already in memory.
           2. The max score frame or alarm frame is available.'''

        ret = False

        # Look through monitor events list, starting with the latest
        idx = 0
        while not ret:
            event = self.api.getMonitorLatestEvent(self.id, idx)
            # There was an error getting the event
            if event['id'] == -1:
                break
            # The latest event is already in memory
            if event['id'] == self.latest_event['id']:
                break
            # The max score frame for this event exists
            if os.path.isfile(self.eventImage(event)):
                self.latest_event = event
                ret = True
            # The max score frame isn't there yet, but the alarm frame is
            elif os.path.isfile(self.eventImage(event, "alarm.jpg")):
                self.latest_event = event
                ret = True
            idx += 1

        return ret

    def detectObjects(self):
        '''Detects objects in latest event. Returns: 
           frame: the OpenCV frame object
           objclass: the class name of the object detected with highest confidence in the frame
           maxconfidence: the confidence of the object detected (0-1)'''
        frame = None
        objclass = ""
        maxconfidence = 0.0

        # Get the event image file. First try the maxscore frame (snapshot.jpg), but if that's
        # not available, try the alarm frame (alarm.jpg).
        has_img = True
        maxscore_img = self.eventImage(self.latest_event)
        alarm_img = self.eventImage(self.latest_event, "alarm.jpg")
        event_img = None
        if maxscore_img is not None and os.path.isfile(maxscore_img):
            event_img = maxscore_img
        elif alarm_img is not None and os.path.isfile(alarm_img):
            event_img = alarm_img
        else:
            has_img = False
        if not has_img:
            self.debug("Event image not present on disk.")
            return frame, objclass, maxconfidence

        # Open the max score frame. Since we've already checked that the file exists on disk,
        # this should return a valid frame object, but it will be None if there is a problem
        # reading it.
        frame = imread(event_img)

        # Return the max score frame if we're not doing object detection
        if not self.detect_objects:
            return frame, objclass, maxconfidence

        # Detect objects in video. We'll default to the max score image if there is a problem
        # reading the video.
        if self.detect_in == "video":
            video_file = self.eventVideo(self.latest_event)
            if not os.path.isfile(video_file):
                self.debug("Event video not present on disk. Detecting in max score frame instead.")
            else:
                bestframe, classes, confidences = self.detector.detectInVideo(video_file,
                                                  annotate_name=False, show=False,
                                                  annotate_fps=False, return_first_detection=True)
                if bestframe is None:
                    self.debug("No objects found. Trying max score image instead.")
                else:
                    maxconfidence = max(confidences)
                    objclass = classes[confidences.index(maxconfidence)]
                    return bestframe, objclass, maxconfidence

        # Detect objects in max score image
        bestframe, classes, confidences = self.detector.detectInImage(event_img,
                                          annotate_name=False, show=False)
        if bestframe is None:
            self.debug("Error opening max score image. No detection done.", "stderr")
        else:
            frame = bestframe
            if len(confidences) > 0:
                maxconfidence = max(confidences)
                objclass = classes[confidences.index(maxconfidence)]

        return frame, objclass, maxconfidence
