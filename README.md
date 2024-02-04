zoneminder-notifier
================================================================================
zoneminder-notifier is a daemon designed to send notifications quickly after
they occur by email (including SMS or MMS gateways) or Pushover. It also can do
object detection based on pre-trained open source neural network models to
minimize false alerts. It works by polling active monitors for new events via
the ZoneMinder API. Object detection uses OpenCV. Email notifications are sent
with the Mutt email client, while Pushover notifications can also be sent by
email to your account's email gateway address or via the Pushover API. If
object detection is enabled, the image attachment will include boxes and
confidence levels around detected objects.

Requirements
================================================================================
* ZoneMinder with API version 2.0 enabled (tested with ZoneMinder 1.36.32)
* Python 3 (tested with version 3.10.6)
* Python modules: setuptools, requests, cv2, numpy, matplotlib, mysql (mysql-connector-python)
* Mutt (if you wish to send notifications via email)
* Pushover account and api token (if you wish to send notifications via Pushover
  API)

Installation
================================================================================
An install script is provided. It is intended to be run as root or with sudo. It
will install Python modules in a system Python site-packges directory, the
config file in /etc, executables in /usr/bin, and object detection model data in
/usr/share/zm-notifier. Most of this data is not tracked in the git repository
due to size but is provided in the release tarballs.

The install script also automatically installs, enables, and starts the systemd
zm_notifier service. If your distro does not use systemd, you should comment out
those lines in the install script and consult your distro's documentation for
how to run the daemon automatically at startup.

Usage
================================================================================
* Edit /etc/zm_notifier.cfg. Inputs are explained in the comments of this file.
  Please read them all carefully and fill out accordingly. Note that you need a
  section with the name of each of your ZoneMinder monitors if you want
  zoneminder-notifier to do object detection.
* Please be aware that ZoneMinder credentials are stored in plain text in the
  configuration file, so you should be careful with it. Using the provided
  install script, this file will be readable only by root.
* If needed, configure Mutt and make sure that you can send emails to the
  intended addresses, using the user account that will also run
  zoneminder-notifier (root / sudo -i if you use the provided systemd service).
* After installing, check the logs for any errors and edit the config file if
  needed. Using the provided systemd service, log messages will be written to
  /var/log/zm_notifier.log.
* If your distro does not have systemd, you can redirect the standard output
  and standard error to the log file in this way:

  /usr/bin/zm_notifier > /var/log/zm_notifier.log 2>&1 &

* It is also possible to run zm_notifier from the command line and view the
  output directly. If you want to do this for testing, just stop the system
  service first.

Object Detection Models
================================================================================
zoneminder-notifier comes with support built-in for four different object
detection models: Darknet (Yolo V4), SSD Mobilenet V3 (2020_01_14 version), SSD
Inception V2 (2017_11_17 version), and Histograms of Oriented Gradients (people
only detection model included with OpenCV). The data for these models are
included in the releases of zoneminder-notifier. The README in the model_data
directory includes the urls from where they were downloaded.

All except Histograms of Oriented Gradients (HOG) are trained on the COCO
datasets and are suitable for detecting a wide variety of object classes (HOG
detects people only). For each monitor, the classes you want it to actually
pay attention to should be specified in a comma-separated list. It is possible
to do object detection on either the max score frame from each new ZoneMinder
event or the entire video. The former is much faster and generally recommended.
Darknet is the most reliable model but also the slowest, but it offers an
excellent combination of speed and accuracy when detecting in the max score
frame only.

If you want to do object detection on entire event videos, you need to first
configure ZoneMinder to save videos under monitor settings. Please test
carefully to make sure your system is not getting overloaded analyzing entire
videos when many events are happening. To save computations, zoneminder-notifier
will stop analyzing a video as soon as it has made a successful detection, but
this doesn't help for events where none of the requested object classes are
found.

The images below represent the result of Darknet object detection with the
classes "person, chair, sofa, bicycle" from some of my ZoneMinder events.

![alt tag](https://raw.githubusercontent.com/montagdude/zoneminder-notifier/master/sample_images/analysis_image-1.jpg)
![alt tag](https://raw.githubusercontent.com/montagdude/zoneminder-notifier/master/sample_images/analysis_image-2.jpg)
![alt tag](https://raw.githubusercontent.com/montagdude/zoneminder-notifier/master/sample_images/analysis_image-5.jpg)
![alt tag](https://raw.githubusercontent.com/montagdude/zoneminder-notifier/master/sample_images/analysis_image-7.jpg)
