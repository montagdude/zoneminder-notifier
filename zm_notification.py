import subprocess
import requests
import time
import zm_util

class Notification:
    def __init__(self, tmp_message_file, tmp_attachment):
        self.message_file = tmp_message_file
        self.attachment = tmp_attachment
        self.subject = "ZoneMinder event alert"

        # Keep track of the last time we received a 500 response from the API server.
        # Their documentation says to wait at least 5 seconds in that case.
        self.pushover_last_error = 0.
        self.pushover_error_timeout = 5.

    def sendNotifications(self, msg, email_addresses=[], pushover_data=None):
        '''Sends notifications. email_addresses is a list of dicts of the form:
           email_address["address"]: the email address
           email_address["image"]: True/False - whether to attach an image.
           To send Pushover notification, pass a dict in this format:
           {"api_token": pushover_api_token,
            "user_key": pushover_user_key,
            "attach_image": True/False}'''

        # Email notifications
        if len(email_addresses) > 0:
            # Write the message
            if not self.writeMessage(msg):
                return False

            # Send emails
            for addr in email_addresses:
                if not self.sendEmail(addr["address"], addr["image"]):
                    return False

        # Pushover API notifications
        if pushover_data is not None:
            api_token = pushover_data["api_token"]
            user_key = pushover_data["user_key"]
            attach_image = pushover_data["attach_image"]
            return self.sendPushoverNotification(api_token, user_key, msg, attach_image)

        return True

    def writeMessage(self, msg):
        '''Writes message to tmp file'''
        try:
            f = open(self.message_file, 'w')
        except IOError:
            zm_util.debug("Cannot write to {:s}.".format(self.message_file), "stderr")
            return False
        f.write(msg)

        return True

    def sendEmail(self, address, attach_image=False):
        '''Sends an email to the specified address with mutt.'''
        try:
            f = open(self.message_file)
        except IOError:
            zm_util.debug("Cannot open {:s}.".format(self.message_file), "stderr")
            return False
        if attach_image:
            check = subprocess.run(['mutt', '-s', self.subject, '-a', self.attachment, '--',
                                   address], stdin=f)
        else:
            check = subprocess.run(['mutt', '-s', self.subject, address], stdin=f)

        f.close()
        return check.returncode == 0

    def sendPushoverNotification(self, api_token, user_key, msg, attach_image):
        '''Sends a notification via the Pushover API. Returns True if successful or False if not.'''
        url = "https://api.pushover.net/1/messages.json"
        data = {"token": api_token, "user": user_key, "title": self.subject, "message": msg}

        # Check if it's okay to send the request
        # See "Being Friendly to our API" section in Pushover API documentation
        now = time.time()
        if now - self.pushover_last_error < self.pushover_error_timeout:
            zm_util.debug("Skipping Pushover notification due to recent API request error.",
                          "stderr")
            return False

        # Send the request
        if attach_image:
            try:
                f = open(self.attachment, "rb")
                attachment_data = {"attachment": (self.attachment, f, "image/jpeg")}
                r = requests.post(url, data=data, files=attachment_data)
                f.close()
            except IOError:
                zm_util.debug("Unable to open {:s} for Pushover notification.", "stderr")
                r = requests.post(url, data=data)
        else:
            r = requests.post(url, data=data)

        # Check the response and return
        if not r.ok:
            zm_util.debug("Pushover request returned {:d}.".format(r.status_code), "stderr")
            self.pushover_last_error = time.time()
            return False
        return True
