# Mindful News v4 — main.py version: 2025-06-19-v4.1

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

# Load prompts
def get_version(file_path):
    try:
        with open(file_path, "r") as f:
            lines = f.readlines()
        for line in lines:
            if "version:" in line.lower():
                return line.strip().split(":")[1].strip()
    except:
        return None
    return None

with open("feeds.json") as f:
    feeds = json.load(f)
feeds_version = get_version("feeds.json")

with open("prompts/clustering_prompt.txt", "r") as f:
    clustering_prompt_template = f.read()
clustering_version = get_version("prompts/clustering_prompt.txt")

with open("prompts/synthesis_prompt.txt", "r") as f:
    synthesis_prompt_template = f.read()
synthesis_version = get_version("prompts/synthesis_prompt.txt")

# Setup OpenAI
openai.api_key = os.getenv("OPENAI_API_KEY")

# Fetch first image
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

# 🚀 Startup log
print(f"\nMindful News v4 — version check:\n")
print(f"main.py version: 2025-06-19-v4.1")
print(f"feeds.json version: {feeds_version}")
print(f"clustering_prompt.txt version: {clustering_version}")
print(f"synthesis_prompt.txt version: {synthesis_version}")

# Load RSS template
env = Environment(loader=FileSystemLoader("templates"))
template = env.get_template("rss_template.xml")
rss_version = get_version("templates/rss_template.xml")
print(f"rss_template.xml version: {rss_version} -->\n")

# Fetch feeds
articles = []
for region, region_feeds in feeds.items():
    for url in region_feeds:
        print(f"🌍 Fetching feed: {url}")
        feed = feedparser.parse(url)
        for entry in feed.entries:
            pub_date = dateparser.parse(entry.get("published", datetime.utcnow().isoformat()))

            # Image
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

# Sort articles
articles = sorted(articles, key=lambda x: x['pubDate'], reverse=True)
articles = articles[:config.MAX_ARTICLES]

# Clustering
print("\n🧠 Clustering articles...")
cluster_input = "\n\n".join([f"Title: {a['title']}\nSummary: {a['summary']}" for a in articles])

clustering_response = openai.chat.completions.create(
    model="gpt-4o",
    messages=[{"role": "user", "content": f"{clustering_prompt_template}\n\n{cluster_input}"}],
    max_tokens=4096
)

cluster_text = clustering_response.choices[0].message.content
clusters = []

current_cluster = []
for line in cluster_text.split("\n"):
    line = line.strip()
    if line.startswith("- ") or line.startswith("* "):
        current_cluster.append(line[2:].strip())
    elif line == "" and current_cluster:
        clusters.append(current_cluster)
        current_cluster = []
if current_cluster:
    clusters.append(current_cluster)

print(f"\n✅ Clustering done. {len(clusters)} clusters found.")

# Synthesis
rss_items = []
for cluster in clusters:
    if len(cluster) == 0:
        continue
    synthesis_input = "\n".join([f"- {title}" for title in cluster])
    synthesis_response = openai.chat.completions.create(
        model="gpt-4o",
        messages=[{"role": "user", "content": f"{synthesis_prompt_template}\n\n{synthesis_input}"}],
        max_tokens=2048
    )
    story = synthesis_response.choices[0].message.content

    # Pick image (first one in cluster with image)
    selected_image = ""
    for a in articles:
        if any(title in a["title"] for title in cluster):
            if a["image"]:
                selected_image = a["image"]
                break

    rss_items.append({
        "title": cluster[0],  # Use first title as headline
        "summary": story,
        "link": "",  # No canonical link for merged item
        "pubDate": datetime.utcnow().strftime('%a, %d %b %Y %H:%M:%S +0000'),
        "image": selected_image,
        "category": "Mindful News"
    })

print(f"\n✅ Final RSS items: {len(rss_items)}")

# Render RSS feed
rss_content = template.render(
    articles=rss_items,
    build_date=datetime.utcnow().strftime('%a, %d %b %Y %H:%M:%S +0000')
)

with open(config.OUTPUT_RSS_FILE, "w", encoding="utf-8") as f:
    f.write(rss_content)

print(f"\n✅ RSS feed written to {config.OUTPUT_RSS_FILE}\n")