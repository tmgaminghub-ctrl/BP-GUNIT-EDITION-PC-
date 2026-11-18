#!/bin/sh
# Bulletproof PC - campaign launcher (Linux).
# Needs python3 with tkinter (Debian/Ubuntu: sudo apt install python3-tk),
# a C compiler, and the graphics/audio libraries listed in README.md.
set -eu
cd "$(dirname "$0")"
if [ "$#" -gt 0 ]; then
    exec python3 -B play.py "$@"
fi
exec python3 -B launcher/campaign.py
