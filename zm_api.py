# Some portions of this class influenced by the pyzm project, so thanks for that.

import requests
import time
import zm_util
from json.decoder import JSONDecodeError
# If you have a webserver serving HTTPS with a self-signed certificate, you
# may want to uncomment the line below.
#import urllib3
#urllib3.disable_warnings()

class ZMAPI:
    def __init__(self, localserver, username, password, webserver=None, verify_ssl=True,
                 debug_level=1):
        self.username = username
        self.password = password
        self.verify = verify_ssl
        self.debug_level = debug_level

        self.apipath = localserver + '/zm/api'
        if webserver is None:
            self.webpath = localserver + '/zm/index.php'
        else:
            self.webpath = webserver + '/zm/index.php'

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

    def _makeRequest(self, url, params=[], method="get", post_data=None):
        '''Makes a request to the API, appending access token, and returns response.
           params is a list of options to be appended at the end of the url (other
           than the access token). Automatically refreshes tokens if required.
           method: 'get' or 'post'
           post_data: optional dict of data to go along with a post request'''

        # Initialize r as bad request so calling method can catch it on error
        r = requests.Response()
        r.status_code = 400

        # Refresh tokens if needed
        if not self._refreshTokens():
            return r

        # Put together the url
        access_url = url + '?token={:s}'.format(self.access_token)
        for item in params:
            access_url += '&' + item

        # Make the request and return the response
        if method == 'get':
            try:
                r = requests.get(access_url, verify=self.verify)
            except requests.exceptions.ConnectionError:
                self.debug(1, "Get request failed due to connection error.", "stderr")
        elif method == 'post':
            try:
                r = requests.post(access_url, data=post_data, verify=self.verify)
            except requests.exceptions.ConnectionError:
                self.debug(1, "Post request failed due to connection error.", "stderr")
        return r

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
        try:
            r = requests.post(url=login_url, data=login_data, verify=self.verify)
            if r.ok:
                try:
                    rj = r.json()
                except JSONDecodeError:
                    self.debug(1, "Login failed due to error decoding response.", "stderr")
                    return False
                self.access_token = rj['access_token']
                self.access_timeout = float(rj['access_token_expires']) + time.time()
                self.refresh_token = rj['refresh_token']
                self.refresh_token_timeout = float(rj['refresh_token_expires']) + time.time()
                api_version = rj['apiversion']
                if api_version != '2.0':
                    self.debug(1, "API version 2.0 required.", "stderr")
                    return False
            else:
                self.debug(1, "Login failed with status {:d}.".format(r.status_code), "stderr")
                return False
        except requests.exceptions.ConnectionError:
            self.debug(1, "Login failed due to connection error.", "stderr")
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

    def getMonitorLatestEvent(self, monitorID, idx=0):
        '''Returns pertinent information about the latest event for a monitor.
           res['id']: eventid (-1 by default or on error)
           res['maxscore_frameid']: frameid of maxscore (0 by default)
           res['path']: filesystem path of the event on the server ("" by default)
           res['video_name']: file name of the video ("" by default)
           The input idx is optional and defaults to 0, which means it returns the latest event
           available. Increase the index to return an earlier event.

           Note: normally when searching events, you'd need to get the number of pages as follows:
               monitor_url = self.apipath + '/events/index/MonitorId:{:d}.json'\
                                            .format(monitorID)
               r = self._makeRequest(monitor_url, params=['page=1'])
               if not r.ok:
                   return res
               rj = r.json()
               npages = rj['pagination']['pageCount']
           and then loop over pages to find the latest event. This process is described in the API
           documentation. However, due to the way the API sorts events, the first result on the
           first page will be the latest event for the monitor.'''

        res = {'id':-1, 'maxscore_frameid':0, 'path':"", 'video_name':""}

        # Get the list of events for this monitor in descending order based on EndTime
        monitor_url = self.apipath + '/events/index/MonitorId:{:d}.json'.format(monitorID)
        r = self._makeRequest(monitor_url, params=['page=1', 'sort=EndTime', 'direction=desc'])
        if not r.ok:
            self.debug(1, "Error getting events in getMonitorLatestEvent", "stderr")
            return res
        rj = r.json()

        # Since the list is already sorted, the first in the list will be the latest one
        events = rj['events']
        if len(events) > 0:
            event = events[idx]
            ID = int(event['Event']['Id'])
            res['id'] = ID
            # This can be None if ZoneMinder stopped while the event was in progress
            maxscoreid = event['Event']['MaxScoreFrameId']
            if maxscoreid is not None:
                res['maxscore_frameid'] = int(maxscoreid)
                res['path'] = event['Event']['FileSystemPath']
                res['video_name'] = event['Event']['DefaultVideo']
            else:
                # Return the next event instead
                return self.getMonitorLatestEvent(monitorID, idx+1)

        return res

    def getEventURL(self, eventid):
        '''Returns url for the event specified by the given eventid'''
        return self.webpath + "?view=event&eid={:d}".format(eventid)

    def getRunStates(self):
        '''Returns a list of run states. Each item in the list is a dict with the form:
           item['id']: Id of the run state in the DB
           item['name']: run state name
           item['active']: True/False: whether this is the active run state. Note that just
                           because a run state is listed as active doesn't mean ZM is running.
                           It could just be the last one that ran. Use getDaemonStatus to
                           determine if it is running.
           List will be empty if there is an error.'''

        runstates = []
        stateurl = self.apipath + "/states.json"
        r = self._makeRequest(stateurl)
        if not r.ok:
            self.debug(1, "Error getting run states", "stderr")
            return runstates
        rj = r.json()
        states = rj['states']
        for state in states:
            statedict = state['State']
            runstates.append({'id': statedict['Id'],
                              'name': statedict['Name'],
                              'active': statedict['IsActive']==1})
        return runstates

    def changeRunState(self, runstate_name):
        '''Changes run state. Returns True on success or False on error.'''

        stateurl = self.apipath + "/states/change/{:s}.json".format(runstate_name)
        r = self._makeRequest(stateurl, method="post")
        return r.ok
