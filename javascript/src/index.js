'use strict';

/*
FAM parser.

(C) 2015 Jeroen F.J. Laros <J.F.J.Laros@lumc.nl>
*/

//var fs = require('fs');

var BinParser = require('bin-parser');

function FamParser(fileContent) {
  var parser = new BinParser.BinReader(
        fileContent, require('../../structure.yml'),
        require('../../types.yml'), undefined, true),
      items = ['name', 'id_number', 'comments', 'members'],
      parsed = parser.parsed,
      relationships = {},
      spouses,
      members,
      keys,
      i,
      j;

  parser.parsed = {
    'family': {
      'relationships': []
    },
    'metadata': {}
  };

  // Extract the relationships and put them in the family structure.
  for (i = 0; i < parsed.members.length; i++) {
    spouses = BinParser.pop(parsed.members[i], 'spouses');
    for (j = 0; j < spouses.length; j++) {
      members = [parsed.members[i].id, BinParser.pop(spouses[j], 'id')].sort(
        BinParser.numerical);
      spouses[j].member_ids = members;
      relationships[members.join('_')] = spouses[j];
    }
  }

  keys = Object.keys(relationships).sort();
  for (i = 0; i < keys.length; i++) {
    parser.parsed.family.relationships.push(relationships[keys[i]]);
  }

  // Put all family related data in the family structure.
  for (i = 0; i < items.length; i++) {
    parser.parsed.family[items[i]] = BinParser.pop(parsed, items[i]);
  }

  // Annotate the genetic symbols.
  for (i = 0; i < parsed.genetic_symbols.length; i++) {
    parsed.genetic_symbols[i].name =
      parser.types.genetic_symbol.function.args.annotation[i];
  }

  parser.parsed.metadata.genetic_symbols = BinParser.pop(parsed,
    'genetic_symbols');

  // Annotate the additional symbols.
  for (i = 0; i < parsed.additional_symbols.length; i++) {
    parsed.additional_symbols[i].name =
      parser.types.additional_symbol.function.args.annotation[i];
  }

  // Merge the additional and custom symbols.
  parser.parsed.metadata.additional_symbols = BinParser.pop(parsed,
    'additional_symbols').concat(BinParser.pop(parsed, 'custom_symbols'));

  // Put the rest in the metadata structure.
  BinParser.update(parser.parsed.metadata, parsed);

  return parser;
}

module.exports = FamParser;
