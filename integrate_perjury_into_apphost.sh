#!/usr/bin/env bash
set -euo pipefail

echo "=== AppHost Perjury Native App Integration ==="

SRC="$PWD"
DST="/opt/apphost/app/native/perjury"
APPHOST_SERVICE="apphost.service"
ENV_CONF="/opt/apphost/app/env.conf"
REGISTRY="/opt/apphost/data/apps.json"

# ------------------------------------------------------------------------------
# 1. Validate source
# ------------------------------------------------------------------------------
if [ ! -d "$SRC/perjury_app" ]; then
    echo "ERROR: Cannot find $SRC/perjury_app"
    exit 1
fi

echo "→ Creating native directory: $DST"
sudo mkdir -p "$DST"

# ------------------------------------------------------------------------------
# 2. Sync application code
# ------------------------------------------------------------------------------
echo "→ Syncing Perjury code into AppHost native folder..."
sudo rsync -av --delete \
    "$SRC/perjury_app/" \
    "$DST/perjury_app/"

echo "→ Creating data + logs directories..."
sudo mkdir -p "$DST/data" "$DST/logs"

# ------------------------------------------------------------------------------
# 3. Set correct permissions (www-data:www-data)
# ------------------------------------------------------------------------------
echo "→ Setting ownership and permissions (www-data:www-data)..."
sudo chown -R www-data:www-data "$DST"
sudo find "$DST" -type f -exec chmod 640 {} \;
sudo find "$DST" -type d -exec chmod 750 {} \;

# ------------------------------------------------------------------------------
# 4. Ensure PYTHONPATH includes native perjury directory
# ------------------------------------------------------------------------------
echo "→ Ensuring PYTHONPATH includes native perjury directory..."

if [ -f "$ENV_CONF" ]; then
    if ! grep -q "native/perjury" "$ENV_CONF"; then
        echo "PYTHONPATH=/opt/apphost/app/native/perjury:\$PYTHONPATH" \
            | sudo tee -a "$ENV_CONF" >/dev/null
        echo "→ Added native/perjury to $ENV_CONF"
    else
        echo "→ Already present in $ENV_CONF"
    fi
else
    echo "WARN: $ENV_CONF does not exist; cannot auto-append PYTHONPATH."
fi

# ------------------------------------------------------------------------------
# 5. Update AppHost registry
# ------------------------------------------------------------------------------
echo "→ Updating registry at $REGISTRY..."

if [ ! -f "$REGISTRY" ]; then
    echo "ERROR: Registry file not found at $REGISTRY"
    exit 1
fi

TMP="$(mktemp)"

# Create entry for Perjury app
read -r -d '' NEW_ENTRY <<EOF
{
    "id": "perjury",
    "name": "Perjury",
    "type": "native",
    "module": "perjury_app.app:create_perjury_blueprint",
    "mount": "/perjury"
}
EOF

# Insert only if missing
if grep -q '"id": "perjury"' "$REGISTRY"; then
    echo "→ Registry already contains perjury entry, skipping insert."
else
    echo "→ Adding Perjury to registry."

    # Insert before closing bracket of JSON array
    sudo awk -v entry="$NEW_ENTRY" '
        BEGIN { added=0 }
        /^\]/ {
            print "  ,"
            print "  " entry
            added=1
        }
        { print }
        END { if (!added) print entry }
    ' "$REGISTRY" > "$TMP"

    sudo mv "$TMP" "$REGISTRY"
    sudo chown www-data:www-data "$REGISTRY"
    sudo chmod 640 "$REGISTRY"
fi

# ------------------------------------------------------------------------------
# 6. Restart AppHost
# ------------------------------------------------------------------------------
echo "→ Restarting AppHost service..."
sudo systemctl daemon-reload
sudo systemctl restart "$APPHOST_SERVICE"

echo "=== DONE ==="
echo "Perjury installed at: $DST"
echo "View at: http://<server-ip>/apps/perjury/"
