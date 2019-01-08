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
import matplotlib.pyplot as plt
import numpy as np

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

        # If we got no data, then we should finish up
        if len(data) == 0:
            record_elem.log(
                LogLevel.ERR,
                "Recording {}: no data after {} entries read!".format(
                    name,
                    entries_read))
            break

        entries_read += len(data)

        # We're going to pack up each entry into a msgpack item and
        #   then write it to the file. If it's already msgpack'd
        #   that's totally fine, this will just pack up the keys and ID
        for entry in data:
            packed_data = msgpack.packb(entry, use_bin_type=True)

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

def _get_recording(data):
    '''
    Returns the contents of a recording. Takes a msgpack serialized
    request object with the following fields:

    name: required recording name
    start: start entry index
    stop: stop entry index
    msgpack: if we should use msgpack to deserialize values, assumed false

    Will return a Response() type on error, else a list of all items
    in the recording.
    '''
    if (("name" not in data) or (type(data["name"]) is not str)):
        return Response(err_code=1, err_str="Name is required", serialize=True)

    name = data["name"]

    file = None
    for folder in [PERM_RECORDING_LOC, TEMP_RECORDING_LOC]:
        filename = os.path.join(folder, name + RECORDING_EXTENSION)
        if os.path.exists(filename):
            try:
                file = open(filename, 'rb', buffering=0)
                break
            except:
                return Response(err_code=2, err_str="Failed to open file {}".format(filename), serialize=True)

    # Make sure we found the file
    if file is None:
        return Response(err_code=3, err_str="No recording {}".format(name), serialize=True)

    start_idx = 0
    stop_idx = -1
    use_msgpack = False

    if ("start" in data) and (type(data["start"]) is int):
        start_idx = data["start"]
    if ("stop" in data) and (type(data["stop"]) is int):
        stop_idx = data["stop"]
    if ("msgpack" in data) and (type(data["msgpack"]) is bool):
        use_msgpack = data["msgpack"]

    # Now, we want to loop over the file. Note that when we packed the file
    #   we packed it as individual msgpack objects with no padding/association
    #   between them so we need to use the msgpack streaming API
    unpacker = msgpack.Unpacker(file, raw=False)
    response_items = []
    for i, unpacked in enumerate(unpacker):
        if (i >= start_idx):

            # Make the
            repacked = (unpacked["id"], {})

            # If we should use msgpack to deserialize
            for k in unpacked:
                if k != "id":
                    if use_msgpack:
                        repacked[1][k] = msgpack.unpackb(unpacked[k], raw=False)
                    else:
                        repacked[1][k] = unpacked[k]

            response_items.append(repacked)

        if ((stop_idx != -1) and (i >= stop_idx)):
            break

    return response_items

def get_recording(data):
    '''
    Returns the contents of a recording. Takes a msgpack serialized
    request object with the following fields:

    name: required recording name
    start: start entry index
    stop: stop entry index
    msgpack: if we should use msgpack to deserialize values, assumed false
    '''

    # Load the recording using the function we share with plot_recording
    result = _get_recording(data)
    if type(result) is not list:
        return result
    else:
        return Response(result, serialize=True)

