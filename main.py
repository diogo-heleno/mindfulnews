# Mindful News Aggregator - main_v3.py
# version: 2025-06-19-v3.0

import feedparser
import openai
import json
import config
import os
import requests
import re
from bs4 import BeautifulSoup
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

with open("prompts/clustering_prompt.txt", "r") as f:
    clustering_prompt_template = f.read()

with open("prompts/synthesis_prompt.txt", "r") as f:
    synthesis_prompt_template = f.read()

# Setup OpenAI
openai.api_key = os.getenv("OPENAI_API_KEY")

# Function to fetch first image from article page
def fetch_og_image(url):
    try:
        response = requests.get(url, timeout=10)
        if response.status_code != 200:
            return None

        soup = BeautifulSoup(response.text, "html.parser")
        og_image = soup.find("meta", property="og:image")
        if og_image and og_image.get("content"):
            return og_image["content"]

        # Fallback — first <img> tag
        first_img = soup.find("img")
        if first_img and first_img.get("src"):
            return first_img["src"]

    except Exception as e:
        print(f"⚠️ Error fetching image from {url}: {e}")

    return None

# Fetch and parse feeds
articles = []

for region, region_feeds in feeds.items():
    for url in region_feeds:
        print(f"🌍 Fetching: {url} ({region})")
        feed = feedparser.parse(url)
        for entry in feed.entries:
            pub_date = dateparser.parse(entry.get("published", datetime.utcnow().isoformat()))
            if (datetime.now(pub_date.tzinfo) - pub_date).days > config.RUN_INTERVAL_HOURS:
                continue

            # Try to find image URL from RSS
            image_url = None
            if 'media_content' in entry:
                image_url = entry.media_content[0].get('url', None)
            elif 'media_thumbnail' in entry:
                image_url = entry.media_thumbnail[0].get('url', None)

            if not image_url:
                image_url = fetch_og_image(entry.link)

            articles.append({
                "title": entry.title,
                "link": entry.link,
                "summary": entry.get("summary", ""),
                "pubDate": pub_date,
                "image": image_url,
                "region": region
            })

# Deduplicate by link
unique_articles = {a['link']: a for a in articles}
articles = list(unique_articles.values())

# Sort by date
articles = sorted(articles, key=lambda x: x['pubDate'], reverse=True)
articles = articles[:config.MAX_ARTICLES]

# Step 1: Filter articles
filtered_articles = []

for a in articles:
    filter_prompt = f"{filter_prompt_template}\n\nHeadline: {a['title']}\nSummary: {a['summary']}"
    filter_response = openai.chat.completions.create(
        model="gpt-4o",
        messages=[{"role": "user", "content": filter_prompt}],
        max_tokens=20
    )
    filter_decision = filter_response.choices[0].message.content.strip()

    if filter_decision == "Acceptable":
        filtered_articles.append(a)
    else:
        print(f"⏭️ Skipping: {a['title']} ({filter_decision})")

print(f"✅ Filtered articles: {len(filtered_articles)}")

# Step 2: Prepare clustering prompt
article_list_text = ""
for a in filtered_articles:
    article_list_text += f"Title: {a['title']}\nSummary: {a['summary']}\nURL: {a['link']}\nRegion: {a['region']}\n\n"

clustering_prompt = f"{clustering_prompt_template}\n\n{article_list_text}"

# Step 3: Call GPT for clustering
clustering_response = openai.chat.completions.create(
    model="gpt-4o",
    messages=[{"role": "user", "content": clustering_prompt}],
    max_tokens=3000
)

clustering_result = clustering_response.choices[0].message.content.strip()
print(f"🧩 Clustering result:\n{clustering_result}")

# Now parse clustering result (you will need to parse GPT response here — I will help you in next version)

# For this v3 skeleton — simulate 1 story per article (no actual clustering yet)
final_articles = []

for a in filtered_articles:
    synthesis_prompt = f"{synthesis_prompt_template}\n\nTitle: {a['title']}\nSummary: {a['summary']}\nRegion: {a['region']}\nURL: {a['link']}"
    synthesis_response = openai.chat.completions.create(
        model="gpt-4o",
        messages=[{"role": "user", "content": synthesis_prompt}],
        max_tokens=500
    )
    synthesis_result = synthesis_response.choices[0].message.content.strip()

    # Parse synthesis result:
    if "Headline:" in synthesis_result and "Summary:" in synthesis_result:
        headline = synthesis_result.split("Headline:")[1].split("Summary:")[0].strip()
        summary = synthesis_result.split("Summary:")[1].strip()
    else:
        headline = a['title']
        summary = a['summary']

    final_articles.append({
        "title": headline,
        "link": a['link'],
        "summary": summary,
        "pubDate": a['pubDate'].strftime('%a, %d %b %Y %H:%M:%S +0000'),
        "category": "Other",  # For now — can be improved
        "image": a['image'] or ""
    })

# Render RSS feed
env = Environment(loader=FileSystemLoader("templates"))
template = env.get_template("rss_template.xml")

rss_content = template.render(
    articles=final_articles,
    build_date=datetime.utcnow().strftime('%a, %d %b %Y %H:%M:%S +0000')
)

with open(config.OUTPUT_RSS_FILE, "w", encoding="utf-8") as f:
    f.write(rss_content)

print(f"✅ {len(final_articles)} articles written to {config.OUTPUT_RSS_FILE}")
