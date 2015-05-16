'use strict';

/*
FAM parser.

(C) 2015 Jeroen F.J. Laros <J.F.J.Laros@lumc.nl>
*/
// NOTE: All integers are probably 2 bytes.

var DESC_PREFIX = 'DESC_',
    EOF_MARKER = 'End of File',
    MAPS = {
      'PROBAND': {
        0x00: 'NOT_A_PROBAND',
        0x01: 'ABOVE_LEFT',
        0x02: 'ABOVE_RIGHT',
        0x03: 'BELOW_LEFT',
        0x04: 'BELOW_RIGHT',
        0x05: 'LEFT',
        0x06: 'RIGHT'
      },
      'SEX': {
        0x00: 'MALE',
        0x01: 'FEMALE',
        0x02: 'UNKNOWN'
      },
      'TWIN_STATUS': {
        0x00: 'NONE',
        0x01: 'MONOZYGOUS',
        0x02: 'DIZYGOUS',
        0x03: 'UNKNOWN',
        0x04: 'TRIPLET',
        0x05: 'QUADRUPLET',
        0x06: 'QUINTUPLET',
        0x07: 'SEXTUPLET'
      },
      'ANNOTATION_1': {
        0x00: 'NONE',
        0x01: 'P',
        0x02: 'SAB',
        0x03: 'TOP',
        0x04: 'SB',
        0x0b: 'BAR'
      },
      'ANNOTATION_2': {
        0x00: 'NONE',
        0x01: 'AFFECTED'
      }
    },
    FLAGS = {
      'INDIVIDUAL': {
        0x04: 'LOOP_BREAKPOINT',
        0x08: 'HIDE_INFO'
      },
      'RELATIONSHIP': {
        0x01: 'INFORMAL',
        0x02: 'CONSANGUINEOUS',
        0x04: 'SEPARATED',
        0x08: 'DIVORCED'
      }
    };

/*
Miscellaneous functions.
*/

function ord(character) {
  return character.charCodeAt(0);
}

