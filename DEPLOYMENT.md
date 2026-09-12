# Deployment Guide

## Overview

Championship Squares is a lightweight Python Flask application suitable for running on local machines, small servers, or cloud platforms. This guide covers production deployment scenarios.

---

## System Requirements

### Minimum
- Python 3.10 or later
- 512 MB RAM
- Single CPU core
- 100 MB disk space

### Recommended
- Python 3.10+
- 2 GB RAM
- 2+ CPU cores
- 500 MB disk space (logs)

### Operating Systems
- Linux (Ubuntu 18.04+, CentOS 7+, Debian 10+)
- macOS (10.14+)
- Windows 10/11

---

## Local Deployment

### Standard Setup

1. **Clone repository:**
   ```bash
   git clone <repository-url>
   cd championship-squares
   ```

2. **Create and activate virtual environment** (REQUIRED):
   ```bash
   python3 -m venv venv
   source venv/bin/activate  # Linux/macOS
   # or
   venv\Scripts\activate  # Windows
   ```

3. **Install dependencies:**
   ```bash
   pip install .
   ```

4. **Run server:**
   ```bash
   python app.py
   ```

Server starts on `http://localhost:8080` (Windows/macOS) or network-accessible on Linux.

**Important:** Always use a virtual environment to isolate project dependencies from your system Python. Never install dependencies globally with `pip install` directly on your system.

### Launcher Scripts

For convenience, use provided launcher scripts:

**Linux/macOS:**
```bash
./start_server.sh
```

**Windows:**
```powershell
.\start_server.ps1
```

These scripts automate venv activation and dependency installation.

---

## Network Access

### Windows/macOS Local Only
By default, server is accessible only from localhost. To allow network access:

Edit `config.py`:
```python
platform_hosts = {
    'windows': '0.0.0.0',  # Change from 'localhost'
    'linux': '0.0.0.0',
    'darwin': '0.0.0.0'     # Change from 'localhost'
}
```

### Linux Network Access
Default configuration (`0.0.0.0`) allows network access. Verify firewall allows port 8080:

```bash
# Check if port is open
sudo ufw allow 8080

# Or check iptables
sudo iptables -L -n | grep 8080
```

---

## Production Deployment

Championship Squares uses one threaded Waitress process. Start it with the provided
launcher scripts or `python app.py`; Flask's development server is reserved for
loopback-only development.

### Using Launcher Scripts (Recommended)

The provided launcher scripts handle virtual environment setup, dependency installation, and server startup.

**Linux/macOS:**
```bash
./start_server.sh
```

**Windows:**
```powershell
.\start_server.ps1
```

These scripts:
- Create virtual environment if needed
- Install dependencies from pyproject.toml
- Activate virtual environment
- Start Waitress on port 8080

### Manual Startup

If you prefer to run the application directly:

```bash
python app.py
```

This starts Waitress with configuration from `config.py`, 32 request threads, bounded
request sizes, and one shared in-process game state.

### Reverse proxies and public hosting

Do not publish this passwordless-ADMIN application through a generic reverse proxy.
The trusted LAN is the security boundary, and proxying all clients through loopback
can erase the address information used to enforce it. Public remote access is
supported only through the built-in player-only Cloudflare Quick Tunnel described in
`CLOUDFLARE.md`.

Multi-device play uses `/api/events` (server-sent events). Each active browser
keeps one connection open and fetches state when a saved change is announced.
Reconnections and returning to a hidden tab refresh state automatically; polling
every five seconds is used only when the event connection is unavailable.

Run **one server process with threading enabled** (the `python app.py` launcher
does this). Game state and notifications are shared in memory between its threads.
Do not use multiple worker processes or replicas with this implementation. A WSGI
server needs enough threads for the connected browsers plus ordinary API requests.
Multiple workers would require shared state and a shared notification broker.

---

## Docker Deployment

### Dockerfile

Create `Dockerfile` in project root:

```dockerfile
FROM python:3.10-slim

WORKDIR /app

COPY pyproject.toml .
RUN pip install --no-cache-dir .

COPY . .

EXPOSE 8080

CMD ["python", "app.py"]
```

### Build and Run

```bash
# Build image
docker build -t championship-squares:latest .

# Run container
docker run -d \
  -p 8080:8080 \
  -v $(pwd)/game_state.db:/app/game_state.db \
  --name championship-squares \
  championship-squares:latest
```

**Docker Compose** (`docker-compose.yml`):

```yaml
version: '3.8'

services:
  app:
    build: .
    ports:
      - "8080:8080"
    volumes:
      - ./game_state.db:/app/game_state.db
    restart: unless-stopped
    environment:
      - FLASK_ENV=production
```

Run with:
```bash
docker-compose up -d
```

---

## Cloud Platforms

Generic cloud hosting is unsupported because it would expose passwordless ADMIN or
require trusting proxy headers from infrastructure outside the app's current threat
model. Use the Quick Tunnel for remote players. A conventional public deployment
requires authenticated ADMIN access and an explicit trusted-proxy configuration first.

---

## Configuration for Production

### Environment Variables

Set via `.env` file or system environment:

