# Deployment Guide

## Overview

Championship Squares is a lightweight Python Flask application suitable for running on local machines, small servers, or cloud platforms. This guide covers production deployment scenarios.

---

## System Requirements

### Minimum
- Python 3.7+
- 512 MB RAM
- Single CPU core
- 100 MB disk space

### Recommended
- Python 3.9+
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

2. **Create virtual environment:**
   ```bash
   python3 -m venv venv
   source venv/bin/activate  # Linux/macOS
   # or
   venv\Scripts\activate  # Windows
   ```

3. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

4. **Run server:**
   ```bash
   python app.py
   ```

Server starts on `http://localhost:8080` (Windows/macOS) or network-accessible on Linux.

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

### Using Gunicorn

For production, replace Flask's development server with Gunicorn:

**Install Gunicorn:**
```bash
pip install gunicorn
```

**Run server:**
```bash
gunicorn -w 4 -b 0.0.0.0:8080 app:app
```

**Parameters:**
- `-w 4` - Use 4 worker processes (adjust for your CPU cores)
- `-b 0.0.0.0:8080` - Bind to all interfaces on port 8080
- `app:app` - Load the Flask app

**Recommended settings for scalability:**
```bash
gunicorn \
  -w 4 \
  -b 0.0.0.0:8080 \
  --timeout 120 \
  --access-logfile - \
  --error-logfile - \
  app:app
```

### Using systemd (Linux)

Create systemd service file `/etc/systemd/system/championship-squares.service`:

```ini
[Unit]
Description=Championship Squares
After=network.target

[Service]
Type=notify
User=www-data
WorkingDirectory=/opt/championship-squares
ExecStart=/opt/championship-squares/venv/bin/gunicorn \
  -w 4 \
  -b 0.0.0.0:8080 \
  app:app
Restart=on-failure
RestartSec=10

[Install]
WantedBy=multi-user.target
```

**Enable and start:**
```bash
sudo systemctl daemon-reload
sudo systemctl enable championship-squares
sudo systemctl start championship-squares
sudo systemctl status championship-squares
```

### Reverse Proxy (nginx)

Use nginx to proxy requests and handle SSL:

**Nginx config** `/etc/nginx/sites-available/championship-squares`:

```nginx
upstream championship_squares {
    server 127.0.0.1:8080;
}

server {
    listen 80;
    server_name example.com;

    location / {
        proxy_pass http://championship_squares;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    location /api/ {
        proxy_pass http://championship_squares;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    }
}
```

**Enable site:**
```bash
sudo ln -s /etc/nginx/sites-available/championship-squares \
           /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl restart nginx
```

### SSL/TLS with Let's Encrypt

Use Certbot for free SSL certificates:

```bash
sudo apt install certbot python3-certbot-nginx
sudo certbot --nginx -d example.com
```

Certbot automatically updates nginx config with SSL.

---

## Docker Deployment

### Dockerfile

Create `Dockerfile` in project root:

```dockerfile
FROM python:3.9-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8080

CMD ["gunicorn", "-w", "4", "-b", "0.0.0.0:8080", "app:app"]
```

### Build and Run

```bash
# Build image
docker build -t championship-squares:latest .

# Run container
docker run -d \
  -p 8080:8080 \
  -v $(pwd)/game_state.json:/app/game_state.json \
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
      - ./game_state.json:/app/game_state.json
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

### Heroku

1. **Install Heroku CLI**
2. **Create Procfile:**
   ```
   web: gunicorn -w 4 -b 0.0.0.0:$PORT app:app
   ```
3. **Create app and deploy:**
   ```bash
   heroku create championship-squares
   git push heroku main
   ```

### AWS EC2

1. Launch Ubuntu 20.04 instance
2. Install Python 3.9+
3. Clone repository
4. Use systemd service (see above)
5. Attach security group allowing ports 80, 443, 8080

### DigitalOcean App Platform

1. Connect GitHub repository
2. Auto-detect Python
3. Set run command: `gunicorn -w 4 -b 0.0.0.0:8080 app:app`
4. Configure environment (optional)
5. Deploy

### PythonAnywhere

1. Upload repository files
2. Configure Python web app (Flask)
3. Point WSGI file to app.py
4. Reload web app
5. Access via provided URL

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

Game state stored in `game_state.json`. Backup strategies:

**Daily backup:**
```bash
# Cron job (add to crontab)
0 2 * * * cp /opt/championship-squares/game_state.json \
                /backup/game_state.$(date +\%Y\%m\%d).json
