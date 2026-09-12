# start_server.ps1 - Windows launcher for Championship Squares
# Usage: powershell -ExecutionPolicy Bypass -File .\start_server.ps1 [--lite|--no-lite] {start|stop|status|restart|install|uninstall}
#        --lite      Enable lite mode (reduced visual effects for better performance)
#        --no-lite   Disable lite mode
#        install     Create a desktop shortcut (.lnk) in this folder
#        uninstall   Remove the desktop shortcut from this folder

# ---------------------------------------------------------------------------
# Argument parsing  (no param() block so that $args is populated)
# ---------------------------------------------------------------------------
$LiteMode         = 0
$LiteModeExplicit = 0
$Action           = "start"
$remaining        = @()

foreach ($arg in $args) {
    switch ($arg) {
        "--lite"    { $LiteMode = 1; $LiteModeExplicit = 1 }
        "--no-lite" { $LiteMode = 0; $LiteModeExplicit = 1 }
        default     { $remaining += @($arg) }
    }
}
if ($remaining.Count -gt 0) {
    $Action = $remaining[0]
}

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
$ScriptDir = Split-Path -Parent -Path $PSCommandPath
$VenvDir   = Join-Path $ScriptDir "venv"
$PidFile   = Join-Path $ScriptDir "server.pid"
$LiteFile  = Join-Path $ScriptDir ".lite_mode"
$LogDir    = Join-Path $ScriptDir "logs"
$LogFile   = Join-Path $LogDir "server.log"
$ErrLog    = Join-Path $LogDir "server_err.log"

if (-not (Test-Path $LogDir)) {
    New-Item -ItemType Directory -Path $LogDir | Out-Null
}

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
function Get-Python {
    $venvPython = Join-Path $VenvDir "Scripts" "python.exe"
    if (Test-Path $venvPython) { return $venvPython }
    return "python"
}

function Ensure-Venv {
    if (-not (Test-Path $VenvDir)) {
        Write-Host "First run — creating virtual environment..."
        & python -m venv $VenvDir
        if ($LASTEXITCODE -ne 0) {
            Write-Host "ERROR: Failed to create virtual environment. Is Python installed?"
            exit 1
        }
    }
    $venvPython = Join-Path $VenvDir "Scripts" "python.exe"
    & $venvPython -c "import flask, qrcode, waitress" 2>$null
    if ($LASTEXITCODE -ne 0) {
        Write-Host "Installing or updating dependencies..."
        & $venvPython -m pip install --upgrade pip
        if ($LASTEXITCODE -ne 0) {
            Write-Host "ERROR: Failed to update pip."
            exit 1
        }
        & $venvPython -m pip install $ScriptDir
        if ($LASTEXITCODE -ne 0) {
            Write-Host "ERROR: Failed to install dependencies."
            exit 1
        }
    }
}

function Test-Running {
    if (-not (Test-Path $PidFile)) { return $false }
    $pid = (Get-Content $PidFile -Raw).Trim()
    try {
        $null = Get-Process -Id [int]$pid -ErrorAction Stop
        return $true
    }
    catch { return $false }
}

# ---------------------------------------------------------------------------
# Actions
# ---------------------------------------------------------------------------
function Start-Server {
    if (Test-Running) {
        $pid = (Get-Content $PidFile -Raw).Trim()
        Write-Host "Server already running (pid=$pid)."
        Start-Process -FilePath "cmd.exe" -ArgumentList "/c start http://localhost:8080" -NoNewWindow
        return
    }

    Ensure-Venv
    $python = Get-Python
    $appPy  = Join-Path $ScriptDir "app.py"

    # Resolve lite mode: explicit flag > persisted file
    if ($LiteModeExplicit -eq 0 -and (Test-Path $LiteFile)) {
        $LiteMode = 1
    }

    if ($LiteMode -eq 1) {
        Write-Host "Starting championship-squares (LITE MODE)..."
        Set-Content -Path $LiteFile -Value "1"
        $env:LITE_MODE = "1"
    }
    else {
        Write-Host "Starting championship-squares..."
        if ($LiteModeExplicit -eq 1) {
            Remove-Item -Path $LiteFile -ErrorAction SilentlyContinue
        }
        $env:LITE_MODE = "0"
    }

    $proc = Start-Process -FilePath $python -ArgumentList $appPy `
        -WorkingDirectory $ScriptDir `
        -RedirectStandardOutput $LogFile `
        -RedirectStandardError  $ErrLog `
        -NoNewWindow -PassThru

    Set-Content -Path $PidFile -Value $proc.Id
    Write-Host "Started (pid=$($proc.Id)). Logs: $LogDir"
}

