#!/bin/bash

# Start MJPG‑Streamer
mjpg_streamer -o "output_http.so -p 5050 -w /home/subrov/mjpg-streamer-experimental/www" \
              -i "input_uvc.so -d /dev/video0 -r 1920x1080 -f 30" &

# Give mjpg_streamer a moment to start, then start Node server
sleep 1
node server.js
