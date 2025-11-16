# Perjury App (native Flask app)

A secure, single-use PIN-protected image viewer with IP blocking, token-based access,
and an administrative control panel.

## Features

- One-time token view:
  - Token + PIN required
  - On success:
    - token is permanently marked as used
    - viewer IP is permanently blocked
    - optional global lockout for all IPs
- 10-second (configurable) view window with automatic redirect
- Flat-file JSON storage:
  - `settings.json`
  - `tokens.json`
  - `blocks.json`
  - `log.json`
- Native Flask app that can run:
  - Standalone (`python main.py`)
  - As a blueprint under AppHost (see below)

## Data directory

By default, the app stores data under:

- If `PERJURY_DATA_DIR` is set: that path
- Else if `APPHOST_DATA_DIR` is set: `$APPHOST_DATA_DIR/perjury`
- Else: `perjury_app/data/` (local, created automatically)

## Running standalone

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
python main.py
```

Then open:

- http://127.0.0.1:5000/           (info)
- http://127.0.0.1:5000/control/   (control panel)
- http://127.0.0.1:5000/view/<token>  (one-time view)
```

# AppHost integration (native app mode)

1. Push this project to GitHub, for example:

   - Repository: `https://github.com/<yourname>/perjury-app`

2. On your AppHost server, install the package inside the AppHost venv:

```bash
cd /opt/apphost/app
source venv/bin/activate
pip install git+https://github.com/<yourname>/perjury-app.git
```

3. Edit `apphost/apps_app.py` in the AppHost code and register the blueprint:

```python
# at the top
from perjury_app import create_perjury_blueprint

# inside create_apps_app():
def create_apps_app():
    app = Flask("apps_app", template_folder=TEMPLATE_DIR, static_folder=STATIC_DIR)

    # Register Perjury under /apps/perjury/
    perjury_bp = create_perjury_blueprint()
    app.register_blueprint(perjury_bp, url_prefix="/perjury")

    @app.route("/")
    def apps_index():
        apps = list_apps()
        return render_template("apps/index.html", apps=apps)

    # (rest of existing routes)
    ...
```

4. Create a Perjury entry in AppHost (optional, for listing):

   - Go to `http://<server>/admin/`
   - Create a new app:
     - slug: `perjury`
     - name: `Perjury App`
     - type: `native`
     - description: whatever you like

   Then you can manually edit the Apps template to link to `/apps/perjury/` if desired.

5. Restart AppHost:

```bash
sudo systemctl restart apphost
```

Now Perjury is available at:

- `http://<server>/apps/perjury/`         (info + instructions)
- `http://<server>/apps/perjury/control/` (control panel; protect at Nginx)
- `http://<server>/apps/perjury/view/<token>` (one-time view)
```

## Security notes

- Protect `/apps/perjury/control/` at Nginx level (IP allowlist, HTTP basic auth, VPN, etc.).
- The app is intentionally minimal and file-based; you can extend it with:
  - hashed PINs
  - AES encryption at rest
  - database-backed storage
  - audit exports
