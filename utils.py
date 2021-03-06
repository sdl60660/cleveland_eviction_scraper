
import os
import json
import csv
from datetime import datetime
from collections import OrderedDict, Counter


# Comes from here: https://stackoverflow.com/questions/18857352/remove-very-last-character-in-file
# Using as utility for more efficient handling of JSON concatenation
def truncate_utf8_chars(filename, count, ignore_newlines=True):
    """
    Truncates last `count` characters of a text file encoded in UTF-8.
    :param filename: The path to the text file to read
    :param count: Number of UTF-8 characters to remove from the end of the file
    :param ignore_newlines: Set to true, if the newline character at the end of the file should be ignored
    """
    with open(filename, 'rb+') as f:
        last_char = None

        size = os.fstat(f.fileno()).st_size

        offset = 1
        chars = 0
        while offset <= size:
            f.seek(-offset, os.SEEK_END)
            b = ord(f.read(1))

            if ignore_newlines:
                if b == 0x0D or b == 0x0A:
                    offset += 1
                    continue

            if b & 0b10000000 == 0 or b & 0b11000000 == 0b11000000:
                # This is the first byte of a UTF8 character
                chars += 1
                if chars == count:
                    # When `count` number of characters have been found, move current position back
                    # with one byte (to include the byte just checked) and truncate the file
                    f.seek(-1, os.SEEK_CUR)
                    f.truncate()
                    return
            offset += 1


def prep_json_for_appending(filepath):
    if not os.path.exists(filepath):
        with open(filepath, 'r') as f:
            f.write('[')
    elif type(json.load(open(filepath, 'r'))) != list:
        raise TypeError('If JSON file already exists, it must be in array format')
    else:
        # Remove end bracket (']') from JSON file, so we can json.dumps append to the array and then close it later
        truncate_utf8_chars(filepath, 1)


def close_off_json(filepath):
    with open(filepath, 'a') as f:
        f.write(']')


def get_year_range(infile):
    if os.path.splitext(infile)[1] == '.json':
        with open(infile, 'r') as f:
            all_data = json.load(f)
    else: 
        with open(infile, 'r') as f:
            all_data = [x for x in csv.DictReader(f)]

    file_dates = sorted([datetime.strptime(x['File Date'], '%m/%d/%Y') for x in all_data])
    start_year = int(file_dates[0].year)
    end_year = int(file_dates[-1].year)
    
    return start_year, end_year

class OrderedCounter(Counter, OrderedDict):
    'Counter that remembers the order elements are first encountered'

    def __repr__(self):
        return '%s(%r)' % (self.__class__.__name__, OrderedDict(self))

    def __reduce__(self):
        return self.__class__, (OrderedDict(self),)