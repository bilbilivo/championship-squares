# CHAMPIONSHIP SQUARES

Small web app to run a Championship Squares game. Works on Linux, macOS, and Windows.

## Quick start

Clone the repository:

```bash
git clone https://github.com/bilbilivo/championship-squares.git
cd championship-squares
```

On Ubuntu or Debian, install the Python venv support first:

```bash
sudo apt install python3-venv
```

If you are on a very minimal Python install and `python3 -m venv` still complains about missing
`ensurepip`, install:

```bash
sudo apt install python3-full
```

Then start the app:

```bash
./start_server.sh start
```

On first run, the launcher will:

- create a project-local virtual environment in `./venv`
- install the app and its Python dependencies into that virtual environment
- create a desktop shortcut
- start the server and open `http://localhost:8080`

You do not need to run `pip install` system-wide for this project. The launcher is designed to use
its own virtual environment.

## Requirements

- Python 3.10 or later
- Bash on Unix-like systems
- PowerShell on Windows
- A web browser with JavaScript enabled

## Running the app

Unix and macOS:

```bash
./start_server.sh start
./start_server.sh status
./start_server.sh stop
./start_server.sh restart
```

Windows PowerShell:

```powershell
powershell -ExecutionPolicy Bypass -File .\start_server.ps1 start
powershell -ExecutionPolicy Bypass -File .\start_server.ps1 status
powershell -ExecutionPolicy Bypass -File .\start_server.ps1 stop
powershell -ExecutionPolicy Bypass -File .\start_server.ps1 restart
```

The app opens `http://localhost:8080` in your default browser automatically on start.

## Lite mode

Use `--lite` to reduce visual effects on slower hardware. Use `--no-lite` to switch back.
End-game fireworks start automatically and run until the celebration closes,
including in lite mode and when the browser reports reduced motion. Other effects
continue to respect those settings.
The setting is persisted across restarts.

```bash
./start_server.sh --lite start
./start_server.sh restart
./start_server.sh --no-lite restart
```

## If setup was interrupted

If you previously ended up with a partial or broken `venv`, the launcher should repair it
automatically. If you still want to reset it manually, remove it and start again:

```bash
rm -rf venv
./start_server.sh start
```

This is the safest fix for errors such as:

- `ModuleNotFoundError: No module named 'flask'`
- `externally-managed-environment`

Those errors usually mean the launcher was not using the project virtual environment correctly, or
that an earlier setup attempt left the virtual environment incomplete.

## Visual design guideline

Prioritize **more content, less empty space** while preserving the retro look. Use compact player rows, modest gaps and padding, and responsive layouts that make full use of the screen. Keep text readable and touch controls easy to use; avoid decorative whitespace that reduces room for the board or players.

## Board navigation

- The board starts with readable square cells. Drag to pan, scroll or pinch to zoom, or use the **− / +** buttons.
- Zoom out as far as the full-board scale. The board stays flush with the top and left score axes; unused space remains on the right or bottom. Selecting a cell smaller than 24px zooms in before allowing a claim.
- **Go to score** brings the current score into view at a readable size.
- Player rows show an initial badge, name, and remaining/total allocation, such as **40/40**.
- With the board focused, use arrow keys to pan and **+ / −** to zoom.
- On smaller screens, scroll to the player controls and use **Players** to collapse or expand the panel.

The layout adapts to the available window space while keeping the retro theme. System reduced-motion preferences are respected alongside the existing lite mode.

## Desktop shortcut

The `install` action creates a desktop shortcut for one-click launching.

Unix and macOS:

```bash
./start_server.sh install
./start_server.sh uninstall
```

On Linux, this creates a `.desktop` file in the project folder and installs it to
`~/.local/share/applications` so the app appears in your Applications menu. The launcher also runs
`install` automatically on first run.

Windows:

```powershell
powershell -ExecutionPolicy Bypass -File .\start_server.ps1 install
powershell -ExecutionPolicy Bypass -File .\start_server.ps1 uninstall
```

`uninstall` removes the shortcut. It does not remove the virtual environment or game data.

## Files of interest

- `app.py` - main application
- `config.py` - platform-aware configuration
- `start_server.sh` - Unix and macOS launcher
- `start_server.ps1` - Windows launcher
- `pyproject.toml` - project metadata and dependencies

## More documentation

- `API_DOCUMENTATION.md`
- `CONFIGURATION.md`
- `DEPLOYMENT.md`
- `TESTING.md`
- `TROUBLESHOOTING.md`

## License

MIT

## Trademark notice

Team names, league names, and related trademarks are the property of their respective owners.
This project is not affiliated with or endorsed by any professional sports league or team.

## Support

If you find this project useful, consider supporting it:

[![Donate](https://img.shields.io/badge/Donate-PayPal-blue.svg)](https://paypal.me/bilbilivo)

## Contributing

Contributions welcome. Please open issues or submit pull requests.
