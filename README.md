# FAM file parser

A library for parsing FAM files from Python or Javascript.


## Python library

Installation:

    python setup.py install

Command line invocation:

    fam_parser data/example.fam -

Use as a library:

    import sys
    from fam_parser import FamParser

    parser = FamParser()
    parser.read(open('data/example.fam'))
    parser.write(sys.stdout)


## Javascript library

Installation:

    npm install .

Command line invocation:

    fam-parser data/example.fam

Use as a library:

    var FamParser = require('fam-parser');

    var parser = new FamParser(fs.readFileSync(
      'data/example.fam').toString('binary')
    );

    parser.getMembers().forEach(function(member) {
      console.log(member.SURNAME);
    });


## Development of the FAM parser

We use the Python implementation for most of the development as it includes
more debugging functionality. Any changes are later lifted to the Javascript
implementation.

### Preparations
First, make sure that `wine` is installed and that your CPU allows execution of
16-bit instructions:

    echo 1 > /proc/sys/abi/ldt16

### Reverse engineering
Run Cyrillic:

    wine cyrillic.exe

And start editing a pedigree. Use `xxd` and `watch` to find differences:

    while true; do watch --differences=permanent xxd pedigree.fam; done

Press `Ctrl+c` to clear the highlights.

### Debugging
If something is wrong, then probably a skipped field is now assumed to be of
fixed size, while it should be of variable size. To find the offending field,
add the following line to the function `_set_field`:

    print name

The offending field is probably one of the unnamed fields above the one you
found, hopefully the nearest one.

Now you can give the unnamed field a name so you can inspect its content.

    while true; do
      watch --differences=permanent \
        "fam_parser -d pedigree.fam - | tail -100 | head -50"
    done

Vary the values for `head` and `tail` to focus on the part of the output you
want to inspect.