```bash
FLASK_ENV=production
LITE_MODE=0
MAX_PLAYERS=20
```

**In app startup:**
```python
import os
LITE_MODE = os.environ.get('LITE_MODE', '0') == '1'
MAX_PLAYERS = int(os.environ.get('MAX_PLAYERS', 12))
```

### Database Backup

Game state stored in `game_state.db`. Backup strategies:

**Daily backup:**
```bash
# Cron job (add to crontab)
0 2 * * * cp /opt/championship-squares/game_state.db \
                /backup/game_state.$(date +\%Y\%m\%d).db
```

**Cloud backup:**
- Upload `game_state.db` to S3 regularly
- Use rsync to remote backup server
- Database service (if migrating from SQLite)

---

## Monitoring & Logging

### Application Logs

Waitress and the application log requests and errors to the terminal. To capture logs to a file:

**Linux/macOS:**
```bash
./start_server.sh > championship-squares.log 2>&1 &
```

**Windows (PowerShell):**
```powershell
.\start_server.ps1 | Tee-Object -FilePath championship-squares.log
```

Or redirect manually:
```bash
python app.py > /var/log/championship-squares/app.log 2>&1
```

### Health Check Endpoint

Test server availability:

```bash
curl http://localhost:8080/
```

Monitor with uptime/health check service:

```bash
# Every 5 minutes
*/5 * * * * curl -f http://localhost:8080/ || systemctl restart championship-squares
```

### Metrics

No built-in metrics. For production monitoring, consider:
- Prometheus + Grafana
- New Relic APM
- Datadog
- CloudWatch (AWS)

---

## Performance Tuning

### Server Configuration

The normal entry point uses 32 Waitress threads and a 100-connection ceiling. This
leaves capacity for the app's long-lived local SSE connections while bounding abuse.

**In config.py:**
```python
self.config = {
    'debug': False,           # Always False in production
    'max_players': 12,        # Increase if needed
}
```

**Environment variables:**
```bash
FLASK_ENV=production
LITE_MODE=1  # Disable animations for better performance
```

### Memory Optimization

Monitor memory per process:

```bash
# Current processes
ps aux | grep python

# Check resource usage
top -p $(pgrep -f "python app.py")
```

Flask typically uses 50-100 MB per instance. Enable lite mode for reduced memory:

```bash
LITE_MODE=1 ./start_server.sh
```

## Security Considerations

### Port 8080 Only

The application has session-based ADMIN/PLAYER permissions, but mode selection has
no password or identity verification: anyone on the host or LAN can select ADMIN.
The LAN is therefore the security boundary. Use only a trusted private network; do
not run on public Wi-Fi or expose port 8080 to the Internet.

### HTTPS

LAN play uses local HTTP. The supported Quick Tunnel terminates public HTTPS at
Cloudflare and receives HSTS responses; do not expose the HTTP origin port publicly.

### File Permissions

Secure game state file:

```bash
chmod 600 game_state.db
chown www-data:www-data game_state.db
```

### Rate Limiting

Verified tunnel traffic is limited in-process. Public traffic receives a general
120-request/minute bucket per authenticated player or pre-login client address;
registration attempts and authenticated player reads or mutations have stricter
buckets. Requests over 16 KiB receive HTTP 413, and throttled requests receive HTTP
429 with `Retry-After`.

---

## Troubleshooting Deployment

### Port Already in Use

```bash
# Find process using port 8080
lsof -i :8080

# Kill process
kill -9 <PID>

# Or use different port
# Edit config.py: 'port': 9000
python app.py
```

### Permission Denied

```bash
# Fix file permissions
chmod +x start_server.sh
chmod 755 /opt/championship-squares

# Check directory ownership
ls -la /opt/championship-squares
```

### Connection Refused

```bash
# Verify server running
ps aux | grep python

# Check firewall
sudo ufw status
sudo ufw allow 8080
```

### Slow Performance

```bash
# Enable lite mode for faster rendering
LITE_MODE=1 ./start_server.sh

# Check system resources
free -h
```

---

## Disaster Recovery

### State File Corruption

If `game_state.db` corrupted:

1. Stop application
2. Restore from backup
3. Restart application
4. Verify game loads

If no backup:
```bash
rm game_state.db
# Application recreates on next start with fresh state
```

### Database Migration

To migrate to another database (future):
1. Keep SQLite as fallback
2. Load from SQLite, write to new database
3. Test thoroughly before switching
4. Keep SQLite backup during migration

---

## Maintenance

### Regular Tasks

**Weekly:**
- Monitor disk space
- Check error logs
- Test game functionality

**Monthly:**
- Backup game_state.db
- Review server performance
- Update dependencies if needed

**Quarterly:**
- Security updates
- Performance optimization
- Capacity planning

---

## Scaling Considerations

### Single Server Limitation

Current design (SQLite storage) limited to:
- Single server instance
- No distributed state
- Not suitable for 1000+ concurrent players

### Future Scaling

To scale beyond current limits:
1. Migrate to client-server database (PostgreSQL)
2. Add caching layer (Redis)
3. Load balance with nginx/HAProxy
4. Consider microservices for game instances
