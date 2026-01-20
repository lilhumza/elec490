#!/usr/bin/env bash
set -euo pipefail

echo "=== Raspberry Pi 5 system setup (OS-managed Python, lgpio from source) ==="

# -------------------------
# OS update
# -------------------------
echo "[1/4] Updating system packages..."
sudo apt-get update -y
sudo apt-get upgrade -y

# -------------------------
# Base + build dependencies
# (No pip installs; keep OS-managed Python)
# -------------------------
echo "[2/4] Installing OS-level dependencies..."
sudo apt-get install -y \
  python3 \
  python3-dev \
  python3-pip \
  build-essential \
  make \
  gcc \
  git \
  curl \
  ca-certificates \
  unzip \
  swig \
  python3-setuptools \
  python3-requests

# -------------------------
# Build + install lgpio from source
# -------------------------
echo "[3/4] Building and installing lgpio from source..."
cd /tmp
sudo rm -rf /tmp/lg-master /tmp/master.zip

wget -q https://github.com/joan2937/lg/archive/master.zip -O /tmp/master.zip
unzip -q /tmp/master.zip -d /tmp
cd /tmp/lg-master

make
sudo make install
sudo ldconfig

# -------------------------
# Sanity checks
# -------------------------
echo "[4/4] Sanity checks..."
python3 - <<'EOF'
import lgpio
print("lgpio module import: OK")
EOF

echo "GPIO chips present:"
ls -l /dev/gpiochip* 2>/dev/null || true

echo "=== Setup complete ==="
