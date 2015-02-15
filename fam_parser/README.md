# Development of the FAM parser

## Preparations
First, make sure that `wine` is installed and that your CPU allows execution of
16-bit instructions:

    echo 1 > /proc/sys/abi/ldt16

## Reverse engineering
Run Cyrillic:

    wine cyrillic.exe

And start editing a pedigree. Use `xxd` and `watch` to find differences:

    watch --differences=permanent xxd pedigree.fam
