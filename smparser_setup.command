#! /bin/bash
cd "$(dirname "$(readlink -f "$0")")"
python3.9 -m pip install --user --upgrade pip
python3.9 -m pip install --user virtualenv
python3.9 -m venv venv
source venv/bin/activate
python3.9 -m pip install -r requirements.txt
