#!/bin/bash

# Start motor control API (thrusters + actuator)
python3 motor_system/motor.py &
MOTOR_PID=$!

# Start MJPG-Streamer
mjpg_streamer -o "output_http.so -p 5050 -w /home/subrov/mjpg-streamer-experimental/www" \
              -i "input_uvc.so -d /dev/video0 -r 1920x1080 -f 30" &
MJPG_PID=$!

# Give background services a moment to start, then start Node server
sleep 1

cleanup() {
  kill "$MOTOR_PID" "$MJPG_PID" 2>/dev/null
}

trap cleanup EXIT
node server.js
