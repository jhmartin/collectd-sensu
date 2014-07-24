"""Collectd to Sensu OutputWriter"""
# Copyright 2014 Jason Martin
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#
# Based heavily on Collectd-Librato

import collectd
import json
import time
import math
import re
import socket
from string import maketrans
from copy import copy

# NOTE: This version is grepped from the Makefile, so don't change the
# format of this line.
VERSION = "0.0.1"

CONFIG = { 'sensuhost' : 'localhost',
           'port' : 3030,
           'handler' : 'graphite',
           'types_db' : '/usr/share/collectd/types.db',
           'metric_prefix' : socket.gethostname(),
           'metric_separator' : '.',
           'source' : None,
           'flush_interval_secs' : 30,
           'flush_max_measurements' : 600,
           'flush_timeout_secs' : 15,
           'lower_case' : False,
           'single_value_names' : False
           }
PLUGIN_NAME = 'Collectd-Sensu.py'
TYPES = {}

def str_to_num(in_string):
    """
    Convert type limits from strings to floats for arithmetic.
    """

    return float(in_string)

def get_time():
    """
    Return the current time as epoch seconds.
    """

    return int(time.mktime(time.localtime()))

def sanitize_field(field):
    """
    Santize Metric Fields: delete paranthesis and split on periods
    """
    field = field.strip()

    # convert spaces to underscores
    trans = maketrans(' ', '_')

    # Strip ()
    field = field.translate(trans, '()')

    # Split based on periods
    return field.split(".")

#
# Parse the types.db(5) file to determine metric types.
#
def sensu_parse_types_file(path):
    """Parse the given collectd.types file"""

    types_file = open(path, 'r')

    for line in types_file:
        fields = line.split()
        if len(fields) < 2:
            continue

        type_name = fields[0]

        if type_name[0] == '#':
            continue

        collectd_type_value = []
        for datasource in fields[1:]:
            datasource = datasource.rstrip(',')
            datasource_fields = datasource.split(':')

            if len(datasource_fields) != 4:
                collectd.warning('%s: cannot parse data source ' \
                                 '%s on type %s' %
                                 (PLUGIN_NAME, datasource, type_name))
                continue

            collectd_type_value.append(datasource_fields)

        TYPES[type_name] = collectd_type_value

    types_file.close()

def sensu_config(passed_config):
    """Handle the collectd configuration for Sensu"""
    #global CONFIG

    for child in passed_config.children:
        val = child.values[0]

        if child.key == 'MetricPrefix':
            CONFIG['metric_prefix'] = val
        elif child.key == 'SensuHost':
            CONFIG['sensuhost'] = val
        elif child.key == 'Handler':
            CONFIG['handler'] = val
        elif child.key == 'Port':
            CONFIG['port'] = int(val)
        elif child.key == 'TypesDB':
            CONFIG['types_db'] = val
        elif child.key == 'MetricSeparator':
            CONFIG['metric_separator'] = val
        elif child.key == 'LowercaseMetricNames':
            CONFIG['lower_case'] = True
        elif child.key == 'IncludeSingleValueNames':
            CONFIG['single_value_names'] = True
        elif child.key == 'FloorTimeSecs':
            CONFIG['floor_time_secs'] = int(val)
        elif child.key == 'Source':
            CONFIG['source'] = val
        elif child.key == 'IncludeRegex':
            CONFIG['include_regex'] = val.split(',') if val else []
        elif child.key == 'FlushIntervalSecs':
            try:
                CONFIG['flush_interval_secs'] = int(str_to_num(val))
            except:
                msg = '%s: Invalid value for FlushIntervalSecs: %s' % \
                          (PLUGIN_NAME, val)
                raise Exception(msg)

def sensu_flush_metrics(output):
    """
    Send a collection of values to Sensu.
    """

    body = json.dumps({ 'name': 'collectd', 
                        'type':'metric',
                        'handler':'graphite',
                        'output' : "\n".join(output),})

    sensusocket = socket.socket()

    try:
        sensusocket.connect((CONFIG['sensuhost'], CONFIG['port']))
        sensusocket.sendall(body)
        sensusocket.close()
    except socket.error, (value, message):
        #Send failed
        collectd.warning('Sensu Send failed: ' 
                          + message + ', Err#' + str(value))
        if sensusocket:
            sensusocket.close() 
        return

