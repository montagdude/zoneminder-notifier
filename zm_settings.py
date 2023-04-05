#!/usr/bin/env python3

import configparser
import os
import sys
import zm_util

class Settings:
    def __init__(self, config_file="/etc/zm_notifier.cfg"):
        '''Read and store static sections (all sections except monitors) from config file. Monitors
           settings are read in the readMonitorsSettings method.'''
        self.config_file = config_file
        config = configparser.ConfigParser()
        try:
            f = open(self.config_file)
        except IOError:
            zm_util.debug("Error opening {:s}".format(self.config_file), "stderr")
            sys.exit(1)
        f.close()
        if len(config.read(self.config_file)) == 0:
            zm_util.debug("Error parsing {:s}".format(self.config_file), "stderr")
            sys.exit(1)

        # Check for required sections in config file
        for section in ["ZoneMinderAPI", "Notification", "Daemon"]:
            if not config.has_section(section):
                zm_util.debug("No section {:s} found in {:s}".format(section, self.config_file),
                              "stderr")
                sys.exit(1)

        # ZoneMinderAPI settings
        section = "ZoneMinderAPI"
        self.local_server_address = zm_util.get_from_config(config, section, "local_server_address")
        self.world_server_address = zm_util.get_from_config(config, section, "world_server_address")
        self.username = zm_util.get_from_config(config, section, "username")
        self.password = zm_util.get_from_config(config, section, "password")
        self.verify_ssl = zm_util.get_bool_from_config(config, section, "verify_ssl",
                                                       required=False, default=True)

        # Notification settings
        section = "Notification"
        self.tmp_message_file = zm_util.get_from_config(config, section, "tmp_message_file",
                                                  required=False, default="/tmp/zm_event_email.txt")
        self.tmp_analysis_image = zm_util.get_from_config(config, section, "tmp_analysis_image",
                                               required=False, default="/tmp/zm_analysis_image.jpg")
        w = zm_util.get_int_from_config(config, section, "analysis_image_width")
        h = zm_util.get_int_from_config(config, section, "analysis_image_height")
        self.analysis_image_size = (w,h)
        addresses = zm_util.get_from_config(config, section, "addresses", required=False,
                                            default="")
        self.notify_no_object = zm_util.get_bool_from_config(config, section, "notify_no_object",
                                                             required=False, default=False)
        self.no_notification_runstate = zm_util.get_from_comfig(config, section,
                                             "no_notification_runstate", required=False, default="")

        # Convert email addresses and attachment settings to lists
        if addresses != "":
            addresses = addresses.replace(" ","").split(",")
            attach_image = zm_util.get_from_config(config, section, "attach_image") \
                           .replace(" ","").split(",")
            if len(addresses) != len(attach_image):
                zm_util.debug("Must specify attach_image for each address", "stderr")
                sys.exit(1)
        else:
            addresses = []

        # Get email settings in a more convenient form
        self.to_addresses = []
        valid_yes = ['yes', '1', 'on', 'true']
        valid_no = ['no', '0', 'off', 'false']
        for i, address in enumerate(addresses):
            to_address = {"address": address, "image": False}
            if attach_image[i].lower() in valid_yes:
                to_address["image"] = True
            elif attach_image[i].lower() in valid_no:
                to_address["image"] = False
            else:
                zm_util.debug("attach_image must be Yes/No", "stderr")
                sys.exit(1)
            self.to_addresses.append(to_address)

        # Pushover API notification settings
        self.pushover_data = None
        use_pushover_api = zm_util.get_bool_from_config(config, section, "use_pushover_api",
                                                        required=False, default=False)
        if use_pushover_api:
            pushover_api_token = zm_util.get_from_config(config, section, "pushover_api_token")
            pushover_user_key = zm_util.get_from_config(config, section, "pushover_user_key")
            pushover_attach_image = zm_util.get_bool_from_config(config, section,
                                              "pushover_attach_image", required=False, default=True)
            self.pushover_data = {"api_token": pushover_api_token, "user_key": pushover_user_key,
                                  "attach_image": pushover_attach_image}

        # Daemon settings
        section = "Daemon"
        self.running_timeout = zm_util.get_int_from_config(config, section, "running_timeout",
                                                           required=False, default=5)
        self.stopped_timeout = zm_util.get_int_from_config(config, section, "stopped_timeout",
                                                           required=False, default=30)

        # Detector settings
        section = "Darknet"
        self.darknet_model = os.path.join("/usr", "share", "zm-notifier", "yolov4",
                                          "yolov4.weights")
        self.darknet_config = os.path.join("/usr", "share", "zm-notifier", "yolov4", "yolov4.cfg")
        self.darknet_classes = os.path.join("/usr", "share", "zm-notifier", "coco.names.80")
        darknet_width = 416
        darknet_height = 416
        if config.has_section(section):
            self.darknet_model = zm_util.get_from_config(config, section, "model_path",
                                                         required=False, default=self.darknet_model)
            self.darknet_config = zm_util.get_from_config(config, section, "config_path",
                                                        required=False, default=self.darknet_config)
            self.darknet_classes = zm_util.get_from_config(config, section, "classes_path",
                                                       required=False, default=self.darknet_classes)
            darknet_width = zm_util.get_int_from_config(config, section, "analysis_width",
                                                        required=False, default=darknet_width)
            darknet_height = zm_util.get_int_from_config(config, section, "analysis_height",
                                                        required=False, default=darknet_height)
        self.darknet_analysis_size = (darknet_width,darknet_height)

        section = "MobileNetV3"
        datadir = "ssd_mobilenet_v3_large_coco_2020_01_14"
        self.mobilenet_model = os.path.join("/usr", "share", "zm-notifier", datadir,
                                            "frozen_inference_graph.pb")
        self.mobilenet_config = os.path.join("/usr", "share", "zm-notifier", datadir,
                                             datadir+".pbtxt")
        self.mobilenet_classes = os.path.join("/usr", "share", "zm-notifier", "coco.names.91")
        if config.has_section(section):
            self.mobilenet_model = zm_util.get_from_config(config, section, "model_path",
                                                       required=False, default=self.mobilenet_model)
            self.mobilenet_config = zm_util.get_from_config(config, section, "config_path",
                                                      required=False, default=self.mobilenet_config)
            self.mobilenet_classes = zm_util.get_from_config(config, section, "classes_path",
                                                     required=False, default=self.mobilenet_classes)

        section = "InceptionV2"
        datadir = "ssd_inception_v2_coco_2017_11_17"
        self.inception_model = os.path.join("/usr", "share", "zm-notifier", datadir,
                                            "frozen_inference_graph.pb")
        self.inception_config = os.path.join("/usr", "share", "zm-notifier", datadir,
                                             datadir+".pbtxt")
        self.inception_classes = os.path.join("/usr", "share", "zm-notifier", "coco.names.91")
        inception_width = 416
        inception_height = 416
        if config.has_section(section):
            self.inception_model = zm_util.get_from_config(config, section, "model_path",
                                                       required=False, default=self.inception_model)
            self.inception_config = zm_util.get_from_config(config, section, "config_path",
                                                      required=False, default=self.inception_config)
            self.inception_classes = zm_util.get_from_config(config, section, "classes_path",
                                                     required=False, default=self.inception_classes)
            inception_width = zm_util.get_int_from_config(config, section, "analysis_width",
                                                          required=False, default=inception_width)
            inception_height = zm_util.get_int_from_config(config, section, "analysis_height",
                                                           required=False, default=inception_height)
        self.inception_analysis_size = (inception_width,inception_height)

        section = "HOG"
        hog_width = 640
        hog_height = 480
        hog_stridex = 8
        hog_stridey = 8
        self.hog_scale = 1.05
        if config.has_section(section):
            hog_width = zm_util.get_int_from_config(config, section, "analysis_width",
                                                                  required=False, default=hog_width)
            hog_height = zm_util.get_int_from_config(config, section, "analysis_height",
                                                                 required=False, default=hog_height)
            hog_stridex = zm_util.get_int_from_config(config, section, "win_stride_x",
                                                                required=False, default=hog_stridex)
            hog_stridey = zm_util.get_int_from_config(config, section, "win_stride_y",
                                                                required=False, default=hog_stridey)
            self.hog_scale = zm_util.get_float_from_config(config, section, "scale", required=False,
                                                           default=self.hog_scale)
        self.hog_analysis_size = (hog_width,hog_height)
        self.hog_winstride = (hog_stridex,hog_stridey)

    def readMonitorSettings(self, api_monitors):
        '''Reads monitor settings given a list of monitors from the API'''

        # Read config file again
        config = configparser.ConfigParser()
        config.read(self.config_file)

        # Get monitor settings dict
        self.monitors = {}
        for api_mon in api_monitors:
            # Read monitor config section
            mname = api_mon["name"]
            self.monitors[mname] = {}
            detect_objects = False
            detection_model = ""
            detect_classes = []
            confidence_threshold = 0.4
            detect_in = ""
            self.monitors[mname]["check_events"] = True
            if not config.has_section(mname):
                zm_util.debug("No config section for {:s}, not doing object detection." \
                              .format(mname))
            else:
                self.monitors[mname]["check_events"] = zm_util.get_bool_from_config(config, mname,
                                                       "check_events", required=False, default=True)
                detect_objects = zm_util.get_bool_from_config(config, mname, "detect_objects",
                                                              required=False, default=False)
                detection_model = zm_util.get_from_config(config, mname, "detection_model",
                                                          required=False, default="Darknet")
                detect_classes = zm_util.get_from_config(config, mname, "detect_classes",
                                                         required=False, default="person")
                detect_classes = detect_classes.replace(" ", "").split(",")
                confidence_threshold = zm_util.get_float_from_config(config, mname,
                                                "confidence_threshold", required=False, default=0.4)
                detect_in = zm_util.get_from_config(config, mname, "detect_in", required=False,
                                                    default="image")
            self.monitors[mname]["detect_objects"] = detect_objects
            self.monitors[mname]["detection_model"] = detection_model
            self.monitors[mname]["detect_classes"] = detect_classes
            self.monitors[mname]["confidence_threshold"] = confidence_threshold
            self.monitors[mname]["detect_in"] = detect_in
