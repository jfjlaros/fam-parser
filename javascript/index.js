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

function trim(data) {
  return data.split(String.fromCharCode(0x00))[0];
}

function raw(data) {
  return convertToHex(data);
}

function comment(data) {
  return data.split(String.fromCharCode(0x09) +
    String.fromCharCode(0x03)).join('\n');
}

function info(data) {
  return data.split(String.fromCharCode(0xe9) +
    String.fromCharCode(0xe9)).join('\n');
}

function freeText(data) {
  return data.split(String.fromCharCode(0x0b) +
    String.fromCharCode(0x0b)).join('\n');
}

function description(data) {
  return DESC_PREFIX + pad(ord(data), 2);
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
  return '0x' + pad(hex(integer(data), 6));
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
    if (dateInt === 0xffffffff) {
      return 'DEFINED';
    }
    return dateInt.toString();
  }
  return 'UNKNOWN';
}

/*
FAM file parsing.
*/
function FamParser(fileContent) {
  var data = fileContent,
      parsed = {
        'METADATA': {
          'GENETIC_SYMBOLS': [],
          'ADDITIONAL_SYMBOLS': []
        },
        'FAMILY': {
          'MEMBERS': [],
          'DISEASE_LOCI': [],
          'QUANTITATIVE_VALUE_LOCI': [],
          'RELATIONSHIPS': []
        },
        'TEXT_FIELDS': []
      },
      delimiter = 0x0d, // REMOVE

      definitions = yaml.load(requireFile('../fam_fields.yml')),

      eofMarker = '',
      lastId = 0,
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
      field = data.slice(offset, -1).split(String.fromCharCode(delimiter))[0];
      extracted = field.length + 1;
    }

    offset += extracted;
    return field;
  }

  /*
  Replace a value with its annotation.

  :arg str data: Encoded data.
  :arg dict annotation: Annotation of {data}.

  :return str: Annotated representation of {data}.
  */
  function annotate(data, annotation) {
    var index = ord(data);

    if (index in definitions.MAPS[annotation]) {
      return definitions.MAPS[annotation][index];
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

      if (!(flag in definitions.FLAGS[annotation])) {
        if (value) {
          destination['FLAGS_' + annotation + '_' + pad(hex(flag), 2)] = value;
        }
      }
      else {
        destination[definitions.FLAGS[annotation][flag]] = value;
      }
    }
    return destination;
  }

  /*
  Extract marker information.
  */
  function parseMarkers() {
    while (raw(getField(1)) !== '01') {
      getField(439);
    }
  }

  /*
  Extract disease locus information.
  */
  function parseDiseaseLocus() {
    var locus = {
          'NAME': getField(),
          'COLOUR': colour(getField(3))
        };

    getField(1);
    locus['PATTERN'] = annotate(getField(1), 'PATTERN');

    parsed['FAMILY']['DISEASE_LOCI'].push(locus);
  }

  /*
  Extract header information.
  */
  function parseHeader() {
    var index;

    parsed['METADATA']['SOURCE'] = trim(getField(26));
    parsed['FAMILY']['NAME'] = getField();
    parsed['FAMILY']['ID_NUMBER'] = getField();
    parsed['METADATA']['FAMILY_DRAWN_BY'] = getField();
    lastId = integer(getField(2));
    getField(2); // LAST_INTERNAL_ID

    for (index = 0; index < 7; index++) {
      parseDiseaseLocus();
    }

    parsed['FAMILY']['COMMENTS'] = getField();
    parsed['METADATA']['CREATION_DATE'] = date(getField(4));
    parsed['METADATA']['LAST_UPDATED'] = date(getField(4));

    getField(5);
    for (index = 0; index < 7; index++) {
      parsed['FAMILY']['QUANTITATIVE_VALUE_LOCI'].push({'NAME': getField()});
    }

    parsed['METADATA']['SELECTED_ID'] = integer(getField(2));

    getField(7);
    parseMarkers();
    getField(9);
  }

  /*
  Extract relationship information.

  :arg int personId: The partner in this relationship.
  */
  function parseRelationship(personId) {
    var relationship = {'MEMBERS': [personId, integer(getField(2))].sort(
          function(a,b) {return a - b;})},
        key;

    update(relationship, flags(getField(1), 'RELATIONSHIP'));

    relationship['RELATION_NAME'] = getField();

    key = relationship['MEMBERS'].toString();
    if (relationshipKeys[key] === undefined) {
      parsed['FAMILY']['RELATIONSHIPS'].push(relationship);
      relationshipKeys[key] = true;
    }
  }

  /*
  Extract chromosome information.
  */
  function parseChromosome() {
    var chromosome = {};

    while (raw(getField(1)) !== '22') {
      getField(11);
    }
    getField(9);
  }

  /*
  Extract person information.
  */
  function parseMember() {
    var member = {
          'SURNAME': getField(),
          'OTHER_SURNAMES': getField(),
          'FORENAMES': getField(),
          'KNOWN_AS': getField(),
          'MAIDEN_NAME': getField(),
          'ETHNICITY': {
            'SELF': getField(),
            'M_G_MOTHER': getField(),
            'M_G_FATHER': getField(),
            'P_G_MOTHER': getField(),
            'P_G_FATHER': getField()
          },
          'ORIGINS': {
            'SELF': getField(),
            'M_G_MOTHER': getField(),
            'M_G_FATHER': getField(),
            'P_G_MOTHER': getField(),
            'P_G_FATHER': getField()
          },
          'ADDRESS': getField(),
          'ADDITIONAL_INFORMATION': info(getField()),
          'DATE_OF_BIRTH': date(getField(4)),
          'DATE_OF_DEATH': date(getField(4)),
          'SEX': annotate(getField(1), 'SEX'),
          'ID': integer(getField(2)),
          'PEDIGREE_NUMBER': integer(getField(2)),
          'MOTHER_ID': integer(getField(2)),
          'FATHER_ID': integer(getField(2)),
          'INTERNAL_ID': integer(getField(2)), // Remove?
          'NUMBER_OF_INDIVIDUALS': integer(getField(2)),
          'AGE_GESTATION': getField(),
          'INDIVIDUAL_ID': getField()
        },
        numberOfSpouses = integer(getField(1)),
        index;

    getField(1);
    for (index = 0; index < numberOfSpouses; index++) {
      parseRelationship(member.ID);
    }

    update(member, {
      'TWIN_ID': integer(getField(2)),
      'COMMENT': getField(),
      'ADOPTION_TYPE': annotate(getField(1), 'ADOPTION_TYPE'),
      'GENETIC_SYMBOLS': integer(getField(1))
    });
    getField(1);

    update(member, flags(getField(1), 'INDIVIDUAL'));

    update(member, {
      'PROBAND': annotate(getField(1), 'PROBAND'),
      'X_COORDINATE': integer(getField(2)),
      'Y_COORDINATE': integer(getField(2)),
      'ANNOTATION_1': annotate(getField(1), 'ANNOTATION_1'),
      'MULTIPLE_PREGNANCIES': annotate(getField(1), 'MULTIPLE_PREGNANCIES')
    });
    getField(3);

    parseChromosome();
    getField(2);
    parseChromosome();

    member['ANNOTATION_2'] = annotate(getField(1), 'ANNOTATION_2');

    getField(12);
    for (index = 0; index < 7; index++) {
      getField(24);
    }

    member['ADDITIONAL_SYMBOLS'] = integer(getField(1)); // -19?

    // NOTE: DNA and BLOOD fields are switched in Cyrillic. i.e., if DNA is
    // selected, the BLOOD_LOCATION field is stored and if BLOOD is
    // selected, the DNA_LOCATION field is stored. This is probably a bug.
    if (member['DNA']) {
        member['DNA_LOCATION'] = getField();
    }
    if (member['BLOOD']) {
        member['BLOOD_LOCATION'] = getField();
    }
    if (member['CELLS']) {
        member['CELLS_LOCATION'] = getField();
    }

    update(member, flags(getField(1), 'SAMPLE'));

    member['SAMPLE_NUMBER'] = getField();
    getField(3);  // COLOUR
    getField(17);
    getField(2);  // PATTERN

    parsed['FAMILY']['MEMBERS'].push(member);

    return member['ID'];
  }

  /*
  Extract information from a text field.
  */
  function parseText() {
    // TODO: X and Y coordinates have more digits.
    var text = {};

    text['CONTENT'] = freeText(getField());
    getField(54);
    text['X_COORDINATE'] = integer(getField(1));
    getField(3);
    text['Y_COORDINATE'] = integer(getField(1));
    getField(7);

    parsed['TEXT_FIELDS'].push(text);
  }

  /*
  Extract information from the footer.
  */
  function parseFooter() {
    var numberOfUnknownData = integer(getField(1)),
        numberOfCustomDescriptions,
        numberOfTextFields,
        index;

    getField(2);

    for (index = 0; index < numberOfUnknownData; index++) {
      getField(12);
    }

    numberOfCustomDescriptions = integer(getField(1));
    getField(1);

    for (index = 0; index < 19; index++) {
      parsed['METADATA']['GENETIC_SYMBOLS'].push({
        'NAME': definitions.MAPS['GENETIC_SYMBOL'][index],
        'VALUE': getField()
      });
    }

    for (index = 0; index < 4; index++) {
      parsed['METADATA']['ADDITIONAL_SYMBOLS'].push({
        'NAME': definitions.MAPS['ADDITIONAL_SYMBOL'][index],
        'VALUE': getField()
      });
    }

    for (index = 0; index < numberOfCustomDescriptions; index++) {
      parsed['METADATA']['ADDITIONAL_SYMBOLS'].push({
        'NAME': getField(),
        'VALUE': getField()
      });
    }

    getField(14);
    parsed['METADATA']['ZOOM'] = integer(getField(2));
    parsed['METADATA']['UNKNOWN_1'] = raw(getField(4)); // Zoom.
    parsed['METADATA']['UNKNOWN_2'] = raw(getField(4)); // Zoom.
    getField(20);

    numberOfTextFields = integer(getField(1));
    getField(1);

    for (index = 0; index < numberOfTextFields; index++) {
      parseText();
    }

    eofMarker = getField(11);
    getField(15);
  }

  /*
  Parse a FAM file.
  */
  function parse() {
    var index;

    parseHeader();

    while (parseMember() !== lastId);

    parseFooter();

    if (eofMarker !== definitions.EOF_MARKER) {
      throw 'No EOF marker found.';
    }
  }

  /*
  Write the parsed FAM file to the console.
  */
  this.dump = function() {
    console.log('--- YAML DUMP ---');
    console.log(yaml.dump(parsed));
    console.log('\n--- DEBUG INFO ---\n');
    console.log('EOF_MARKER: ' + eofMarker);
  };

  /*
  Get parsed object.
  */
  this.getParsed = function() {
    return parsed;
  };

  parse();
}

module.exports = FamParser;