```

**Cloud backup:**
- Upload `game_state.json` to S3 regularly
- Use rsync to remote backup server
- Database service (if migrating from JSON)

---

## Monitoring & Logging

### Application Logs

Redirect to file:

```bash
gunicorn \
  -w 4 \
  -b 0.0.0.0:8080 \
  --access-logfile /var/log/championship-squares/access.log \
  --error-logfile /var/log/championship-squares/error.log \
  app:app
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

### Gunicorn Workers

Calculate optimal workers:
```
Workers = (2 × CPU cores) + 1
```

Example (4 cores):
```bash
gunicorn -w 9 -b 0.0.0.0:8080 app:app
```

### Memory Optimization

Monitor memory per process:

```bash
# Current processes
ps aux | grep gunicorn

# Set memory limit (systemd)
MemoryLimit=512M  # In service file
```

### Caching Headers

Add to nginx reverse proxy:

```nginx
location /static/ {
    expires 30d;
    add_header Cache-Control "public, immutable";
}
```

---

## Security Considerations

### Port 8080 Only

Application has no built-in authentication. Deploy with:
- Reverse proxy (nginx with auth)
- VPN/firewall (restrict IP access)
- Local network only (trusted users)

### HTTPS Required

Always use HTTPS in production:
- Self-signed certificates (internal)
- Let's Encrypt (public)
- AWS ACM (AWS deployments)

### File Permissions

Secure game state file:

```bash
chmod 600 game_state.json
chown www-data:www-data game_state.json
```

### Rate Limiting

Add rate limiting to nginx:

```nginx
limit_req_zone $binary_remote_addr zone=api_limit:10m rate=10r/s;

location /api/ {
    limit_req zone=api_limit burst=20 nodelay;
    proxy_pass http://championship_squares;
}
```

---

## Troubleshooting Deployment

### Port Already in Use

```bash
# Find process using port 8080
lsof -i :8080

# Kill process
kill -9 <PID>

# Or use different port
gunicorn -b 0.0.0.0:9000 app:app
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
ps aux | grep gunicorn

# Check firewall
sudo ufw status
sudo ufw allow 8080
```

### Slow Performance

```bash
# Increase workers
gunicorn -w 8 -b 0.0.0.0:8080 app:app

# Use lite mode for testing
LITE_MODE=1 gunicorn -w 4 -b 0.0.0.0:8080 app:app
```

---

## Disaster Recovery

### State File Corruption

If `game_state.json` corrupted:

1. Stop application
2. Restore from backup
3. Restart application
4. Verify game loads

If no backup:
```bash
rm game_state.json
# Application recreates on next start with fresh state
```

### Database Migration

To migrate from JSON to database (future):
1. Keep JSON as fallback
2. Load from JSON, write to database
3. Test thoroughly before switching
4. Keep JSON backup during migration

---

## Maintenance

### Regular Tasks

**Weekly:**
- Monitor disk space
- Check error logs
- Test game functionality

**Monthly:**
- Backup game_state.json
- Review server performance
- Update dependencies if needed

**Quarterly:**
- Security updates
- Performance optimization
- Capacity planning

---

## Scaling Considerations

### Single Server Limitation

Current design (JSON file storage) limited to:
- Single server instance
- No distributed state
- Not suitable for 1000+ concurrent players

### Future Scaling

To scale beyond current limits:
1. Migrate to database (PostgreSQL/MongoDB)
2. Use application server (Gunicorn/uWSGI)
3. Add caching layer (Redis)
4. Load balance with nginx/HAProxy
5. Consider microservices for game instances
