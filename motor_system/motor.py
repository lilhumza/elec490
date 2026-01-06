#!/usr/bin/env python3
import time
import signal
from http.server import BaseHTTPRequestHandler, HTTPServer

import pigpio

HOST = "0.0.0.0"
PORT = 8080

# Front-left motor pins (BCM)
FL_IN1 = 5
FL_IN2 = 6
FL_PWM = 12

PWM_HZ = 2000
DEADBAND = 6          # percent (0..100). Anything smaller becomes stop.
MAX_PCT = 100
MIN_PCT = -100

pi = pigpio.pi()
if not pi.connected:
    raise RuntimeError("pigpio not connected. Is pigpiod running? (sudo systemctl start pigpiod)")

# init pins
for pin in (FL_IN1, FL_IN2, FL_PWM):
    pi.set_mode(pin, pigpio.OUTPUT)

pi.set_PWM_frequency(FL_PWM, PWM_HZ)

# keep last commanded value for debugging
state = {"FL": 0}

def stop_fl():
    pi.write(FL_IN1, 0)
    pi.write(FL_IN2, 0)
    pi.set_PWM_dutycycle(FL_PWM, 0)
    state["FL"] = 0

def set_fl_pct(pct: int):
    """
    pct: integer in [-100..100]
    """
    if not isinstance(pct, int):
        raise ValueError("TYPE speed must be int")
    if pct < MIN_PCT or pct > MAX_PCT:
        raise ValueError("RANGE speed must be between -100 and 100")

    # deadband
    if abs(pct) < DEADBAND or pct == 0:
        stop_fl()
        return

    # direction
    if pct > 0:
        pi.write(FL_IN1, 1)
        pi.write(FL_IN2, 0)
    else:
        pi.write(FL_IN1, 0)
        pi.write(FL_IN2, 1)

    duty = int((abs(pct) / 100.0) * 255)
    pi.set_PWM_dutycycle(FL_PWM, duty)
    state["FL"] = pct

class Handler(BaseHTTPRequestHandler):
    def _send_text(self, code: int, text: str):
        body = (text + "\n").encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "text/plain; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        if self.path == "/health":
            return self._send_text(200, "OK V1 HEALTH")
        if self.path == "/state":
            return self._send_text(200, f"OK V1 FL={state['FL']}")
        return self._send_text(404, "ERR V1 NOTFOUND")

    def do_POST(self):
        if self.path != "/cmd":
            return self._send_text(404, "ERR V1 NOTFOUND")

        length = int(self.headers.get("Content-Length", "0"))
        raw = self.rfile.read(length).decode("utf-8", errors="strict").strip()

        # Strict command language:
        #   V1 SET FL=<int -100..100>
        #   V1 STOP
        #   V1 GET
        try:
            parts = raw.split()
            if len(parts) < 2 or parts[0] != "V1":
                return self._send_text(400, "ERR V1 SYNTAX expected 'V1 <VERB>'")

            verb = parts[1]

            if verb == "STOP":
                if len(parts) != 2:
                    return self._send_text(400, "ERR V1 SYNTAX STOP takes no args")
                stop_fl()
                return self._send_text(200, "OK V1")

            if verb == "GET":
                if len(parts) != 2:
                    return self._send_text(400, "ERR V1 SYNTAX GET takes no args")
                return self._send_text(200, f"OK V1 FL={state['FL']}")

            if verb == "SET":
                if len(parts) != 3:
                    return self._send_text(400, "ERR V1 SYNTAX SET requires exactly one assignment: FL=<val>")

                tok = parts[2]
                if not tok.startswith("FL="):
                    return self._send_text(400, "ERR V1 SYNTAX only FL=<val> supported in this build")

                val_s = tok.split("=", 1)[1]
                try:
                    pct = int(val_s)
                except:
                    return self._send_text(400, "ERR V1 TYPE FL must be int")

                set_fl_pct(pct)
                return self._send_text(200, "OK V1")

            return self._send_text(400, f"ERR V1 SYNTAX unknown verb {verb}")

        except ValueError as e:
            # our set_fl_pct throws ValueError("CODE message")
            msg = str(e)
            return self._send_text(400, f"ERR V1 {msg}")
        except Exception as e:
            return self._send_text(500, f"ERR V1 INTERNAL {e}")

    def log_message(self, *_):
        return

def shutdown(*_):
    stop_fl()
    pi.stop()
    raise SystemExit(0)

def main():
    signal.signal(signal.SIGINT, shutdown)
    signal.signal(signal.SIGTERM, shutdown)

    stop_fl()
    server = HTTPServer((HOST, PORT), Handler)
    print(f"FL motor server listening on http://{HOST}:{PORT}")
    print("POST /cmd with: 'V1 SET FL=<int -100..100>' or 'V1 STOP' or 'V1 GET'")
    server.serve_forever()

if __name__ == "__main__":
    main()
