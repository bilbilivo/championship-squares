# Troubleshooting Guide

## General Issues

### Server Won't Start

**Problem:** "Address already in use" or port binding error

**Solutions:**
1. Check if server already running:
   ```bash
   ps aux | grep python
   ```
2. Kill existing process:
   ```bash
   kill -9 <PID>
   ```
3. Use different port in config.py:
   ```python
   'port': 9000  # Change from 8080
   ```
4. On Windows/macOS, try restarting the machine

---

### Cannot Connect to Server

**Problem:** "Connection refused" or browser shows error

**Possible Causes:**
- Server not running
- Wrong host/port
- Firewall blocking
- Network access issue

**Solutions:**

1. **Verify server running:**
   ```bash
   python app.py
   # Should see "Running on http://..."
   ```

2. **Check connection locally:**
   ```bash
   curl http://localhost:8080/
   ```

3. **Windows/macOS can't access from another machine:**
   - Change host in `config.py` from 'localhost' to '0.0.0.0'
   - Restart server

4. **Linux network access blocked:**
   ```bash
   sudo ufw allow 8080
   # or check iptables
   sudo iptables -I INPUT -p tcp --dport 8080 -j ACCEPT
   ```

5. **Try different port:**
   ```bash
   # Edit config.py
   'port': 9000
   ```
   Then access at `http://localhost:9000/`

---

### Browser Shows Blank/Error Page

**Problem:** White screen, JavaScript error, or 404

**Possible Causes:**
- Template file missing
- JavaScript error
- CSS not loading
- Browser cache issue

**Solutions:**

1. **Clear browser cache:**
   - Chrome/Edge: Ctrl+Shift+Delete
   - Firefox: Ctrl+Shift+Delete
   - Safari: Cmd+Shift+Delete

2. **Check browser console for errors:**
   - Press F12
   - Click "Console" tab
   - Look for red error messages

3. **Verify template exists:**
   ```bash
   ls -la templates/index.html
   ```

4. **Check server logs:**
   - Terminal running server should show errors
   - Look for lines starting with "ERROR"

5. **Try different browser:**
   - Test in Chrome, Firefox, Safari
   - Check if issue is browser-specific

---

## Game State Issues

### Game Won't Load/Reset

**Problem:** Game state not persisting or reset button doesn't work

**Possible Causes:**
- File permission issue
- Corrupted database file
- Disk full
- Invalid sport configuration

**Solutions:**

1. **Check file permissions:**
   ```bash
   ls -l game_state.db
   # Should be writable by current user
   chmod 644 game_state.db
   ```

2. **Check if disk full:**
   ```bash
   df -h
   # Look for 100% usage
   ```

3. **Repair corrupted state file:**
   ```bash
   # Delete corrupted file (fresh start)
   rm game_state.db
   # Server recreates on next start
   ```

4. **Verify Database integrity:**
   ```bash
   sqlite3 game_state.db "PRAGMA integrity_check;"
   # Should return "ok"
   ```

---

### Can't Add Player

**Problem:** "Add Player" button doesn't work or error appears

**Possible Causes:**
- Maximum players reached
- Invalid name
- Server error
- Player initial already exists

**Solutions:**

1. **Check player count:**
   - Look at standings
   - If 12 players shown, maximum reached
   - Remove a player first

2. **Check player name:**
   - Use simple names (letters only)
   - Avoid special characters
   - Try "TestPlayer" format

3. **Check browser console:**
   - Press F12, Console tab
   - Look for error messages
   - Share error text if asking for help

4. **Check server logs:**
   - Look at terminal running server
   - Search for error messages
   - May indicate database/file issue

5. **Reset game and try again:**
   - Click "Reset" button
   - Remove all players
   - Try adding new player

---

### Player Information Wrong

**Problem:** Initials incorrect, tokens miscounted, or name wrong

**Possible Causes:**
- Stale browser cache
- State not saved
- Multiple browser tabs
- Initial generation issue

**Solutions:**

1. **Refresh browser:**
   - Press F5 or Ctrl+R
   - Or Ctrl+Shift+R for hard refresh

2. **Close other tabs:**
   - Only use one browser tab at a time
   - Multiple tabs can cause sync issues

3. **Check API directly:**
   ```bash
   curl http://localhost:8080/api/state | python -m json.tool
   ```
   Compare with UI display

---

## Score & Multiplier Issues

### Scores Don't Update

**Problem:** Score input doesn't change display

**Possible Causes:**
- Value out of range
- Server not responding
- Invalid input format
- State not saving

**Solutions:**

1. **Verify score in valid range:**
   - NFL: 0-70
   - NHL: 0-12
   - NBA: 0-160
   - MLB: 0-30
   - Olympics: 0-12
   - FIFA: 0-10

