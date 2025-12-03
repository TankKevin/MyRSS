# MyRSS

Python backend script that fetches configured RSS feeds at 08:00 each day, packages them, and emails the digest to recipients.

## Quick start
1) Create a virtual environment and install dependencies
```bash
cd /Users/applekvt/Projects_KVT/MyRSS
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

2) Configure environment variables (write them into `.env` and the program will auto-load, or export them directly)
```
RSS_FEEDS="Tech|https://example.com/feed.xml,News|https://example.com/news.xml"  # Multiple feeds: separate with commas or new lines, each entry is name|url
# For a single feed you can keep using the legacy variables:
RSS_FEED_URL=https://example.com/feed.xml
RSS_FEED_NAME=Tech                                # Optional, defaults to "RSS"
RSS_VERIFY_SSL=true                # Set to false if the feed has certificate issues (less secure)
SMTP_HOST=smtp.example.com
SMTP_PORT=587
EMAIL_FROM_NAME=Kevin Tan               # Optional, display name for the From header
SMTP_USERNAME=your_smtp_user        # Optional, leave blank if the server does not require authentication
SMTP_PASSWORD=your_smtp_password    # Optional
SMTP_STARTTLS=true                  # Enable STARTTLS, default is true
EMAIL_FROM=notify@example.com
EMAIL_TO=user1@example.com,user2@example.com
EMAIL_SUBJECT=Daily RSS Digest      # Optional, uses the default if omitted
ENTRY_LIMIT=20                      # Optional, limit the number of fetched entries
```

3) Run once manually to verify
```bash
# Recommended: run as a module to avoid relative import issues
python -m rss_mailer.runner

# Or run the file directly
python rss_mailer/runner.py
```

### Customize the email template
- The HTML template lives at `rss_mailer/templates/email.html` (Jinja2); adjust styles/fields as needed.
- The email also includes a plain-text backup in case some clients skip HTML.
- By default it only sends RSS entries published on the previous UTC day; if nothing matches, the email notes it is empty.

## Docker deployment
1) Build the image
```bash
docker build -t myrss:latest .
```

2) Prepare `.env` on the server (you can reuse `.env.example`). Run a test:
```bash
docker run --rm --env-file .env myrss:latest
```

3) Schedule the job (example: 08:00 in the server timezone, edit host `crontab -e`):
```
0 8 * * * docker run --rm --env-file /path/to/.env myrss:latest >> /var/log/myrss.log 2>&1
```
- To keep the container timezone in sync with the host, also mount `-v /etc/localtime:/etc/localtime:ro`.

## Schedule daily at 08:00
Add to local `crontab -e` (assuming the project path is `/Users/applekvt/Projects_KVT/MyRSS` and the virtual environment above):
```
0 8 * * * cd /Users/applekvt/Projects_KVT/MyRSS && . .venv/bin/activate && python -m rss_mailer.runner >> cron.log 2>&1
```
Note: `cron.log` records run logs for troubleshooting.

## Code structure
- `rss_mailer/config.py`: read and validate environment variables.
- `rss_mailer/rss_fetcher.py`: fetch and parse RSS (uses feedparser).
- `rss_mailer/email_sender.py`: build email body and send via SMTP.
- `rss_mailer/runner.py`: entry point connecting config, fetching, and email sending.
- `requirements.txt`: Python dependencies.

## Additional notes
- The email body is plain text and includes the title, published time (UTC), and link.
- For Gmail, use `SMTP_HOST=smtp.gmail.com`, `SMTP_PORT=587`, and enable an app password in your account settings.
- If your SMTP server requires SSL instead of STARTTLS, set `SMTP_STARTTLS=false` and set `SMTP_PORT` to the SSL port (for example 465); ensure the server accepts plaintext or adjust the code to use `smtplib.SMTP_SSL`.
