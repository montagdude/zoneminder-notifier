import os
import sys
import cv2
import numpy as np
import time
from matplotlib import cm
from copy import copy

cmap = cm.get_cmap('Spectral')

class DetectorBase:
    '''Base class for object detection with OpenCV'''

    def __init__(self, name, config_path, model_path, identify_classes=[],
                 confidence_threshold=0.4, nms_threshold=0.4):
        '''Constructor for DetectorBase class
        name: name to be applied to annotated images
        config_path: path of neural net configuration file
        model_path: path of neural net model file or weights
        identify_classes: list of classes to identify (empty means all classes)
        confidence_threshold: ignore detected objects with confidence less than this
        nms_threshold: non-maximum suppression threshold for removing overlapping boxes'''
        self.name = name
        self.classes = []
        self.identifyClasses = identify_classes
        self.identifyClassIDs = []
        self.conf_threshold = confidence_threshold
        self.nms_threshold = nms_threshold

        # Annotation settings
        self.name_fc = (255,255,255)
        self.name_fs = 0.5
        self.fps_fc = (255,255,255)
        self.fps_fs = 0.5

        # Things that will be populated later
        self.classes = []
        self.identifyClassIDs = []
        self.classesColor = None

        # Initialize object detection network
        self.initializeNetwork(config_path, model_path)

    def readClasses(self, classes_path):
        '''Reads class list and assigns colors'''
        with open(classes_path, 'r') as f:
            self.classes = f.read().splitlines()

        if len(self.identifyClasses) == 0:
            self.identifyClasses = self.classes

        # Get list of IDs to identify
        for class_name in self.identifyClasses:
            try:
                classID = self.classes.index(class_name)
            except ValueError:
                sys.stderr.write("{:s} is not an available class. Skipping.\n".format(class_name))
                continue
            self.identifyClassIDs.append(classID)

        # Assign a unique color to each class
        nclasses = len(self.identifyClassIDs)
        colorvals = np.linspace(0,1,nclasses)
        self.classesColor = np.zeros((nclasses,3))
        for i in range(nclasses):
            rgba = cmap(colorvals[i])
            for j in range(3):
                self.classesColor[i,j] = rgba[j]*255

    def initializeNetwork(self, config_path, model_path):
        raise NotImplementedError

    def detectObjects(self, frame):
        '''Derived classes must detect objects in a frame and return the following:
           classes:     detected class IDs from classes list
           confidences: confidence for each detection
           boxes:       bounding boxes for each detection as list of OpenCV rects
           These must be filtered by confidence threshold and requested classes to identify.'''
        raise NotImplementedError

    def removeOverlapping(self, classes, confidences, boxes):
        '''Removes overlapping boxes with lower confidence using nms threshold. Returns
           new lists of classes, confidences, and boxes.'''
        # Get indices to keep
        indices = cv2.dnn.NMSBoxes(boxes, confidences, self.conf_threshold, self.nms_threshold)

        # Construct remaning boxes
        newclasses = []
        newconfidences = []
        newboxes = []
        idx = 0
        for classID, confidence, box in zip(classes, confidences, boxes):
            if idx in indices:
                newclasses.append(classID)
                newconfidences.append(confidence)
                newboxes.append(box)
            idx += 1
        return newclasses, newconfidences, newboxes

    def detectInFrame(self, frame, annotate_name=True):
        '''Performs object detection on a frame and returns detection data along with
           an annotated frame'''

        # We need to have at least one class to detect
        if len(self.identifyClassIDs) == 0:
            sys.stderr.write("No classes to identify. Call readClasses first.\n")
            return [], [], []

        # Do object detection and remove overlapping boxes
        classes, confidences, boxes = self.detectObjects(frame)
        classes, confidences, boxes = self.removeOverlapping(classes, confidences, boxes)

        # Draw boxes with class label and confidence
        annotated_frame = copy(frame)
        for classID, confidence, box in zip(classes, confidences, boxes):
            left = box[0]
            top = box[1]
            classLabel = self.classes[classID]
            color = self.classesColor[self.identifyClassIDs.index(classID)]
            cv2.rectangle(annotated_frame, box, color, thickness=2)
            displayText = "{}:{:.2f}".format(classLabel, confidence)
            cv2.putText(annotated_frame, displayText, (left, top-10), cv2.FONT_HERSHEY_PLAIN,
                        1, color, 2)

        # Label the frame with the class name
        if annotate_name:
            cv2.putText(annotated_frame, self.name, (20,20), cv2.FONT_HERSHEY_SIMPLEX, self.name_fs,
                        self.name_fc, 1)

        return classes, confidences, boxes, annotated_frame

    def detectInImage(self, image_file, annotate_name=True, show=True):
        '''Performs object detection on an image file, returns the frame, classes, and confidences,
           and optionally displays the result'''
        file_err_msg = "Error opening image file {:s}.\n".format(image_file)
        if os.path.isfile(image_file):
            frame = cv2.imread(image_file)
        else:
            sys.stderr.write(file_err_msg)
            return
        if frame is None:
            sys.stderr.write(file_err_msg)
            return

        # Detect objects in the frame and annotate
        classes, confidences, _, frame = self.detectInFrame(frame, annotate_name)

        if show:
            # Display image
            cv2.imshow("Result", frame)

            # Clean up
            cv2.waitKey(0)
            cv2.destroyAllWindows()
        return frame, classes, confidences

    def detectInVideo(self, video_file, annotate_name=True, show=True, annotate_fps=True,
                      return_first_detection=False):
        '''Performs object detection on a video and returns the frame with the highest
           singular detection confidence, along with the list of classes and confidences for
           that frame. Optionally displays the video as detection occurs. If return_first_detection,
           will return as soon as any successful detections occur.'''
        cap = cv2.VideoCapture(video_file)
        if not cap.isOpened():
            self.stderr.write("Error opening video file {:s}.\n".format(video_file))

        success, frame = cap.read()
        width = cap.get(cv2.CAP_PROP_FRAME_WIDTH)
        height = cap.get(cv2.CAP_PROP_FRAME_HEIGHT)

        bestframe = None
        bestscore = 0.
        bestclasses = None
        bestconfidences = None
        lastTime = 0
        while success:
            currentTime = time.time()
            fps = 1./(currentTime - lastTime)
            fps_label = "FPS: {:.1f}".format(fps)
            lastTime = currentTime

            # Detect objects in the frame and annotate
            classes, confidences, _, frame = self.detectInFrame(frame, annotate_name)

            # Update best score
            for confidence in confidences:
                if confidence > bestscore:
                    bestscore = confidence
                    bestframe = frame
                    bestclasses = classes
                    bestconfidences = confidences

            # Add frames per second annotation
            if annotate_fps:
                cv2.putText(frame, fps_label, (int(width)-100,20), cv2.FONT_HERSHEY_SIMPLEX,
                            self.fps_fs, self.fps_fc, 1)

            # Get out of loop now if returning first detection
            if return_first_detection and bestscore > self.conf_threshold:
                break

            # Display image
            if show:
                cv2.imshow("Result", frame)

                # Catch quit key
                if cv2.waitKey(1) & 0xFF == ord('q'):
                    break

            success, frame = cap.read()

        # Clean up
        cap.release()
        if show:
            cv2.destroyAllWindows()

        return bestframe, bestclasses, bestconfidences


