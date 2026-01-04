# Championship Squares

Small web app to run a Championship Squares game. Works on Linux, macOS, Windows and Raspberry Pi (3+).

**Quick overview**
- Start the server from a Python virtual environment or use the provided `start_server.sh` launcher.

**Requirements**
- Python 3.7+
- Flask (installed via `requirements.txt`)
- Web browser with JavaScript enabled

Installation
------------
1. Clone the repository:

```bash
git clone https://github.com/bilbilivo/championship-squares.git
cd championship-squares
```

2. Create and activate a virtual environment (recommended):

Unix / macOS / Raspberry Pi:

```bash
python3 -m venv venv
source venv/bin/activate
```

Windows (PowerShell):

```powershell
python -m venv venv
venv\Scripts\Activate.ps1
```

3. Install dependencies:

```bash
pip install -r requirements.txt
```

Running the app
---------------

Unix / macOS / Raspberry Pi:

Preferred: use the launcher which activates the `venv` and manages the process:
```bash
./start_server.sh start
./start_server.sh status
./start_server.sh stop
```

Windows (PowerShell):

run directly inside an activated venv:
```bash
python app.py
```

Open a browser to:
- `http://localhost:8080` (default)

Notes for Raspberry Pi
----------------------
- `config.py` writes a `config.json` with a Raspberry Pi-specific entry (port 8080). Adjust it if needed.
- The app tries to open a browser when started; on headless devices this will fail harmlessly — the server still runs.

Files of interest
-----------------
- `app.py` — main application
- `config.py` — platform-aware configuration
- `start_server.sh` — launcher that activates `venv` and manages the process
- `requirements.txt` — Python dependencies

License
-------
MIT

Contributing
------------
Contributions welcome. Please open issues or submit pull requests.
