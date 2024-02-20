import sys
import os
from datetime import datetime
from cv2 import imread
from zm_util import debug,get_highest_scored_image,get_new_pictures_list


class Monitor:
    def __init__(self, monitor_name, monitor_id, zmapi, detector, ms):
        '''Initialize monitor with name, id, pointers to ZMAPI and detector instances, and detection
           settings'''
        self.name = monitor_name
        self.id = monitor_id
        self.api = zmapi
        self.detector = detector
        self.detect_objects = ms["detect_objects"]
        self.detect_in = ms["detect_in"]
        self.score_treshold = ms["score_treshold"]
        self.positive_detections_per_event_in_batch_limit = ms["positive_detections_per_event_in_batch_limit"]

        self.ID_POSITION = 0
        self.FRAME_ID_POSITION = 1
        self.FRAME_SCORE = 2
        self.EVENT_ID_POSITION = 3
        self.START_DATE_POSITION = 4
        self.VIDEO_FILENAME_POSITION = 5
        self.STORAGE_PATH_POSITION = 6
        self.STATS_TO_PRINT = 7

        # Sanity checks
        if self.detect_objects:
            if self.detector is None:
                self.debug("Must pass a detector to detect objects.", "stderr")
                sys.exit(1)
            if not self.detect_in in ["image", "video"]:
                self.debug("detect_in must be 'image' or 'video'.", "stderr")
                sys.exit(1)
            if not self.score_treshold in range(0,256):
                self.debug("score_treshold must be in range 0..255.", "stderr")
                sys.exit(1)

        # Get latest event
        self.latest_event = self.api.getMonitorLatestEvent(self.id)

        # to remember last processed point
        self.latest_EventPictureID = -1
        self.EventPicturesList = []

        # Save active state
        self.checkActive()

        self.current_frame_for_analyse = None


    def debug(self, message, pipename='stdout'):
        debug("{:s}: {:s}".format(self.name, message), pipename)

    def checkActive(self):
        '''Checks if monitor is active'''
        self.active = self.api.getMonitorDaemonStatus(self.id)
        return self.active

    def get_event_image_filename(self, event):
        '''Returns the path to the best event image'''
        if event['id'] == -1:
            return None
        PictureID = get_highest_scored_image(event)
        if PictureID > -1:
            imgfile = os.path.join(event['path'], f"{PictureID:05d}-capture.jpg")
            if os.path.isfile(imgfile):
                return imgfile

        # The max score frame isn't there yet, but the snapshot frame is
        imgfile = os.path.join(event['path'],"snapshot.jpg")
        if os.path.isfile(imgfile):
            return imgfile

        # The max score frame isn't there yet, but the alarm frame is
        imgfile = os.path.join(event['path'],"alarm.jpg")
        if os.path.isfile(imgfile):
            return imgfile

        return None

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
            self.current_frame_for_analyse = self.get_event_image_filename(event)
            if self.current_frame_for_analyse != None:
                self.latest_event = event
                ret = True
            idx += 1

        return ret

    def getNewEventPicturesList(self):
        '''Gets a new event from the MySQL.
           An event is considered ready to be processed if:
           1. It is different from the one already in memory.
           2. The max score frame or alarm frame is available.'''

        self.EventPicturesList = get_new_pictures_list(self.score_treshold, self.id, self.latest_EventPictureID,self.detect_in)
        #if len(self.EventPicturesList) > 0:
        #    self.latest_EventPictureID = self.EventPicturesList[-1][self.ID_POSITION] # last frame.ID

    def get_filename_from_one_frame(self,one_frame):
        return (f"{one_frame[self.STORAGE_PATH_POSITION]}/{self.id}/"
                f"{one_frame[self.START_DATE_POSITION].strftime('%Y-%m-%d')}/{one_frame[self.EVENT_ID_POSITION]}/"
                f"{one_frame[self.FRAME_ID_POSITION]:05d}-capture.jpg")
    def get_video_filename_from_one_frame(self,one_frame):
        return (f"{one_frame[self.STORAGE_PATH_POSITION]}/{self.id}/"
                f"{one_frame[self.START_DATE_POSITION].strftime('%Y-%m-%d')}/"
                f"{one_frame[self.EVENT_ID_POSITION]}/{one_frame[self.VIDEO_FILENAME_POSITION]}")


    def detectObjects(self, _frame):
        '''Detects objects in _frame. Returns:
           frame: the OpenCV frame object
           objclass: the class name of the object detected with highest confidence in the frame
           maxconfidence: the confidence of the object detected (0-1)'''
        frame = None
        objclass = ""
        maxconfidence = 0.0
        # just prepare for future usage if video was analysed or we have to again in next batch
        processed_flag = True if self.detect_in == "image" else False

        # construct correct filename and check if it exists
        self.current_frame_for_analyse = self.get_filename_from_one_frame(_frame)

        if not os.path.isfile(self.current_frame_for_analyse):
            self.debug(f"Cannot open frame file . ({_frame[self.STATS_TO_PRINT]} : {self.current_frame_for_analyse})")
            return frame, objclass, maxconfidence,processed_flag

        # Detect objects in video. We'll default to the max score image if there is a problem
        # reading the video.
        if self.detect_in == "video":

            # construct correct filename and check if it exists
            video_file = self.get_video_filename_from_one_frame(_frame)
            self.debug(f"Video analyse started. ({_frame[self.EVENT_ID_POSITION]} : {video_file})")

            if not os.path.isfile(video_file):
                self.debug("Event video not present on disk. Detecting in most fresh frame instead.")
            else:
                bestframe, classes, confidences,processed_flag = self.detector.detectInVideo(video_file,
                                                  annotate_name=False, show=False,
                                                  annotate_fps=False, return_first_detection=True)
                if bestframe is None:
                    if processed_flag is True :
                        self.debug("No object detected in video -> trying most fresh frame image instead.")
                    else:
                        self.debug("Cannot analyze video -> trying most fresh frame image instead.")
                else:
                    maxconfidence = max(confidences)
                    objclass = classes[confidences.index(maxconfidence)]
                    return bestframe, objclass, maxconfidence, processed_flag

        # Detect objects in max score image
        # Open the max score frame.
        # this should return a valid frame object, but it will be None if there is a problem
        # reading it.
        self.debug(f"Frame analyse started. ({_frame[self.STATS_TO_PRINT]} : {self.current_frame_for_analyse})")
        frame = imread(self.current_frame_for_analyse)
        bestframe, classes, confidences = self.detector.detectInImage(self.current_frame_for_analyse,
                                                                      annotate_name=False, show=False)
        if bestframe is None:
            self.debug("Error opening frame. No detection done.", "stderr")
        else:
            frame = bestframe
            if len(confidences) > 0:
                maxconfidence = max(confidences)
                objclass = classes[confidences.index(maxconfidence)]

        return frame, objclass, maxconfidence,processed_flag
