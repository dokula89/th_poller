# Git Auto-Update System Implementation

## Overview

Queue Poller now supports automatic updates via Git, allowing seamless synchronization across multiple computers (Windows, macOS, Linux).

## Features Implemented

### 1. Auto-Update on Startup
- ✅ Checks for updates once per day on application launch
- ✅ Fetches latest changes from `origin/main`
- ✅ Automatically applies updates if new commits exist
- ✅ Stashes local changes before updating
- ✅ Falls back to `git reset --hard` if pull fails
- ✅ Shows user notification when updates are applied
- ✅ Logs all update operations

### 2. Cross-Platform Compatibility
- ✅ Works on Windows, macOS, and Linux
- ✅ Platform-specific startup scripts (`start.bat`, `start.sh`)
- ✅ Automatic virtual environment creation
- ✅ Automatic dependency installation

### 3. Update Throttling
- ✅ Only checks once per 24 hours
- ✅ Uses `.last_git_check` marker file
- ✅ Prevents excessive network requests

### 4. Error Handling
- ✅ Graceful failure if git not installed
- ✅ Timeout protection (30s for fetch, 30s for pull)
- ✅ Automatic recovery with `git reset --hard`
- ✅ Detailed logging of all operations

## How It Works

### Update Check Flow

1. **On Application Startup**:
   - Check if `.last_git_check` exists
   - If it exists and < 24 hours old, skip check
   - If > 24 hours or doesn't exist, proceed

2. **Fetch Latest**:
   - Run `git fetch origin`
   - Compare local HEAD with `origin/main`
   - Count commits behind

3. **If Updates Available**:
   - Stash any local changes: `git stash`
   - Pull updates: `git pull origin main`
   - If pull fails, force update: `git reset --hard origin/main`
   - Show notification to user
   - Update `.last_git_check` timestamp

4. **If Already Up-to-Date**:
   - Log "Already up to date"
   - Update `.last_git_check` timestamp

### File Structure

```
th_poller/
├── config_hud.py              # Main application with auto-update
├── .gitignore                 # Excludes machine-specific files
├── .last_git_check            # Update check timestamp (gitignored)
├── requirements.txt           # Python dependencies
├── start.bat                  # Windows startup script
├── start.sh                   # macOS/Linux startup script
├── QUICKSTART.md              # Quick setup guide
└── SETUP_CROSS_PLATFORM.md    # Detailed setup guide
```

### Files Excluded from Git (`.gitignore`)

```
# Machine-specific
.last_git_check
.session_*
session_*.json

# Data folders
Captures/
images/

# Virtual environment
.venv/
venv/

# Python
__pycache__/
*.pyc

# Logs
*.log
```

## Usage Instructions

### Windows

1. **First Time Setup**:
   ```cmd
   git clone <repo-url>
   cd th_poller
   start.bat
   ```

2. **Daily Use**:
   - Double-click `start.bat`
   - Auto-update checks once per day
   - No manual git commands needed

### macOS/Linux

1. **First Time Setup**:
   ```bash
   git clone <repo-url>
   cd th_poller
   chmod +x start.sh
   ./start.sh
   ```

2. **Daily Use**:
   ```bash
   ./start.sh
   ```
   - Auto-update checks once per day
   - No manual git commands needed

## Manual Update Commands

If needed, you can manually update:

```bash
# Check for updates
git fetch origin
git status

# Pull updates
git pull origin main

# Force update (overwrites local changes)
git reset --hard origin/main
git pull origin main
```

## Sharing Workflow

### Computer A (Make Changes)
```bash
# Make your edits
git add .
git commit -m "Added new feature"
git push origin main
```

### Computer B & C (Receive Changes)
- **Automatic**: Just launch the app (checks once per day)
- **Manual**: Run `git pull origin main`

## Database Sharing

For multiple computers to work together, they must share the same database:

### Recommended Options:

1. **Cloud MySQL** (Best):
   - AWS RDS
   - DigitalOcean Managed MySQL
   - Google Cloud SQL

2. **Remote MySQL**:
   ```sql
   -- On server, allow remote connections:
   GRANT ALL PRIVILEGES ON offta.* TO 'root'@'%' IDENTIFIED BY 'password';
   FLUSH PRIVILEGES;
   ```

3. **SSH Tunnel** (Secure):
   ```bash
   # On client, create tunnel:
   ssh -L 3306:localhost:3306 user@server-ip
   
   # Then connect to localhost:3306
   ```

## Configuration

### Database Connection

Edit `config_core.py` or use environment variables:

```python
DB_CONFIG = {
    'host': 'your.mysql.server.com',  # Shared MySQL server
    'port': 3306,
    'user': 'root',
    'password': 'your_password',
    'database': 'offta'
}
```

### Git Remote

Set up your git remote:

```bash
# HTTPS (easier)
git remote add origin https://github.com/yourusername/th_poller.git

# SSH (more secure)
git remote add origin git@github.com:yourusername/th_poller.git
```

## Troubleshooting

### "Git not found" Error

**Windows**:
1. Install [Git for Windows](https://git-scm.com/download/win)
2. Restart terminal
3. Verify: `git --version`

**macOS**:
```bash
brew install git
```

**Linux**:
```bash
sudo apt install git
```

### Update Not Working

```bash
# Check git status
git status

# See what's different
git diff

# Reset to remote (careful - loses changes)
git reset --hard origin/main
```

### Database Connection Issues

1. Check MySQL is running
2. Test connection:
   ```bash
   mysql -h your-server -u root -p
   ```
3. Check firewall allows port 3306
4. Verify credentials in config

### Conflicts When Pulling

```bash
# Save your changes
git stash

# Pull latest
git pull origin main

# Re-apply your changes
git stash pop
```

## Security Best Practices

1. **Never commit passwords**:
   - Use `.env` files (gitignored)
   - Or use environment variables

2. **Use SSH keys for Git**:
   ```bash
   ssh-keygen -t ed25519 -C "your_email@example.com"
   # Add to GitHub: Settings → SSH Keys
   ```

3. **Secure MySQL**:
   - Use strong passwords
   - Enable SSL connections
   - Use SSH tunnels over internet
   - Restrict remote access by IP

4. **Keep dependencies updated**:
   ```bash
   pip install --upgrade -r requirements.txt
   ```

## Benefits

✅ **Single Source of Truth**: One codebase, synchronized everywhere
✅ **Automatic Updates**: No manual git commands needed daily
✅ **Cross-Platform**: Works on Windows, macOS, Linux
✅ **Safe Updates**: Stashes changes, can recover from errors
✅ **Version Control**: Full git history, can rollback if needed
✅ **Collaborative**: Multiple people can work on same codebase

## Limitations

- Updates only check once per day (prevents excessive checking)
- Requires internet connection for git operations
- Local database files are not synced (by design)
- Capture files are not synced (too large, local only)

## Future Enhancements

Possible additions:
- Manual "Check for Updates" button in UI
- Show current version/commit in title bar
- Automatic restart after update
- Background update check (every N hours)
- Update changelog display
- Rollback to previous version feature