function hex(value) {
  return value.toString(16)
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
Helper functions.
*/

function identity(data) {
  return data;
}

function trim(data) {
  return data.split(String.fromCharCode(0x00))[0];
}

function raw(data) {
  return convertToHex(data);
}

function bit(data) {
  return pad(ord(data).toString(2), 8);
}

function comment(data) {
  return data.split(String.fromCharCode(0x09) + String.fromCharCode(0x03));
}

function freetext(data) {
  return data.split(String.fromCharCode(0x0b) + String.fromCharCode(0x0b));
}

function description(data) {
  return DESC_PREFIX + pad(ord(data), 2)
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

/*
Decode a date.

The date is encoded as an integer, representing the year followed by the (zero
padded) day of the year.

:arg str data: Binary encoded date.

:return str: Date in format '%Y%j', 'DEFINED' or 'UNKNOWN'.
*/
function date(data) {
  var dateInt = integer(data);

  if (dateInt) {
    if (dateInt === 0xffffff) {
      return 'DEFINED';
    }
    return dateInt.toString();
  }
  return 'UNKNOWN';
}

/*
Replace a value with its annotation.

:arg str data: Encoded data.
:arg dict annotation: Annotation of {data}.

:return str: Annotated representation of {data}.
*/
function annotate(data, annotation) {
  var index = ord(data);

  if (index in MAPS[annotation]) {
    return MAPS[annotation][index];
  }
  return convertToHex(data);
}

/*
Explode a bitfield into flags.

:arg dict destination: Destination dictionary.
:arg int bitfield: Bit field.
:arg str annotation: Annotation of {bitfield}.
*/
function flags(destination, bitfield, annotation) {
  var flag,
      value;

  for (flag = 0x01; flag < 0x100; flag <<= 1) {
    value = Boolean(flag & bitfield);

    if (!(flag in FLAGS[annotation])) {
      if (value) {
        destination['FLAGS_' + annotation + '_' + pad(hex(flag), 2)] = value;
      }
    }
    else {
      destination[FLAGS[annotation][flag]] = value;
    }
  }
}

/*
FAM file parsing.
*/
function FamParser(fileContent) {
  var data = fileContent,
      offset = 0,
      delimiter = 0x0d,
      metadata = {},
      members = [],
      relationships = {},
      texts = [],
      crossovers = [];

  /*
  Extract a field from {data} using either a fixed size, or a delimiter. After
  reading, {offset} is set to the next field.

  :arg object destination: Destination object.
  :arg int size: Size of fixed size field.
  :arg str name: Field name.
  :arg function func: Conversion function.
  */
  function setField(destination, size, name, func) {
    var field,
        extracted;

    if (size) {
      field = data.slice(offset, offset + size);
      extracted = size;
    }
    else {
      field = data.slice(offset, -1).split(String.fromCharCode(delimiter))[0];
      extracted = field.length + 1;
    }

    if (name !== undefined) {
      if (func !== undefined) {
        if (func === annotate) {
          destination[name] = annotate(field, name);
        }
        else {
          destination[name] = func(field);
        }
      }
      else {
        destination[name] = identity(field);
      }
    }
    offset += extracted;
  }

  /*
  Extract header information.
  */
  function parseHeader() {
    setField(metadata, 26, 'SOURCE', trim);
    setField(metadata, 0, 'FAMILY_NAME');
    setField(metadata, 0, 'FAMILY_ID');
    setField(metadata, 0, 'AUTHOR');
    setField(metadata, 2, 'LAST_ID', integer);
    setField(metadata, 2, 'LAST_INTERNAL_ID', integer);
    setField(metadata, 42);
    setField(metadata, 0, 'COMMENT');
    setField(metadata, 3, 'DATE_CREATED', date);
    setField(metadata, 1);
    setField(metadata, 3, 'DATE_UPDATED', date);
    setField(metadata, 14);
    setField(metadata, 2, 'SELECTED_ID', integer);
    setField(metadata, 16);
  }

  /*
  Extract relationship information.

  :arg int personId: The partner in this relationship.
  */
  function parseRelationship(personId) {
    var relationship = {},
        relationFlags,
        key;

    relationship.MEMBER_1_ID = personId;
    setField(relationship, 2, 'MEMBER_2_ID', integer);
    setField(relationship, 1, 'RELATION_FLAGS', integer);
    setField(relationship, 0, 'RELATION_NAME');

    flags(relationship, relationship['RELATION_FLAGS'], 'RELATIONSHIP');

    key = [personId, relationship.MEMBER_2_ID].sort().toString();
    if (relationships[key] === undefined) {
      relationships[key] = relationship;
    }
  }

  /*
  Extract crossover information.

  :arg int personId: The person who has these crossovers.
  */
  function parseCrossover(personId) {
    var crossover = {},
        alleles = 0,
        events = 0,
        flag;

    crossover.ID = personId;
    while (alleles < 2) {
      flag = 'FLAG_' + pad(events, 2);

      setField(crossover, 1, flag, raw);
      if (crossover[flag] === '22') {
        setField(crossover, 9, 'ALLELE_' + pad(alleles, 2), raw);
        if (!alleles) {
          setField(crossover, 2, 'SPACER_' + pad(alleles, 2), raw);
        }
        alleles++;
      }
      else {
        setField(crossover, 11, 'CROSSOVER_' + pad(events, 2), raw);
      }
      events++;
    }

    crossovers.push(crossover);
  }

  /*
  Extract person information.
  */
  function parseMember() {
    var member = {},
        index;

    setField(member, 0, 'SURNAME');
    setField(member, 1);
    setField(member, 0, 'FORENAMES');
    setField(member, 1);
    setField(member, 0, 'MAIDEN_NAME');
    setField(member, 11);
    setField(member, 0, 'COMMENT', comment);
    setField(member, 3, 'DATE_OF_BIRTH', date);
    setField(member, 1);
    setField(member, 3, 'DATE_OF_DEATH', date);
    setField(member, 1);
    setField(member, 1, 'SEX', annotate);
    setField(member, 2, 'ID', integer);
    setField(member, 2, 'PEDIGREE_NUMBER', integer);
    setField(member, 2, 'MOTHER_ID', integer);
    setField(member, 2, 'FATHER_ID', integer);
    setField(member, 2, 'INTERNAL_ID', integer);
    setField(member, 1, 'NUMBER_OF_INDIVIDUALS', integer);
    setField(member, 1);
    setField(member, 0, 'AGE_GESTATION');
    setField(member, 0, 'INDIVIDUAL_ID');
    setField(member, 1, 'NUMBER_OF_SPOUSES', integer);
    setField(member, 1);

    for (index = 0; index < member.NUMBER_OF_SPOUSES; index++) {
      parseRelationship(member.ID);
    }

    setField(member, 2, 'TWIN_ID', integer);
    setField(member, 2);
    setField(member, 1, 'DESCRIPTION_1', description);
    setField(member, 1);
    setField(member, 1, 'INDIVIDUAL_FLAGS', integer);
    setField(member, 1, 'PROBAND', annotate);
    setField(member, 1, 'X_COORDINATE', integer);
    setField(member, 1);
    setField(member, 1, 'Y_COORDINATE', integer);
    setField(member, 1);
    setField(member, 1, 'ANNOTATION_1', annotate);
    setField(member, 1, 'TWIN_STATUS', annotate);
    setField(member, 3);

    parseCrossover(member.ID);

    setField(member, 1, 'ANNOTATION_2', annotate);
    setField(member, 180);
    setField(member, 1, 'DESCRIPTION_2', description);
    setField(member, 1);
    setField(member, 0, 'UNKNOWN_TEXT', identity);
    setField(member, 22);

    flags(member, member['INDIVIDUAL_FLAGS'], 'INDIVIDUAL');

    members.push(member);

    return member['ID'];
  }

  /*
  Extract information from a text field.
  */
  function parseText() {
    // TODO: X and Y coordinates have more digits.
    var text = {};

    setField(text, 0, 'TEXT', freetext);
    setField(text, 54);
    setField(text, 1, 'X_COORDINATE', integer);
    setField(text, 3);
    setField(text, 1, 'Y_COORDINATE', integer);
    setField(text, 7);

    texts.push(text)
   }

  /*
  Extract information from the footer.
  */
  function parseFooter() {
    var index;

    setField(metadata, 1, 'NUMBER_OF_UNKNOWN_DATA', integer);
    setField(metadata, 2);

    for (index = 0; index < metadata.NUMBER_OF_UNKNOWN_DATA; index++) {
      setField(metadata, 12, 'UNKNOWN_DATA_' + pad(index, 2), raw);
    }

    setField(metadata, 1, 'NUMBER_OF_CUSTOM_DESC', integer);
    setField(metadata, 1);

    for (index = 0; index < 23; index++) {
      setField(metadata, 0, DESC_PREFIX + pad(index, 2), identity);
    }

    for (index = 0; index < metadata.NUMBER_OF_CUSTOM_DESC; index++) {
      setField(metadata, 0, 'CUSTOM_DESC_' + pad(index, 2), identity);
      setField(metadata, 0, 'CUSTOM_CHAR_' + pad(index, 2), identity);
    }

    setField(metadata, 14);
    setField(metadata, 2, 'ZOOM', integer);
    setField(metadata, 4, 'UNKNOWN_1', raw); // Zoom.
    setField(metadata, 4, 'UNKNOWN_2', raw); // Zoom.
    setField(metadata, 20);
    setField(metadata, 1, 'NUMBER_OF_TEXT_FIELDS', integer);
    setField(metadata, 1);
  }

  /*
  Extract information from the trailer.
  */
  function parseTrailer() {
    setField(metadata, 11, 'EOF_MARKER', identity);
    setField(metadata, 15);
  }

  /*
  Parse a FAM file.
  */
  function parse() {
    var current_id = 0,
        index;

    parseHeader();

    while (current_id !== metadata.LAST_ID) {
      current_id = parseMember();
    }

    parseFooter();
    for (index = 0; index < metadata.NUMBER_OF_TEXT_FIELDS; index++) {
      parseText();
    }

    parseTrailer();
    if (metadata.EOF_MARKER !== EOF_MARKER) {
      throw 'No EOF marker found.';
    }
  }

  /*
  Write the parsed FAM file to the console.
  */
  this.dump = function() {
    var index,
        key;

    console.log('--- METADATA ---\n');
    console.log(metadata);

    for (index = 0; index < members.length; index++) {
      console.log('\n\n--- MEMBER ---\n');
      console.log(members[index]);
    }

    for (key in relationships) {
      console.log('\n\n--- RELATIONSHIP ---\n');
      console.log(relationships[key]);
    }

    /*
    for (index = 0; index < crossovers.length; index++) {
      console.log('\n\n--- CROSSOVER ---\n');
      console.log(crossovers[index]);
    }
    */

    for (index = 0; index < texts.length; index++) {
      console.log('\n\n--- TEXT ---\n');
      console.log(texts[index]);
    }
  };

  /*
  Get an array of member objects.
  */
  this.getMembers = function() {
    return members;
  };

  /*
  Get an array of relationship objects.
  */
  this.getRelationships = function() {
    return Object.keys(relationships).map(function(key) {
      return relationships[key];
    });
  };

  parse();
}

module.exports = FamParser;
