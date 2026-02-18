# CHAMPIONSHIP SQUARES

Small web app to run a Championship Squares game. Works on Linux, macOS, and Windows.

**Quick overview**
- Clone the repo and run the launcher. It creates the virtual environment and installs dependencies automatically on first run.

**Requirements**
- Python 3.10 or later
- Web browser with JavaScript enabled

Installation
------------
Install GitHub CLI if you don't have it:

```bash
# Ubuntu / Debian
sudo apt install gh

# macOS
brew install gh

# Other platforms: https://cli.github.com/
```

Clone the repository:

```bash
gh repo clone bilbilivo/championship-squares
cd championship-squares
```

If you're on Ubuntu/Debian, install the required Python packages:

```bash
sudo apt install python3-venv python3-pip
```

The launchers handle virtual environment creation and dependency installation automatically on first run.

Running the app
---------------

Unix / macOS:

```bash
./start_server.sh start
./start_server.sh status
./start_server.sh stop
./start_server.sh restart
```

Windows (PowerShell):

```powershell
powershell -ExecutionPolicy Bypass -File .\start_server.ps1 start
powershell -ExecutionPolicy Bypass -File .\start_server.ps1 status
powershell -ExecutionPolicy Bypass -File .\start_server.ps1 stop
powershell -ExecutionPolicy Bypass -File .\start_server.ps1 restart
```

The app opens `http://localhost:8080` in your default browser automatically on start.

Pass `--lite` to enable reduced visual effects (useful on slower machines), or `--no-lite` to
explicitly disable it. The setting is persisted across restarts.

```bash
./start_server.sh --lite start
```

Desktop shortcut (install / uninstall)
---------------------------------------

The `install` action creates a desktop shortcut for one-click launching.

**Unix / macOS** — creates a `.desktop` file in the project folder and installs it to
`~/.local/share/applications` so the app appears in your Applications menu:

```bash
./start_server.sh install
./start_server.sh uninstall
```

On first run the launcher runs `install` automatically, so the shortcut is created without
having to call it manually.

**Windows** — creates a `.lnk` shortcut in the project folder:

```powershell
powershell -ExecutionPolicy Bypass -File .\start_server.ps1 install
powershell -ExecutionPolicy Bypass -File .\start_server.ps1 uninstall
```

`uninstall` removes the shortcut (and, on Linux, the Applications menu entry). It does not
remove the virtual environment or any game data.

Files of interest
-----------------
- `app.py` — main application
- `config.py` — platform-aware configuration
- `start_server.sh` — Unix/macOS launcher
- `start_server.ps1` — Windows launcher
- `pyproject.toml` — project metadata and dependencies

License
-------
MIT

Contributing
------------
Contributions welcome. Please open issues or submit pull requests.
