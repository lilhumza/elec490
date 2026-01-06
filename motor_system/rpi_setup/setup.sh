#!/usr/bin/env bash
set -e

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
echo "[1/5] Updating system packages..."
sudo apt-get update -y
sudo apt-get upgrade -y

# -------------------------
# System dependencies
# -------------------------
echo "[2/5] Installing OS-level dependencies..."
sudo apt-get install -y \
  python3 \
  python3-pip \
  pigpio \
  python3-pigpio \
  curl \
  git

# -------------------------
# Enable pigpio daemon
# -------------------------
echo "[3/5] Enabling pigpio daemon..."
sudo systemctl enable pigpiod
sudo systemctl start pigpiod

# -------------------------
# Pip tooling
# -------------------------
echo "[4/5] Upgrading pip..."
sudo python3 -m pip install --upgrade pip setuptools wheel

# -------------------------
# Python dependencies
# -------------------------
echo "[5/5] Installing Python requirements..."
sudo python3 -m pip install -r "${REQ_FILE}"

echo "=== Setup complete ==="
echo "pigpiod status:"
systemctl --no-pager status pigpiod | head -n 10
