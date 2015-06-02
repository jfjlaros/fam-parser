'use strict';

/*
YANL writer.

This writer only works for objects of type C.

An object if of type C when it is a collection of key-value pairs where all
values are:
- Atomic (str, int, float, etc.). 
- Type C.
- List, where the elements are of type C.
  
(C) 2015 Jeroen F.J. Laros <J.F.J.Laros@lumc.nl>
*/

/*
Convert an object to a YAML string.

:arg dict object: An object.
:arg indent: Depth of recursion, used for indentation.

:return str: A YAML representation of {object}.
*/
function buildYaml(object, indent) {
  var string = '',
      padding = '',
      tempString,
      index,
      key;

  for (index = 0; index < indent; index++) {
    padding += '  ';
  }

  if (typeof(object) === 'object') {
    string += '\n';

    if (Object.prototype.toString.call(object) === '[object Object]') {
      for (key in object) {
        string += padding + key + ': ' + buildYaml(object[key], indent + 1);
      }
    }
    else {
      for (key in object) {
        tempString = buildYaml(object[key], indent + 1);
        string += padding + '- ' + tempString.slice(indent * 2 + 3,
          tempString.length);
      }
    }
  }
  else {
    return object + '\n';
  }

  return string;
}

/*
Convert an object of type C to a YAML string.

:arg dict dictionary: An object of type C.

:return str: YAML representation of {dictionary}.
*/
function toYaml(dictionary) {
  return buildYaml(dictionary, 0);
}

module.exports = toYaml;
