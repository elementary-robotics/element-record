## Record

### Build Status

[![CircleCI](https://circleci.com/gh/elementary-robotics/element-record.svg?style=svg&circle-token=2165af3c4fc8f3009dd936c3dc645d083c470382)](https://circleci.com/gh/elementary-robotics/element-record)

### Overview

This element provides the recording functionality for the atom system. It
will listen to a stream and record all entries for either a fixed amount
of time or number of entries. The recording can be stored either in the
system-wide `tmpfs` that's mounted in `docker-compose` or in a persistent folder
mapped from your host system again using `docker-compose`.

The recordings can be retrieved in a number of ways:
1. Access the raw file on disk -- likely the least useful
2. Access them through the API. This element has an API that will return
recordings either entirely or by chunk. Recordings are returned as a msgpack'd
list of entries.
3. Convert them to CSV. This element provides an API to convert any recording
into a CSV and allows for custom processing of the data in doing so
4. View them as a plot. This element will load a recording and can visualize
the data in plots through a powerful, flexible API. In the API you can specify
how to format/convert the data from the recording into a plottable format so
that it should meet all of your needs. Plots are interactive and can be saved
as images.

All commands and responses from this element use msgpack serialization and
deserialization.

### File locations

The `record` element supports saving files in both temporary and permanent file locations. The temporary location will be in the shared `tmpfs` mounted between all elements in `docker-compose` at `/shared` in the container. The permanent location **must be mounted by the user in docker-compose** and must be located at `/recordings`. If the user doesn't mount a folder at `/recordings` in the container, then only the temporary storage of files will work. See the `docker-compose` section of these docs for more details

### Commands

#### `start`: Start Recording

> <button class="copy-button" onclick='copyText(this, "command record start {\"name\":\"example\", \"t\":5, \"perm\":false, \"e\":\"waveform\", \"s\":\"serialized\"}")'>Copy</button> Atom CLI example

```shell_session
> command record start {"name":"example", "t":5, "perm":false, "e":"waveform", "s":"serialized"}
{
  "data": "Started recording example for 5 seconds and storing in /shared",
  "err_code": 0,
  "err_str": ""
}

```

##### Request

The start recording command takes a msgpack'd JSON object with the following
keys:

| Key | Required | Default | Description |
|-----|----------|---------|-------------|
| `name` | yes | | Name of the recording. This will create a recording file named `name.atomrec` |
| `e` | yes | | Name of element whose stream we want to record |
| `s` | yes | | Name of stream we want to record |
| `t` | no | 10 | Duration of the recording, in seconds.
| `n` | no | | Duration of the recording, in entries. If specified, will override the `t` value specified. |
| `perm` | no | `false` | Whether to store the recording in the permanent or temporary location |

##### Response

On success, returns a msgpack'd string letting the user know that the recording
was started and where it was started.

On error, returns one of the error codes below:

| Error | Description |
|-------|-------------|
| 1 | Name not provided |
| 2 | Element name not provided |
| 3 | Stream not provided |
| 4 | Name already in use |
| 5 | `perm` true but `/recordings` not mounted in system |

#### `stop`: Stop Recording

> <button class="copy-button" onclick='copyText(this, "command record stop \"example\"")'>Copy</button> Atom CLI example

```shell_session
> command record stop "example"
{
  "data": "Success",
  "err_code": 0,
  "err_str": ""
}
```
##### Request

The request for this API is simply a msgpack'd string with the active
recording name to stop

##### Response

On success, returns a msgpack'd string letting the user know that the recording
was stopped

On error, returns one of the error codes below:

| Error | Description |
|-------|-------------|
| 1 | Recording not valid. Command must be for a valid, active recording |

#### `wait`: Wait for recording to finish

> <button class="copy-button" onclick='copyText(this, "command record wait \"example\"")'>Copy</button> Atom CLI example

```shell_session
> command record wait "example"
{
  "data": "Returned after 22.64138627052307 seconds",
  "err_code": 0,
  "err_str": ""
}
```
##### Request

The request for this API is simply a msgpack'd string with the active
recording which we'd like to wait for completion.

##### Response

On success, returns a msgpack'd string letting the user know that the recording
is now done along with how long we spent waiting for it.

On error, returns one of the error codes below:

| Error | Description |
|-------|-------------|
| 1 | Recording not valid. Command must be for a valid, active recording |

#### `list`: List all recordings

> <button class="copy-button" onclick='copyText(this, "command record list")'>Copy</button> Atom CLI example

```shell_session
> command record list
{
  "data": [
    "example"
  ],
  "err_code": 0,
  "err_str": ""
}
```
##### Request

None.

##### Response

A msgpack'd list of recording names which are present in the system, both
in the temporary and permanent filesystem locations.

#### `get`: Get Recording Data

> <button class="copy-button" onclick='copyText(this, "command record get {\"name\":\"example\", \"msgpack\":true, \"start\": 0, \"stop\":0}")'>Copy</button> Atom CLI example

```shell_session
> command record get {"name":"example", "msgpack":true, "start": 0, "stop":0}
{
  "data": [
    [
      "1553901473204-0",
      {
        "tan": -1.1766610378013764,
        "sin": 0.7619910470709031,
        "cos": -0.647587557156396
      }
    ]
  ],
  "err_code": 0,
  "err_str": ""
}

```

##### Request

The get recording request takes a msgpack'd JSON object with the following
fields:

| Key | Required | Default | Description |
|-----|----------|---------|-------------|
| `name` | yes | | Name of the recording. This will create a recording file named `name.atomrec` |
| `msgpack` | no | false | Whether or not to use `msgpack` to unpack entry values before returning them. Consult the documentation of the stream producing the values to determine if this is necessary. |
| `start` | no | 0 | Start entry index. The get request will return all entries in the range [start, stop], inclusive |
| `stop` | no | -1 | End entry index. The get request will return all entries in the range [start, stop], inclusive |

##### Response

A msgpack'd list of entries. Each entry is a tuple with the following values

| Index | Description |
|-------|-------------|
| 0 | Redis ID of the entry in the stream |
| 1 | `key:value` map of data from the stream for the entry |

On error, returns one of the error codes below:

| Error | Description |
|-------|-------------|
| 1 | Name not provided |
| 2 | Failed to open recording file |
| 3 | Recording doesn't exist |

#### `plot`: Plot recording data

> <button class="copy-button" onclick='copyText(this, "command record plot {\"name\":\"example\", \"msgpack\":true, \"plots\":[ { \"data\": [[ \"x\", [\"sin\"], \"value\" ]] } ] }")'>Copy</button> Plots sin(x) from example recording

```shell_session
> command record plot { "name":"example", "msgpack":true, "plots":[ { "data": [[ "x", ["sin"], "value" ]] } ] }
```

> <button class="copy-button" onclick='copyText(this, "command record plot { \"name\":\"example\", \"msgpack\":true, \"plots\":[ { \"data\": [[ \"x\", [\"sin\"], \"value\" ]], \"title\": \"Sin(x)\", \"x_label\": \"time (ms)\", \"y_label\": \"sin(x)\", \"legend\": false } ] }")'>Copy</button> Plots sin(x) from example recording, with title and access labels. Removes the legend.

```shell_session
> command record plot { "name":"example", "msgpack":true, "plots":[ { "data": [[ "x", ["sin"], "value" ]], "title": "Sin(x)", "x_label": "time (ms)", "y_label": "sin(x)", "legend": false } ] }
```

> <button class="copy-button" onclick='copyText(this, "command record plot {\"name\":\"example\", \"msgpack\":true, \"plots\":[ { \"data\": [[ \"x\", [\"sin\", \"cos\"], \"value\" ]] } ] }")'>Copy</button> Plots sin(x) and cos(x) from example recording on a single plot

```shell_session
> command record plot { "name":"example", "msgpack":true, "plots":[ { "data": [[ "x", ["sin", "cos"], "value" ]] } ] }
```

> <button class="copy-button" onclick='copyText(this, "command record plot {\"name\":\"example\", \"msgpack\":true, \"plots\":[ { \"data\": [[ \"x\", [\"sin\", \"cos\"],  \"value\" ], [\"max(-10, min(x, 10))\", [\"tan\"], \"value\"]] } ] } ")'>Copy</button> Plots sin(x), cos(x) and tan(x) from example recording on a single plot. Bounds tan(x) using a python lambda between -10 and 10

```shell_session
> command record plot {"name":"example", "msgpack":true, "plots":[ { "data": [[ "x", ["sin", "cos"],  "value" ], ["max(-10, min(x, 10))", ["tan"], "value"]] } ] }
```

> <button class="copy-button" onclick='copyText(this, "command record plot { \"name\": \"example\", \"msgpack\":true, \"plots\":[ { \"data\": [[ \"x\", [\"sin\"],  \"value\" ]] }, { \"data\": [[ \"x\", [\"cos\"],  \"value\" ]] }, { \"data\": [[ \"max(-10, min(x, 10))\", [\"tan\"],  \"value\" ]] } ] }")'>Copy</button> Plots sin(x), cos(x) and tan(x) from example recording on multiple plots. Bounds tan(x) using a python lambda between -10 and 10

```shell_session
> command record plot { "name": "example", "msgpack":true, "plots":[ { "data": [[ "x", ["sin"],  "value" ]] }, { "data": [[ "x", ["cos"],  "value" ]] }, { "data": [[ "max(-10, min(x, 10))", ["tan"],  "value" ]] } ] }
```

> <button class="copy-button" onclick='copyText(this, "command record plot { \"name\" : \"example\", \"msgpack\":true, \"show\": false, \"save\": true, \"perm\" : true,  \"plots\":[ { \"data\": [[ \"x\", [\"sin\", \"cos\"],  \"value\" ], [\"max(-10, min(x, 10))\", [\"tan\"], \"value\"]] } ] } ")'>Copy</button> Plots sin(x), cos(x) and tan(x) from example recording on a single plot. Bounds tan(x) using a python lambda between -10 and 10. Saves the plot as a png and doesn't show it to the user.

```shell_session
> command record plot {"name":"example", "msgpack":true, "show": false, "save": true, "perm" : true,  "plots":[ { "data": [[ "x", ["sin", "cos"],  "value" ], ["max(-10, min(x, 10))", ["tan"], "value"]] } ] }
```

##### Request

The plot recording request takes a msgpack'd JSON object with the following
fields:

| Key | Required | Default | Description |
|-----|----------|---------|-------------|
| `name` | yes | | Name of the recording. This will create a recording file named `name.atomrec` |
| `plots` | yes | | List of plots to make, where each item in the list is a *plot object* (see below) |
| `msgpack` | no | false | Whether or not to use `msgpack` to unpack entry values before returning them. Consult the documentation of the stream producing the values to determine if this is necessary. |
| `start` | no | 0 | Start entry index. The plot request will plot all entries in the range [start, stop], inclusive |
| `stop` | no | -1 | End entry index. The plot request will plot all entries in the range [start, stop], inclusive |
| `show` | no | true | If `true`, will show each plot and allow the user to interact with them. The API call won't return until all plots are closed |
| `save` | no | false | If `true`, will save a `.png` of each plot |
| `perm` | no | false | If `true`, store plots in permanent filesystem location, else in temporary filesystem location. |
| `x` | no | redis timestamp | A string intended to be the pythonic completion of `lambda entry: ` which will be passed the entry key:value map for each entry in the recording and is expected to return an x-value for the entry to be plotted against. This allows us to use something other than the redis timestamp for plotting x-values which is particularly useful when your data packets contain their own timestamps which are more accurate than the one auto-generated by redis |

###### `plot` object

The core of the `plot` request is the list of `plot` objects specified in the `plots` key. Each `plot` object is in itself a msgpack'd JSON object with the following fields:

| Key | Required | Default | Description |
|-----|----------|---------|-------------|
| `data` | yes | | A list of tuples with either 2 or 3 values describing which keys to plot and how to interpret their data |
| `title` | no | something reasonable | Title to use for the plot |
| `x_label` | no | something reasonable | X label to use for the plot |
| `y_label` | no | something reasobable | Y label to use for the plot |
| `legend` | no | true | If `true`, will show the legend on the plot, else will not |

The `data` object, as mentioned above, is a list of 2 or 3 valued tuples describing the data lines to be put on the plot. Its contents are as follows:

| Index | Required | Description |
|-------|----------|-------------|
| 0 | yes | A string intended to be the pythonic completion of `lambda x: ` which, for each key in the keys list for this data entry (index 1), will be passed the data from the key |
| 1 | yes | A list of keys to be used. For each entry in the recording, for each key in this list, the lambda from index 0 will be applied on the data to create the data point to be plotted |
| 2 | no | Optional label to be used for the data in the plot. If not passed a reasonable default will be generated |

Putting this all together, an example plots object for data recorded from the waveform
serialized stream could look like:

```
"plots": [
    {
        "data": [
            ["x", ["sin", "cos"], "value"],
        ],
        "title": "Some Title",
        "y_label": "Some Y Label",
        "x_label": "Some X Label",
        "legend": true,
    },
    {
        "data": [
            ["max(-10, min(x, 10))", ["tan"], "value"],
        ],
        ...
    }
]
```

With this object we'll be generating two separate plots.

On the first plot we'll have two lines, one for `sin` and one for `cos` where we'll
be graphing the raw data, `x`, from each entry. If we look at the waveform's `serialized` stream documentation we see that the `serialized` stream produces 3 keys: `sin`, `cos` and `tan`.

On the second plot we'll have just one line, the tan(x) value, though we run the data through a python lambda function to bound it in [-10, 10].

###### Lambdas

Lambdas in Python are simple one-line functions. See [the Python docs](https://docs.python.org/3/tutorial/controlflow.html#lambda-expressions) for more detail.

##### Response

A msgpack'd string with the success of the plotting function

On error, returns one of the error codes below:

| Error | Description |
|-------|-------------|
| 1 | Name not provided |
| 2 | Failed to open recording file |
| 3 | Recording doesn't exist |
| 4 | Recoding has 0 entries |
| 5 | `plots` not provided |
| 6 | Unable to process lambda for x values. `x` was specified, but the string provided wasn't able to be combined with `lambda entry: ` to create a valid lambda |
| 7 | A `plot` object doesn't have a `data` field |
| 8 | A tuple from the `data` list of a `plot` object is the wrong length. Must be 2 or 3 values in size |
| 9 | A lambda from a tuple in a `data` list wasn't able to be combined with `lambda x: ` to create a valid lambda |
| 10 | A key from the key list of a tuple in a `data` list doesn't exist in the recording |

#### `csv`: Convert recording to CSV file

> <button class="copy-button" onclick='copyText(this, "command record csv {\"name\":\"example\", \"msgpack\":true, \"perm\":true} ")'>Copy</button> Save CSV in permanent location using msgpack on values

```shell_session
> command record csv {"name":"example", "msgpack":true, "perm":true}
```

> <button class="copy-button" onclick='copyText(this, "command record csv {\"name\":\"example\", \"msgpack\":true, \"perm\":true, \"desc\":\"test\"}")'>Copy</button> Add description to filename

```shell_session
> command record csv {"name":"example", "msgpack":true, "perm":true, "desc":"test"}
```

> <button class="copy-button" onclick='copyText(this, "command record csv { \"name\" :\"example\", \"msgpack\":true, \"perm\":true, \"desc\": \"asin\", \"x\":\"__import__(\\\"math\\\").asin(entry[\\\"sin\\\"])\"}")'>Copy</button> Add lambda for column 0


```shell_session
> command record csv {"name":"example", "msgpack":true, "perm":true, "desc": "asin", "x":"__import__(\"math\").asin(entry[\"sin\"])"}
```

> <button class="copy-button" onclick='copyText(this, "command record csv { \"name\" :\"example\", \"msgpack\":true, \"perm\":true, \"desc\": \"multiplied\", \"lambdas\": {\"sin\":\"x * 10\", \"cos\": \"x * 5\"}}")'>Copy</button> Multiply scale by 10x on all data

```shell_session
> command record csv {"name":"example", "msgpack":true, "perm":true, "desc": "multiplied", "lambdas": {"sin":"x * 10", "cos": "x * 5"}}
```

##### Request

The `csv` request takes a recording name and will create **one csv file per key** in the recording according to the passed parameters.

| Key | Required | Default | Description |
|-----|----------|---------|-------------|
| `name` | yes | | Name of the recording. This will create a recording file named `name.atomrec` |
| `msgpack` | no | false | Whether or not to use `msgpack` to unpack entry values before returning them. Consult the documentation of the stream producing the values to determine if this is necessary. |
| `lambdas` | no | | Multi-typed, can be string or dictionary. If dictionary, `key:lambda` values to convert entry data into an iterable object that can then be written to the CSV. If a lambda is not specified for a key, will try to iterate over `entry[key]` and write values to columns. Intended to be the pythonic completion of `lambda x: ` . If string, same as above except same lambda is applied to all keys |
| `x` | no | redis timestamp | A string intended to be the pythonic completion of `lambda entry: ` which will be passed the entry key:value map for each entry in the recording and is expected to return an x-value for the entry for column 0 of the CSV. This allows us to use something other than the redis timestamp forcolumn 0 which is particularly useful when your data packets contain their own timestamps which are more accurate than the one auto-generated by redis |
| `desc` | no | | Optional string. If specified, will tack this string onto the filename of the `.csv` files generated so that they're not overwritten |
| `perm` | no | false | If `true`, store csv in permanent filesystem location, else in temporary filesystem location. |
| `start` | no | 0 | Start entry index. The csv request will process all entries in the range [start, stop], inclusive |
| `stop` | no | -1 | End entry index. The csv request will process all entries in the range [start, stop], inclusive |

##### Response

A msgpack'd string indicating the success of the request

On error, returns one of the error codes below:

| Error | Description |
|-------|-------------|
| 1 | Name not provided |
| 2 | Failed to open recording file |
| 3 | Recording doesn't exist |
| 4 | Failed to open output CSV file |
| 5 | Unable to process lambda for x values. `x` was specified, but the string provided wasn't able to be combined with `lambda entry: ` to create a valid lambda |
| 6 | Unable to process lambda for a key. A lambda was specified, but the string provided wasn't able to be combined with `lambda x: ` to create a valid lambda |
| 7 | `lambdas` argument is not a string or dictionary |

### docker-compose configuration
```yaml
  record:
    image: elementaryrobotics/element-record
    volumes:
      - type: volume
        source: shared
        target: /shared
        volume:
          nocopy: true
      - ".:/recordings"
    depends_on:
      - "nucleus"
    environment:
      - "GRAPHICS=1"
```

A pretty standard `docker-compose` configuration, noting that we can
specify to use the in-container graphics through the `GRAPHICS=1` setting. The
main thing to be sure to do in here is to map some directory on your host
computer to `/recordings` in the container! This is where the permanent files
are stored, and if this isn't done then nothing will be able to be saved
permanently. All of the temporary filesystem commands will still work.


### Launch Options

<!-- Javascript to make the copy button work if we're not also in atom-doc. Uncomment this for debug -->
<!-- <script>
function copyText(x, str) {

  // Create an element with the text, copy it, then remove it
  const el = document.createElement('textarea');
  el.value = str;
  document.body.appendChild(el);
  el.select();
  document.execCommand('copy');
  document.body.removeChild(el);

  // Change the text in the button to note it's been copied
  x.innerHTML = "  ✓  ";
}
</script> -->
