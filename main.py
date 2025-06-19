# mindfulnews main.py (v4.2)

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
from datetime import datetime, timezone
from collections import defaultdict

# Load feeds
with open("feeds.json") as f:
    feeds = json.load(f)

# Load prompts
def load_prompt(file_path):
    with open(file_path, "r") as f:
        content = f.read()
        # Extract version line if present
        version_match = re.search(r"version[:=]\s*([^\s]+)", content)
        version = version_match.group(1) if version_match else "unknown"
        return content, version

clustering_prompt, clustering_version = load_prompt("prompts/clustering_prompt.txt")
synthesis_prompt, synthesis_version = load_prompt("prompts/synthesis_prompt.txt")

# Load template
template_path = "templates/rss_template.xml"
with open(template_path, "r") as f:
    template_content = f.read()
    template_version_match = re.search(r"version[:=]\s*([^\s]+)", template_content)
    template_version = template_version_match.group(1) if template_version_match else "unknown"

# Setup OpenAI
openai.api_key = os.getenv("OPENAI_API_KEY")

# Version info
main_version = "2025-06-19-v4.2"
feeds_version = "unknown"  # You can manually add version line in feeds.json if you want

print("\nMindful News v4 — version check:\n")
print(f"main.py version: {main_version}")
print(f"feeds.json version: {feeds_version}")
print(f"clustering_prompt.txt version: {clustering_version}")
print(f"synthesis_prompt.txt version: {synthesis_version}")
print(f"rss_template.xml version: {template_version}\n")

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

# Fetch and parse feeds
articles = []
for category, urls in feeds.items():
    for url in urls:
        print(f"🌍 Fetching feed: {url}")
        feed = feedparser.parse(url)
        for entry in feed.entries:
            pub_date = dateparser.parse(entry.get("published", datetime.utcnow().isoformat()))
            # Ensure timezone-aware UTC for consistent comparison
            pub_date = pub_date.astimezone(timezone.utc)

            # Skip articles older than configured limit
            age_hours = (datetime.now(timezone.utc) - pub_date).total_seconds() / 3600
            if age_hours > config.RUN_INTERVAL_HOURS:
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
                "image": image_url
            })

print(f"\n✅ Total articles fetched: {len(articles)}")

# Deduplicate
unique_articles = {a['link']: a for a in articles}
articles = list(unique_articles.values())
print(f"✅ Total articles after dedup: {len(articles)}")

# Sort by date
articles = sorted(articles, key=lambda x: x['pubDate'], reverse=True)

# Prepare input for clustering
cluster_input = ""
for idx, a in enumerate(articles, start=1):
    cluster_input += f"[{idx}] Title: {a['title']}\nSummary: {a['summary']}\n\n"

# Call OpenAI to cluster articles
print("\n🧠 Calling OpenAI to cluster articles...")
clustering_response = openai.chat.completions.create(
    model="gpt-4o",
    messages=[
        {"role": "user", "content": f"{clustering_prompt}\n\n{cluster_input}"}
    ],
    max_tokens=4096,
    temperature=0.7
)

clusters_text = clustering_response.choices[0].message.content.strip()

# Parse clusters
clusters = defaultdict(list)
current_cluster = None
for line in clusters_text.splitlines():
    line = line.strip()
    if re.match(r"^Cluster \d+", line, re.I):
        current_cluster = line
    elif re.match(r"^\d+", line):
        if current_cluster:
            clusters[current_cluster].append(line)

print(f"✅ Clustering done — {len(clusters)} clusters found.\n")

# Call synthesis for each cluster
env = Environment(loader=FileSystemLoader("templates"))
template = env.get_template("rss_template.xml")

rss_items = []
for cluster_name, cluster_articles in clusters.items():
    selected_articles = []
    for item in cluster_articles:
        match = re.search(r"(\d+)", item)
        if match:
            idx = int(match.group(1)) - 1
            if 0 <= idx < len(articles):
                selected_articles.append(articles[idx])

    if not selected_articles:
        continue

    # Prepare synthesis input
    synth_input = ""
    for a in selected_articles:
        synth_input += f"Title: {a['title']}\nSummary: {a['summary']}\nSource: {a['link']}\n\n"

    print(f"📝 Synthesizing: {cluster_name} — {len(selected_articles)} articles")

    synthesis_response = openai.chat.completions.create(
        model="gpt-4o",
        messages=[
            {"role": "user", "content": f"{synthesis_prompt}\n\n{synth_input}"}
        ],
        max_tokens=2048,
        temperature=0.7
    )

    final_text = synthesis_response.choices[0].message.content.strip()

    # Choose latest pubDate
    pub_date = max(a['pubDate'] for a in selected_articles)

    # Choose first non-null image (could be improved)
    image_url = next((a['image'] for a in selected_articles if a['image']), None)

    rss_items.append({
        "title": f"{cluster_name} — {len(selected_articles)} articles",
        "link": selected_articles[0]['link'],
        "summary": final_text,
        "pubDate": pub_date.strftime('%a, %d %b %Y %H:%M:%S +0000'),
        "category": "Other",
        "image": image_url or ""
    })

print(f"\n✅ Final RSS items: {len(rss_items)}")

# Render RSS feed
rss_content = template.render(
    articles=rss_items,
    build_date=datetime.utcnow().strftime('%a, %d %b %Y %H:%M:%S +0000')
)

with open(config.OUTPUT_RSS_FILE, "w", encoding="utf-8") as f:
    f.write(rss_content)

print(f"✅ RSS feed written to {config.OUTPUT_RSS_FILE}")