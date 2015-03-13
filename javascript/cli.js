#!/usr/bin/env node


'use strict';


var fs = require('fs');
var path = require('path');
var FamParser = require('./index');


var main = function(filename) {
  var FP = new FamParser(fs.readFileSync(filename).toString('binary'));
  FP.dump();
};


var exitCode = main(
  path.resolve(process.cwd(), process.argv[2])
);


/*
 * Wait for the stdout buffer to drain.
 * See https://github.com/eslint/eslint/issues/317
 */
process.on('exit', function() {
  process.reallyExit(exitCode);
});
