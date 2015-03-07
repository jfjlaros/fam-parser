var fs = require('fs');

/**
 * Miscellaneous functions.
 */
function convertToHex(data) {
  var result = '',
      padding,
      character,
      index;

  for (index = 0; index < data.length; index++) {
    character = data.charCodeAt(index).toString(16);

    padding = '';
    if (character.length < 2) {
      padding = '0';
    }

    result += padding + character;
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

function raw(data) {
  return convertToHex(data);
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
      parsed = {
        'metadata': {},
        'relationships': {},
      };

  /**
   * Extract a field from {data} using either a fixed size, or a delimiter.
   * After reading, {offset} is set to the next field.
   */
  function setField(destination, size, name, func) {
    var extracted;

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

  this.parse = function() {
    parseHeader();
  };

  this.dump = function() {
    return metadata;
  };
}


var T1 = new FamParser(fs.readFileSync(
  '../data/example.fam').toString('binary'));
T1.parse();
console.log(T1.dump());
