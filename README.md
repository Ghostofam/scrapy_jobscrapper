# Career Scraper

A robust web scraping application built with Scrapy and Playwright that extracts job listings from multiple career websites, stores the data in Google Sheets, and sends email notifications with the latest job opportunities.

## Project Overview

Career Scraper is designed to automate the process of monitoring job opportunities from multiple companies' career pages. It currently supports scraping from:

- Devsinc (via Workable portal)
- Systems Ltd (via SAP SuccessFactors)

The application uses Playwright for handling JavaScript-rendered content, Google Sheets API for data storage, and SMTP for email notifications.

### Key Features

- Headless browser automation with Playwright
- Automatic pagination handling
- Duplicate job detection
- Data storage in Google Sheets
- Email notifications with formatted job listings
- Environment variable configuration

## File and Directory Structure

```
career_scraper/
├── career_scraper/              # Main package directory
│   ├── spiders/                 # Spider implementations
│   │   ├── __init__.py          # Spider package initialization
│   │   ├── career_spider.py     # Main spider implementation
│   │   ├── .env                 # Environment variables (not in version control)
│   │   └── jobs-data-*.json     # Google API credentials (not in version control)
│   ├── __init__.py              # Package initialization
│   ├── items.py                 # Item definitions
│   ├── middlewares.py           # Middleware components
│   ├── pipelines.py             # Item processing pipelines
│   └── settings.py              # Scrapy settings
├── .gitignore                   # Git ignore configuration
├── output.json                  # Output file for scraped data
├── README.md                    # Project documentation
└── scrapy.cfg                   # Scrapy configuration file
```

## Installation and Setup

### Prerequisites

- Python 3.7+
- pip (Python package installer)
- Google account (for Google Sheets integration)

### Step 1: Clone the Repository

```bash
git clone <repository-url>
cd career_scraper
```

### Step 2: Create and Activate Virtual Environment

```bash
# Windows
python -m venv venv
venv\Scripts\activate

# macOS/Linux
python3 -m venv venv
source venv/bin/activate
```

### Step 3: Install Dependencies

```bash
pip install scrapy scrapy-playwright gspread oauth2client python-dotenv
playwright install  # Install browser binaries
```

### Step 4: Configure Google Sheets API

1. Go to the [Google Cloud Console](https://console.cloud.google.com/)
2. Create a new project
3. Enable the Google Sheets API and Google Drive API
4. Create a service account and download the JSON credentials file
5. Place the credentials file in the `career_scraper/spiders/` directory
6. Create a Google Sheet named "Jobs Data" and share it with the service account email

### Step 5: Configure Environment Variables

Create a `.env` file in the `career_scraper/spiders/` directory with the following variables:

```
sender_email = "your-email@gmail.com"
sender_password = "your-app-password"  # Gmail app password, not your regular password
recipient_email = "recipient@example.com"
```

Note: For Gmail, you need to create an App Password in your Google Account security settings.

## Usage

### Running the Spider

```bash
cd career_scraper
scrapy crawl career_spider
```

### Output

The spider will:

1. Scrape job listings from configured websites
2. Store the data in Google Sheets (separate worksheets for each company)
3. Send an email with formatted job listings to the configured recipient

### Command-line Options

```bash
# Save output to JSON file
scrapy crawl career_spider -o output.json

# Run with debug logging
scrapy crawl career_spider --loglevel=DEBUG
```

## How It Works

### Scraping Process

1. The spider starts by visiting the main career pages of Devsinc and Systems Ltd
2. It extracts links to third-party job portals (Workable for Devsinc, SAP SuccessFactors for Systems Ltd)
3. For each portal:
   - It navigates to the job listings page
   - Handles pagination to load all available jobs
   - Extracts job details (title, link, location)
4. After scraping, it processes the data and stores it in Google Sheets
5. Finally, it sends an email notification with the job listings

### Data Storage

The spider stores job data in a Google Sheet with separate worksheets for each company:
- "Devsinc" worksheet for Devsinc jobs
- "Systems Ltd" worksheet for Systems Ltd jobs

Each worksheet contains columns for:
- Title
- Link
- Source
- Country
- Cities

### Email Notifications

The spider sends HTML-formatted emails containing tables of job listings for each company, with links to apply directly.

## Troubleshooting

### Common Issues

1. **Authentication Errors with Google Sheets**
   - Ensure the credentials file is correctly placed
   - Verify the service account has access to the Google Sheet

2. **Email Sending Failures**
   - For Gmail, ensure you're using an App Password, not your regular password
   - Check that "Less secure app access" is enabled in your Google account

3. **Playwright Browser Issues**
   - Run `playwright install` to ensure browsers are properly installed
   - Try updating Playwright: `pip install --upgrade playwright`

4. **Rate Limiting or Blocking**
   - Add delays between requests in settings.py
   - Consider using proxies for high-volume scraping

## Contributing Guidelines

### Development Workflow

1. Create a feature branch from `main`
2. Make your changes
3. Test thoroughly
4. Submit a pull request

### Coding Standards

- Follow PEP 8 style guidelines
- Add docstrings to all functions and classes
- Use meaningful variable and function names

### Adding New Job Sources

To add a new job source:
1. Extend the `start_urls` list in `career_spider.py`
2. Add a new parsing method for the specific website
3. Update the `parse` method to handle the new URL pattern
4. Add a new storage method in the `spider_closed` signal handler

## Future Improvements

- Add more job sources
- Implement filtering by job type, experience level, etc.
- Create a web interface for viewing and filtering jobs
- Add scheduling for automatic periodic scraping
- Implement proxy rotation for better reliability

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Credits and Acknowledgments

- [Scrapy](https://scrapy.org/) - Web scraping framework
- [Playwright](https://playwright.dev/) - Browser automation
- [gspread](https://gspread.readthedocs.io/) - Google Sheets API wrapper
- [python-dotenv](https://github.com/theskumar/python-dotenv) - Environment variable management
