#
# record.py
#   Simple recorder and viewer element
#
from atom import Element
from atom.messages import Response, LogLevel
from threading import Thread
import time
import msgpack
import os

# Where to store temporary recordings
TEMP_RECORDING_LOC = "/shared"

# Where to store permanent recordings
PERM_RECORDING_LOC = "/recordings"

# Recording extension
RECORDING_EXTENSION = ".atomrec"

# Default number of seconds to record for
DEFAULT_N_SEC = 10

# Interval at which we will poll the stream for entries, in seconds
POLL_INTERVAL = 0.1

# Max time to block for data
BLOCK_MS = 1000

# Active recording threads
active_recordings = {}

def record_fn(name, n_entries, n_sec, perm, element, stream):
    '''
    Mainloop for a recording thread. Creates a new
    element with the proper name and listens on and
    records the stream until we're told to stop
    '''
    global active_recordings

    # Make an element from the name
    record_elem = Element("record_" + name)

    # Open the file for the recording
    filename = os.path.join(
        PERM_RECORDING_LOC if perm else TEMP_RECORDING_LOC, name + RECORDING_EXTENSION)
    try:
        record_file = open(filename, 'wb')
    except:
        record_elem.log(
            LogLevel.ERR, "Unable to open file {}".format(filename))
        del active_recordings[name]
        return

    # At the outer loop, we want to loop until we've been cancelled
    last_id = "$"
    intervals = 0
    entries_read = 0
    while name in active_recordings:

        # Read the data
        data = record_elem.entry_read_since(element, stream, last_id, n=n_entries, block=BLOCK_MS)
        entries_read += len(data)

        # We're going to pack up each entry into a msgpack item and
        #   then write it to the file. If it's already msgpack'd
        #   that's totally fine, this will just pack up the keys and ID
        packed_data = msgpack.packb(data, use_bin_type=True)

        # Write the packed data to file
        record_file.write(packed_data)

        # If n_entries is not none then we want to subtract
        #   off the number of entries left and perhaps break out
        if n_entries is not None:
            n_enties -= len(data)
            if (n_enties <= 0):
                break

        # Otherwise see if we've recorded for longer than our
        #   elapsed time
        else:
            intervals += 1
            if (intervals * POLL_INTERVAL) >= n_sec:
                break

        # If we got here, we should sleep for the interval before
        #   making the next call
        time.sleep(POLL_INTERVAL)

        # And update the last ID
        last_id = data[-1]["id"]

    # Once we're out of here we want to note that we're no longer
    #   active in the global system
    thread = active_recordings.pop(name)

    # And we want to close the file
    record_file.close()

    # And log that we completed the recording
    record_elem.log(LogLevel.INFO, "Finished recording {} with {} entries read".format(
        name, entries_read))


def start_recording(data):

    # Data should be a dictionary with the following keys
    #   name: required. String for the name of the recording
    #   t: Optional time (in seconds) to record for. If omitted, will
    #           default to 10
    #   n: Optional number of entries to record for. If omitted will default
    #           to default time. If both time and n are specified, n will
    #           take precedence
    #   p: Optional boolean to make the recording persistent/permanent.
    #           Will store the recording in a different location if so
    #   e: Required element name
    #   s: Required stream name
    global active_recordings

    # Make sure we got a name
    if ("name" not in data) or (type(data["name"]) is not str):
        return Response(err_code=1, err_str="name must be in data", serialize=True)

    # Make sure we got an element
    if ("e" not in data) or (type(data["e"]) is not str):
        return Response(err_code=2, err_str="element must be in data", serialize=True)

    # Make sure we got a stream
    if ("s" not in data) or (type(data["s"]) is not str):
        return Response(err_code=3, err_str="stream must be in data", serialize=True)

    # Get the name
    name = data["name"]
    element = data["e"]
    stream = data["s"]

    # Check that the name is not in use
    if name in active_recordings:
        return Response(err_code=4, err_str="Name {} already in use".format(name), serialize=True)

    n_entries = None
    n_sec = DEFAULT_N_SEC
    perm = False

    # Process either the n or t values that came in over the API
    if ("n" in data) and (type(data["n"]) is int):
        n_entries = data["n"]
    if ("t" in data) and (type(data["t"]) is int):
        n_sec = data["t"]
    if ("p" in data) and (type(data["p"]) is bool):
        perm = data["p"]

        # If we have a permanent data request, make sure the user has
        #   mounted a permanent location
        if perm and not os.path.exists(PERM_RECORDING_LOC):
            return Response(err_code=5, err_str="Please mount {} in your docker-compose file".format(PERM_RECORDING_LOC), serialize=True)

    # Spawn a new thread that will go ahead and do the recording
    thread = Thread(target=record_fn, args=(name, n_entries, n_sec, perm, element, stream,), daemon=True)

    # Put the thread into the active_recordings struct
    active_recordings[name] = thread

    thread.start()

    # Make the response
    return Response(\
        "Started recording {} for {} and storing in {}".format(
            name, \
            "{} entries".format(n_entries) if n_entries != None else "{} seconds".format(n_sec), \
            PERM_RECORDING_LOC if perm else TEMP_RECORDING_LOC), \
        serialize=True)

def stop_recording(data):
    '''
    Stops a recording. Data should be a msgpack'd string of the name
    '''
    # Active recordings
    global active_recordings

    # Make sure the recording is active
    if data not in active_recordings:
        return Response(err_code=1, err_str="Recording {} not active".format(data), serialize=True)

    # Note the thread and delete it from the active recordings object
    thread = active_recordings.pop(data)

    # Wait for the recording thread to finish
    thread.join()

    return Response("Success")

def wait_recording(data):
    '''
    Waits for a recording to finish
    '''
    # Active recordings
    global active_recordings

    # Make sure the recording is active
    if data not in active_recordings:
        return Response(err_code=1, err_str="Recording {} not active".format(data), serialize=True)

    start_time = time.time()
    active_recordings[data].join()
    stop_time = time.time()

    return Response("Returned after {} seconds".format(stop_time - start_time))

def list_recordings(data):
    '''
    Returns a list of all recordings in the system
    '''

    recordings = []

    # Loop over all locations
    for folder in [PERM_RECORDING_LOC, TEMP_RECORDING_LOC]:

        # If the folder doesn't exist, just move on
        if not os.path.exists(folder):
            continue

        # Loop over all folders in the location
        for filename in os.listdir(folder):

            # If it ends with our extension, then add it
            if filename.endswith(RECORDING_EXTENSION):
                recordings.append(filename.strip(RECORDING_EXTENSION))

    return Response(recordings, serialize=True)



if __name__ == '__main__':
    elem = Element("record")
    elem.command_add("start", start_recording, timeout=1000, deserialize=True)
    elem.command_add("stop", stop_recording, timeout=1000, deserialize=True)
    elem.command_add("wait", wait_recording, timeout=60000, deserialize=True)
    elem.command_add("list", list_recordings, timeout=1000)
    elem.command_loop()