def sensu_queue_measurements(output, data):
    """Add measurements to a queue and batch send to Sensu"""
    # Updating shared data structures
    #
    data['lock'].acquire()

    data['output'].extend(output)

    curr_time = get_time()
    last_flush = curr_time - data['last_flush_time']
    length = len(data['output'])

    if (last_flush < CONFIG['flush_interval_secs'] and \
           length < CONFIG['flush_max_measurements']) or \
           length == 0:
        data['lock'].release()
        return

    flush_output = data['output']
    data['output'] = []
    data['last_flush_time'] = curr_time
    data['lock'].release()

    sensu_flush_metrics(flush_output)

def sensu_write(collectd_values, data=None):
    """Write collectd data to sensu"""
    if collectd_values.type not in TYPES:
        collectd.warning('%s: do not know how to handle type %s. ' \
                         'do you have all your types.db files configured?' % \
                         (PLUGIN_NAME, collectd_values.type))
        return

    collectd_values_type = TYPES[collectd_values.type]

    if len(collectd_values_type) != len(collectd_values.values):
        collectd.warning('%s: differing number of values for type %s' % \
                         (PLUGIN_NAME, collectd_values.type))
        return

    name = []

    if len(CONFIG['metric_prefix']) > 0:
        name.append(CONFIG['metric_prefix'])

    name.append(collectd_values.plugin)
    if collectd_values.plugin_instance:
        name.extend(sanitize_field(collectd_values.plugin_instance))

    name.append(collectd_values.type)
    if collectd_values.type_instance:
        name.extend(sanitize_field(collectd_values.type_instance))

    output = []

    srcname = CONFIG['source']
    if srcname == None:
        srcname = collectd_values.host

    for i in range(len(collectd_values.values)):
        value = collectd_values.values[i]
        ds_name = collectd_values_type[i][0]
        ds_type = collectd_values_type[i][1]

        # We only support Gauges, Counters and Derives at this time
        if ds_type != 'GAUGE' and ds_type != 'COUNTER' and \
               ds_type != 'DERIVE':
            continue

        # Can value be None?
        if value is None:
            continue

        # Skip NaN values. These can be emitted from plugins like `tail`
        # when there are no matches.
        if math.isnan(value):
            continue

        # Skip counter values that are negative.
        if ds_type != 'GAUGE' and value < 0:
            continue

        name_tuple = copy(name)
        if len(collectd_values.values) > 1 or CONFIG['single_value_names']:
            name_tuple.append(ds_name)

        metric_name = CONFIG['metric_separator'].join(name_tuple)
        if CONFIG['lower_case']:
            metric_name = metric_name.lower()

        regexs = CONFIG.get('include_regex', [])
        matches = len(regexs) == 0
        for regex in regexs:
            if re.match(regex, metric_name):
                matches = True
                break

        if not matches:
            continue

        # Floor measure time?
        m_time = int(collectd_values.time)
        if CONFIG.has_key('floor_time_secs'):
            m_time /= CONFIG['floor_time_secs']
            m_time *= CONFIG['floor_time_secs']

        measurement = "%s\t%d\t%d" % (metric_name, value, m_time)
        output.append(measurement)

    sensu_queue_measurements(output, data)

def sensu_init():
    """Prepare to send data to Sensu"""
    import threading

    try:
        sensu_parse_types_file(CONFIG['types_db'])
    except:
        msg = '%s: ERROR: Unable to open TypesDB file: %s.' % \
              (PLUGIN_NAME, CONFIG['types_db'])
        raise Exception(msg)

    data_init = {
        'lock' : threading.Lock(),
        'last_flush_time' : get_time(),
        'output' : [],
        }

    collectd.register_write(sensu_write, data = data_init)

collectd.register_config(sensu_config)
collectd.register_init(sensu_init)
