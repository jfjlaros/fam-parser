# FAM file parser

A library for parsing FAM files from Python or Javascript.


## Python library

Installation:

    pip install fam-parser

Use as a library:

    from fam_parser import FamParser

    parser = FamParser(open('example.fam', 'rb').read())
    print(parser.parsed)

Command line invocation:

    fam_parser example.fam -

You can also invoke it directly from the repository root directory without
installation:

    python -m python.fam_parser example.fam -


## Javascript library

Installation:

    npm install fam-parser

Installation from source:

    npm install
    npm run dist

Use as a library:

    var FamParser = require('fam-parser');

    var parser = new FamParser(fs.readFileSync(
      'example.fam').toString('binary')
    );

    parser.getMembers().forEach(function(member) {
      console.log(member.SURNAME);
    });

Command line invocation:

    ./node_modules/.bin/fam-parser example.fam

(Or, if you installed globally using `npm install -g`, the `fam-parser` binary
should be in your `$PATH`.)

You can also invoke it directly from the repository root directory without
installation:

    node javascript/cli.js example.fam


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
