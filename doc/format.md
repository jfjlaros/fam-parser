---
title: Structure of the FAM file format
author: Jeroen F.J. Laros
---

# Introduction
In this document we describe the assumptions and deductions made in the
process of reverse engineering the Cyrillic FAM file format. We start with a
description of the general layout of the format, a description of the
discovered data structures and an enumeration of peculiarities.

This document is by no means complete and will be subjected to change as the
reverse engineering progresses.

# General layout of a FAM file
A FAM file can be partitioned into three sections; a header, a list of members
and a footer. In this section we describe the parts that were reverse
engineered and the interpretation we have deduced.

## Header
The header contains metadata such as the name of the family, the author,
creation and modification dates, comments, etc. It also contains the ID of the
last member in the list of members (`LAST_ID`). This value is important while
parsing the list of members, as this must be used as a stop condition (if the
current ID equals the ID in the header, we are currently parsing the last
member in the list). IDs seem to be reused when they become available, but it
is not entirely clear what the underlying rules are.

There is a second ID in the header (`LAST_INTERNAL_ID`) that is also
connected to IDs in the members list (`INTERNAL_ID`). This ID seems to be
incremented only, there seems to be no reusing. At the moment it is not clear
how these IDs are used or whether they are useful at all. It is also unclear
whether this ID can be used to terminate the iteration over the members list.

## Members
A member (an element of the members list) contains a large number of variables
like name, date of birth, sex, ID, parent IDs, all sorts of flags, coordinates,
etc. It also contains a list of relationships and a list of crossover events.

Some of the member annotation is configurable, ...

### Relationships
To iterate over the list of relationships, we use the variable
`NUMBER_OF_SPOUSES` in our stop condition. One relationship (an element of this
list) consists of the ID of the other member in this relationship, some flags
(divorced, informal, etc.) and a name for this relationship. Note that since
there are always two members in a relationship, this information is repeated
(and thus redundant) in the other member.

### Crossovers
The crossovers section consists of two sub sections, one for each allele. The
contents of these sub sections are not clear, except that they themselves
consist of a list of fields that appear to be encoding for crossover events.

### Twins
If an individual has one or more twins, the ID of one of these twins is given.
There is also a flag indicating the zygosity of the twins. Mixed zygosity twins
are not supported it seems.

## Footer
### Descriptions
### Custom descriptions
### Free text
### Trailer
### Unknown list

# Data types
## Source
The first 26 bytes of a FAM file are reserved for the `SOURCE` field. It
contains the name and version number of the program that created the file.
Typically it contains a string like: `Pedigree Editor V6.5`. This field is of
constant size, but the sting inside is delimited by `0x00`. The remaining bits
are undefined, they sometimes contain parts of the memory (garbage).

## Flags
Flags are stored as bit fields of one byte. The following fields are known to
be flags:

- `INDIVIDUAL` (part of the member data structure).
- `RELATIONSHIP` (part of the relationship data structure).

## Maps
Maps are one bit integers that map to one value. The following fields (all part
of the member data structure) are known to be maps:

- `PROBAND`
- `SEX`
- `TWIN_STATUS`
- `ANNOTATION_1`

The `ANNOTATION_2` field is suspected to be a map, but at this moment we do not
have sufficient evidence, it could also be a flag.

## Text fields
A text field is a byte string delimited by `0x0d`. The encoding is plain ASCII
as far as we can tell. There is support for fonts and font sizes, perhaps even
colours, but at this moment we do not know how these attributes are stored.

### Comments
The `COMMENT` field (part of the member data structure) is a text field that
can span multiple lines. The lines are internally separated by `0x0903`.

### Free text
The `TEXT` field (part of the text data structure) is a text field that can
span multiple lines, just like the `COMMENT` field. However, in this case the
lines are internally separated by `0x0b0b`.

## Integers
All integers are stored using the little-endian convention. The default size
seems to be 16 bits, although for dates (see below) 24 bits are used.

## Dates
Dates are encoded in a 24 bits integer, which are stored using the
little-endian convention. The encoding is in the date format `%Y%j`: the year
with century in four decimals followed by the day of the year as a zero-padded
number in three decimals. For example, the 3rd of May, 2015 is encoded as
`2015123`.

Note that the day of the year is one based, but we have seen it been set to
zero on occasions. For now, we interpret this as the year being set, but the
day of the year being unknown.

There are two special values for dates, being `0000000` and `16777215`
(`0xFFFFFFF`). The first value is interpreted as `UNKNOWN`, the second one as
`DEFINED`. The `DEFINED` value is used when a person is deceased but the date
of death is not given.

Leap years are taken into account, so the first of March 2012 (a leap year) is
encoded as `2012061`, while the first of March 2013 is encoded as `2013060`.

# Peculiarities
`PEDIGREE_NUMBER`
