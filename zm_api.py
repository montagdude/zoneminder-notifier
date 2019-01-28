#!/usr/bin/env python
#
# Thanks to the zm-py project for showing me how to do the API requests in
# Python. Some ideas for the ZMAPI class are taken from there too.

import sys
import requests
from datetime import datetime
import urllib3
urllib3.disable_warnings()  # Disable warnings about unverified SSL. The server
                            # uses my own self-signed certificate.

class ZMAPI:

    def __init__(self, server, username, password, verify_ssl=True,
                 debug_level=1):
        self._server = server.rstrip('/')
        self._username = username
        self._password = password
        self._verify_ssl = verify_ssl
        self._cookies = None
        self._debug_level = debug_level

    def debug(self, level, message, pipe="stdout"):

        if level >= self._debug_level:
            if pipe == "stderr":
                sys.stderr.write("{:s}\n".format(message))
            else:
                print(message)

    def login(self):
        # Logs in and returns True if successful, False otherwise

        login_post = {'user': self._username, 'pass': self._password}
        login_url = self._server + "/zm/api/host/login.json"
        response = requests.post(url=login_url, data=login_post,
                                 verify=self._verify_ssl)
        self._cookies = response.cookies

        # Check if login was successful (note request above returns request.ok
        # even if the wrong username and password were supplied)

        version_url = self._server + '/zm/api/host/getVersion.json'
        response = requests.get(url=version_url, cookies=self._cookies,
                                verify=self._verify_ssl)
        if not response.ok:
            self.debug(1, "Error logging into ZoneMinder", "stderr")
            return False
        else:
            return True

    def logout(self):
        # Logs out and returns True if successful, False otherwise

        logout_url = self._server + "/zm/api/host/logout.json"
        response = requests.get(url=logout_url, verify=self._verify_ssl)
        if response.ok:
            return True
        else:
            self.debug(1, "Connection error in logout", "stderr")
            return False

    def getDaemonStatus(self):
        # Returns True if ZoneMinder is running, False if not or on error

        daemon_url = self._server + "/zm/api/host/daemonCheck.json"
        response = requests.get(url=daemon_url, cookies = self._cookies,
                                verify=self._verify_ssl)

        if response.ok:
            status = int(response.json()['result'])
            if status == 1:
                return True
        else:
            self.debug(1, "Connection error in getDaemonStatus", "stderr")

        return False

    def getMonitors(self, active_only=False):
        # Gets list of monitors and distills it to just the monitor's ID and
        # name. If you only want active monitors, use active_only=True.
        # Monitor list will be empty if connection error occurs.

        monitors_url = self._server + "/zm/api/monitors.json"
        response = requests.get(url=monitors_url, cookies=self._cookies,
                                verify=self._verify_ssl)

        monitors = []
        if response.ok:
            data = response.json()
            for item in data['monitors']:
                monitor = {}
                monitor['id'] = int(item['Monitor_Status']['MonitorId'])
                monitor['name'] = item['Monitor']['Name'].encode('ascii')
                if active_only:
                    if self.getMonitorDaemonStatus(monitor['id']):
                        monitors.append(monitor)
                        self.debug(1, "Appended monitor {:d}"\
                                   .format(monitor['id']))
                else:
                    self.debug(1, "Appended monitor {:d}".format(monitor['id']))
                    monitors.append(monitor)
        else:
            self.debug(1, "Connection error in getMonitors", "stderr")
        return monitors

    def getMonitorDaemonStatus(self, monitorID):
        # Returns True if daemon is running for monitor, False if not or if
        # there is a connection error

        monitor_url = self._server \
                    + "/zm/api/monitors/daemonStatus/id:{:d}/daemon:zmc.json" \
                      .format(monitorID)
        response = requests.get(url=monitor_url, cookies=self._cookies,
                                verify=self._verify_ssl)

        if response.ok:
            data = response.json()
            status = data['status']
            statustext = data['statustext'].encode('ascii')
            if (not status) or \
               statustext.startswith('Unable to connect'):
                return False
            else:
                return True
        else:
            self.debug(1, "Connection error in getMonitorDaemonStatus",
                       "stderr")
            return False

    def getMonitorLatestEvent(self, monitorID):
        # Returns the latest ID and max score frame ID event for a monitor. If
        # connection error occurs or there are no events for the monitor, both
        # will be 0.

        # First need to determine the number of pages

        monitor_url = self._server \
                    + "/zm/api/events/index/MonitorID:{:d}.json?page=1"\
                      .format(monitorID)
        response = requests.get(url=monitor_url, cookies=self._cookies,
                                verify=self._verify_ssl)

        latest_eventid = 0
        maxscore_frameid = 0
        if not response.ok:
            self.debug(1, "Connection error in getMonitorLatestEvent", "stderr")
            return latest_eventid, maxscore_frameid

        # Loop through all events and get most recent one based on end time

        npages = response.json()['pagination']['pageCount']
        latest_endTime = datetime.strptime('1970-01-01 00:00:00',
                                           '%Y-%m-%d %H:%M:%S')
        for i in range(npages):
            monitor_url = self._server \
                        + "/zm/api/events/index/MonitorID:{:d}.json?page={:d}"\
                          .format(monitorID, i)
            response = requests.get(url=monitor_url, cookies=self._cookies,
                                    verify=self._verify_ssl)
            data = response.json()
            for event in data['events']:
                endTime = event['Event']['EndTime']
                ID = int(event['Event']['Id'])
                if endTime is not None:
                    endTime_obj = datetime.strptime(endTime.encode('ascii'),
                                                    '%Y-%m-%d %H:%M:%S')
                    if endTime_obj > latest_endTime:
                        latest_endTime = endTime_obj
                        latest_eventid = ID
                        maxscore_frameid = \
                            int(event['Event']['MaxScoreFrameId'])
        return latest_eventid, maxscore_frameid

    def getFrameURL(self, frameid):
        # Returns url for the image specified by the given frameid

        return self._server \
               + "/zm/index.php?view=image&fid={:d}&eid=&show=capture" \
                 .format(frameid)

    def getFrameImage(self, frameid, output_filename):
        # Downloads image specified by frameid to the given filename. Returns
        # True if everything succeeded, or False otherwise.

        frame_url = self.getFrameURL(frameid)
        response = requests.get(url=frame_url, cookies=self._cookies,
                                verify=self._verify_ssl)
        if response.ok:
            try:
                f = open(output_filename, 'wb')
            except IOError:
                self.debug(1, "Error opening file {:s}".format(output_filename),
                           "stderr")
                return False
            f.write(response.content)
            self.debug(1, "Saved image {:s}.".format(output_filename))
            return True
        else:
            return False
