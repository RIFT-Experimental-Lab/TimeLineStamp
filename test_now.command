#!/bin/zsh
set -e
cd -- "${0:A:h}"
exec python3 test_now.py "$@"
