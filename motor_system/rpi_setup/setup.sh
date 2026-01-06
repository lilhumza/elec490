#!/usr/bin/env bash
set -euo pipefail

echo "=== Raspberry Pi system setup ==="

# -------------------------
# Resolve script directory
# -------------------------
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REQ_FILE="${SCRIPT_DIR}/requirements.txt"

# -------------------------
# Check requirements.txt
# -------------------------
if [ ! -f "${REQ_FILE}" ]; then
  echo "ERROR: requirements.txt not found in ${SCRIPT_DIR}"
  echo "Ensure requirements.txt is in the same directory as setup.sh"
  exit 1
fi

echo "Using requirements file: ${REQ_FILE}"

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
  python3-pip \
  python3-dev \
  build-essential \
  git \
  curl \
  ca-certificates

# -------------------------
# Build + install pigpio from source
# -------------------------
echo "[3/6] Building and installing pigpio from source..."
cd /tmp
sudo rm -rf /tmp/pigpio
git clone https://github.com/joan2937/pigpio.git
cd pigpio
make
sudo make install
sudo ldconfig

# -------------------------
# Create/enable pigpiod systemd service (minimal + reliable)
# Source: https://github.com/joan2937/pigpio/issues/632#issuecomment-3379034242
# -------------------------
echo "[4/6] Installing and enabling pigpiod systemd service..."
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
# Pip tooling
# -------------------------
echo "[5/6] Upgrading pip tooling..."
sudo python3 -m pip install --upgrade pip setuptools wheel

# -------------------------
# Python dependencies
# -------------------------
echo "[6/6] Installing Python requirements..."
sudo python3 -m pip install -r "${REQ_FILE}"

# -------------------------
# Sanity checks
# -------------------------
echo "=== Sanity checks ==="
echo "pigpiod status:"
systemctl --no-pager status pigpiod | head -n 12 || true

echo "Python pigpio import test:"
python3 - <<'EOF'
import pigpio
pi = pigpio.pi()
print("Connected:", bool(pi.connected))
pi.stop()
EOF

echo "=== Setup complete ==="
