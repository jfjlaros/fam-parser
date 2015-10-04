#!/bin/bash

test_cli() {
  seed=${RANDOM}
  py="/tmp/${seed}_py.yml"
  js="/tmp/${seed}_js.yml"

  echo $1
  python -m python.cli $1 $py
  nodejs javascript/bin/cli.js $1 > $js

  compare_yaml $py $js

  rm $py $js
}

for filename in data/*.fam; do
  test_cli $filename
done
