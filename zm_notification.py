import subprocess
import zm_util

class Notification:
    def __init__(self, tmp_message_file, tmp_attachment):
        self.message_file = tmp_message_file
        self.attachment = tmp_attachment
        self.subject = "ZoneMinder event alert"

    def sendNotifications(self, email_addresses, msg):
        '''Sends notifications. email_addresses is a list of dicts of the form:
           email_address["address"]: the email address
           email_address["image"]: True/False - whether to attach an image'''

        # Write the message
        if not self.writeMessage(msg):
            return False

        # Send emails
        for addr in email_addresses:
            if not self.sendEmail(addr["address"], addr["image"]):
                return False

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
