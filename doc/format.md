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

There is a second ID in the header (`INTERNAL_ID_INCREMENT`) that is also
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

# Data structures
## Source
## Flags
## Text fields
0x0d

### Comments
0x0903

### Free text
0x0b0b

## Integers
## Dates

# Peculiarities
`PEDIGREE_NUMBER`