function Stop-Server {
    if (-not (Test-Path $PidFile)) {
        Write-Host "No pid file found. Is the server running?"
        return
    }

    $pid = (Get-Content $PidFile -Raw).Trim()
    try {
        $null = Get-Process -Id [int]$pid -ErrorAction Stop
        Write-Host "Stopping server (pid=$pid)..."
        Stop-Process -Id [int]$pid -Force
        Start-Sleep -Seconds 1
        Remove-Item -Path $PidFile -ErrorAction SilentlyContinue
        Write-Host "Stopped."
    }
    catch {
        Write-Host "Process $pid not running. Removing stale pid file."
        Remove-Item -Path $PidFile -ErrorAction SilentlyContinue
    }
}

function Get-Status {
    if (Test-Path $PidFile) {
        $pid = (Get-Content $PidFile -Raw).Trim()
        try {
            $null = Get-Process -Id [int]$pid -ErrorAction Stop
            $liteTag = if (Test-Path $LiteFile) { " in LITE MODE" } else { "" }
            Write-Host "Running$liteTag (pid=$pid). Logs: $LogDir"
            return
        }
        catch {
            Write-Host "Stale pid file found (pid=$pid)."
            return
        }
    }
    Write-Host "Not running."
}

function Install-Shortcut {
    $lnkPath  = Join-Path $ScriptDir "championship-squares.lnk"
    $pngPath  = Join-Path $ScriptDir "icon.png"
    $icoPath  = Join-Path $ScriptDir "icon.ico"
    $psScript = Join-Path $ScriptDir "start_server.ps1"

    # Windows shortcuts require .ico — convert from PNG if available
    if (Test-Path $pngPath) {
        Add-Type -AssemblyName System.Drawing
        $image  = [System.Drawing.Image]::FromFile($pngPath)
        $icon   = [System.Drawing.Icon]::FromImage($image)
        $stream = [System.IO.File]::Create($icoPath)
        $icon.Save($stream)
        $stream.Close()
        $image.Dispose()
    }

    $shell = New-Object -COM WScript.Shell
    $lnk   = $shell.CreateShortcut($lnkPath)
    $lnk.TargetPath        = "powershell.exe"
    $lnk.Arguments         = "-ExecutionPolicy Bypass -NoProfile -File `"$psScript`" start"
    $lnk.WorkingDirectory  = $ScriptDir
    if (Test-Path $icoPath) {
        $lnk.IconLocation  = "$icoPath,0"
    }
    $lnk.Save()

    Write-Host "Shortcut created: $lnkPath"
    Write-Host "Double-click it from this folder to launch the game."
}

function Uninstall-Shortcut {
    $lnkPath = Join-Path $ScriptDir "championship-squares.lnk"
    $icoPath = Join-Path $ScriptDir "icon.ico"
    $removed = $false

    if (Test-Path $lnkPath) {
        Remove-Item -Path $lnkPath -Force
        Write-Host "Removed shortcut: $lnkPath"
        $removed = $true
    }

    if (Test-Path $icoPath) {
        Remove-Item -Path $icoPath -Force
        Write-Host "Removed icon cache: $icoPath"
    }

    if (-not $removed) {
        Write-Host "No shortcut found to remove."
    } else {
        Write-Host "✓ Championship Squares shortcut has been removed."
    }
}

# ---------------------------------------------------------------------------
# Dispatch
# ---------------------------------------------------------------------------
switch ($Action) {
    "start"     { Start-Server }
    "stop"      { Stop-Server }
    "status"    { Get-Status }
    "restart"   { Stop-Server; Start-Server }
    "install"   { Install-Shortcut }
    "uninstall" { Uninstall-Shortcut }
    default     {
        Write-Host "Usage: powershell -ExecutionPolicy Bypass -File .\start_server.ps1 [--lite|--no-lite] {start|stop|status|restart|install|uninstall}"
        Write-Host "       --lite      Enable lite mode (reduced visual effects)"
        Write-Host "       --no-lite   Disable lite mode (full visual effects)"
        Write-Host "       install     Create a desktop shortcut (.lnk) in this folder"
        Write-Host "       uninstall   Remove the desktop shortcut from this folder"
    }
}
