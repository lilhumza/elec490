#!/usr/bin/env bash
set -euo pipefail

echo "=== Raspberry Pi motor controller system setup (OS-managed Python) ==="

# -------------------------
# Resolve script directory
# -------------------------
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REQ_FILE="${SCRIPT_DIR}/requirements.txt"

# Keep the check since you asked for it; we just won't pip-install it on trixie.
if [ ! -f "${REQ_FILE}" ]; then
  echo "ERROR: requirements.txt not found in ${SCRIPT_DIR}"
  echo "Ensure requirements.txt is in the same directory as setup.sh"
  exit 1
fi
echo "Found requirements.txt at: ${REQ_FILE}"
echo "Note: On Debian trixie, Python deps are installed via apt (externally-managed env)."

# -------------------------
# OS update
# -------------------------
echo "[1/6] Updating system packages..."
sudo apt-get update -y
sudo apt-get upgrade -y

# -------------------------
# Base + build dependencies
# -------------------------
echo "[2/6] Installing OS-level dependencies..."
sudo apt-get install -y \
  python3 \
  python3-dev \
  python3-pip \
  build-essential \
  git \
  curl \
  ca-certificates

# -------------------------
# Python libs via apt (OS-approved)
# -------------------------
echo "[3/6] Installing Python libraries via apt..."
sudo apt-get install -y \
  python3-requests

# -------------------------
# Build + install pigpio from source
# -------------------------
echo "[4/6] Building and installing pigpio from source..."
cd /tmp
sudo rm -rf /tmp/pigpio
git clone https://github.com/joan2937/pigpio.git
cd pigpio
make
sudo make install
sudo ldconfig

# Ensure the Python module is available (some distros/paths differ)
echo "-> Verifying Python can import pigpio..."
if ! python3 -c "import pigpio" >/dev/null 2>&1; then
  echo "-> pigpio import failed; installing pigpio.py into dist-packages"
  # pigpio.py is in the repo root after clone
  PY_SITE="$(python3 -c 'import sysconfig; print(sysconfig.get_paths()[\"purelib\"])')"
  sudo install -m 0644 pigpio.py "${PY_SITE}/pigpio.py"
fi

# -------------------------
# Create/enable pigpiod systemd service
# -------------------------
echo "[5/6] Installing and enabling pigpiod systemd service..."
sudo tee /etc/systemd/system/pigpiod.service >/dev/null <<'EOF'
[Unit]
Description=Pigpio daemon
After=network.target

[Service]
Type=forking
ExecStart=/usr/local/bin/pigpiod
ExecStop=/bin/kill -s TERM $MAINPID
Restart=on-failure
RestartSec=1s

[Install]
WantedBy=multi-user.target
EOF

sudo systemctl daemon-reload
sudo systemctl enable pigpiod
sudo systemctl restart pigpiod

# -------------------------
# Sanity checks
# -------------------------
echo "[6/6] Sanity checks..."
echo "pigpiod status:"
systemctl --no-pager status pigpiod | head -n 12 || true

python3 - <<'EOF'
import pigpio
pi = pigpio.pi()
print("pigpio module import: OK")
print("pigpiod connected:", bool(pi.connected))
pi.stop()
EOF

echo "=== Setup complete ==="
echo "Reminder: Python deps are OS-managed via apt on trixie. No pip installs were performed."
