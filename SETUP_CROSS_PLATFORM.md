# Queue Poller - Cross-Platform Setup Guide

This guide explains how to set up Queue Poller to work seamlessly across multiple computers (Windows, macOS, Linux).

## Prerequisites

### All Platforms
- **Python 3.8+** installed
- **Git** installed and configured
- **MySQL/MariaDB** server (can be remote or local)

### Windows
- XAMPP (optional, for local MySQL)
- Git for Windows

### macOS
- Homebrew (recommended)
- MySQL or XAMPP

### Linux
- MySQL server
- Git

## Initial Setup (First Computer)

### 1. Clone or Initialize Repository

If starting fresh:
```bash
cd /path/to/th_poller
git init
git remote add origin <your-git-repo-url>
git add .
git commit -m "Initial commit"
git push -u origin main
```

If cloning existing:
```bash
git clone <your-git-repo-url>
cd th_poller
```

### 2. Configure Database Connection

The database connection should be:
- **Remote MySQL server** (recommended for multi-machine setup)
- Or **SSH tunnel** to one machine's MySQL
- Or **cloud MySQL** (AWS RDS, DigitalOcean, etc.)

Edit database connection in `config_core.py` or create a `.env` file:
```
DB_HOST=your.mysql.server.com
DB_PORT=3306
DB_USER=root
DB_PASS=your_password
DB_NAME=offta
```

### 3. Install Python Dependencies

```bash
# Windows
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt

# macOS/Linux
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### 4. First Run

```bash
# Windows
python config_hud.py

# macOS/Linux
python3 config_hud.py
```

## Setup on Additional Computers

### 1. Clone Repository

```bash
git clone <your-git-repo-url>
cd th_poller
```

### 2. Install Dependencies

```bash
# Windows
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt

# macOS/Linux
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### 3. Configure Database

Ensure database connection points to the same shared MySQL server.

### 4. Run

```bash
# Windows
python config_hud.py

# macOS/Linux
python3 config_hud.py
```

## Auto-Update Feature

Queue Poller automatically checks for updates once per day when launched:

- ✅ Fetches latest changes from `origin/main`
- ✅ Auto-updates if new commits are available
- ✅ Preserves local changes (stashes before pull)
- ✅ Shows notification when update is available
- ✅ Cross-platform compatible

### Manual Update

To manually update:
```bash
git pull origin main
```

### Check Update Status

```bash
git fetch origin
git status
```

## Sharing Workflow

### Making Changes on Computer A

1. Make your changes
2. Commit:
   ```bash
   git add .
   git commit -m "Description of changes"
   git push origin main
   ```

### Receiving Changes on Computer B/C

- **Automatic**: Wait for next launch (checks once per day)
- **Manual**: 
  ```bash
  git pull origin main
  ```

## File Synchronization

### Files that ARE synced (via Git):
- All Python code (`*.py`)
- Configuration files
- SQL schema files
- Documentation

### Files that are NOT synced (local only):
- `Captures/` folder (screenshots, HTML, JSON)
- `.venv/` virtual environment
- `__pycache__/` compiled Python
- `.last_git_check` update marker
- Session files
- MySQL database files (`.sql` backups)
- Log files

## Database Considerations

### Shared Database (Recommended)

Use one of these approaches:

1. **Cloud MySQL** (best for reliability)
   - AWS RDS
   - DigitalOcean Managed MySQL
   - Google Cloud SQL

2. **One Computer as MySQL Server**
   - Enable remote MySQL connections
   - Configure firewall rules
   - Use SSH tunnel for security

3. **SSH Tunnel** (secure option)
   ```bash
   # On client machine, create tunnel:
   ssh -L 3306:localhost:3306 user@server-with-mysql
   
   # Then connect to localhost:3306
   ```

### Connection Settings

In `config_core.py` or environment variables:
```python
DB_CONFIG = {
    'host': 'your.mysql.server.com',  # or 'localhost' with SSH tunnel
    'port': 3306,
    'user': 'root',
    'password': 'your_password',
    'database': 'offta'
}
```

## Platform-Specific Notes

### Windows
- Use `\` or `\\` in paths, or use `Path()` from pathlib
- XAMPP install: `C:\xampp`
- Python: Install from python.org or Microsoft Store

### macOS
- Use `/` in paths
- Install Homebrew: `/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"`
- Install Python: `brew install python`
- Install MySQL: `brew install mysql`
- Install Git: `brew install git`

### Linux
- Use `/` in paths
- Install Python: `sudo apt install python3 python3-pip python3-venv`
- Install MySQL: `sudo apt install mysql-server`
- Install Git: `sudo apt install git`

## Troubleshooting

### "Git not found" error
- Install Git for your platform
- Add Git to PATH
- Restart terminal/IDE

### Update not working
```bash
# Check git status
git status

# Manually pull
git pull origin main

# Force update (careful - loses local changes)
git reset --hard origin/main
```

### Database connection fails
- Check MySQL server is running
- Verify firewall allows port 3306
- Test connection: `mysql -h hostname -u root -p`
- Check credentials in config files

### Conflicts between machines
```bash
# Stash local changes
git stash

# Pull latest
git pull origin main

# Re-apply stashed changes
git stash pop
```

## Best Practices

1. **Commit frequently** - Keep changes small and focused
2. **Pull before starting work** - `git pull origin main`
3. **Use descriptive commit messages** - Explain what changed and why
4. **Test before pushing** - Ensure code works before `git push`
5. **Use branches for experiments** - Create feature branches for major changes
6. **Backup database regularly** - Use mysqldump or automated backups
7. **Keep dependencies updated** - `pip install --upgrade -r requirements.txt`

## Security Notes

- ⚠️ **Never commit passwords** or API keys to git
- ✅ Use environment variables or `.env` files (gitignored)
- ✅ Use SSH keys for git authentication
- ✅ Use SSH tunnels for MySQL connections over internet
- ✅ Keep MySQL credentials secure and unique per environment
