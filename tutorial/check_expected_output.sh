#!/bin/bash
cd "$(dirname "$0")" || exit 1
IFS=$'\n\t'

for i in {0..4}_*.py; do
    echo "[FILE] $i"
    diff \
        <(echo -e "1,/# Expected output/d\n %s/^# //\n%p\nq\nq\n" | ed -l --quiet "$i" | head -n -1 | tail -n +2) \
        <(cd ..; python3 carotte.py "tutorial/$i")
done
