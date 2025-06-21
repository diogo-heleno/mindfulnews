config.py v1.4

""" Configuration for Mindful News pipeline """

How many hours back to include feed items (in hours)

RUN_INTERVAL_HOURS = 48

Maximum number of raw articles to process per run

MAX_ARTICLES = 100

Path (relative to project root) where the final RSS feed will be written

OUTPUT_RSS_FILE = "mindfulnews.xml"

Path (relative to project root) where the HTML output will be written (if used)

OUTPUT_HTML_FILE = "mindfulnews.html"

