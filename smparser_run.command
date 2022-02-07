#! /bin/bash
cd "$(dirname "$(readlink -f "$0")")"
python3.9 ./src/smparser.py