class DetectorDarknet(DetectorBase):
    '''OpenCV detection using Darknet models, e.g. Yolo.
       https://opencv-tutorial.readthedocs.io/en/latest/yolo/yolo.html'''

    def __init__(self, name, config_path, model_path, identify_classes=[],
                 confidence_threshold=0.4, nms_threshold=0.4, analysis_size=(416,416)):
        # Initialize parent class
        DetectorBase.__init__(self, name, config_path, model_path, identify_classes,
                              confidence_threshold, nms_threshold)

        # Options for analysis_size are: (320,320), (416,416), (608,608)
        if analysis_size not in [(320,320), (416,416), (608,608)]:
            sys.stderr.write("Unsupported analysis size. Using (416,416).\n")
            analysis_size = (416,416)
        self.analysis_size = analysis_size

    def initializeNetwork(self, config_path, model_path):
        self.net = cv2.dnn.readNetFromDarknet(config_path, model_path)
        ln = self.net.getLayerNames()
        self.ln = [ln[i-1] for i in self.net.getUnconnectedOutLayers()]

    def detectObjects(self, frame):
        blob = cv2.dnn.blobFromImage(frame, 1/255., size=self.analysis_size, swapRB=True,
                                     crop=False)
        self.net.setInput(blob)
        cvOut = self.net.forward(self.ln)
        # Combine the 3 output groups into 1 (10647, 85)
        # large objects (507,85)
        # medium objects (2028, 85)
        # small objects (8112, 85)
        cvOut = np.vstack(cvOut)

        # Rearrange outputs into lists and filter
        height, width = frame.shape[:2]
        classes = []
        confidences = []
        boxes = []
        for output in cvOut:
            scores = output[5:]
            classID = np.argmax(scores)
            confidence = scores[classID]
            if confidence >= self.conf_threshold and classID in self.identifyClassIDs:
                x, y, w, h = output[:4]*np.array([width, height, width, height])
                p0 = int(x - w//2), int(y - h//2)
                p1 = int(x + w//2), int(y + h//2)
                boxes.append([*p0, int(w), int(h)])
                confidences.append(float(confidence))
                classes.append(classID)
        return classes, confidences, boxes


class DetectorSSDMobileNetV3(DetectorBase):
    '''OpenCV detection using the SSD MobileNet V3 model'''

    def initializeNetwork(self, config_path, model_path):
        self.net = cv2.dnn_DetectionModel(model_path, config_path)
        self.net.setInputSize(320,320)
        self.net.setInputScale(1./127.5)
        self.net.setInputMean((127.5, 127.5, 127.5))
        self.net.setInputSwapRB(True)

    def detectObjects(self, frame):
        # Detect objects
        allclasses, allconfidences, allboxes = self.net.detect(frame, self.conf_threshold)

        # Filter by confidence and classID
        classes = []
        confidences = []
        boxes = []
        for classID1, confidence, box in zip(allclasses, allconfidences, allboxes):
            classID = classID1-1    # This model uses 1-referenced classIDs
            if confidence >= self.conf_threshold and classID in self.identifyClassIDs:
                classes.append(classID)
                confidences.append(confidence)
                boxes.append(box)
        return classes, confidences, boxes


class DetectorTensorFlow(DetectorBase):
    '''OpenCV detection using various TensorFlow models.
    https://github.com/opencv/opencv/wiki/TensorFlow-Object-Detection-API'''

    def __init__(self, name, config_path, model_path, identify_classes=[],
                 confidence_threshold=0.4, nms_threshold=0.4, analysis_size=(300,300)):
        # Initialize parent class
        DetectorBase.__init__(self, name, config_path, model_path, identify_classes,
                              confidence_threshold, nms_threshold)

        # Set analysis size
        self.analysis_size = analysis_size

    def initializeNetwork(self, config_path, model_path):
        self.net = cv2.dnn.readNetFromTensorflow(model_path, config_path)

    def detectObjects(self, frame):
        # Detect objects
        blob = cv2.dnn.blobFromImage(frame, size=self.analysis_size, swapRB=True, crop=False)
        self.net.setInput(blob)
        cvOut = self.net.forward()

        # Rearrange outputs into lists and filter
        height, width = frame.shape[:2]
        classes = []
        confidences = []
        boxes = []
        for detection in cvOut[0,0,:,:]:
            confidence = float(detection[2])
            classID = int(detection[1])-1   # This model uses 1-referenced classIDs
            if confidence >= self.conf_threshold and classID in self.identifyClassIDs:
                classes.append(classID)
                confidences.append(confidence)
                left = int(detection[3]*width)
                top = int(detection[4]*height)
                right = int(detection[5]*width)
                bottom = int(detection[6]*height)
                boxes.append([left, top, right-left, bottom-top])
        return classes, confidences, boxes

class DetectorHOG(DetectorBase):
    '''OpenCV detection using Histograms of Oriented Gradients. Note that this class is not
       neural-network based and is only configured to detect people.
       https://thedatafrog.com/en/articles/human-detection-video/'''

    def __init__(self, name, analysis_size=(640,480), win_stride=(8,8), scale=1.05):
        # Initialize parent class
        DetectorBase.__init__(self, name, "", "", ["person"], 0.0, 0.0)

        # Set other parameters
        self.analysis_size = analysis_size
        self.win_stride = win_stride
        self.scale = scale

    def readClasses(self, classes_path):
        '''HOG only identifies person class'''
        self.classes = ['person']
        self.identifyClassIDs = [0]
        self.classesColor = np.zeros((1,3))
        rgba = cmap(0.0)
        for j in range(3):
            self.classesColor[0,j] = rgba[j]*255

    def initializeNetwork(self, config_path, model_path):
        self.hog = cv2.HOGDescriptor()
        self.hog.setSVMDetector(cv2.HOGDescriptor_getDefaultPeopleDetector())

    def detectObjects(self, frame):
        # Resize and convert to grayscale
        analysis_frame = cv2.resize(frame, self.analysis_size)
        analysis_frame = cv2.cvtColor(analysis_frame, cv2.COLOR_RGB2GRAY)

        # Detect people and return bounding boxes
        boxes, weights = self.hog.detectMultiScale(analysis_frame, winStride=self.win_stride,
                                                   scale=self.scale)

        # Scale boxes back to full image size
        h, w = frame.shape[:2]
        ha, wa = analysis_frame.shape[:2]
        for box in boxes:
            box[0] = int(box[0]*w/wa)
            box[1] = int(box[1]*h/ha)
            box[2] = int(box[2]*w/wa)
            box[3] = int(box[3]*h/ha)

        # Add classIDs and confidences (confidence is made up since HOG doesn't have it)
        ndetections = len(boxes)
        classes = [0]*ndetections
        confidences = [1.0]*ndetections

        return classes, confidences, boxes
