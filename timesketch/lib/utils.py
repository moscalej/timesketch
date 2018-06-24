# Copyright 2015 Google Inc. All rights reserved.
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
"""Common functions and utilities."""

import colorsys
import csv
import datetime
import json
import random
import time

from dateutil import parser


def random_color():
    """Generates a random color.

    Returns:
        Color as string in HEX
    """
    hue = random.random()
    golden_ratio_conjugate = (1 + 5**0.5) / 2
    hue += golden_ratio_conjugate
    hue %= 1
    rgb = tuple(int(i * 256) for i in colorsys.hsv_to_rgb(hue, 0.5, 0.95))
    return u'{0:02X}{1:02X}{2:02X}'.format(rgb[0], rgb[1], rgb[2])


def get_csv_dialect(csv_header):
    """Get CSV dialect format.

    Args:
        csv_header: List of CSV column names

    Returns:
        Name of the dialect if known, otherwise None
    """

    # Check if redline format
    redline_fields = {
        u'Alert', u'Tag', u'Timestamp', u'Field', u'Summary'}
    redline_intersection = set(
        redline_fields).intersection(set(csv_header))
    if len(redline_fields) == len(redline_intersection):
        return u'redline'

    # Check if Timesketch supported format
    timesketch_fields = {u'message', u'datetime', u'timestamp_desc'}
    timesketch_intersection = timesketch_fields.intersection(
        set(csv_header))
    if len(timesketch_fields) == len(timesketch_intersection):
        return u'timesketch'

    return None


def read_and_validate_csv(path, delimiter):
    """Generator for reading a CSV or TSV file.

    Args:
        path: Path to the file
        delimiter: character used as a field separator

    Returns:
        Generator of event rows

    Raises:
        RuntimeError is CSV format is unknown
    """
    with open(path, 'rb') as fh:
        reader = csv.DictReader(fh, delimiter=delimiter.decode('string_escape'))
        csv_header = reader.fieldnames
        csv_dialect = get_csv_dialect(csv_header)

        if u'redline' in csv_dialect:
            for row in reader:
                parsed_datetime = parser.parse(row[u'Timestamp'])
                timestamp = int(
                    time.mktime(parsed_datetime.timetuple())) * 1000000
                parsed_datetime_iso_format = parsed_datetime.isoformat()
                row = dict(
                    message=row[u'Summary'],
                    timestamp=timestamp,
                    datetime=parsed_datetime_iso_format,
                    timestamp_desc=row[u'Field'],
                    alert=row[u'Alert'],
                    tag=[row[u'Tag']]
                )
                yield row

        elif u'timesketch' in csv_dialect:
            for row in reader:
                if u'timestamp' not in csv_header and u'datetime' in csv_header:
                    try:
                        parsed_datetime = parser.parse(row[u'datetime'])
                        row[u'timestamp'] = int(
                            time.mktime(parsed_datetime.timetuple())) * 1000000
                    except ValueError:
                        continue
                yield row
        else:
            raise RuntimeError(u'Unknown CSV format')


def read_and_validate_jsonl(path, _):
    """Generator for reading a JSONL (json lines) file.

    Args:
        path: Path to the JSONL file
    """
    # Fields that must be present in each entry of the JSONL file.
    mandatory_fields = [u'message', u'datetime', u'timestamp_desc']
    with open(path, 'rb') as fh:
        lineno = 0
        for line in fh:
            lineno += 1
            try:
                linedict = json.loads(line)
                ld_keys = linedict.keys()
                if u'datetime' not in ld_keys and u'timestamp' in ld_keys:
                    epoch = int(str(linedict[u'timestamp'])[:10])
                    dt = datetime.datetime.fromtimestamp(epoch)
                    linedict[u'datetime'] = dt.isoformat()
                if u'timestamp' not in ld_keys and u'datetime' in ld_keys:
                    linedict[u'timestamp'] = parser.parse(linedict[u'datetime'])

                missing_fields = []
                for field in mandatory_fields:
                    if field not in linedict.keys():
                        missing_fields.append(field)
                if missing_fields:
                    raise RuntimeError(
                        u"Missing field(s) at line {0:n}: {1:s}"
                        .format(lineno, missing_fields))

                yield linedict

            except ValueError as e:
                raise RuntimeError(
                    u"Error parsing JSON at line {0:n}: {1:s}"
                    .format(lineno, e))


def get_validated_indices(indices, sketch_indices):
    """Exclude any deleted search index references.

    Args:
        indices: List of indices from the user
        sketch_indices: List of indices in the sketch

    Returns:
        Set of indices with those removed that is not in the sketch
    """
    exclude = set(indices) - set(sketch_indices)
    if exclude:
        indices = [index for index in indices if index not in exclude]
    return indices
