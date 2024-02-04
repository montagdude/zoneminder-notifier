import sys
import mysql.connector
from datetime import datetime
from configparser import NoOptionError


def debug(message, pipe="stdout"):

    curr_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    if pipe == "stderr":
        sys.stderr.write("{:s} {:s}\n".format(curr_time, message))
    else:
        sys.stdout.write("{:s} {:s}\n".format(curr_time, message))

def get_from_config(config, section, option, required=True, default=None):

    try:
        val = config.get(section, option)
    except NoOptionError:
        if required:
            debug("{:s}:{:s} is required".format(section, option), "stderr")
            sys.exit(1)
        else:
            val = default

    return val

def get_bool_from_config(config, section, option, required=True, default=None):

    try:
        val = config.getboolean(section, option)
    except NoOptionError:
        if required:
            debug("{:s}:{:s} is required".format(section, option), "stderr")
            sys.exit(1)
        else:
            val = default
    except ValueError:
        debug("{:s}:{:s}: unable to convert string to boolean".format(section,
              option), "stderr")
        sys.exit(1)

    return val

def get_int_from_config(config, section, option, required=True, default=None):

    try:
        val = config.getint(section, option)
    except NoOptionError:
        if required:
            debug("{:s}:{:s} is required".format(section, option), "stderr")
            sys.exit(1)
        else:
            val = default
    except ValueError:
        debug("{:s}:{:s}: unable to convert string to integer".format(section,
              option), "stderr")
        sys.exit(1)

    return val

def get_float_from_config(config, section, option, required=True, default=None):

    try:
        val = config.getfloat(section, option)
    except NoOptionError:
        if required:
            debug("{:s}:{:s} is required".format(section, option), "stderr")
            sys.exit(1)
        else:
            val = default
    except ValueError:
        debug("{:s}:{:s}: unable to convert string to float".format(section,
              option), "stderr")
        sys.exit(1)

    return val


def get_highest_scored_image(event):
    try:
        conn = mysql.connector.connect(host='localhost',
                                       database='zm',
                                       user='zmuser',
                                       password='zmpass',
                                       auth_plugin='mysql_native_password')
        with conn.cursor() as cursor:
            # Read data from database
            sql = """select FrameID from Frames where ID = {}""".format(event['maxscore_frameid'])
            cursor.execute(sql)
            row = cursor.fetchone()
            return row[0] if row != None else -1
    except Exception as e:
        sys.stderr.write(f"Error to get data from database : {e}\n")
        return -1

