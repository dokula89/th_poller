# PHP Server Setup

## Overview
The PHP files have been copied from `C:\xampp\htdocs` to `th_poller/htdocs/` so they can run locally without XAMPP.

## Quick Start

### Option 1: Use Built-in PHP Server (Recommended)
1. Double-click `start_php_server.bat` in the th_poller folder
2. Server will start on http://localhost:8000/
3. PHP files will be served from `th_poller/htdocs/`

### Option 2: Use Python Script
```bash
python start_php_server.py
```

### Option 3: Start Manually
```bash
cd th_poller
php -S localhost:8000 -t htdocs
```

## Configuration

Edit `php_config.env` to switch between servers:

**For built-in PHP server (port 8000):**
```
PHP_BASE_URL=http://localhost:8000
```

**For XAMPP (port 80):**
```
PHP_BASE_URL=http://localhost
```

## Accessing PHP Files

- Old URL: `http://localhost/step5/find_or_create_place.php`
- New URL: `http://localhost:8000/step5/find_or_create_place.php`

The Python application automatically uses the configured `PHP_BASE_URL`.

## Requirements

- PHP 7.4 or higher must be installed and in PATH
- MySQL must be running (localhost:3306)

## Troubleshooting

**"PHP not found" error:**
- Install PHP: https://windows.php.net/download/
- Add PHP to PATH environment variable

**Port 8000 already in use:**
- Change port in start script: `php -S localhost:PORT -t htdocs`
- Update `php_config.env` with new port number

**Database connection errors:**
- Ensure MySQL is running
- Check credentials in PHP files match your MySQL setup
