import sys
from datetime import datetime
import ConfigParser

def debug(message, pipe="stdout"):

    curr_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    if pipe == "stderr":
        sys.stderr.write("{:s} {:s}\n".format(curr_time, message))
    else:
        sys.stdout.write("{:s} {:s}\n".format(curr_time, message))

def get_from_config(config, section, option, required=True, default=None):

    try:
        val = config.get(section, option)
    except ConfigParser.NoOptionError:
        if required:
            debug("{:s}:{:s} is required".format(section, option), "stderr")
            sys.exit(1)
        else:
            val = default

    return val

def get_bool_from_config(config, section, option, required=True, default=None):

    try:
        val = config.getboolean(section, option)
    except ConfigParser.NoOptionError:
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
    except ConfigParser.NoOptionError:
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
    except ConfigParser.NoOptionError:
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
