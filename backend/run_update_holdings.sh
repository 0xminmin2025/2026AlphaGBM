#!/bin/bash
# Script to update portfolio holdings dates using Flask CLI
cd "$(dirname "$0")"
source venv/bin/activate
export FLASK_APP=run.py
flask update-holding-dates
