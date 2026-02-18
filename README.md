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
```

Windows (PowerShell):

```powershell
powershell -ExecutionPolicy Bypass -File .\start_server.ps1 start
powershell -ExecutionPolicy Bypass -File .\start_server.ps1 status
powershell -ExecutionPolicy Bypass -File .\start_server.ps1 stop
```

Both launchers allow toggling reduced visual effects with the `--lite` or `--no-lite` flags. You can also use the `setup` action to create a desktop shortcut for easy launching.

```bash
./start_server.sh setup                                              # Unix / macOS
powershell -ExecutionPolicy Bypass -File .\start_server.ps1 setup    # Windows
```

The app opens `http://localhost:8080` in your default browser automatically on start.

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
