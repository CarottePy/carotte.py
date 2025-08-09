#!/usr/bin/env bash

cd "$(dirname "$0")"

for test_file in *.py; do
    echo "$test_file"
    diff <(cd ..; python3 carotte.py "tests/$test_file") "${test_file%.py}.out"
done
