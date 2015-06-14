'use strict';

/*
FAM parser.

(C) 2015 Jeroen F.J. Laros <J.F.J.Laros@lumc.nl>
*/
// NOTE: All integers are probably 2 bytes.
// NOTE: Colours may be 4 bytes.

var yaml = require('js-yaml'),
    requireFile = require('require-file');

/*
Miscellaneous functions.
*/

function ord(character) {
  return character.charCodeAt(0);
}

function hex(value) {
  return value.toString(16);
}

/*
Pad a string with leading zeroes.

:arg any input: String to be padded.
:arg int length: Length of the resulting string.

:return str: Padded string.
*/
function pad(input, length) {
  var string = input.toString(),
      padding = '',
      index;

  for (index = 0; index < length - string.length; index++) {
    padding += '0';
  }
  return padding + string;
}

/*
Encode a string in hexadecimal.

:arg str data: Input string.

:return str: Hexadecimal representation of {data}.
*/
function convertToHex(data) {
  var result = '',
      index;

  for (index = 0; index < data.length; index++) {
    result += pad(hex(data.charCodeAt(index)), 2);
  }
  return result;
}

/*
Update a dictionary with the properties of another dictionary.

:arg dict target: Target dictionary.
:arg dict source: Source dictionary.
*/
function update(target, source) {
  var item;

  for (item in source) {
    target[item] = source[item];
  }
}

/*
Helper functions.
*/

function raw(data) {
  return convertToHex(data);
}

/*
Decode a little-endian encoded integer.

Decoding is done as follows:
- Reverse the order of the bits.
- Convert the bits to ordinals.
- Interpret the list of ordinals as digits in base 256.

:arg str data: Little-endian encoded integer.

:return int: Integer representation of {data}
*/
function integer(data) {
  var result = 0,
      index;

  for (index = data.length - 1; index >= 0; index--) {
    result = result * 0x100 + data.charCodeAt(index);
  }
  return result;
}

function colour(data) {
  return '0x' + pad(hex(integer(data)), 6);
}

/*
FAM file parsing.
*/
function FamParser(fileContent) {
  var data = fileContent,
      parsed = {},
      internal = {},
      fields = yaml.load(requireFile('../fields.yml')),
      functions = {
        'trim': trim,
        'raw': raw,
        'int': integer,
        'short': integer,
        'date': date,
        'colour': colour
      },
      offset = 0,
      relationshipKeys = {}; // Should be a set.

  /*
  Extract a field from {data} using either a fixed size, or a delimiter. After
  reading, {offset} is set to the next field.

  :arg int size: Size of fixed size field.
  :return str: Content of the requested field.
  */
  function getField(size) {
    var field,
        extracted;

    if (size) {
      field = data.slice(offset, offset + size);
      extracted = size;
    }
    else {
      field = data.slice(offset, -1).split(
        String.fromCharCode(fields.delimiters.field))[0];
      extracted = field.length + 1;
    }

    offset += extracted;
    return field;
  }

  function trim(data) {
    return data.split(String.fromCharCode(fields.delimiters.trim))[0];
  }

  function text(data, delimiters) {
    return data.split(
      String.fromCharCode(fields.delimiters[delimiters][0]) +
      String.fromCharCode(fields.delimiters[delimiters][1])).join('\n');
  }

  /*
  Decode a date.

  The date is encoded as an integer, representing the year followed by the
  (zero padded) day of the year.

  :arg str data: Binary encoded date.

  :return str: Date in format '%Y%j', 'defined' or 'unknown'.
  */
  function date(data) {
    var dateInt = integer(data);

    if (dateInt in fields.maps.date) {
      return fields.maps.date[dateInt];
    }
    return dateInt.toString();
  }

  /*
  Replace a value with its annotation.

  :arg str data: Encoded data.
  :arg dict annotation: Annotation of {data}.

  :return str: Annotated representation of {data}.
  */
  function annotate(data, annotation) {
    var index = ord(data);

    if (index in fields.maps[annotation]) {
      return fields.maps[annotation][index];
    }
    return convertToHex(data);
  }

  /*
  Explode a bitfield into flags.

  :arg int data: Bit field.
  :arg str annotation: Annotation of {data}.
  */
  function flags(data, annotation) {
    var bitfield = integer(data),
        destination = {},
        flag,
        value;

    for (flag = 0x01; flag < 0x100; flag <<= 1) {
      value = Boolean(flag & bitfield);

      if (!(flag in fields.flags[annotation])) {
        if (value) {
          destination['flags_' + annotation + '_' + pad(hex(flag), 2)] = value;
        }
      }
      else {
        destination[fields.flags[annotation][flag]] = value;
      }
    }
    return destination;
  }

  /*
  Parse a FAM file.

  :arg dict structure:
  :arg digt dest:
  */
  function parse(structure, dest) {
    var item,
        index,
        size,
        d;

    for (item in structure) {
      if (structure[item].structure) {
        if (!(structure[item].name in dest)) {
          if (structure[item].size || structure[item].delimiter ||
              structure[item].count) {
            dest[structure[item].name] = [];
          }
          else {
            dest[structure[item].name] = {};
          }
        }
        if (structure[item].size) {
          for (index = 0; index < structure[item].size; index++) {
            d = {};
            parse(structure[item].structure, d);
            dest[structure[item].name].push(d);
          }
        }
        else if (structure[item].count) {
          for (index = 0; index < internal[structure[item].count]; index++) {
            d = {};
            parse(structure[item].structure, d);
            dest[structure[item].name].push(d);
          }
        }
        else if (structure[item].delimiter) {
          while (integer(getField(1)) !=
              fields.delimiters[structure[item].delimiter]) {
            d = {};
            parse(structure[item].structure, d);
            dest[structure[item].name].push(d);
          }
        }
        else {
          parse(structure[item].structure, dest[structure[item].name]);
        }
      }
      else {
        d = dest;
        if (structure[item].internal) {
          d = internal;
        }

        size = 0
        if (structure[item].size) {
          size = structure[item].size;
        }

        if (structure[item].type) {
          if (['int', 'short', 'date', 'colour'].indexOf(
              structure[item].type) !== -1) {
            size = fields.sizeof[structure[item].type];
          }
          if (structure[item].type == 'map') {
            d[structure[item].name] = annotate(getField(fields.sizeof.map),
              structure[item].map);
          }
          else if (structure[item].type == 'flags') {
            update(d, flags(getField(fields.sizeof.flags),
              structure[item].flags));
          }
          else if (structure[item].type == 'text') {
            d[structure[item].name] = text(getField(),
              structure[item]['split']);
          }
          else if (structure[item].type == 'conditional') {
            if (d[structure[item]['condition']]) {
              d[structure[item].name] = getField(size);
            }
          }
          else {
            d[structure[item].name] = functions[structure[item].type](
              getField(size));
         }
        }
        else {
          if (structure[item].name) {
            d[structure[item].name] = getField(size);
          }
          else {
            getField(size);
          }
        }
      }
    }
  }

  /*
  Write the parsed FAM file to the console.
  */
  this.dump = function() {
    console.log('--- YAML DUMP ---');
    console.log(yaml.dump(parsed));
    console.log('\n--- DEBUG INFO ---\n');
    console.log(yaml.dump(internal));
  };

  /*
  Get parsed object.
  */
  this.getParsed = function() {
    return parsed;
  };

  parse(yaml.load(requireFile('../structure.yml')), parsed);
}

module.exports = FamParser;
