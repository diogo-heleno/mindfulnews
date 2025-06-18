import feedparser
import openai
import json
import config
import os
from jinja2 import Environment, FileSystemLoader
from dateutil import parser as dateparser
from datetime import datetime, timedelta

# Load feeds
with open("feeds.json") as f:
    feeds = json.load(f)

# Load prompts
with open("prompts/filter_prompt.txt", "r") as f:
    filter_prompt_template = f.read()

with open("prompts/title_prompt.txt", "r") as f:
    title_prompt_template = f.read()

with open("prompts/rewrite_prompt.txt", "r") as f:
    rewrite_prompt_template = f.read()

with open("prompts/category_prompt.txt", "r") as f:
    category_prompt_template = f.read()

# Setup OpenAI
openai.api_key = os.getenv("OPENAI_API_KEY")

# Fetch and parse feeds
articles = []

for url in feeds:
    feed = feedparser.parse(url)
    for entry in feed.entries:
        pub_date = dateparser.parse(entry.get("published", datetime.utcnow().isoformat()))
        if (datetime.now(pub_date.tzinfo) - pub_date).days > config.RUN_INTERVAL_HOURS:  # Skip too old
            continue

        # Try to find image URL
        image_url = None
        if 'media_content' in entry:
            image_url = entry.media_content[0].get('url', None)
        elif 'media_thumbnail' in entry:
            image_url = entry.media_thumbnail[0].get('url', None)

        articles.append({
            "title": entry.title,
            "link": entry.link,
            "summary": entry.get("summary", ""),
            "pubDate": pub_date,
            "image": image_url
        })

# Deduplicate by link
unique_articles = {a['link']: a for a in articles}
articles = list(unique_articles.values())

# Sort by date
articles = sorted(articles, key=lambda x: x['pubDate'], reverse=True)
articles = articles[:config.MAX_ARTICLES]

# Rewrite and classify
rewritten_articles = []

# List of allowed categories
allowed_categories = [
    "Politics", "Economy", "Environment", "Social Progress",
    "Health", "War and Conflicts", "EU Affairs", "Science and Innovation", "Other"
]

for a in articles:
    # Step 1: Filter article
    filter_prompt = f"{filter_prompt_template}\n\nHeadline: {a['title']}\nSummary: {a['summary']}"
    filter_response = openai.chat.completions.create(
        model="gpt-4o",
        messages=[{"role": "user", "content": filter_prompt}],
        max_tokens=20
    )
    filter_decision = filter_response.choices[0].message.content.strip()

    if filter_decision != "Acceptable":
        print(f"⏭️ Skipping article: {a['title']}")
        continue

    # Step 2: Rewrite title (English, calming, country/region if relevant)
    title_prompt = f"{title_prompt_template}\n\n{a['title']}"
    title_response = openai.chat.completions.create(
        model="gpt-4o",
        messages=[{"role": "user", "content": title_prompt}],
        max_tokens=100
    )
    rewritten_title = title_response.choices[0].message.content.strip()

    # Step 3: Rewrite summary (calm, neutral)
    rewrite_prompt = f"{rewrite_prompt_template}\n\nHeadline: {a['title']}\nSummary: {a['summary']}"
    rewrite_response = openai.chat.completions.create(
        model="gpt-4o",
        messages=[{"role": "user", "content": rewrite_prompt}],
        max_tokens=500
    )
    new_summary = rewrite_response.choices[0].message.content

    if "Skipped due to content" in new_summary:
        print(f"⏭️ Skipping article during rewrite: {a['title']}")
        continue

    # Step 4: Classify
    category_prompt = f"{category_prompt_template}\n\nHeadline: {a['title']}\nSummary: {a['summary']}"
    category_response = openai.chat.completions.create(
        model="gpt-4o",
        messages=[{"role": "user", "content": category_prompt}],
        max_tokens=20
    )
    category = category_response.choices[0].message.content.strip()

    if category not in allowed_categories:
        print(f"⚠️ Invalid category: {category} → Using 'Other'")
        category = "Other"

    # Final article
    rewritten_articles.append({
        "title": rewritten_title,
        "link": a['link'],
        "summary": new_summary,
        "pubDate": a['pubDate'].strftime('%a, %d %b %Y %H:%M:%S +0000'),
        "category": category,
        "image": a['image'] or ""
    })

# Render RSS feed using Jinja2
env = Environment(loader=FileSystemLoader("templates"))
template = env.get_template("rss_template.xml")

rss_content = template.render(
    articles=rewritten_articles,
    build_date=datetime.utcnow().strftime('%a, %d %b %Y %H:%M:%S +0000')
)

with open(config.OUTPUT_RSS_FILE, "w", encoding="utf-8") as f:
    f.write(rss_content)

print(f"✅ {len(rewritten_articles)} articles written to {config.OUTPUT_RSS_FILE}")