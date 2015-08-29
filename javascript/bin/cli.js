#!/usr/bin/env node

'use strict';

var fs = require('fs'),
    path = require('path');

var FamParser = require('../dist/index');

var main = function(filename) {
  var parser = new FamParser(fs.readFileSync(filename).toString('binary'));

  parser.dump();
};

var exitCode = main(
  path.resolve(process.cwd(), process.argv[2])
);

/*
Wait for the stdout buffer to drain.
See https://github.com/eslint/eslint/issues/317
*/
process.on('exit', function() {
  process.reallyExit(exitCode);
});
