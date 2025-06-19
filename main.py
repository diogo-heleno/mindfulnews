# Mindful News Aggregator — main.py version: 2025-06-19-v4.2

import feedparser
import openai
import json
import config
import os
import requests
import re
import time
from bs4 import BeautifulSoup
from jinja2 import Environment, FileSystemLoader
from dateutil import parser as dateparser
from dateutil import tz
from datetime import datetime, timezone, timedelta

# Load feeds
with open("feeds.json") as f:
    feeds = json.load(f)

# Load prompts
def load_prompt(path):
    with open(path, "r") as f:
        lines = f.readlines()
    version_line = next((line.strip() for line in lines if "version:" in line), "unknown")
    return "".join(lines), version_line

clustering_prompt_text, clustering_version = load_prompt("prompts/clustering_prompt.txt")
synthesis_prompt_text, synthesis_version = load_prompt("prompts/synthesis_prompt.txt")

# Setup OpenAI
openai.api_key = os.getenv("OPENAI_API_KEY")

# Fetch version of rss_template.xml
with open("templates/rss_template.xml", "r") as f:
    rss_template_content = f.read()
rss_version_match = re.search(r"version:\s*(.*?)\s*-->", rss_template_content)
rss_version = rss_version_match.group(1) if rss_version_match else "unknown"

# Print version check
print("\nMindful News v4 — version check:\n")
print(f"main.py version: 2025-06-19-v4.2")
print(f"feeds.json version: {feeds.get('version', 'unknown')}")
print(f"clustering_prompt.txt version: {clustering_version}")
print(f"synthesis_prompt.txt version: {synthesis_version}")
print(f"rss_template.xml version: {rss_version}\n")

# Function to fetch first image from article page
def fetch_og_image(url):
    for attempt in range(3):
        try:
            response = requests.get(url, timeout=15)
            if response.status_code != 200:
                return None
            soup = BeautifulSoup(response.text, "html.parser")
            og_image = soup.find("meta", property="og:image")
            if og_image and og_image.get("content"):
                return og_image["content"]
            first_img = soup.find("img")
            if first_img and first_img.get("src"):
                return first_img["src"]
            return None
        except Exception as e:
            print(f"⚠️ Error fetching image from {url} (attempt {attempt+1}): {e}")
            time.sleep(2)
    return None

# Fetch and parse feeds
articles = []

for region, urls in feeds.items():
    if region == "version": continue  # skip version key
    for url in urls:
        print(f"🌍 Fetching feed: {url}")
        feed = feedparser.parse(url)
        for entry in feed.entries:
            pub_date_raw = entry.get("published", entry.get("updated", datetime.utcnow().isoformat()))
            pub_date = dateparser.parse(pub_date_raw)

            # Convert to UTC to avoid timezone comparison bugs
            if pub_date.tzinfo is None:
                pub_date = pub_date.replace(tzinfo=timezone.utc)
            else:
                pub_date = pub_date.astimezone(timezone.utc)

            if (datetime.now(timezone.utc) - pub_date).days > config.RUN_INTERVAL_HOURS:
                continue

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
print(f"\n✅ Total articles fetched: {len(articles)}")

# Sort by date
articles = sorted(articles, key=lambda x: x['pubDate'], reverse=True)
articles = articles[:config.MAX_ARTICLES]
print(f"✅ Total articles after dedup: {len(articles)}")

# Clustering
print(f"\n✅ Clustering...")
clustering_input = ""
for a in articles:
    clustering_input += f"---\nRegion: {a['region']}\nTitle: {a['title']}\nSummary: {a['summary']}\n"

clustering_response = openai.chat.completions.create(
    model="gpt-4o",
    messages=[{"role": "user", "content": f"{clustering_prompt_text}\n\n{clustering_input}"}],
    max_tokens=2000
)
clusters_text = clustering_response.choices[0].message.content
clusters = re.split(r"\n-{5,}\n", clusters_text.strip())
clusters = [c.strip() for c in clusters if c.strip()]
print(f"\n✅ Clustering done. Found {len(clusters)} clusters.\n")

# Synthesize each cluster
rss_items = []

for i, cluster_text in enumerate(clusters):
    print(f"📝 Synthesizing article {i+1}/{len(clusters)}...")
    synthesis_response = openai.chat.completions.create(
        model="gpt-4o",
        messages=[{"role": "user", "content": f"{synthesis_prompt_text}\n\n{cluster_text}"}],
        max_tokens=1500
    )
    final_article = synthesis_response.choices[0].message.content.strip()

    # Parse synthesized output
    title_match = re.search(r"Title:\s*(.*)", final_article)
    summary_match = re.search(r"Summary:\s*(.*)", final_article, re.DOTALL)
    category_match = re.search(r"Category:\s*(.*)", final_article)

    title = title_match.group(1).strip() if title_match else f"Untitled {i+1}"
    summary = summary_match.group(1).strip() if summary_match else ""
    category = category_match.group(1).strip() if category_match else "Other"

    # Use first image from articles in cluster if possible
    image_url = None
    for a in articles:
        if a['title'] in cluster_text and a['image']:
            image_url = a['image']
            break

    rss_items.append({
        "title": title,
        "summary": summary,
        "category": category,
        "link": "",  # we don't have one URL for synthesized — optional improvement
        "pubDate": datetime.utcnow().strftime('%a, %d %b %Y %H:%M:%S +0000'),
        "image": image_url or ""
    })

# Render RSS feed
env = Environment(loader=FileSystemLoader("templates"))
template = env.get_template("rss_template.xml")

rss_content = template.render(
    articles=rss_items,
    build_date=datetime.utcnow().strftime('%a, %d %b %Y %H:%M:%S +0000')
)

with open(config.OUTPUT_RSS_FILE, "w", encoding="utf-8") as f:
    f.write(rss_content)

print(f"\n✅ Final RSS items: {len(rss_items)}")
print(f"✅ RSS feed written to {config.OUTPUT_RSS_FILE}")