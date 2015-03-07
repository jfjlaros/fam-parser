var fs = require('fs');

var PROBAND = ['NOT_A_PROBAND', 'ABOVE_LEFT', 'ABOVE_RIGHT', 'BELOW_LEFT',
      'BELOW_RIGHT', 'LEFT', 'RIGHT'],
    SEX = ['MALE', 'FEMALE', 'UNKNOWN'],
    ANNOTATION_1 = {
      '0000000000000000': 'NONE',
      '0000001000000001': 'FILL',
      '0000001000000000': 'FILL2', // BAR in combination with P or SB?
      '0000001100000000': 'DOT',
      '0000010000000000': 'QUESTION',
      '0000010100000000': 'RIGHT-UPPER',
      '0000011000000000': 'RIGHT-LOWER',
      '0000100000000000': 'LEFT-UPPER',
      '0000011100000000': 'LEFT-LOWER',
    },
    ANNOTATION_2 = {
      '00000000': 'NONE',
      '00000001': 'P',
      '00000100': 'SB',
      '00001011': 'BAR',
      '00000010': 'UNBORN',
      '00000011': 'ABORTED',
    },
    ANNOTATION_3 = {
      '00000000': 'NONE',
      '00010100': '+',
      '00010101': '-'
    },
    RELATIONSHIP = {
      0x04: 'SEPARATED',
      0x10: 'DIVORCED',
    };

/**
 * Miscellaneous functions.
 */
function pad(string, length) {
  var padding = '',
      index;

  for (index = 0; index < length - string.length; index++) {
    padding += '0';
  }
  return padding + string;
}

function convertToHex(data) {
  var result = '',
      index;

  for (index = 0; index < data.length; index++) {
    result += pad(data.charCodeAt(index).toString(16), 2);
  }
  return result;
}

/**
 * Helper functions.
 */
function identity(data) {
  return data;
}

function trim(data) {
  return data.split(String.fromCharCode(0x00))[0];
}

function proband(data) {
  return PROBAND[data.charCodeAt(0)];
}

function sex(data) {
  return SEX[data.charCodeAt(0)];
}

function relation(data) {
  var annotation;

  for (annotation in RELATIONSHIP) {
    if (data === annotation) {
      return RELATIONSHIP[data];
    }
  }
  return 'NORMAL';
}

function raw(data) {
  return convertToHex(data);
}

function bit(data) {
  return pad(data.charCodeAt(0).toString(2), 8);
}

function comment(data) {
  return data.split(String.fromCharCode(0x09) + String.fromCharCode(0x03));
}

function integer(data) {
  var result = 0,
      index;

  for (index = data.length - 1; index >= 0; index--) {
    result = result * 0x100 + data.charCodeAt(index);
  }
  return result;
}

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