2. **Try API directly:**
   ```bash
   curl -X POST http://localhost:8080/api/scores \
     -H "Content-Type: application/json" \
     -d '{"left": 7, "right": 3}'
   ```
   Check if response indicates success

3. **Check server logs:**
   - Terminal should show requests
   - Look for POST /api/scores
   - Check for error messages

4. **Refresh browser:**
   - Press F5
   - Click different sport/sport
   - Check if scores restored

---

### Multiplier Selection Not Working

**Problem:** Multiplier buttons don't respond or selection doesn't apply

**Possible Causes:**
- Insufficient tokens
- Sport configuration wrong
- JavaScript error
- Button not clickable

**Solutions:**

1. **Check available tokens:**
   - Look at player standings
   - Tokens = total - spent
   - Can't claim square if tokens < multiplier

2. **Verify sport multipliers:**
   - Each sport has different multiplier options
   - NFL: 1x, 2x, 4x, 8x
   - Hockey: 1x, 2x, 4x
   - Check GAME_RULES.md for details

3. **Click "Claim Square" after multiplier:**
   - Select multiplier first
   - Then click empty square on board
   - Don't click square first

4. **Check browser console:**
   - Press F12
   - Look for error messages
   - May indicate invalid state

---

## Winner Calculation Issues

### Winner Not Showing

**Problem:** Scores updated but no winner displays

**Possible Causes:**
- No close square exists
- Score not close to any claimed square
- Scores equal (tie)
- Logic error

**Solutions:**

1. **Update scores to realistic final:**
   - Example for NFL: 21-17
   - Check if claimed squares near that score
   - Use test setup to populate board

2. **Check claimed squares:**
   - Look at game board
   - Verify squares claimed in area of final score
   - If all high scores, low final scores won't match

3. **Run test setup:**
   ```bash
   python test_setup.py
   ```
   Populates board with sample data, making winner likely

4. **Check winner via API:**
   ```bash
   curl http://localhost:8080/api/winner | python -m json.tool
   ```
   See raw response

---

### Multiple Winners Display Wrong

**Problem:** Multiple players shown as winners, but calculation seems wrong

**Possible Causes:**
- Tie in distance calculation
- Display showing all ties correctly
- User misunderstanding rules

**Solutions:**

1. **Understand winner rules:**
   - Winner = closest square to final score
   - Distance = |row - left_score| + |col - right_score|
   - Multiple players can tie at same distance

2. **Verify squares manually:**
   - Check distance for each claimed square
   - Example: Final 21-17
     - Square [21, 17] = distance 0 ✓ WINS
     - Square [20, 17] = distance 1
     - Square [21, 16] = distance 1
   - If [21,17] and another [21,17] claimed, both win

3. **Check standings:**
   - See all players and their claimed squares
   - Verify count matches display

---

## Player Management Issues

### Can't Remove Player

**Problem:** Delete button doesn't work or error appears

**Possible Causes:**
- Player ID wrong
- API not responding
- JavaScript error
- Permission issue

**Solutions:**

1. **Verify correct player in standings:**
   - Look at standings list
   - Find player initials
   - Try deleting that player

2. **Use API directly:**
   ```bash
   curl -X DELETE http://localhost:8080/api/players/AB
   # Replace AB with player initials
   ```

3. **Check browser console:**
   - Press F12
   - Look for errors
   - Check network tab for failed requests

4. **Refresh and try again:**
   - Reload page (F5)
   - Wait 2 seconds
   - Try removing again

---

### Player Squares Not Clearing

**Problem:** Remove player but squares still show their initial

**Possible Causes:**
- Page not refreshed
- State not saved
- Delete failed silently
- Browser cache

**Solutions:**

1. **Hard refresh browser:**
   - Press Ctrl+Shift+R (or Cmd+Shift+R on Mac)
   - Forces full page reload

2. **Check API response:**
   - Delete should return success message
   - Verify in browser console network tab

3. **Check server logs:**
   - Terminal should show DELETE request
   - Look for success or error message

4. **Try again:**
   - If delete failed, API will retry next time
   - May eventually succeed

---

## Sport Switching Issues

### Grid Size Wrong After Switching Sports

**Problem:** Sports switched but grid still old size

**Possible Causes:**
- Page not refreshed
- Sport switch failed
- Browser cache
- Config wrong for sport

**Solutions:**

1. **Refresh browser:**
   - Press F5 or Ctrl+R
   - Should show correct grid

2. **Check sport actually switched:**
   ```bash
   curl http://localhost:8080/api/state | grep sport
   ```
   Verify sport in output

3. **Verify config has sport:**
   ```bash
   grep -A 5 "max_scores" config.py
   ```
   Check that selected sport listed

4. **Try different sport:**
   - If one sport broken, try another
   - May indicate config issue with that sport

---

### Scores Reset After Sport Switch

**Problem:** Changed sports and scores went to 0-0

