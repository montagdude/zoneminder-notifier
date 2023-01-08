#!/usr/bin/env python3
#
# Some portions of this class influenced by the pyzm project, so thanks for that.

import requests
import time
import datetime
import zm_util
# If you have a webserver serving HTTPS with a self-signed certificate, you
# may want to uncomment the line below.
#import urllib3
#urllib3.disable_warnings()

class ZMAPI:
    def __init__(self, server, username, password, verify_ssl=True, debug_level=1):
        self.username = username
        self.password = password
        self.verify = verify_ssl
        self.debug_level = debug_level

        self.apipath = server + '/zm/api'
        self.webpath = server + '/zm/index.php'
        self.access_init = None
        self.refresh_init = None

        self.access_token = None
        self.access_timeout = 0
        self.refresh_token = None
        self.refresh_timeout = 0

    def _needAccess(self, access_buffer=300):
        '''Checks if we need a new access token (soon or already)'''
        if self.access_token is None or self._access_timeout <= time.time()+access_buffer:
            return True
        return False

    def _needRefresh(self, refresh_buffer=600):
        '''Checks if we need a new refresh token (soon or already)'''

        if self.refresh_token is None or self.refresh_timeout <= time.time()+refresh_buffer:
            return True
        return False

    def _refreshTokens(self):
        '''Refreshes tokens if needed'''

        if self._needRefresh():
            # Get new tokens via username and password if the refresh token has expired
            check = self.login(method='password')
        else:
            # Get a new access token if needed. Otherwise take no action.
            if self._needAccess():
                check = self.login(method='refresh_token')
        return check

    def _makeRequest(self, url, params=[]):
        '''Makes a request to the API, appending access token, and returns response.
           params is a list of options to be appended at the end of the url (other
           than the access token)'''

        self._refreshTokens()
        access_url = url + '?token={:s}'.format(self.access_token)
        for item in params:
            access_url += '&' + item
        return requests.get(access_url, verify=self.verify)

    def debug(self, level, message, pipename='stdout'):
        if level >= self.debug_level:
            zm_util.debug("zm_api: " + message, pipename)

    def login(self, method='password'):
        '''Performs login and saves access and refresh tokens. Returns True if successful
           and False if not.'''

        login_url = self.apipath + '/host/login.json'
        if method == 'password' or self._needRefresh():
            login_data = {'user': self.username, 'pass': self.password}
        else:
            login_data = {'token': self.refresh_token}
        r = requests.post(url=login_url, data=login_data, verify=self.verify)
        if r.ok:
            rj = r.json()
            self.access_token = rj['access_token']
            self.access_timeout = float(rj['access_token_expires']) + time.time()
            self.refresh_token = rj['refresh_token']
            self.refresh_token_timeout = float(rj['refresh_token_expires']) + time.time()
            api_version = rj['apiversion']
            if api_version != '2.0':
                self.debug(1, "API version 2.0 required.", "stderr")
                return False
            access_init = time.time()
            refresh_init = time.time()
        else:
            self.debug(1, "Login failed with status {:d}.".format(r.status_code), "stderr")
            return False

        return True

    def logout(self):
        '''Logs out of the API and returns True if successful, False if not'''

        logout_url = self.apipath + '/host/logout.json'
        r = self._makeRequest(logout_url)
        return r.ok

    def getDaemonStatus(self):
        '''Returns True if ZoneMinder is running, False if not or on error'''

        daemon_url = self.apipath + '/host/daemonCheck.json'
        r = self._makeRequest(daemon_url)
        if r.ok:
            status = int(r.json()['result'])
            return status == 1
        else:
            self.debug(1, "Connection error in getDaemonStatus", "stderr")
        return False

    def getMonitorDaemonStatus(self, monitorID):
        '''Returns True if a monitor is active, False if not or on error'''

        monitor_url = self.apipath + '/monitors/daemonStatus/id:{:d}/daemon:zmc.json' \
                                     .format(monitorID)
        r = self._makeRequest(monitor_url)
        if r.ok:
            rj = r.json()
            status = rj['status']
            return rj['status']
        else:
            self.debug(1, "Connection error in getMonitorDaemonStatus", "stderr")
            return False

    def getMonitors(self, active_only=False):
        '''Returns a list of monitor ids and names, optionally only the monitors
           that are active. List will be emtpy if a connection error occurs.'''

        monitors_url = self.apipath + '/monitors.json'
        r = self._makeRequest(monitors_url)
        monitors = []
        if r.ok:
            rj = r.json()
            for item in rj['monitors']:
                monitor = {}
                try:
                    monitor['id'] = int(item['Monitor_Status']['MonitorId'])
                    monitor['name'] = item['Monitor']['Name']
                except TypeError:
                    self.debug(1, "No data available for monitor. Skipping.")
                    continue
                if active_only:
                    if self.getMonitorDaemonStatus(monitor['id']):
                        monitors.append(monitor)
                        self.debug(1, "Appended monitor {:d}: {:s}"\
                                   .format(monitor['id'], monitor['name']))
                else:
                    monitors.append(monitor)
                    self.debug(1, "Appended monitor {:d}: {:s}"\
                               .format(monitor['id'], monitor['name']))
        else:
            self.debug(1, "Connection error in getMonitors", "stderr")

        return monitors

    def getMonitorLatestEvent(self, monitorID):
        '''Returns pertinent information about the latest event for a monitor.
           res['id']: eventid (0 by default or on error)
           res['maxscore_frameid']: frameid of maxscore (0 by default)
           res['path']: filesystem path of the event on the server ("" by default)
           res['video_name']: file name of the video ("" by default)'''

        res = {'id':0, 'maxscore_frameid':0, 'path':"", 'video_name':""}

        # Determine the number of pages
        monitor_url = self.apipath + '/events/index/MonitorId:{:d}.json'\
                                     .format(monitorID)
        r = self._makeRequest(monitor_url, params=['page=1'])
        if not r.ok:
            print(r.status_code)
            self.debug(1, "Error getting number of pages in getMonitorLatestEvent", "stderr")
            return res
        rj = r.json()
        npages = rj['pagination']['pageCount']
        dt_fmt = '%Y-%m-%d %H:%M:%S'
        latest_eventtime = datetime.datetime.strptime('1970-01-01 00:00:00', dt_fmt)

        # Loop through all events and get the most recent one based on end time.
        # TODO: is it really necessary to go through all the pages? The API sorts by StartDateTime
        # already, so the last page should have the latest events. Check once I have more than 100
        # events, which is the hardcoded pagination setting in the API source code.
        for i in range(npages, 0, -1):
            # Get the list of events for this monitor in descending order based on EndTime
            monitor_url = self.apipath + '/events/index/MonitorId:{:d}.json'.format(monitorID)
            r = self._makeRequest(monitor_url, params=['page={:d}'.format(i), 'sort=EndTime',
                                                       'direction=desc'])
            if not r.ok:
                self.debug(1, "Error getting page of events in getMonitorLatestEvent", "stderr")
                return res
            rj = r.json()

            # Since the list is already sorted, the first in the list will be the latest one
            events = rj['events']
            if len(events) > 0:
                event = events[0]
                ID = int(event['Event']['Id'])
                eventtime = event['Event']['EndTime']
                if eventtime is not None:
                    time_obj = datetime.datetime.strptime(eventtime, dt_fmt)
                    if time_obj > latest_eventtime:
                        latest_eventtime = time_obj
                        res['id'] = ID
                        res['maxscore_frameid'] = int(event['Event']['MaxScoreFrameId'])
                        res['path'] = event['Event']['FileSystemPath']
                        res['video_name'] = event['Event']['DefaultVideo']

        return res

    def getFrameURL(self, frameid):
        '''Returns url for the image specified by the given frameid'''
        return self.webpath + "?view=image&fid={:d}&eid=&show=capture".format(frameid)
