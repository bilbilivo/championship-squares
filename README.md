# Super Bowl Squares

A cross-platform web application for managing Super Bowl squares, compatible with Unix, Windows, and Raspberry Pi.

## Requirements

- Python 3.7+
- Flask
- Web browser with JavaScript enabled

## Installation

1. Clone the repository:
```bash
git clone <repository-url>
cd super-bowl-squares
```

2. Create a virtual environment (recommended):

### Windows
```bash
python -m venv venv
venv\Scripts\activate
```

### Unix/macOS/Raspberry Pi
```bash
python3 -m venv venv
source venv/bin/activate
```

3. Install required packages:
```bash
pip install -r requirements.txt
```

## Configuration

The application automatically creates a `config.json` file with platform-specific settings. You can modify these settings:

```json
{
    "windows": {
        "host": "localhost",
        "port": 5000
    },
    "linux": {
        "host": "0.0.0.0",
        "port": 5000
    },
    "darwin": {
        "host": "localhost",
        "port": 5000
    },
    "raspberry_pi": {
        "host": "0.0.0.0",
        "port": 8080
    }
}
```

## Running the Application

1. Start the server:

### Windows
```bash
python app.py
```

### Unix/macOS/Raspberry Pi
```bash
python3 app.py
```

2. Open a web browser and navigate to:
- Windows/macOS: `http://localhost:5000`
- Linux/Raspberry Pi: `http://<your-ip-address>:5000` (or port 8080 for Raspberry Pi)

## Features

- Cross-platform compatibility
- Automatic configuration based on platform
- Persistent game state
- Error handling for robustness
- Responsive web interface
- Support for multiple players
- Color-coded player squares
- Automatic team color management

## Directory Structure

```
super-bowl-squares/
├── app.py              # Main application file
├── config.py           # Configuration management
├── requirements.txt    # Python dependencies
├── templates/          # HTML templates
│   └── index.html     # Main interface template
├── static/            # Static files (if any)
└── game_state.json    # Persistent game state
```

## Troubleshooting

1. Port in Use:
   - Windows: Change port in config.json or close competing application
   - Unix/Linux: `sudo lsof -i :5000` to find and kill competing process
   - Raspberry Pi: Change port in config.json (default 8080)

2. Permission Issues:
   - Unix/Linux/Raspberry Pi: Ensure proper file permissions with `chmod`
   - Windows: Run as administrator if needed

3. Template Not Found:
   - Ensure index.html is in the templates directory
   - Check file permissions
   - Verify path separators are correct for your OS

## License

MIT license

## Contributing

[Contributing Guidelines Here]