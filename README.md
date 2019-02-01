zoneminder-notifier
================================================================================
zoneminder-notifier is a lightweight daemon designed to send notifications by
email or text message as soon as events occur in ZoneMinder, optionally using
object detection in alarm frames to eliminate false alerts. It works by
continuously checking whether each active monitor has new events via the
ZoneMinder API. If so, it runs the maxscore frame from the alert through an 
object detection algorithm to check for user-specified classes of objects (e.g.,
person, car, dog). If one or more match is found, it sends a notification.
Object detection can be disabled as well, if you just want to receive
notifications as quickly as possible. By default, the polling frequency is 3
seconds. When ZoneMinder is not running, it checks every 15 seconds by default
to see if it has started.

Requirements
================================================================================
ZoneMinder with API enabled (tested with 1.32.3)
Python 2.7 (tested with 2.7.15; has not been tested with Python 3)
Python modules: requests, urllib3
Mutt (to send notifications)
OpenCV with deep neural network and Python bindings (if using object detection)
YOLO v3 (if using object detection)

Installation
================================================================================
An install script is provided. It is intended to be run as root or with sudo.It
will install Python modules in the system Python site-packages directory, a
config file in /etc, and the daemon zm_notifier in /usr/bin.

Usage
================================================================================
* Edit /etc/zm_notifier.cfg. Required inputs include the server address(es),
  ZoneMinder credentials, email address(es), and paths to YOLO v3 config and
  data files. Because ZoneMinder credentials are stored in plain text, it is
  recommended for this file to be readable only by root (which will be the case
  when using the install script). Please read all comments carefully when
  editing the file.
* If needed, configure Mutt.
* Run /usr/bin/zm_notifier and check for any errors. Edit the config file as
  needed if there are errors. When done testing, you may wish to instead run it
  in the background with outputs redirected to a log file, for example:

  /usr/bin/zm_notifier > /var/log/zm_notifier.log 2>&1 &
