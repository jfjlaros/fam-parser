#!/bin/sh

TEMP_FILE="/tmp/.test_$RANDOM"

echo -n "Testing Python interface "
for i in data/*.fam data/*.FAM; do
  python -m python.fam_parser $i $TEMP_FILE
  
  if ! grep -a "EOF_MARKER: End of File" $TEMP_FILE > /dev/null; then
    echo
    echo Test failed for file $i.
  else
    echo -n .
  fi
done
echo

echo -n "Testing JavaScript interface "
for i in data/*.fam data/*.FAM; do
  nodejs javascript/cli.js $i > $TEMP_FILE
  
  if ! grep -a "EOF_MARKER: 'End of File'" $TEMP_FILE > /dev/null; then
    echo
    echo Test failed for file $i.
  else
    echo -n .
  fi
done
echo

rm $TEMP_FILE