function FamParser(fileContent) {
  var data = fileContent,
      offset = 0,
      delimiter = 0x0d,
      metadata = {},
      members = [],
      relationships = {},
      crossovers = [];

  /**
   * Extract a field from {data} using either a fixed size, or a delimiter.
   * After reading, {offset} is set to the next field.
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
      if (func === undefined) {
        destination[name] = identity(field);
      }
      else {
        destination[name] = func(field);
      }
    }
    offset += extracted;
  }

  function parseHeader() {
    setField(metadata, 26, 'SOURCE', trim);
    setField(metadata, 0, 'FAMILY_NAME');
    setField(metadata, 0, 'FAMILY_ID');
    setField(metadata, 0, 'AUTHOR');
    setField(metadata, 1, 'SIZE', integer);
    setField(metadata, 45);
    setField(metadata, 0, 'COMMENT');
    setField(metadata, 3, 'DATE_CREATED', date);
    setField(metadata, 1);
    setField(metadata, 3, 'DATE_UPDATED', date);
    setField(metadata, 14);
    setField(metadata, 1, 'SELECTED_ID', integer);
    setField(metadata, 17);
  }

  function parseRelationship(personId) {
    var relationship = {},
        relationFlags,
        key;

    relationship.MEMBER_1_ID = personId;
    setField(relationship, 1, 'MEMBER_2_ID', integer);
    setField(relationship, 1);
    setField(relationship, 1, 'RELATION_FLAGS', integer);
    setField(relationship, 0, 'RELATION_NAME');

    relationFlags = relationship.RELATION_FLAGS;
    relationship.RELATION_STATUS = relation(relationFlags);
    relationship.RELATION_IS_INFORMAL = Boolean(relationFlags & 0x01);
    relationship.RELATION_IS_CONSANGUINEOUS = Boolean(relationFlags & 0x02);

    key = [personId, relationship.MEMBER_2_ID].sort().toString();
    if (relationships[key] === undefined) {
      relationships[key] = relationship;
    }
  }

  function parseCrossover(personId) {
    var crossover = {},
        alleles = 0,
        events = 0,
        flag;

    crossover.ID = personId;
    while (alleles < 2) {
      flag = 'FLAG_' + pad(events.toString(), 2);

      setField(crossover, 1, flag, raw);
      if (crossover[flag] === '22') {
        setField(crossover, 9, 'ALLELE_' + pad(alleles.toString(), 2), raw);
        if (!alleles) {
          setField(crossover, 2, 'SPACER_' + pad(alleles.toString(), 2), raw);
        }
        alleles += 1;
      }
      else {
        setField(crossover, 11, 'CROSSOVER_' + pad(events.toString(), 2), raw);
      }
      events += 1;
    }

    crossovers.push(crossover);
  }

  function parseMember() {
    var member = {},
        spouse;

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
    setField(member, 1, 'SEX', sex);
    setField(member, 1, 'ID', integer);
    setField(member, 1);
    setField(member, 1, 'UNKNOWN_1', integer);
    setField(member, 1);
    setField(member, 1, 'MOTHER_ID', integer);
    setField(member, 1);
    setField(member, 1, 'FATHER_ID', integer);
    setField(member, 1);
    setField(member, 1, 'INTERNAL_ID', integer);
    setField(member, 1);
    setField(member, 1, 'NUMBER_OF_INDIVIDUALS', integer);
    setField(member, 1);
    setField(member, 0, 'AGE_GESTATION');
    setField(member, 0, 'INDIVIDUAL_ID');
    setField(member, 1, 'NUMBER_OF_SPOUSES', integer);
    setField(member, 1);

    for (spouse = 0; spouse <  member.NUMBER_OF_SPOUSES; spouse++) {
      parseRelationship(member.ID);
    }

    setField(member, 4);
    setField(member, 1, 'FLAGS_1', bit);
    setField(member, 2);
    setField(member, 1, 'PROBAND', proband);
    setField(member, 1, 'X_COORDINATE', integer);
    setField(member, 1);
    setField(member, 1, 'Y_COORDINATE', integer);
    setField(member, 1);
    setField(member, 1, 'FLAGS_2', bit);
    setField(member, 4);

    parseCrossover(member.ID);

    setField(member, 1, 'FLAGS_3', bit);
    setField(member, 180);
    setField(member, 1, 'FLAGS_4', bit);
    setField(member, 24);

    member.ANNOTATION_1 = ANNOTATION_1[member.FLAGS_1 + member.FLAGS_3];
    member.ANNOTATION_2 = ANNOTATION_2[member.FLAGS_2];
    member.ANNOTATION_3 = ANNOTATION_3[member.FLAGS_4];

    members.push(member);
  }

/*
    def _parse_text(self):
        """
        Extract information from a text field.
        """
        # TODO: X and Y coordinates have more digits.
        text = container.Container()

        self._set_field(text, 0, 'TEXT', _text)
        self._set_field(text, 54)
        self._set_field(text, 1, 'X_COORDINATE', _int)
        self._set_field(text, 3)
        self._set_field(text, 1, 'Y_COORDINATE', _int)
        self._set_field(text, 7)

        self.text.append(text)

*/
  function parseFooter() {
    var index;

    setField(metadata, 3);
    setField(metadata, 1, 'NUMBER_OF_CUSTOM_DESC', integer);
    setField(metadata, 1);

    for (index = 0; index < 23; index++) {
      setField(metadata, 0, 'DESC_' + pad(index, 2), identity);
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

  this.parse = function() {
    var member;

    parseHeader();
    for (member = 0; member < metadata.SIZE; member++) {
      parseMember();
    }

    parseFooter();
  };

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
  };
}


var T1 = new FamParser(fs.readFileSync(
  '../data/example.fam').toString('binary'));
T1.parse();
T1.dump();
