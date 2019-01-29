import sys
from datetime import datetime

def debug(message, pipe="stdout"):

    curr_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    if pipe == "stderr":
        sys.stderr.write("{:s} {:s}\n".format(curr_time, message))
    else:
        sys.stdout.write("{:s} {:s}\n".format(curr_time, message))
