"""
FAM parser.


(C) 2015 Jeroen F.J. Laros <J.F.J.Laros@lumc.nl>
"""


import argparse
import copy
import json
import os
import sys

import bin_parser
import yaml


#def _raw(data):
#    """
#    Return the input data in hexadecimal, grouped by bit.
#
#    :arg str data: Input data.
#
#    :return str: Hexadecimal representation of {data}.
#    """
#    raw_data = data.encode('hex')
#    return ' '.join([raw_data[x:x + 2] for x in range(0, len(raw_data), 2)])
#
#
#def _bit(data):
#    return '{:08b}'.format(ord(data))
#
#
#def _int(data):
#    """
#    Decode a little-endian encoded integer.
#
#    Decoding is done as follows:
#    - Reverse the order of the bits.
#    - Convert the bits to ordinals.
#    - Interpret the list of ordinals as digits in base 256.
#
#    :arg str data: Little-endian encoded integer.
#
#    :return int: Integer representation of {data}
#    """
#    return reduce(lambda x, y: x * 0x100 + y,
#        map(lambda x: ord(x), data[::-1]))
#
#
#def _colour(data):
#    return '0x{:06x}'.format(_int(data))
#
#
#def _block_write(string, block_size, stream=sys.stdout):
#    """
#    Write a string as a block of width {block_size}. This function is mainly
#    for debugging purposes.
#
#    :arg str string: String to be written as a block.
#    :arg int block_size: Width of the block.
#    :arg stream stream: Open writable handle.
#    """
#    for block in map(lambda x: string[x:x + block_size],
#            range(0, len(string), block_size)):
#        stream.write('% {}\n'.format(block))
#
#
#class FamParser(object):
#    """
#    FAM file parsing.
#    """
#    def __init__(self, input_handle, json_output=False, experimental=False,
#            debug=0, log=sys.stdout):
#        """
#        Constructor.
#
#        :arg stream input_handle: Open readable handle to a FAM file.
#        :arg bool json_output: Select JSON instead of YAML output.
#        :arg bool experimental: Enable experimental features.
#        :arg int debug: Debugging level.
#        :arg stream log: Debug stream to write to.
#        """
#        self.data = input_handle.read()
#        self.parsed = {}
#        self.cleaned = {}
#        self._internal = {}
#
#        self._json_output = json_output
#        self._debug = debug
#        self._experimental = experimental | bool(debug)
#        self._log = log
#
#        self._fields = yaml.load(open(
#            os.path.join(os.path.dirname(__file__), '../fields.yml')))
#        self._functions = {
#            'trim': self._trim,
#            'raw': _raw,
#            'int': _int,
#            'short': _int,
#            'date': self._date,
#            'colour': _colour
#        }
#
#        self._offset = 0
#        self._raw_byte_count = 0
#        self._relationship_keys = set([])
#
#        structure = yaml.load(open(
#            os.path.join(os.path.dirname(__file__), '../structure.yml')))
#        self._parse(structure, self.parsed)
#
#        self._cleanup()
#
#        if self._internal['eof_marker'] != self._fields['eof_marker']:
#            raise Exception('No EOF marker found.')
#
#
#    def _get_field(self, size=0):
#        """
#        Extract a field from {self.data} using either a fixed size, or a
#        delimiter. After reading, {self._offset} is set to the next field.
#
#        :arg int size: Size of fixed size field.
#
#        :return str: Content of the requested field.
#        """
#        if size:
#            field = self.data[self._offset:self._offset + size]
#            extracted = size
#        else:
#            field = self.data[self._offset:].split(
#                chr(self._fields['delimiters']['field']))[0]
#            extracted = len(field) + 1
#
#        if self._debug > 1:
#            self._log.write('0x{:06x}: '.format(self._offset))
#            if size:
#                self._log.write('{} ({})'.format(_raw(field), size))
#            else:
#                self._log.write('{}'.format(field))
#            if self._debug < 3:
#                self._log.write('\n')
#
#        self._offset += extracted
#        return field
#
#
#    def _trim(self, data):
#        return data.split(chr(self._fields['delimiters']['trim']))[0]
#
#
#    def _text(self, data, delimiters):
#        return '\n'.join(data.split(
#            chr(self._fields['delimiters'][delimiters][0]) +
#            chr(self._fields['delimiters'][delimiters][1])))
#
#
#    def _date(self, data):
#        """
#        Decode a date.
#
#        The date is encoded as an integer, representing the year followed by
#        the (zero padded) day of the year.
#
#        :arg str data: Binary encoded date.
#
#        :return str: Date in format '%Y%j', 'defined' or 'unknown'.
#        """
#        date_int = _int(data)
#
#        if date_int in self._fields['maps']['date']:
#            return self._fields['maps']['date'][date_int]
#        return str(date_int)
#
#
#    def _annotate(self, data, annotation):
#        """
#        Replace a value with its annotation.
#
#        :arg str data: Encoded data.
#        :arg dict annotation: Annotation of {data}.
#
#        :return str: Annotated representation of {data}.
#        """
#        index = ord(data)
#
#        if index in self._fields['maps'][annotation]:
#            return self._fields['maps'][annotation][index]
#        return '{:02x}'.format(index)
#
#
#    def _flags(self, data, annotation):
#        """
#        Explode a bitfield into flags.
#
#        :arg int data: Bit field.
#        :arg str annotation: Annotation of {data}.
#
#        :return dict: Dictionary of flags and their values.
#        """
#        bitfield = _int(data)
#        flags = {}
#
#        for flag in map(lambda x: 2 ** x, range(8)):
#            value = bool(flag & bitfield)
#
#            if flag not in self._fields['flags'][annotation]:
#                if value:
#                    flags['flags_{}_{:02x}'.format(annotation, flag)] = value
#            else:
#                flags[self._fields['flags'][annotation][flag]] = value
#
#        return flags
#
#
#    def _parse_raw(self, destination, size, key='raw'):
#        """
#        Stow unknown data away in a list.
#
#        This function is needed to skip data of which the function is unknown.
#        If `self._experimental` is set to `True`,  the data is placed in an
#        appropriate place. This is mainly for debugging purposes.
#
#        Ideally, this function will become obsolete (when we have finished the
#        reverse engineering completely).
#
#        :arg dict destination: Destination dictionary.
#        :arg int size: Bytes to be stowed away (see `_get_field`).
#        :arg str key: Name of the list to store the data in.
#        """
#        if self._experimental:
#            if not key in destination:
#                destination[key] = []
#            destination[key].append(_raw(self._get_field(size)))
#        else:
#            self._get_field(size)
#
#        self._raw_byte_count += size
#
#
#    def _parse(self, structure, dest):
#        """
#        Parse a FAM file.
#
#        :arg dict structure:
#        :arg dict dest:
#        """
#        for item in structure:
#            if 'structure' in item:
#                if self._debug > 2:
#                    self._log.write('-- {}\n'.format(item['name']))
#                if item['name'] not in dest:
#                    if set(['size', 'delimiter', 'count']) & set(item):
#                        dest[item['name']] = []
#                    else:
#                        dest[item['name']] = {}
#                if 'size' in item:
#                    for index in range(item['size']):
#                        d = {}
#                        self._parse(item['structure'], d)
#                        dest[item['name']].append(d)
#                elif 'count' in item:
#                    for index in range(self._internal[item['count']]):
#                        d = {}
#                        self._parse(item['structure'], d)
#                        dest[item['name']].append(d)
#                elif 'delimiter' in item:
#                    while (_int(self._get_field(1)) !=
#                            self._fields['delimiters'][item['delimiter']]):
#                        d = {}
#                        self._parse(item['structure'], d)
#                        dest[item['name']].append(d)
#                else:
#                    self._parse(item['structure'], dest[item['name']])
#            else:
#                d = dest
#                if 'internal' in item:
#                    d = self._internal
#
#                size = 0
#                if 'size' in item:
#                    size = item['size']
#
#                if 'type' in item:
#                    if item['type'] in ('int', 'short', 'date', 'colour'):
#                        size = self._fields['sizeof'][item['type']]
#
#                    if item['type'] == 'map':
#                        d[item['name']] = self._annotate(self._get_field(
#                            self._fields['sizeof']['map']), item['map'])
#                    elif item['type'] == 'flags':
#                        d.update(self._flags(self._get_field(
#                            self._fields['sizeof']['flags']), item['flags']))
#                    elif item['type'] == 'text':
#                        d[item['name']] = self._text(self._get_field(),
#                            item['split'])
#                    elif item['type'] == 'conditional':
#                        if d[item['condition']]:
#                            d[item['name']] = self._get_field(size)
#                    else:
#                        d[item['name']] = self._functions[item['type']](
#                            self._get_field(size))
#                else:
#                    if item['name']:
#                        d[item['name']] = self._get_field(size)
#                    else:
#                        self._parse_raw(d, size)
#            if self._debug > 2:
#                self._log.write(' --> {}\n'.format(item['name']))
#
#
#    def _cleanup(self):
#        """
#        """
#        self.cleaned = copy.deepcopy(self.parsed)
#        groups = yaml.load(open(
#            os.path.join(os.path.dirname(__file__), '../groups.yml')))
#
#        for group in groups:
#            self.cleaned[group] = {}
#
#            for item in groups[group]:
#                self.cleaned[group][item] = self.cleaned.pop(item)
#
#        self.cleaned['family']['relationships'] = []
#        for member in self.cleaned['family']['members']:
#            for spouse in member['spouses']:
#                key = tuple(sorted((member['id'], spouse['id'])))
#
#                if key not in self._relationship_keys:
#                    relationship = spouse.copy()
#                    relationship['members'] = list(key)
#                    relationship.pop('id')
#
#                    self.cleaned['family']['relationships'].append(
#                        relationship)
#                    self._relationship_keys.add(key)
#            member.pop('spouses')
#
#        #self.cleaned['metadata'] = {}
#        #for item in self.cleaned:
#        #    if type(item) not in (list, dict):
#        #        self.cleaned['metadata']['item'] = self.cleaned.pop(item)
#
#
#    def write(self, output_handle):
#        """
#        Write the parsed FAM file to a stream.
#
#        :arg stream output_handle: Open writable handle.
#        """
#        if self._debug > 1:
#            output_handle.write('\n\n')
#
#        if self._json_output == True:
#            if self._debug:
#                output_handle.write('--- JSON DUMP ---\n\n')
#            output_handle.write(json.dumps(self.cleaned, indent=4,
#                separators=(',', ': ')))
#            output_handle.write('\n')
#        else:
#            if self._debug:
#                output_handle.write('--- YAML DUMP ---\n\n')
#            yaml.dump(self.cleaned, output_handle, width=76,
#                default_flow_style=False)
#
#        if self._debug:
#            output_handle.write('\n\n--- INTERNAL VARIABLES ---\n\n')
#            yaml.dump(self._internal, output_handle, width=76,
#                default_flow_style=False)
#
#            data_length = len(self.data)
#            parsed = data_length - self._raw_byte_count
#
#            output_handle.write('\n\n--- DEBUG INFO ---\n\n')
#            output_handle.write('Reached byte {} out of {}.\n'.format(
#                self._offset, data_length))
#            output_handle.write('{} bytes parsed ({:d}%)\n'.format(
#                parsed, parsed * 100 // len(self.data)))
#
#
def fam_parser(input_handle, output_handle, json_output=False,
        experimental=False, debug=0):
    """
    Main entry point.

    :arg stream input_handle: Open readable handle to a FAM file.
    :arg stream output_handle: Open writable handle.
    :arg bool json_output: Select JSON instead of YAML output.
    :arg bool experimental: Enable experimental features.
    :arg int debug: Debugging level.
    """
    #parser = FamParser(input_handle, json_output, experimental, debug)
    parser = bin_parser.BinParser(input_handle,
        open(os.path.join(os.path.dirname(__file__), '../structure.yml')),
        open(os.path.join(os.path.dirname(__file__), '../types.yml')),
        experimental=experimental, debug=debug)
    parser.write(output_handle)


def main():
    """
    Command line argument parsing.
    """
    usage = __doc__.split('\n\n\n')
    parser = argparse.ArgumentParser(description=usage[0], epilog=usage[1],
        formatter_class=argparse.RawDescriptionHelpFormatter)

    parser.add_argument('input_handle', type=argparse.FileType('r'),
        help='input file in FAM format')
    parser.add_argument('output_handle', type=argparse.FileType('w'),
        help='output file')
    parser.add_argument('-d', dest='debug', type=int, help='debugging level')
    parser.add_argument('-e', dest='experimental', action='store_true',
        help='enable experimental features')
    parser.add_argument('-j', dest='json_output', action='store_true',
        help='use JSON output instead of YAML')

    try:
        arguments = parser.parse_args()
    except IOError as error:
        parser.error(error)

    try:
        fam_parser(**dict((k, v) for k, v in vars(arguments).items()
            if k not in ('func', 'subcommand')))
    except ValueError as error:
        parser.error(error)


if __name__ == '__main__':
    main()
