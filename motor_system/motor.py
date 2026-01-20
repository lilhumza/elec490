#!/usr/bin/env python3
import signal
import time
from http.server import BaseHTTPRequestHandler, HTTPServer

import lgpio

HOST = "0.0.0.0"
PORT = 8080
GPIOCHIP = 0

PWM_HZ = 2000
DEADBAND_PCT = 6   # abs(value) < 6 => stop

MIN_PCT = -100
MAX_PCT = 100

# -------------------------
# 4 pumps (PWM + direction)
# -------------------------
MOTORS = {
    "FL": {"in1": 5,  "in2": 6,  "pwm": 12, "invert": False},
    "FR": {"in1": 13, "in2": 19, "pwm": 18, "invert": False},
    "RL": {"in1": 16, "in2": 20, "pwm": 21, "invert": False},
    "RR": {"in1": 23, "in2": 24, "pwm": 25, "invert": False},
}

# -------------------------
# Actuator (Option A: EN on/off, no PWM)
# -------------------------
ACT = {
    "in1": 17,     # direction
    "in2": 27,     # direction
    "en":  22,     # enable (remove ENA jumper, wire to this GPIO)
    "invert": False,
}

# Calibration knob:
ACT_FULL_MS = 3250          # time from 0% (retracted) -> 100% (extended)
# Above value was ~3.25+ for 0-100 on 12V DC PSU.
ACT_HOME_MARGIN_MS = 2000
ACT_HOME_MS = ACT_FULL_MS + ACT_HOME_MARGIN_MS

# -------------------------
# Init gpio
# -------------------------
h = lgpio.gpiochip_open(GPIOCHIP)

# init pump pins
for cfg in MOTORS.values():
    lgpio.gpio_claim_output(h, cfg["in1"])
    lgpio.gpio_claim_output(h, cfg["in2"])
    lgpio.gpio_claim_output(h, cfg["pwm"])
    lgpio.tx_pwm(h, cfg["pwm"], PWM_HZ, 0)

# init actuator pins
lgpio.gpio_claim_output(h, ACT["in1"])
lgpio.gpio_claim_output(h, ACT["in2"])
lgpio.gpio_claim_output(h, ACT["en"])
lgpio.gpio_write(h, ACT["en"], 0)

# last commanded values (int percent)
state = {name: 0 for name in MOTORS.keys()}

# actuator estimated state
act_state = {
    "pos": 0.0,         # 0..100 estimated
    "homed": False,
    "moving": False,
    "target": None,     # float target when moving
}

# -------------------------
# Pump helpers
# -------------------------
def _stop_cfg(cfg):
    lgpio.gpio_write(h, cfg["in1"], 0)
    lgpio.gpio_write(h, cfg["in2"], 0)
    lgpio.tx_pwm(h, cfg["pwm"], PWM_HZ, 0)

def stop_all_pumps():
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

    if pct > 0:
        lgpio.gpio_write(h, cfg["in1"], 1)
        lgpio.gpio_write(h, cfg["in2"], 0)
    else:
        lgpio.gpio_write(h, cfg["in1"], 0)
        lgpio.gpio_write(h, cfg["in2"], 1)

    duty_pct = int(abs(pct))  # lgpio duty is percent 0..100
    lgpio.tx_pwm(h, cfg["pwm"], PWM_HZ, duty_pct)
    state[name] = pct

# -------------------------
# Actuator helpers
# -------------------------
def act_stop():
    lgpio.gpio_write(h, ACT["en"], 0)
    lgpio.gpio_write(h, ACT["in1"], 0)
    lgpio.gpio_write(h, ACT["in2"], 0)
    act_state["moving"] = False
    act_state["target"] = None

def act_drive(direction: int):
    """
    direction: +1 extend, -1 retract
    EN is set HIGH (no PWM).
    """
    if ACT.get("invert", False):
        direction = -direction

    # disable before changing direction
    lgpio.gpio_write(h, ACT["en"], 0)

    if direction > 0:
        lgpio.gpio_write(h, ACT["in1"], 1)
        lgpio.gpio_write(h, ACT["in2"], 0)
    else:
        lgpio.gpio_write(h, ACT["in1"], 0)
        lgpio.gpio_write(h, ACT["in2"], 1)

    lgpio.gpio_write(h, ACT["en"], 1)

def act_home():
    """
    Retract longer than full stroke. Internal limit switch stops at retract end.
    Then define pos=0, homed=true.
    """
    act_state["moving"] = True
    act_state["target"] = 0.0

    act_drive(-1)
    time.sleep(ACT_HOME_MS / 1000.0)
    act_stop()

    act_state["pos"] = 0.0
    act_state["homed"] = True

