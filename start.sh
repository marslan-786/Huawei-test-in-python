#!/bin/bash
echo "Starting Virtual Desktop..."
# Hum yahan se direct Chrome bhi launch kar sakte hain
export DISPLAY=:0
chromium --no-sandbox --start-maximized &