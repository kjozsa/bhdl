#!/bin/bash

cd /srv/bhdl
/usr/bin/screen -dmS bhdl /bin/bash -c "source .venv/bin/activate && python app.py"