def act_goto(target_pct: float):
    """
    Blocking move. Requires homed. Time-based estimate with ACT_FULL_MS.
    """
    if target_pct < 0.0 or target_pct > 100.0:
        raise ValueError("RANGE target must be 0..100")
    if not act_state["homed"]:
        raise ValueError("STATE actuator not homed (run 'V1 ACT HOME' first)")

    cur = act_state["pos"]
    if abs(target_pct - cur) < 0.5:
        act_state["pos"] = float(target_pct)
        return

    direction = +1 if target_pct > cur else -1
    delta = abs(target_pct - cur)
    move_s = (delta / 100.0) * (ACT_FULL_MS / 1000.0)

    act_state["moving"] = True
    act_state["target"] = float(target_pct)

    act_drive(direction)
    time.sleep(move_s)
    act_stop()

    act_state["pos"] = float(target_pct)

# -------------------------
# Command parsing
# -------------------------
def parse_cmd_line(line: str):
    """
    Pumps:
      V1 SET FL=10 FR=-20   (partial updates allowed)
      V1 STOP
      V1 GET

    Actuator:
      V1 ACT HOME
      V1 ACT STOP
      V1 ACT GOTO=35
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

    if verb == "ACT":
        if len(parts) != 3:
            raise ValueError("SYNTAX ACT requires exactly one subcommand")

        sub = parts[2]

        if sub == "HOME":
            return ("ACT_HOME", {})

        if sub == "STOP":
            return ("ACT_STOP", {})

        if sub.startswith("GOTO="):
            v = sub.split("=", 1)[1]
            try:
                target = float(v)
            except:
                raise ValueError("TYPE target must be number 0..100")
            if target < 0.0 or target > 100.0:
                raise ValueError("RANGE target must be 0..100")
            return ("ACT_GOTO", {"target": target})

        raise ValueError("SYNTAX ACT unknown subcommand")

    raise ValueError(f"SYNTAX unknown verb {verb}")

# -------------------------
# HTTP server
# -------------------------
class Handler(BaseHTTPRequestHandler):
    def _send_text(self, code: int, text: str):
        body = (text + "\n").encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "text/plain; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _state_line(self):
        s = " ".join([f"{k}={state[k]}" for k in ("FL", "FR", "RL", "RR")])
        a = (
            f"ACT_POS={int(round(act_state['pos']))} "
            f"ACT_HOMED={1 if act_state['homed'] else 0} "
            f"ACT_MOVING={1 if act_state['moving'] else 0} "
            f"ACT_TARGET={'-' if act_state['target'] is None else int(round(act_state['target']))}"
        )
        return f"{s} {a}"

    def do_GET(self):
        if self.path == "/health":
            return self._send_text(200, "OK V1 HEALTH")
        if self.path == "/state":
            return self._send_text(200, f"OK V1 {self._state_line()}")
        return self._send_text(404, "ERR V1 NOTFOUND")

    def do_POST(self):
        if self.path != "/cmd":
            return self._send_text(404, "ERR V1 NOTFOUND")

        length = int(self.headers.get("Content-Length", "0"))
        raw = self.rfile.read(length).decode("utf-8", errors="strict").strip()

        try:
            verb, payload = parse_cmd_line(raw)

            if verb == "STOP":
                stop_all_pumps()
                act_stop()
                return self._send_text(200, "OK V1")

            if verb == "GET":
                return self._send_text(200, f"OK V1 {self._state_line()}")

            if verb == "SET":
                for name, pct in payload.items():
                    set_motor_pct(name, pct)
                return self._send_text(200, "OK V1")

            if verb == "ACT_HOME":
                act_home()
                return self._send_text(200, "OK V1")

            if verb == "ACT_STOP":
                act_stop()
                return self._send_text(200, "OK V1")

            if verb == "ACT_GOTO":
                act_goto(payload["target"])
                return self._send_text(200, "OK V1")

            return self._send_text(400, "ERR V1 SYNTAX")

        except ValueError as e:
            return self._send_text(400, f"ERR V1 {str(e)}")
        except Exception as e:
            return self._send_text(500, f"ERR V1 INTERNAL {e}")

    def log_message(self, *_):
        return

def shutdown(*_):
    stop_all_pumps()
    act_stop()
    lgpio.gpiochip_close(h)
    raise SystemExit(0)

def main():
    signal.signal(signal.SIGINT, shutdown)
    signal.signal(signal.SIGTERM, shutdown)

    stop_all_pumps()
    act_stop()

    server = HTTPServer((HOST, PORT), Handler)
    print(f"motor.py listening on http://{HOST}:{PORT}")
    print("POST /cmd with:")
    print("  Pumps: 'V1 SET FL=.. FR=.. RL=.. RR=..' (partial ok), 'V1 STOP', 'V1 GET'")
    print("  Act:   'V1 ACT HOME', 'V1 ACT GOTO=NN', 'V1 ACT STOP'")
    print(f"Act calibration: ACT_FULL_MS={ACT_FULL_MS} (HOME uses ACT_HOME_MS={ACT_HOME_MS})")
    server.serve_forever()

if __name__ == "__main__":
    main()
