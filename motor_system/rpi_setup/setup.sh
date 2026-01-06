#!/usr/bin/env bash
set -euo pipefail

echo "=== Raspberry Pi system setup (OS-managed Python, pigpio from source) ==="

# -------------------------
# OS update
# -------------------------
echo "[1/5] Updating system packages..."
sudo apt-get update -y
sudo apt-get upgrade -y

# -------------------------
# Base + build dependencies
# -------------------------
echo "[2/5] Installing OS-level dependencies..."
sudo apt-get install -y \
  python3 \
  python3-dev \
  python3-pip \
  build-essential \
  git \
  curl \
  ca-certificates \
  python3-requests

# -------------------------
# Build + install pigpio from source
# -------------------------
echo "[3/5] Building and installing pigpio from source..."
cd /tmp
sudo rm -rf /tmp/pigpio
git clone https://github.com/joan2937/pigpio.git
cd pigpio
make
sudo make install
sudo ldconfig

# Ensure the Python module is importable (paths can vary by distro)
echo "-> Verifying Python can import pigpio..."
if ! python3 -c "import pigpio" >/dev/null 2>&1; then
  echo "-> pigpio import failed; installing pigpio.py into Python site-packages"
  PY_SITE="$(python3 -c 'import sysconfig; print(sysconfig.get_paths()["purelib"])')"
  sudo install -m 0644 pigpio.py "${PY_SITE}/pigpio.py"
fi

# -------------------------
# Create/enable pigpiod systemd service
# -------------------------
echo "[4/5] Installing and enabling pigpiod systemd service..."
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
echo "[5/5] Sanity checks..."
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
