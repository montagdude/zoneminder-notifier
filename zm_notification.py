import os
import subprocess
import requests
import time
import zm_util
import smtplib,ssl
from email.mime.text import MIMEText
from email.mime.image import MIMEImage
from email.mime.multipart import MIMEMultipart

class Notification:
    def __init__(self,st):
        #self.message_file = tmp_message_file
        #self.attachment = tmp_attachment
        self.setup = st
        self.subject = "ZoneMinder event alert"

        # Keep track of the last time we received a 500 response from the API server.
        # Their documentation says to wait at least 5 seconds in that case.
        self.pushover_last_error = 0.
        self.pushover_error_timeout = 5.

    def sendNotifications(self, msg, email_addresses, pushover_data=None,tmp_analysis_filename=None):
        '''Sends notifications. email_addresses is a list of dicts of the form:
           email_address["address"]: the email address
           email_address["image"]: True/False - whether to attach an image.
           To send Pushover notification, pass a dict in this format:
           {"api_token": pushover_api_token,
            "user_key": pushover_user_key,
            "attach_image": True/False}'''

        if email_addresses is None:
           return False

        # Email notifications
        if len(email_addresses) > 0:
            if tmp_analysis_filename is not None:
                # Write the message
                if not self.writeMessage(msg,tmp_analysis_filename+".txt"):
                    return False

            # Send emails
            for addr in email_addresses:
                #start_time = time.time()
                if self.setup.email_client == "mutt":
                    if not self.sendEmail_mutt(addr["address"], addr["image"],tmp_analysis_filename):
                        return False
                else:
                    if not self.sendEmail_smtp(addr["address"], addr["image"],tmp_analysis_filename):
                        return False
                #print("Time spend to send email {} seconds ---".format(time.time() - start_time))

        # Pushover API notifications
        if pushover_data is not None:
            api_token = pushover_data["api_token"]
            user_key = pushover_data["user_key"]
            attach_image = pushover_data["attach_image"]
            return self.sendPushoverNotification(api_token, user_key, msg, attach_image,tmp_analysis_filename+".jpg")

        return True

    def writeMessage(self, msg,message_file):
        '''Writes message to tmp file'''
        try:
            f = open(message_file, 'w')
        except IOError:
            zm_util.debug("Cannot write to {:s}.".format(message_file), "stderr")
            return False
        f.write(msg)

        return True

    def sendEmail_mutt(self, address, attach_image=False,tmp_analysis_filename = None):
        '''Sends an email to the specified address with mutt.'''
        message_file = tmp_analysis_filename + ".txt"
        try:
            f = open(message_file)
        except IOError:
            zm_util.debug("Cannot open {:s}.".format(message_file), "stderr")
            return False
        if attach_image and os.path.isfile(tmp_analysis_filename + ".jpg"):
            check = subprocess.run(['mutt', '-s', self.subject, '-a', tmp_analysis_filename + ".jpg" , '--',
                                   address], stdin=f)
        else:
            check = subprocess.run(['mutt', '-s', self.subject, address], stdin=f)

        f.close()
        return check.returncode == 0

    def sendPushoverNotification(self, api_token, user_key, msg, attach_image,tmp_analysis_image):
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
                attachment_data = {"attachment": (tmp_analysis_image, f, "image/jpeg")}
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



    def sendEmail_smtp(self, address, attach_image=False,tmp_analysis_filename = None):
        '''Sends an email to the specified address with smtp.'''

        msg = MIMEMultipart()
        msg['Subject'] = self.subject
        msg['From'] = self.setup.smtp_usr
        msg['To'] = address

        if tmp_analysis_filename is not None:
            zm_util.debug("Constructing email to {}".format(address), "stdout")
            try:
                if os.path.isfile(tmp_analysis_filename + ".txt"):
                    with open(tmp_analysis_filename + ".txt", 'rb') as f:
                        txt_data = f.read()
                        text = MIMEText(txt_data,_charset="utf-8")
                        msg.attach(text)
            except Exception as e:
                zm_util.debug("Cannot process file {} : {}.".format(tmp_analysis_filename + ".txt",e), "stderr")
                return False

            if attach_image:
                try:
                    if os.path.isfile(tmp_analysis_filename + ".jpg"):
                        with open(tmp_analysis_filename + ".jpg", 'rb') as f:
                            img_data = f.read()
                            image = MIMEImage(img_data, name=os.path.basename(tmp_analysis_filename + ".jpg"))
                            msg.attach(image)
                except Exception as e:
                    zm_util.debug("Cannot process file {} : {}.".format(tmp_analysis_filename + ".txt",e), "stderr")
                    return False
            zm_util.debug("Constructing email result : OK ", "stdout")

        zm_util.debug("[sendEmail_smtp] Sending email", "stdout")
        try:
            context = ssl.create_default_context()
            with smtplib.SMTP(self.setup.smtp_server) as server:
                server.ehlo()  # Can be omitted
                server.starttls(context=context)
                server.ehlo()  # Can be omitted
                server.login(self.setup.smtp_usr, self.setup.smtp_pwd)
                server.sendmail(msg['From'], msg['To'], msg.as_string())
        except Exception as e:
            zm_util.debug("Cannot send email: {}.".format(e), "stderr")
            return False

        zm_util.debug("[sendEmail_smtp] OK. ", "stdout")
        return True

