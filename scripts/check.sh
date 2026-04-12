#!/usr/bin/env bash
set -e

python -m py_compile app.py
python -m py_compile scanner.py
python -m py_compile predict.py