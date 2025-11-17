#!/usr/bin/env bash

set -e
echo "=== AppHost Perjury Integration ==="

# Source location (your cloned repo)
SRC="$PWD"

# Target in AppHost
DST="/opt/apphost/app/native/perjury"
REGISTRY="/opt/apphost/app/registry/apps.json"
APPHOST_SERVICE="apphost.service"

if [ ! -d "$SRC/perjury_app" ]; then
    echo "ERROR: Cannot find perjury_app/ inside $SRC"
    exit 1
fi

echo "→ Creating native directory: $DST"
sudo mkdir -p "$DST"

echo "→ Syncing source code into AppHost..."
sudo rsync -av --delete \
    "$SRC/perjury_app/" \
    "$DST/perjury_app/"

# Ensure logs/data directories are created
sudo mkdir -p "$DST/data"
sudo mkdir -p "$DST/logs"

echo "→ Ensuring permissions..."
sudo chown -R apphost:apphost "$DST"
sudo find "$DST" -type f -exec chmod 640 {} \;
sudo find "$DST" -type d -exec chmod 750 {} \;

echo "→ Registering Perjury in AppHost registry..."
if [ ! -f "$REGISTRY" ]; then
    echo "ERROR: AppHost registry not found at $REGISTRY"
    exit 1
fi

# Add registry entry only if missing
if ! sudo jq -e '.apps[] | select(.id=="perjury")' "$REGISTRY" >/dev/null 2>&1; then
    sudo jq '.apps += [{
        "id": "perjury",
        "name": "Perjury",
        "type": "native",
        "entry": "perjury_app:create_perjury_app",
        "url_prefix": "/perjury"
    }]' "$REGISTRY" | sudo tee "$REGISTRY" >/dev/null
    echo "→ Perjury added to registry."
else
    echo "→ Perjury already exists in registry. Skipping."
fi

# Ensure the app loader can import the module path
echo "→ Checking PYTHONPATH inclusion..."
if ! grep -q "native/perjury" /opt/apphost/app/env.conf 2>/dev/null; then
    echo "PYTHONPATH=/opt/apphost/app/native/perjury:\$PYTHONPATH" | sudo tee -a /opt/apphost/app/env.conf
    echo "→ Added to env.conf"
fi

echo "→ Restarting AppHost..."
sudo systemctl daemon-reload
sudo systemctl restart "$APPHOST_SERVICE"

echo "=== DONE ===
Perjury app installed at: $DST
Accessible at: http://<server-ip>/apps/perjury/
"
