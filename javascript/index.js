'use strict';

/*
FAM parser.

(C) 2015 Jeroen F.J. Laros <J.F.J.Laros@lumc.nl>
*/

var fs = require('fs');

var BinParser = require('bin-parser');

function FamParser(fileContent) {
  var parser = new BinParser(fileContent,
    fs.readFileSync('structure.yml').toString('binary'), // FIXME: webpack
    fs.readFileSync('types.yml').toString('binary'));    // FIXME: webpack
  return parser;
}

module.exports = FamParser;
