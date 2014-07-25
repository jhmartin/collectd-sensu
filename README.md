# Introduction
[![Code Health](https://landscape.io/github/jhmartin/collectd-sensu/master/landscape.png)](https://landscape.io/github/jhmartin/collectd-sensu/master)
collectd-sensu is a [collectd](http://www.collectd.org/) plugin that
publishes collectd values to [Sensu](https://sensuapp.org) using the Event Data API to Sensu Client.

Collectd-librato was largely influenced by
[collectd-librato](https://github.com/librato/collectd-librato).

# Requirements

* Collectd versions 4.9.5, 4.10.3, and 5.0.0 (or later). Earlier
  versions of 4.9.x and 4.10.x may require a patch to fix the Python
  plugin in collectd (See below).
* Python 2.6 or later.
* A Sensu Client installation.

# Installation

If you have a `/etc/collectd5.conf` file it should probably contain something like the following:
```
BaseDir     "/var/lib/collectd5"
PIDFile     "/var/run/collectd5.pid"
TypesDB     "/usr/share/collectd5/types.db"
LoadPlugin syslog
LoadPlugin cpu
LoadPlugin interface
LoadPlugin load
LoadPlugin memory
<LoadPlugin "python">
  Globals true
</LoadPlugin>
<Plugin "python">
  ModulePath "/usr/lib64/collectd/python"
  Import "collectd_sensu"
  Interactive false
</Plugin>

```

The plugin will connect to the Sensu client on localhost tcp port 3030.

## From Source

Installation from source is provided by the Makefile included in the
project.

Simply clone this repository and run make install as root:

```
$ git clone git://github.com/jhmartin/collectd-sensu.git
$ cd collectd-sensu
$ sudo make install
Installed collected-sensu plugin, add this
to your collectd configuration to load this plugin:

    <LoadPlugin "python">
        Globals true
    </LoadPlugin>

    <Plugin "python">
        # collectd-sensu.py is at /opt/collectd-sensu-0.0.1/lib/collectd-sensu.py
        ModulePath "/opt/collectd-sensu-0.0.1/lib"
        Interactive false

        Import "collectd-sensu"
    </Plugin>
```

The output above includes a sample configuration file for the
plugin. Simply add this to `/etc/collectd.conf` or drop in the
configuration directory as `/etc/collectd.d/sensu.conf` and restart
collectd. See the next section for an explanation of the plugin's
configuration variables.


# Configuration

The plugin does not require configuration and should work out-of-box.

To control the frequency (resolution) of metrics sent by collectd to
Sensu, you must update the collectd option
[`Interval`](http://collectd.org/wiki/index.php/Interval) specified
in the global *collectd.conf* file to the desired resolution in seconds.

The following parameters are available:

* `TypesDB` - file(s) defining your Collectd types. This should be the
  sames as your TypesDB global config parameters. This will default to
  the file `/usr/share/collectd/types.db`. **NOTE**: This plugin will
  not work if it can't find the types.db file.

* `LowercaseMetricNames` - If preset, all metric names will be converted
  to lower-case (default no lower-casing).

* `MetricPrefix` - If present, all metric names will contain this string
  prefix. Do not include a trailing period or separation character
  (see `MetricSeparator`). Set to the empty string to disable any
  prefix. Defaults to "collectd".

* `MetricSeparator` - String to separate the components of a metric name
  when combining the plugin name, type, and instance name. Defaults to
  a period (".").

* `IncludeSingleValueNames` - Normally, any metric type listed in
  `types.db` that only has a single value will not have the name of
  the value suffixed onto the metric name. For most single value
  metrics the name is simply a placeholder like "value" or "count", so
  adding it to the metric name does not add any particular value. If
  `IncludeSingleValueNames` is set however, these value names will be
  suffixed onto the metric name regardless.

* `Source` - By default the source name is taken from the configured
  collectd hostname. If you want to override the source name that is
  used with Sensu you can set the `Source` variable to a
  different source name.

* `IncludeRegex` - This option can be used to control the metrics that
  are sent to Sensu. It should be set to a comma-separated
  list of regular expression patterns to match metric names
  against. If a metric name does not match one of the regex's in this
  variable, it will not be sent to Sensu. By default, all
  metrics in collectd are sent to Sensu. For example, the
  following restricts the set of metrics to CPU and select df metrics:

  `IncludeRegex "collectd.cpu.*,collectd.df.df.dev.free,collectd.df.df.root.free"`

* `FloorTimeSecs` - Set the time interval (in seconds) to floor all
  measurement times to. This will ensure that the real-time samples on
  graphs will align on the time interval boundary across multiple
  collectd hosts. By default, measurement times are not floored and use
  the exact timestamp emitted from collectd. This value should be set
  to the same `Interval` defined in the main *collectd.conf*.

* `Handler` - The Sense handler to which the metrics will be passed. Defaults to "graphite".

* `SensuHost` - The Sense client host where metrics will be sent. Defaults to "localhost".

* `Port` - The Sense client port where metrics will be sent. Defaults to 3030.
## Example

The following is an example Collectd configuration for this plugin:

    <LoadPlugin "python">
        Globals true
    </LoadPlugin>

    <Plugin "python">
        # collectd-sensu.py is at /opt/collectd-sensu-0.0.1/lib/collectd-sensu.py
        ModulePath "/opt/collectd-sensu-0.0.1/lib"

        Import "collectd_sensu"
        Interactive false

        <Module "collectd_sensu">
            Port "3031"
        </Module>
    </Plugin>

## Supported Metrics

Collectd-Sensu currently supports the following collectd metric
types:

* GAUGE,COUNTER,DERIVE

Other metric types are currently ignored. 

# Operational Notes

This plugin uses a best-effort attempt to deliver metrics to Sensu
Metrics. If a flush fails to POST metrics to Sensu the flush
will not currently be retried, but instead dropped. In most cases this
should not happen, but if it does the plugin will continue to flush
metrics after the failure. So in the worst case there may appear a
short gap in your metric graphs.

The plugin needs to parse Collectd type files. If there was an error
parsing a specific type (look for log messages at Collectd startup
time), the plugin will fail to write values for this type. It will
simply skip over them and move on to the next value. It will write a log
message every time this happens so you can correct the problem.

The plugin needs to perform redundant parsing of the type files because
the Collectd Python API does not provide an interface to the types
information (unlike the Perl and Java plugin APIs). Hopefully this will
be addressed in a future version of Collectd.

# Contributing

If you would like to contribute a fix or feature to this plugin please
feel free to fork this repo, make your change and submit a pull
request!
