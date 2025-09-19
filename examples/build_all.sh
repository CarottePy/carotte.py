#!/usr/bin/env bash

cd "$(dirname "$0")" || exit 1

for test_file in [a-z]*.py; do
    echo "BUILD: $test_file"
    (cd ..; python3 carotte.py "examples/$test_file" -p -o "examples/${test_file%.py}.net")
done
