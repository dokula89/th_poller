# Queue Poller - Quick Start

## First-Time Setup

### Windows
1. Double-click `start.bat`
2. The script will automatically:
   - Create virtual environment
   - Install dependencies
   - Launch Queue Poller

### macOS/Linux
1. Open Terminal
2. Navigate to th_poller directory:
   ```bash
   cd /path/to/th_poller
   ```
3. Run the startup script:
   ```bash
   chmod +x start.sh  # First time only
   ./start.sh
   ```

## Auto-Update Feature

Queue Poller checks for updates automatically:
- ✅ Checks once per day on startup
- ✅ Downloads and applies updates automatically
- ✅ Shows notification when update is available
- ✅ No manual intervention needed

## Sharing Between Computers

### Setup on Computer 1 (Main)

1. Initialize git repository (if not done):
   ```bash
   git init
   git remote add origin https://github.com/yourusername/th_poller.git
   git add .
   git commit -m "Initial commit"
   git push -u origin main
   ```

### Setup on Computer 2 & 3

1. Clone repository:
   ```bash
   git clone https://github.com/yourusername/th_poller.git
   cd th_poller
   ```

2. Run startup script:
   - Windows: Double-click `start.bat`
   - macOS/Linux: `./start.sh`

3. Done! Updates will sync automatically.

## Database Configuration

All computers should connect to the same MySQL database:

### Option 1: Cloud Database (Recommended)
- Use AWS RDS, DigitalOcean, or Google Cloud SQL
- Configure connection in `config_core.py`

### Option 2: Remote MySQL
- Enable MySQL on one computer
- Allow remote connections
- Point other computers to that IP

### Option 3: SSH Tunnel
- Create SSH tunnel to main computer
- Connect through localhost:3306

## Common Commands

### Manual Update
```bash
git pull origin main
```

### Check for Updates
```bash
git fetch origin
git status
```

### Commit Changes
```bash
git add .
git commit -m "Your message"
git push origin main
```

## Troubleshooting

### Git not found
- Install Git for your platform
- Restart terminal/IDE

### Dependencies not installing
- Check internet connection
- Try: `pip install --upgrade pip`
- Then: `pip install -r requirements.txt`

### Database connection fails
- Check MySQL server is running
- Verify connection details in config
- Test with: `mysql -h hostname -u root -p`

## Need Help?

See detailed documentation in `SETUP_CROSS_PLATFORM.md`
