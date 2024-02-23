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


def get_new_pictures_list(score_treshold,monitor_id,latest_EventPictureID,detect_in):
    try:
        conn = mysql.connector.connect(host='localhost',
                                       database='zm',
                                       user='zmuser',
                                       password='zmpass',
                                       auth_plugin='mysql_native_password')
        with conn.cursor() as cursor:
            # Read data from database
            if detect_in == 'video':
                # firstly we try to pick last one record/frame for video per event
                sql_video_frames = """select max(f.Id) as ID
                                        from 
                                            (select Frames.ID as ID,Frames.EventID as EventID
                                            from   zm.Frames,zm.Events
                                            where  Frames.EventID = Events.ID
                                            and    Frames.Score >= {}
                                            and    Events.MonitorID = {}
                                            and    Frames.ID > {} ) as f
                                        group by f.EventID  
                                        order by ID""".format(score_treshold, monitor_id,latest_EventPictureID)
                if (latest_EventPictureID == -1):
                    # just last one - init after start
                    sql_video_frames = sql_video_frames + " desc limit 1"

                cursor.execute(sql_video_frames)
                video_frames = cursor.fetchall()

                # there are no new records
                if len(video_frames) == 0:
                    return []

                video_frames_str = ", ".join(str(frame[0]) for frame in video_frames)
                frames_selection = f"in ({video_frames_str})"
            else:
                frames_selection = f" > {latest_EventPictureID}"


            sql = """select Frames.ID as ID,Frames.FrameID as FrameID,Frames.Score as Score,Events.ID as EventID,
                           Events.StartDateTime as StartDateTime,Events.DefaultVideo as VideoFile,  
                           Storage.Path as StoragePath
                    from   zm.Frames,zm.Events,zm.Storage,zm.Monitors
                    where  Frames.EventID = Events.ID
                    and    Monitors.ID = {}
                    and    Frames.Score >= {}
                    and    Events.MonitorID = {}
                    and    Frames.ID {}
                    and    Storage.ID = Monitors.StorageID 
                    order by Frames.ID""".format(monitor_id, score_treshold, monitor_id,frames_selection)
            if (latest_EventPictureID==-1):
                # just last one - init after start
                sql = sql + " desc limit 1"
            cursor.execute(sql)
            rows = cursor.fetchall()
            return rows if rows != None else []
    except Exception as e:
        sys.stderr.write(f"Error to get data from database : {e}\n")
        return []



