# Championship Squares

Small web app to run a Championship Squares game. Works on Linux, macOS, and Windows.

**Quick overview**
- Clone the repo and run the launcher. It creates the virtual environment and installs dependencies automatically on first run.

**Requirements**
- Python 3.7+
- Web browser with JavaScript enabled

Installation
------------
Clone the repository:

```bash
git clone https://github.com/bilbilivo/championship-squares.git
cd championship-squares
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

Both launchers support `--lite` / `--no-lite` flags to toggle reduced visual effects, and a `setup` action to create a desktop shortcut for double-click launching:

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
- `requirements.txt` — Python dependencies

License
-------
MIT

Contributing
------------
Contributions welcome. Please open issues or submit pull requests.
