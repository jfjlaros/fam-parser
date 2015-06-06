#!/bin/bash

python_command="python -m python.fam_parser -d 1"
javascript_command="nodejs javascript/cli.js"

python_test() {
  echo -n "Testing Python interface "
  for i in data/*.fam data/*.FAM; do
    $python_command $i $TEMP_FILE

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
}

javascript_test() {
  echo -n "Testing JavaScript interface "
  for i in data/*.fam data/*.FAM; do
    $javascript_command $i > $TEMP_FILE

    if ! grep "^EOF_MARKER: End of File$" $TEMP_FILE > /dev/null; then
      echo
      echo Test failed for file $i.
    else
      echo -n .
    fi
  done
  echo
}

concordance_test() {
  echo -n "Testing JavaScript interface concordance "
  for i in data/*.fam data/*.FAM; do
    $python_command $i - | sed 's/ /_/g' > $TEMP_FILE
    $javascript_command $i | sed 's/^ *//;s/^- //;s/ /_/g' > $TEMP_FILE2

    for l in $(cat $TEMP_FILE2); do
      if ! grep -F -- $l $TEMP_FILE > /dev/null; then
        echo
        echo Test failed on line $l for file $i.
        break
      fi
    done
    echo -n .
  done
  echo
}

TEMP_FILE="/tmp/.test_$RANDOM"
#python_test
#javascript_test
TEMP_FILE2="/tmp/.test_$RANDOM"
concordance_test
rm $TEMP_FILE $TEMP_FILE2
