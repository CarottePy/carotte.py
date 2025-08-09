#!/usr/bin/env bash

#
# (c) 2022-2023 hbens
# SPDX-License-Identifier: CC0-1.0
#
# A small script to check python and shell scripts
#

cd "$(dirname "$0")" || exit 1

CHECK_ONLY=0
[[ $# -gt 0 ]] && CHECK_ONLY=1

STATUS=0

find . -name "*.sh" -exec shellcheck {} \; || STATUS=1

# $@: python files to check
check_python() {
    if [ $# -eq 0 ]; then
        return
    fi

    black_args=(-l 120 --target-version py312)
    [[ "${CHECK_ONLY}" -eq 0 ]] && black_args+=(-q)
    [[ "${CHECK_ONLY}" -eq 1 ]] && black_args+=(--check --diff)
    #black "${black_args[@]}" "$@" || STATUS=1

    isort_args=()
    [[ "${CHECK_ONLY}" -eq 1 ]] && isort_args+=(-c)
    isort "${isort_args[@]}" "$@" || STATUS=1

    pylint -j 0 "$@" --score=n --output-format=colorized || STATUS=1

    mypy --disallow-untyped-defs --color-output "$@" || STATUS=1
}

readarray -d '' python_files < \
    <(find . -name "*.py" -not -path "./tutorial/*" -not -path "./assignhooks/*" -type f -print0)
check_python "${python_files[@]}"

exit "${STATUS}"
