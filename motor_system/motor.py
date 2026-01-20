#!/usr/bin/env python3
import signal
from http.server import BaseHTTPRequestHandler, HTTPServer

import lgpio

HOST = "0.0.0.0"
PORT = 8080

GPIOCHIP = 0  # if you ever need to change chips on Pi 5, start here

PWM_HZ = 2000
DEADBAND_PCT = 6   # abs(value) < 6 => stop

MIN_PCT = -100
MAX_PCT = 100

MOTORS = {
    "FL": {"in1": 5,  "in2": 6,  "pwm": 12, "invert": False},
    "FR": {"in1": 13, "in2": 19, "pwm": 18, "invert": False},
    "RL": {"in1": 16, "in2": 20, "pwm": 21, "invert": False},
    "RR": {"in1": 23, "in2": 24, "pwm": 25, "invert": False},
}

# open gpiochip
h = lgpio.gpiochip_open(GPIOCHIP)

# init pins: claim outputs
for cfg in MOTORS.values():
    lgpio.gpio_claim_output(h, cfg["in1"])
    lgpio.gpio_claim_output(h, cfg["in2"])
    lgpio.gpio_claim_output(h, cfg["pwm"])

# last commanded values (int percent)
state = {name: 0 for name in MOTORS.keys()}

def _stop_cfg(cfg):
    lgpio.gpio_write(h, cfg["in1"], 0)
    lgpio.gpio_write(h, cfg["in2"], 0)
    # stop PWM: duty=0
    lgpio.tx_pwm(h, cfg["pwm"], PWM_HZ, 0)

def stop_all():
    for name, cfg in MOTORS.items():
        _stop_cfg(cfg)
        state[name] = 0

def set_motor_pct(name: str, pct: int):
    if name not in MOTORS:
        raise ValueError(f"NAME unknown motor {name}")

    if not isinstance(pct, int):
        raise ValueError(f"TYPE {name} must be int")

    if pct < MIN_PCT or pct > MAX_PCT:
        raise ValueError(f"RANGE {name} must be between -100 and 100")

    cfg = MOTORS[name]
    if cfg.get("invert", False):
        pct = -pct

    if pct == 0 or abs(pct) < DEADBAND_PCT:
        _stop_cfg(cfg)
        state[name] = 0
        return

    # Direction pins
    if pct > 0:
        lgpio.gpio_write(h, cfg["in1"], 1)
        lgpio.gpio_write(h, cfg["in2"], 0)
    else:
        lgpio.gpio_write(h, cfg["in1"], 0)
        lgpio.gpio_write(h, cfg["in2"], 1)

    # lgpio PWM duty is percent (0..100)
    duty_pct = int(abs(pct))
    lgpio.tx_pwm(h, cfg["pwm"], PWM_HZ, duty_pct)

    state[name] = pct

def parse_cmd_line(line: str):
    """
    Strict language:
      V1 SET FL=10 FR=-20   (partial updates allowed)
      V1 STOP
      V1 GET
    """
    line = line.strip()
    if not line:
        raise ValueError("SYNTAX empty command")

    parts = line.split()
    if len(parts) < 2 or parts[0] != "V1":
        raise ValueError("SYNTAX expected 'V1 <VERB>'")

    verb = parts[1]

    if verb == "STOP":
        if len(parts) != 2:
            raise ValueError("SYNTAX STOP takes no args")
        return ("STOP", {})

    if verb == "GET":
        if len(parts) != 2:
            raise ValueError("SYNTAX GET takes no args")
        return ("GET", {})

    if verb == "SET":
        if len(parts) < 3:
            raise ValueError("SYNTAX SET requires at least one assignment")

        updates = {}
        for token in parts[2:]:
            if "=" not in token:
                raise ValueError(f"SYNTAX bad assignment '{token}' (expected NAME=VALUE)")
            name, val = token.split("=", 1)
            name = name.strip()
            val = val.strip()

            if name in updates:
                raise ValueError(f"SYNTAX duplicate assignment for {name}")
            if name not in MOTORS:
                raise ValueError(f"NAME unknown motor {name}")

            try:
                pct = int(val)
            except:
                raise ValueError(f"TYPE {name} must be int")

            if pct < MIN_PCT or pct > MAX_PCT:
                raise ValueError(f"RANGE {name} must be between -100 and 100")

            updates[name] = pct

        return ("SET", updates)

    raise ValueError(f"SYNTAX unknown verb {verb}")

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
            s = " ".join([f"{k}={state[k]}" for k in ("FL", "FR", "RL", "RR")])
            return self._send_text(200, f"OK V1 {s}")
        return self._send_text(404, "ERR V1 NOTFOUND")

    def do_POST(self):
        if self.path != "/cmd":
            return self._send_text(404, "ERR V1 NOTFOUND")

        length = int(self.headers.get("Content-Length", "0"))
        raw = self.rfile.read(length).decode("utf-8", errors="strict").strip()

        try:
            verb, updates = parse_cmd_line(raw)

            if verb == "STOP":
                stop_all()
                return self._send_text(200, "OK V1")

            if verb == "GET":
                s = " ".join([f"{k}={state[k]}" for k in ("FL", "FR", "RL", "RR")])
                return self._send_text(200, f"OK V1 {s}")

            if verb == "SET":
                for name, pct in updates.items():
                    set_motor_pct(name, pct)
                return self._send_text(200, "OK V1")

            return self._send_text(400, "ERR V1 SYNTAX")

        except ValueError as e:
            return self._send_text(400, f"ERR V1 {str(e)}")
        except Exception as e:
            return self._send_text(500, f"ERR V1 INTERNAL {e}")

    def log_message(self, *_):
        return

def shutdown(*_):
    stop_all()
    lgpio.gpiochip_close(h)
    raise SystemExit(0)

def main():
    signal.signal(signal.SIGINT, shutdown)
    signal.signal(signal.SIGTERM, shutdown)

    stop_all()
    server = HTTPServer((HOST, PORT), Handler)
    print(f"4-pump server (lgpio) listening on http://{HOST}:{PORT}")
    print("POST /cmd with: 'V1 SET FL=.. FR=.. RL=.. RR=..' (partial ok), 'V1 STOP', 'V1 GET'")
    server.serve_forever()

if __name__ == "__main__":
    main()