**Explanation:** This is expected behavior! Switching sports resets scores because:
- Different sports have different maximum scores
- Score 70 is valid in NFL but invalid in Hockey (max 12)
- Automatically resets to prevent invalid states

**No action needed** - this is normal.

---

## Network/Connection Issues

### Server Works Locally But Not From Other Computer

**Problem:** Works on Windows/macOS with localhost but not from another machine

**Solution:**

**Windows/macOS change host:**
Edit `config.py`:
```python
platform_hosts = {
    'windows': '0.0.0.0',    # Change from 'localhost'
    'linux': '0.0.0.0',
    'darwin': '0.0.0.0'       # Change from 'localhost'
}
```

Restart server, then access from other machine using server IP:
```
http://<server-ip>:8080
```

**Linux firewall:**
```bash
sudo ufw allow 8080
```

---

### High Latency/Slow Updates

**Problem:** Game UI slow, score updates lag, or animations stutter

**Possible Causes:**
- Server overloaded
- Network slow
- Browser performance
- D3.js animation intensive

**Solutions:**

1. **Enable lite mode:**
   ```bash
   LITE_MODE=1 python app.py
   ```
   Disables animations and effects

2. **Check network:**
   ```bash
   ping <server-ip>
   # Should show < 50ms for local network
   ```

3. **Close other applications:**
   - Free up system RAM
   - Reduce network traffic
   - Close other browser tabs

4. **Try different browser:**
   - Chrome usually fastest
   - Firefox, Safari also acceptable
   - Internet Explorer not supported

5. **Reduce player count:**
   - More players = larger grid = slower rendering
   - Remove inactive players

---

## File System Issues

### game_state.db Corrupted

**Problem:** Game won't load or error about database

**Solutions:**

1. **Check integrity:**
   ```bash
   sqlite3 game_state.db "PRAGMA integrity_check;"
   ```

2. **Restore from backup:**
   ```bash
   cp game_state.db.backup game_state.db
   ```

3. **Start fresh:**
   ```bash
   rm game_state.db
   # Server creates new file on next start
   ```

4. **View last known good:**
   ```bash
   # Not easily possible with binary DB file from git
   # Use backup instead
   ```

---

### File Permission Errors

**Problem:** Cannot write game state, permission denied

**Solutions:**

1. **Fix ownership:**
   ```bash
   sudo chown $USER game_state.db
   ```

2. **Fix permissions:**
   ```bash
   chmod 644 game_state.db
   chmod 755 .
   ```

3. **Run with proper user:**
   ```bash
   # Don't run as root
   su - appuser -c "python app.py"
   ```

---

## Browser-Specific Issues

### Chrome/Chromium Issues

**Problem:** Game works in Firefox but not Chrome

**Solutions:**
- Clear cookies/cache (Ctrl+Shift+Delete)
- Disable extensions (try incognito mode)
- Check console for errors (F12)

### Firefox Issues

**Problem:** Grid or animations not rendering

**Solutions:**
- Enable JavaScript (should be default)
- Check about:config for disabled features
- Try different profile (fresh Firefox)

### Safari Issues

**Problem:** CSS Grid not working or animations choppy

**Solutions:**
- Update Safari (WebKit must be current)
- Disable extensions
- Check developer console (Cmd+Option+I)

---

## Getting Help

### Information to Provide

If reporting issue, include:
1. **Browser:** Chrome 95, Firefox 94, Safari 15, etc.
2. **Operating System:** Windows 10, macOS 11, Ubuntu 20.04, etc.
3. **Python version:** `python --version`
4. **Server logs:** Output from terminal running app.py
5. **Browser console:** F12 > Console tab errors
6. **Steps to reproduce:** Exact steps to cause issue
7. **Expected vs actual:** What should happen vs what does happen

### Debug Information

Before reporting, try to gather:

```bash
# Python version and packages
python --version
pip show flask requests

# Check server logs for errors
grep ERROR logs/*.log

# Verify connectivity
curl -v http://localhost:8080/api/state

# Check system resources
free -h  # or 'top' on macOS
```

### Common Support Sites

- GitHub Issues (if public repository)
- Project documentation (README.md, docs/)
- Configuration guide (CONFIGURATION.md)
- Developer guide (DEVELOPER_GUIDE.md)

---

## Prevention Tips

**To avoid most issues:**

1. ✓ Use Python 3.10+ (stated requirement)
2. ✓ Install all dependencies via `pip install .` (or `pip install ".[dev]"` for dev)
3. ✓ Run server before opening browser
4. ✓ Use one browser tab at a time
5. ✓ Refresh browser after making changes
6. ✓ Clear cache regularly (Ctrl+Shift+Delete)
7. ✓ Check terminal for error messages
8. ✓ Use correct host setting for your OS
9. ✓ Enable firewall access on Linux (ufw)
10. ✓ Back up game_state.db regularly
