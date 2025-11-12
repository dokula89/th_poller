# TH Poller - Real Estate Listing Extraction System

A Python-based automated queue poller system for extracting and processing real estate listings from various sources. Features a modern Tkinter GUI with tab-based navigation and API integration.

## Features

- **Multi-Tab Interface**: Networks, Websites, Parcel, Code, 911, and Accounts management
- **API Integration**: RESTful PHP backend for data fetching and processing
- **Metro Filtering**: Dynamic metro selection with real-time filtering
- **Queue Management**: Process listings through 6-step workflow
- **Live Logging**: 3-line rolling log display with color-coded messages
- **Auto-Refresh**: Configurable 5-second auto-refresh for queue monitoring

## Tech Stack

- **Frontend**: Python 3.x, Tkinter
- **Backend**: PHP 7/8 (XAMPP/Apache)
- **Database**: MySQL (remote connection to offta database)
- **APIs**: Custom PHP endpoints for data operations

## Project Structure

```
th_poller/
├── config_utils.py          # Main UI and queue management
├── worker.py                # Background worker processes
├── worker_new.py            # Updated worker implementation
├── parser_core.py           # HTML parsing and extraction
├── process_daily_captures.py # Daily capture processing
├── download_images.py       # Image downloading utilities
├── field_mappings.json      # Field mapping configuration
├── launch_poller.pyw        # Application launcher
├── Captures/                # Captured HTML/JSON files (gitignored)
└── __pycache__/             # Python cache (gitignored)
```

## Installation

### Prerequisites

- Python 3.8 or higher
- XAMPP (for local PHP/Apache server)
- MySQL access to offta database
- Required Python packages:
  ```bash
  pip install requests mysql-connector-python pillow
  ```

### Setup

1. Clone the repository:
   ```bash
   git clone <your-repo-url>
   cd th_poller
   ```

2. Configure XAMPP:
   - Place PHP API files in `c:\xampp\htdocs\step5\`
   - Ensure Apache is running on localhost

3. Update database credentials in PHP files if needed:
   - Host: `172.104.206.182:3306`
   - Database: `offta`
   - User: `seattlelisted_usr`

4. Launch the application:
   ```bash
   python launch_poller.pyw
   ```

## API Endpoints

The system uses several PHP endpoints located in `c:\xampp\htdocs\step5\`:

- `get_major_metros.php` - Fetch metro names
- `get_parcel_metros.php` - Get metros with parcel links
- `get_accounts.php` - Retrieve user accounts
- `get_code_cities.php` - Cities with code websites
- `get_911_cities.php` - Cities with 911 websites
- `queue_website_api.php` - Queue management

## Usage

### Main Interface

1. **Networks Tab**: View queued listing networks
2. **Websites Tab**: Manage website queue
3. **Parcel Tab**: Metro-specific parcel data (filter by metro dropdown)
4. **Code Tab**: Cities with code website links
5. **911 Tab**: Cities with 911 website links
6. **Accounts Tab**: User account management with search

### Metro Filter

- Located in the header next to the Logs button
- Dynamically loads 6 major metros from database
- Filters Parcel tab data when changed

### Processing Steps

Each queue item goes through 6 steps:
1. **Capture HTML** - Fetch webpage content
2. **Create JSON** - Parse HTML to structured data
3. **Manual Match** - Download and match images
4. **Process DB** - Upload images to server
5. **Insert DB** - Store listing data
6. **Address Match** - Geocode and match addresses

## Configuration

Key configuration is in `config_utils.py`:

- Auto-refresh interval: 5 seconds
- Queue table limit: 100 items
- Metro API timeout: 8 seconds
- Default status filter: "queued"

## Features

### UI Components

- **Mailer Button**: Email functionality (placeholder)
- **Accounts Search**: Filter accounts by name/email
- **Live Logs**: 3-line rolling log with color coding
  - Green: Success
  - Red: Error
  - Yellow: Warning
  - Gray: Info
- **Loading Indicator**: Shows during tab switches

### Tab-Specific Features

- **Parcel Tab**: Integrates with metro filter, shows county data
- **Accounts Tab**: Real-time search, displays role and last seen
- **Code/911 Tabs**: City-based filtering from database

## Development

### Recent Updates

- Migrated all tabs from direct MySQL to API calls
- Fixed metro dropdown async loading issue
- Added Mailer button for future email integration
- Implemented 3-line log display
- Moved Metro selector to header position

### Known Issues

- Accounts API may timeout on large datasets
- Metro dropdown loads asynchronously (1-2 second delay)

## Contributing

This is a private project. Contact the repository owner for contribution guidelines.

## License

Private/Proprietary - All rights reserved

## Support

For issues or questions, check the `debug_queue.log` file for detailed error messages.

## Author

Trusty Housing Development Team
