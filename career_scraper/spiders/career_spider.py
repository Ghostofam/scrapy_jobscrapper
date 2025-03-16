import scrapy
import gspread
import dotenv
import os
import smtplib
import sqlite3
from oauth2client.service_account import ServiceAccountCredentials
from scrapy_playwright.page import PageMethod
from scrapy import signals
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText


class CareerSpider(scrapy.Spider):
    name = "career_spider"
    start_urls = ["https://www.devsinc.com/career", "https://www.systemsltd.com/careers"]

    @classmethod
    def from_crawler(cls, crawler, *args, **kwargs):
        spider = super(CareerSpider, cls).from_crawler(crawler, *args, **kwargs)
        crawler.signals.connect(spider.spider_closed, signal=signals.spider_closed)
        return spider

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        dotenv.load_dotenv()
        self.jobs_devsinc = []
        self.jobs_systems = []

        # Google Sheets API setup
        scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
        creds = ServiceAccountCredentials.from_json_keyfile_name("jobs-data-452918-43b8a3d5d7c0.json", scope)
        self.client = gspread.authorize(creds)
        self.sheet = self.client.open("Jobs Data") # Ensure spreadsheet exists
        self.db_connection = sqlite3.connect("jobs")  # Connect to SQLite database
        self.db_cursor = self.db_connection.cursor()

    def parse(self, response):
        """Extract third-party career page links."""
        if "devsinc" in response.url:
            link_devsinc = response.css('a[href*="workable.com"]::attr(href)').get()
            if link_devsinc:
                self.logger.info(f"Found Devsinc Workable portal: {link_devsinc}")
                yield scrapy.Request(
                    link_devsinc,
                    callback=self.parse_devsinc_jobs,
                    meta={"playwright": True, "playwright_include_page": True, "playwright_page_methods": [
                        PageMethod("wait_for_load_state", "networkidle")
                    ]}
                )

        elif "systemsltd" in response.url:
            link_systemsltd = response.css('a[href*="sapsf.eu"]::attr(href)').get()
            if link_systemsltd:
                self.logger.info(f"Found Systems Ltd third-party link: {link_systemsltd}")
                yield scrapy.Request(
                    link_systemsltd,
                    callback=self.parse_systemsltd_jobs,
                    meta={"playwright": True, "playwright_include_page": True, "playwright_page_methods": [
                        PageMethod("wait_for_load_state", "networkidle")
                    ]}
                )

    async def parse_devsinc_jobs(self, response):
        """Scrape job listings from Devsinc's Workable page."""
        page = response.meta.get("playwright_page")
        if not page:
            self.logger.error("Playwright page not found in response.meta!")
            return

        try:
            self.logger.info("Checking for and dismissing popups...")
            await page.evaluate('''() => {
                const backdrop = document.querySelector('div[data-ui="backdrop"]');
                if (backdrop) backdrop.remove();

                const cookieConsent = document.querySelector('div[data-ui="cookie-consent"] button');
                if (cookieConsent) cookieConsent.click();

                const modalCloseButton = document.querySelector('button[aria-label="Close"]');
                if (modalCloseButton) modalCloseButton.click();
            }''')
            await page.wait_for_timeout(2000)

            while True:
                load_more_button = await page.query_selector('button[data-ui="load-more-button"]')
                if load_more_button:
                    self.logger.info("Clicking 'Show more' button...")
                    await page.evaluate('element => element.scrollIntoView()', load_more_button)
                    await page.wait_for_timeout(1000)
                    try:
                        await load_more_button.click(timeout=5000)
                    except Exception as e:
                        self.logger.warning(f"Retrying 'Show more' button click: {e}")
                        continue

                    await page.wait_for_load_state("networkidle")
                    await page.wait_for_timeout(3000)
                else:
                    break

            self.logger.info("Scrolling down to load all jobs...")
            await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
            await page.wait_for_timeout(2000)

            jobs = await page.evaluate('''() => {
                return Array.from(document.querySelectorAll('li.styles--1vo9F')).map(el => {
                const titleElement = el.querySelector('h3.styles--3TJHk');
                const linkElement = el.querySelector('a.styles--1OnOt');

                // Extract location details
                const locationElement = el.querySelector('div[data-ui="job-location-tooltip"] span');
                let city = "Not Specified";
                let country = "Not Specified";

                if (locationElement) {
                    const locationText = locationElement.innerText.trim();
                    const locationParts = locationText.split(",").map(part => part.trim());

                    // Extract city (first part of the location)
                    city = locationParts[0] || "Not Specified";

                    // Extract country (last part of the location)
                    country = locationParts[locationParts.length - 1] || "Not Specified";
                }

                return {
                    title: titleElement ? titleElement.innerText.trim() : null,
                    link: linkElement ? linkElement.href : null,
                    city: city,
                    country: country
                    };
                }).filter(job => job.title && job.link); // Remove any invalid entries
            }''')

        # Yield results and save to Devsinc tab
            if jobs:
                for job in jobs:
                    self.jobs_devsinc.append([job['title'], job['link'], 'Devsinc', job['country'], job['city']])
                    yield {
                        'title': job['title'],
                        'link': job['link'],
                        'source': 'Devsinc',
                        'country': job['country'],
                        'city': job['city']
                    }
                    self.logger.info(f"Successfully scraped {len(jobs)} jobs for Devsinc!")
            else:
                self.logger.warning("No jobs were extracted for Devsinc!")

        except Exception as e:
            self.logger.error(f"Error while scraping Devsinc jobs: {e}")  # Always close Playwright page

    async def parse_systemsltd_jobs(self, response):
        """Scrape job listings from Systems Ltd's SAP SuccessFactors page without clicking."""
        page = response.meta.get("playwright_page")
        if not page:
            self.logger.error("Playwright page not found in response.meta!")
            return

        try:
            all_jobs = []

            while True:
            # Get job elements
                job_elements = await page.query_selector_all('tr.jobResultItem')

                for job_element in job_elements:
                    try:
                        # Extract job title
                        job_link = await job_element.query_selector('a.jobTitle')
                        job_title = await job_link.text_content() if job_link else None
                        job_url = await job_link.get_attribute('href') if job_link else None

                        # Extract country
                        country_element = await job_element.query_selector('span.jobMFieldContent[aria-label^="Country"]')
                        if country_element:
                            country_attr = await country_element.get_attribute("onclick")
                            country = country_attr.split("[")[-1].split("]")[0].replace("&quot;", "").strip() if country_attr else "Not Specified"
                        else:
                            country = "Not Specified"

                        # Extract city (handles single and multiple values)
                        city_element = await job_element.query_selector('span.jobMFieldContent[aria-label^="City"]')
                        if city_element:
                            city_attr = await city_element.get_attribute("onclick")
                            cities = city_attr.split("[")[-1].split("]")[0].replace("&quot;", "").split(",") if city_attr else ["Not Specified"]
                            cities = [city.strip() for city in cities]
                            city_string = ", ".join([city.strip().replace('"', '') for city in cities])  # Convert list to a string
                        else:
                            cities = ["Not Specified"]

                        # Append job details
                        if job_title and job_url:
                            all_jobs.append([job_title.strip(), job_url, "Systems Ltd", country, city_string])

                    except Exception as e:
                        self.logger.warning(f" Error processing a job: {e}")

                # Check for next page button
                next_page_button = await page.query_selector('a.paginationArrow[title="Next Page"]')
                if next_page_button:
                    await next_page_button.click()
                    await page.wait_for_load_state("networkidle")
                    await page.wait_for_timeout(3000)
                else:
                    break

            self.jobs_systems.extend(all_jobs)
            self.logger.info(f"Collected {len(all_jobs)} Systems Ltd jobs.")
            await page.close()

        except Exception as e:
            self.logger.error(f"Error while scraping Systems Ltd jobs: {e}")

    def save_to_database(self, jobs):
            """Save jobs to the SQLite database."""
            try:
                for job in jobs:
                # Check if the job link already exists in the database
                    self.db_cursor.execute("SELECT id FROM Jobs WHERE link = ?", (job[1],))
                    if not self.db_cursor.fetchone():
                    # Insert the job into the database
                        self.db_cursor.execute("""
                            INSERT INTO Jobs (title, link, source, country, cities)
                            VALUES (?, ?, ?, ?, ?)
                            """, (job[0], job[1], job[2], job[3], job[4]))
                self.db_connection.commit()
                self.logger.info(f"Successfully saved {len(jobs)} jobs to the database.")
            except Exception as e:
                self.logger.error(f"Error saving jobs to the database: {e}")

    def spider_closed(self, spider):
        """Upload scraped jobs to Google Sheets."""
        self.logger.info("Saving scraped data to Google Sheets...")

        def save_to_sheet(sheet_name, jobs, filter_test_jobs=False):
            """Helper function to save jobs to a specific sheet."""
            if not jobs:
                self.logger.warning(f" No job data found for {sheet_name}. Skipping upload.")
                return

            try:
        # Get or create the worksheet
                try:
                    worksheet = self.sheet.worksheet(sheet_name)
                except gspread.exceptions.WorksheetNotFound:
                    worksheet = self.sheet.add_worksheet(title=sheet_name, rows="100", cols="5")  # Adjusted to 5 columns

        # Ensure headers are present
                existing_headers = worksheet.row_values(1)
                required_headers = ["Title", "Link", "Source", "Country", "Cities"]  # Updated headers

                if not existing_headers or existing_headers[:5] != required_headers:
                    worksheet.insert_row(required_headers, index=1)

        # Fetch existing job links to prevent duplicates
                existing_links = set(worksheet.col_values(2)[1:])  # Skip header row (column 2 is "Link")

        # Remove test jobs if required
                if filter_test_jobs:
                    jobs = [job for job in jobs if "test" not in job[0].lower() and "dummy" not in job[0].lower()]

        # Filter out jobs that already exist in the sheet
                new_jobs = [job for job in jobs if job[1] not in existing_links]

        # Append only new jobs
                if new_jobs:
            # Ensure each job has all required fields (fill missing fields with "Not Specified")
                    formatted_jobs = [
                    [
                    job[0],  # Title
                    job[1],  # Link
                    job[2],  # Source
                    job[3] if len(job) > 3 else "Not Specified",  # Country
                    job[4] if len(job) > 4 else "Not Specified"   # Cities
                    ]
                    for job in new_jobs
                    ]

                    worksheet.append_rows(formatted_jobs, value_input_option="RAW")
                    self.logger.info(f" Successfully saved {len(new_jobs)} new jobs to {sheet_name} sheet.")
                else:
                    self.logger.warning(f" No new jobs found for {sheet_name}. All jobs are already in the sheet.")

            except Exception as e:
                self.logger.error(f" Error saving data to {sheet_name} sheet: {e}")
        
                
        def send_email(self):
            """Send scraped job data via email."""
            sender_email = os.getenv('sender_email', "")
            print("sender_email:",sender_email)
            sender_password = os.getenv('sender_password', "")
            print("sender_password",sender_password)
            recipient_email = os.getenv('recipient_email', "")
            print("recipient_email",recipient_email)

            subject = "New Job Listings - Devsinc & Systems Ltd"
    
    # HTML table structure
            def format_jobs_html(jobs, company_name):
                """Formats job data as an HTML table."""
                if not jobs:
                    return f"<p>No new job postings found for {company_name}.</p>"

                html = f"<h3>{company_name} Job Listings</h3><table border='1' cellpadding='5' cellspacing='0' style='border-collapse: collapse;'>"
                html += "<tr><th>Title</th><th>Link</th><th>Country</th><th>City</th></tr>"
        
                for job in jobs:
                    html += f"<tr><td>{job[0]}</td><td><a href='{job[1]}' target='_blank'>Apply Here</a></td><td>{job[3]}</td><td>{job[4]}</td></tr>"
        
                html += "</table>"
                return html

    # Create email body
            email_body = f"""
            <html>
            <body>
                <h2>New Job Listings</h2>
                {format_jobs_html(self.jobs_devsinc, "Devsinc")}
                <br>
                {format_jobs_html(self.jobs_systems, "Systems Ltd")}
                <br>
                <p>Best Regards,<br>Career Scraper Bot</p>
            </body>
            </html>
            """

        # Configure SMTP server
            try:
                msg = MIMEMultipart()
                msg["From"] = sender_email
                msg["To"] = recipient_email
                msg["Subject"] = subject

                msg.attach(MIMEText(email_body, "html"))

                server = smtplib.SMTP("smtp.gmail.com", 587)
                server.starttls()
                server.login(sender_email, sender_password)
                server.sendmail(sender_email, recipient_email, msg.as_string())
                server.quit()

                self.logger.info("Email sent successfully!")

            except Exception as e:
                self.logger.error(f"Error sending email: {e}")

        save_to_sheet("Devsinc", self.jobs_devsinc,filter_test_jobs=True)
        save_to_sheet("Systems Ltd", self.jobs_systems,filter_test_jobs=True)
        self.save_to_database(self.jobs_devsinc)
        self.save_to_database(self.jobs_systems)
        self.logger.info("Sending email...")
        send_email(self)
        self.logger.info("Sent Email")
        def __del__(self):
            """Close the database connection when the spider is destroyed."""
            if hasattr(self, "db_connection"):
                self.db_connection.close()
                self.logger.info("Database connection closed.")
        