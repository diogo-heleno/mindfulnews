# main_v3.6.py

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
from datetime import datetime

# VERSION
MAIN_VERSION = "2025-06-19-v3.6"

# Load feeds
with open("feeds.json") as f:
    feeds = json.load(f)
    feeds_version = feeds.get("_version", "unknown")

# Load prompts
def load_prompt(filename):
    with open(filename, "r", encoding="utf-8") as f:
        lines = f.readlines()
        version = "unknown"
        if len(lines) > 0 and "version:" in lines[0]:
            version = lines[0].split("version:")[1].strip()
        return "".join(lines), version

clustering_prompt_template, clustering_version = load_prompt("prompts/clustering_prompt.txt")
synthesis_prompt_template, synthesis_version = load_prompt("prompts/synthesis_prompt.txt")

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
        
        first_img = soup.find("img")
        if first_img and first_img.get("src"):
            return first_img["src"]

    except Exception as e:
        print(f"⚠️ Error fetching image from {url}: {e}")

    return None

# Fetch feeds
articles = []
for region, region_feeds in feeds.items():
    if region.startswith("_"): continue  # skip _version
    for url in region_feeds:
        print(f"🌍 Fetching feed: {url}")
        feed = feedparser.parse(url)
        for entry in feed.entries:
            pub_date = dateparser.parse(entry.get("published", datetime.utcnow().isoformat()))
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
                "region": region,
                "image": image_url
            })

# Dedup
unique_articles = {a['link']: a for a in articles}
articles = list(unique_articles.values())
articles = sorted(articles, key=lambda x: x['pubDate'], reverse=True)
print(f"✅ Total articles fetched after dedup: {len(articles)}")

# Build clustering prompt
clustering_prompt = clustering_prompt_template + "\n\n"
for idx, a in enumerate(articles):
    clustering_prompt += f"""
### Article {idx+1}
Region: {a['region']}
Title: {a['title']}
Summary: {a['summary']}
Link: {a['link']}
"""
print("🛠️ Sending clustering prompt...")

# Clustering step
clustering_response = openai.chat.completions.create(
    model="gpt-4o",
    messages=[{"role": "user", "content": clustering_prompt}],
    max_tokens=4000
)
cluster_json = clustering_response.choices[0].message.content.strip()

# Parse clusters
try:
    clusters = json.loads(cluster_json)
except Exception as e:
    print(f"❌ ERROR parsing cluster JSON: {e}")
    print("Response was:")
    print(cluster_json)
    clusters = []

print(f"✅ Clusters parsed: {len(clusters)}")

# Synthesis step
rss_articles = []

for cidx, cluster in enumerate(clusters):
    print(f"📝 Synthesizing cluster {cidx+1}/{len(clusters)}")

    cluster_articles = [articles[i] for i in cluster["article_indexes"]]
    all_titles = "\n".join([a['title'] for a in cluster_articles])
    all_summaries = "\n\n".join([a['summary'] for a in cluster_articles])

    synthesis_prompt = synthesis_prompt_template.format(
        cluster_title=cluster["cluster_title"],
        all_titles=all_titles,
        all_summaries=all_summaries
    )

    synthesis_response = openai.chat.completions.create(
        model="gpt-4o",
        messages=[{"role": "user", "content": synthesis_prompt}],
        max_tokens=1000
    )
    result = synthesis_response.choices[0].message.content.strip()

    # Extract fields
    match = re.search(r"Title:\s*(.*?)\nSummary:\s*(.*?)\nCategory:\s*(.*?)\n", result, re.DOTALL)
    if match:
        rss_articles.append({
            "title": match.group(1).strip(),
            "summary": match.group(2).strip(),
            "category": match.group(3).strip(),
            "pubDate": datetime.utcnow().strftime('%a, %d %b %Y %H:%M:%S +0000'),
            "link": cluster_articles[0]['link'],
            "image": cluster_articles[0]['image'] or ""
        })
    else:
        print(f"⚠️ Could not parse synthesis result, skipping cluster.")
        print(result)

# Render RSS feed
env = Environment(loader=FileSystemLoader("templates"))
template = env.get_template("rss_template.xml")

rss_content = template.render(
    articles=rss_articles,
    build_date=datetime.utcnow().strftime('%a, %d %b %Y %H:%M:%S +0000')
)

with open(config.OUTPUT_RSS_FILE, "w", encoding="utf-8") as f:
    f.write(rss_content)

# Version info
print(f"""
Mindful News v3 — version check:

main.py version: {MAIN_VERSION}
feeds.json version: {feeds_version}
clustering_prompt.txt version: {clustering_version}
synthesis_prompt.txt version: {synthesis_version}
rss_template.xml version: (check inside template!)
""")

print(f"✅ Final RSS: {len(rss_articles)} articles written to {config.OUTPUT_RSS_FILE}")