#!/bin/sh

TEMP_FILE="/tmp/.test_$RANDOM"

echo -n "Testing Python interface "
for i in data/*.fam data/*.FAM; do
  python -m python.fam_parser -d -e $i $TEMP_FILE
  
  if ! grep "^EOF_MARKER: End of File$" $TEMP_FILE > /dev/null; then
    echo
    echo Test failed for file $i.
  elif grep "^_RAW_[0-9][0-9]:.* 0d" $TEMP_FILE > /dev/null; then
    echo
    echo Possible unhandled text field in file $i.
  else
    echo -n .
  fi
done
echo

echo -n "Testing JavaScript interface "
for i in data/*.fam data/*.FAM; do
  nodejs javascript/cli.js $i > $TEMP_FILE
  
  if ! grep "^  EOF_MARKER: 'End of File' }$" $TEMP_FILE > /dev/null; then
    echo
    echo Test failed for file $i.
  else
    echo -n .
  fi
done
echo

rm $TEMP_FILE