def plot_recording(data):
    '''
    Makes a plot of the recording. Takes a msgpack-serialized JSON
    object with the following fields
    name : required recording name
    plots: list of plots to make, where each item in the list is a list as well.
        Each item in the plots list is a tuple, with values:
            - 0 : lambda function to perform on the data. The data will be
                    passed to the lambda as a dictionary named `x`
            - 1 : list of keys on which to perform the lambda function
            - 2 : optional label

        An example plots field would look like:
            "plots": [
                [
                    ["x[0]", ["joint_0", "joint_1"], "label0"],
                ],
                [
                    ["x[1]", ["joint_0", "joint_1"], "label1"],
                    ["x[2]", ["joint_0", "joint_1"], "label2"],
                ],
            ]
    start: Entry index to start the plot at
    stop: Entry index to stop the plot at
    msgpack: Whether or not to use msgpack to deserialize each key on
        readback from the recording. Default false
    save: Optional, if true will save an image of each plot, default false
    show: Optional, default true, will show the plots in an interactive
        fashion
    perm: Optional, default false. If true will save in the permanent
        file location, else temporary
    x: Optional lambda for converting an entry into a timestamp. If not
        passed, will use the redis timestamp. If passed, will be a
        lambda for an entry lambda entry: ... where the user supplies ...
        to convert the entry into an x-label
    '''

    # Load the recording. If we failed to load it just return that error
    result = _get_recording(data)
    if type(result) is not list:
        return result

    # Get the number of results
    n_results = len(result)
    if (n_results == 0):
        return Respose(err_code=4, err_str="0 results for recording", serialize=True)

    # We should have a list of all of the entries that we care about seeing
    #   and now for each entry need to go ahead and run all of the lambdas
    if ("plots" not in data) or (type(data["plots"]) is not list):
        return Response(err_code=5, err_str="Plots must be specified", serialize=True)

    # Note the plots
    plots = data["plots"]

    if ("x" in data):
        try:
            x_lambda = eval("lambda entry: " + data["x"])
            x_data = [x_lambda(entry[1]) for entry in result]
            x_label = str(data["x"])
        except:
            return Response(err_code=6, err_str="Unable to convert {} to x data lambda".format(data["x"]))
    else:
        x_data = [int(entry[0].split('-')[0]) for entry in result]
        x_label = "Redis Timestamp (ms)"

    x_data = np.array(x_data)
    x_data -= x_data[0]

    # Create the x-label for the data. If none is passed then we'll
    #   just use the redis timestamp, otherwise the user will give us a lambda
    #   for an entire

    # Convert the input data to lambdas
    figures = []
    for plot_n, plot in enumerate(plots):

        # List of lambdas to run
        lambdas = []
        total_lines = 0

        # Make the lambda
        for val in plot:

            # Make sure the length of the array is proper
            if ((len(val) < 2) or (len(val) > 3)):
                return Response(err_code=7, err_str="Each plot value should have 2 or 3 items", serialize=True)

            # Try to make the lambda from the first one
            try:
                lamb = eval("lambda x: " + val[0])
            except:
                return Response(err_code=8, err_str="Unable to make lambda from {}".format(val[0]), serialize=True)

            # Make sure each key exists in the first data item
            for key in val[1]:
                if key not in result[0][1]:
                    return Response(err_code=9, err_str="Key {} not in data".format(key), serialize=True)

            # Add the number of keys in this lambda to the total number of lines
            total_lines += len(val[1])

            # Get the label
            if len(val) == 3:
                label = str(val[2])
            else:
                label = str(val[0])

            lambdas.append((lamb, val[1], label))

        # Now we want to preallocate the data for the plot. It should be a
        #   matrix that's n-dimensional by lambda-key pair and entry
        data = np.zeros((total_lines, n_results))

        # And finally we want to loop over all of the data
        for i, result in enumerate(result):

            idx = 0
            for (l, keys, label) in lambdas:
                for key in keys:
                    data[idx][i] = l(result[1][key])
                    idx += 1

        # Now, we can go ahead and make the figure
        fig = plt.figure()
        figures.append(fig)

        # Plot all of the lines
        idx = 0
        for (l, keys, label) in lambdas:
            for key in keys:
                plt.plot(x_data, data[idx,:], label=label)

        # Make the title and x label
        plt.title("Plot {}".format(plot_n))
        plt.xlabel(x_label)

    # Draw the new plot
    plt.show()

    return Response("Success", serialize=True)


if __name__ == '__main__':
    elem = Element("record")
    elem.command_add("start", start_recording, timeout=1000, deserialize=True)
    elem.command_add("stop", stop_recording, timeout=1000, deserialize=True)
    elem.command_add("wait", wait_recording, timeout=60000, deserialize=True)
    elem.command_add("list", list_recordings, timeout=1000)
    elem.command_add("get", get_recording, timeout=1000, deserialize=True)
    elem.command_add("plot", plot_recording, timeout=60000, deserialize=True)

    # Want to launch the plot thread s.t. our plot API can return quickly

    elem.command_loop()
