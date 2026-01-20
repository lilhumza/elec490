# Raspberry Pi Motor + Actuator Control (REST)

This repo provides:

* `setup.sh`: installs `lgpio` (Pi 5 compatible) using OS-managed Python.
* `motor.py`: simple HTTP server exposing a strict command language to control:

  * 4 DC pumps via L298N (PWM + direction): `FL`, `FR`, `RL`, `RR`
  * 1 linear actuator via L298N (enable on/off + direction), time-based positioning with homing

---

## Hardware Assumptions

### Pumps (4x DC motors)

Each pump is driven by an L298N channel:

* `IN1/IN2` = direction
* `ENA` = PWM input (remove jumper if you want Pi-controlled PWM)

### Actuator (12V DC linear actuator with internal limit switches)

Driven by one L298N channel (Option A):

* `IN1/IN2` = direction (extend/retract)
* `ENA` = enable pin (ON/OFF, no PWM)
* Remove the ENA jumper for the actuator channel and wire ENA to a Pi GPIO.

---

## Files

* `setup.sh`
  Updates the system, installs build dependencies, builds/installs `lgpio` from source, and performs sanity checks.

* `motor.py`
  Runs an HTTP server:

  * `GET /health`
  * `GET /state`
  * `POST /cmd` (text/plain strict commands)

---

## Setup (Raspberry Pi 5)

```bash
chmod +x setup.sh
./setup.sh
```

If you see GPIO permission issues, ensure your user is in the `gpio` group:

```bash
sudo usermod -aG gpio $USER
newgrp gpio
```

Reboot if required.

---

## Run

```bash
python3 motor.py
```

Server listens on:

* `http://0.0.0.0:8080`

---

## API

### Endpoints

* `GET /health`

  * Returns: `OK V1 HEALTH`

* `GET /state`

  * Returns: pumps + actuator state in a single line

* `POST /cmd` with header `Content-Type: text/plain`

  * Sends a single strict command line (examples below)

---

## Command Language (Strict)

### Pumps

* Set any subset of motors (partial updates allowed):

  * `V1 SET FL=30`
  * `V1 SET FL=30 FR=30 RL=30 RR=30`
  * Values are integers in `[-100..100]`

    * Positive = forward
    * Negative = reverse
    * Small magnitudes are stopped via deadband

* Stop everything (pumps + actuator):

  * `V1 STOP`

* Get state:

  * `V1 GET`

### Actuator

* Home (retract to internal limit, then define position = 0):

  * `V1 ACT HOME`

* Move to percent position (0..100) using time-based estimate:

  * `V1 ACT GOTO=50`
  * Requires homing first.

* Stop actuator immediately:

  * `V1 ACT STOP`

---

## Calibration Notes (Actuator)

The actuator position is estimated by time after a HOME reference.

The key parameter in `motor.py` is:

* `ACT_FULL_MS`
  Time in milliseconds from fully retracted (0%) to fully extended (100%).

If `GOTO=10` retracts too far, `ACT_FULL_MS` is likely too large.
If `GOTO=100` doesn’t reach full extension, `ACT_FULL_MS` is too small.

`ACT_FULL_MS = 3250` is the current working value for this build.

---

## Sample Commands (localhost)

### Health + state

```bash
curl http://localhost:8080/health

curl -X POST http://localhost:8080/cmd \
  -H "Content-Type: text/plain" \
  --data 'V1 GET'
```

### Pumps

```bash
curl -X POST http://localhost:8080/cmd \
  -H "Content-Type: text/plain" \
  --data 'V1 SET FL=40'

curl -X POST http://localhost:8080/cmd \
  -H "Content-Type: text/plain" \
  --data 'V1 SET FR=-60'

curl -X POST http://localhost:8080/cmd \
  -H "Content-Type: text/plain" \
  --data 'V1 SET FL=30 FR=30 RL=30 RR=30'

curl -X POST http://localhost:8080/cmd \
  -H "Content-Type: text/plain" \
  --data 'V1 SET RL=-40 RR=-40'

curl -X POST http://localhost:8080/cmd \
  -H "Content-Type: text/plain" \
  --data 'V1 STOP'
```

### Actuator

```bash
# Home (retract fully, define ACT_POS=0)
curl -X POST http://localhost:8080/cmd \
  -H "Content-Type: text/plain" \
  --data 'V1 ACT HOME'

# Extend fully (100%)
curl -X POST http://localhost:8080/cmd \
  -H "Content-Type: text/plain" \
  --data 'V1 ACT GOTO=100'

# Mid-stroke (~50%)
curl -X POST http://localhost:8080/cmd \
  -H "Content-Type: text/plain" \
  --data 'V1 ACT GOTO=50'

# Small retract (~10%)
curl -X POST http://localhost:8080/cmd \
  -H "Content-Type: text/plain" \
  --data 'V1 ACT GOTO=10'

# Stop actuator
curl -X POST http://localhost:8080/cmd \
  -H "Content-Type: text/plain" \
  --data 'V1 ACT STOP'
```

### Combined Example

```bash
curl -X POST http://localhost:8080/cmd \
  -H "Content-Type: text/plain" \
  --data 'V1 SET FL=25 FR=25 RL=25 RR=25'

curl -X POST http://localhost:8080/cmd \
  -H "Content-Type: text/plain" \
  --data 'V1 ACT GOTO=30'

curl -X POST http://localhost:8080/cmd \
  -H "Content-Type: text/plain" \
  --data 'V1 STOP'
```

---

## Notes / Known Limitations

* Actuator `GOTO` is currently implemented with a blocking sleep (simple and reliable for bring-up).

  * Pumps keep running during actuator motion, but the server cannot accept new commands until the move finishes.
* If actuator direction is reversed, set `ACT["invert"] = True` in `motor.py`.
* If any motor direction is reversed, set `"invert": true` in `motor.py`.
