#!/usr/bin/env node

'use strict';

/*
Command line interface for the FAM parser.
*/
var fs = require('fs'),
    path = require('path'),
    yaml = require('js-yaml');

var FamParser = require('../dist/index');

function main(inputFile, outputFile) {
  var parser = new FamParser(fs.readFileSync(inputFile));

  fs.writeFileSync(outputFile, '---\n');
  fs.appendFileSync(outputFile, yaml.dump(parser.parsed));
}

// Wait for the stdout buffer to drain, see
// https://github.com/eslint/eslint/issues/317
process.on('exit', function() {
  process.reallyExit(main(
    path.resolve(process.cwd(), process.argv[2]),
    path.resolve(process.cwd(), process.argv[3])));
});
