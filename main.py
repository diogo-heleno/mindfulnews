# main_v3.8.py — version: 2025-06-19-v3.8

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

# VERSION CHECK
MAIN_VERSION = "2025-06-19-v3.8"

# Load feeds
with open("feeds.json") as f:
    feeds_data = json.load(f)
    feeds_version = feeds_data.get("_version", "unknown")
    feeds = []
    for region, urls in feeds_data.items():
        if region != "_version":
            feeds.extend(urls)

# Load prompts
def load_prompt(filename):
    with open(filename, "r") as f:
        text = f.read()
    version_match = re.search(r"version:\s*(\S+)", text)
    version = version_match.group(1) if version_match else "unknown"
    return text, version

clustering_prompt, clustering_version = load_prompt("prompts/clustering_prompt.txt")
synthesis_prompt, synthesis_version = load_prompt("prompts/synthesis_prompt.txt")

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

# Version check print
print("\nMindful News v3 — version check:\n")
print(f"main.py version: {MAIN_VERSION}")
print(f"feeds.json version: {feeds_version}")
print(f"clustering_prompt.txt version: {clustering_version}")
print(f"synthesis_prompt.txt version: {synthesis_version}\n")

# Fetch and parse feeds
articles = []
for url in feeds:
    print(f"🌍 Fetching feed: {url}")
    feed = feedparser.parse(url)
    for entry in feed.entries:
        try:
            pub_date = dateparser.parse(entry.get("published", datetime.utcnow().isoformat()))
        except Exception:
            pub_date = datetime.utcnow()

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
            "image": image_url or ""
        })

print(f"\n✅ Total articles fetched: {len(articles)}")

# Deduplicate
unique_articles = {a['link']: a for a in articles}
articles = list(unique_articles.values())
print(f"✅ Total articles after dedup: {len(articles)}\n")

# Sort by date
for article in articles:
    if article["pubDate"].tzinfo is None:
        article["pubDate"] = article["pubDate"].replace(tzinfo=datetime.now().astimezone().tzinfo)

articles = sorted(articles, key=lambda x: x["pubDate"], reverse=True)
articles = articles[:config.MAX_ARTICLES]

# Chunk into groups for clustering
chunk_size = 20
chunks = [articles[i:i + chunk_size] for i in range(0, len(articles), chunk_size)]

clusters = []

for idx, chunk in enumerate(chunks):
    print(f"🚀 Running clustering on chunk {idx + 1}/{len(chunks)} — {len(chunk)} articles")

    chunk_text = ""
    for article in chunk:
        chunk_text += f"---\nHeadline: {article['title']}\nSummary: {article['summary']}\nLink: {article['link']}\n\n"

    full_clustering_prompt = clustering_prompt + f"\n\n{chunk_text}"

    response = openai.chat.completions.create(
        model="gpt-4o",
        messages=[{"role": "user", "content": full_clustering_prompt}],
        max_tokens=3000
    )
    clusters_text = response.choices[0].message.content.strip()
    clusters.append(clusters_text)

print(f"\n✅ Clustering done.\n")

# Combine clusters
all_clusters_text = "\n\n".join(clusters)

# Run synthesis
print("📝 Running synthesis prompt...")
final_prompt = synthesis_prompt + f"\n\n{all_clusters_text}"

response = openai.chat.completions.create(
    model="gpt-4o",
    messages=[{"role": "user", "content": final_prompt}],
    max_tokens=4000
)
final_rss_text = response.choices[0].message.content.strip()

# Parse final items
rss_items = []
item_blocks = re.split(r"---+", final_rss_text)

for block in item_blocks:
    block = block.strip()
    if not block:
        continue
    title_match = re.search(r"Title:\s*(.+)", block)
    summary_match = re.search(r"Summary:\s*(.+)", block, re.DOTALL)
    link_match = re.search(r"Link:\s*(.+)", block)
    category_match = re.search(r"Category:\s*(.+)", block)

    if title_match and summary_match and link_match and category_match:
        item = {
            "title": title_match.group(1).strip(),
            "summary": summary_match.group(1).strip(),
            "link": link_match.group(1).strip(),
            "category": category_match.group(1).strip(),
            "pubDate": datetime.utcnow().strftime('%a, %d %b %Y %H:%M:%S +0000'),
            "image": ""
        }
        rss_items.append(item)

print(f"\n✅ Final RSS items: {len(rss_items)}")

# Render RSS feed
env = Environment(loader=FileSystemLoader("templates"))
template = env.get_template("rss_template.xml")

rss_content = template.render(
    articles=rss_items,
    build_date=datetime.utcnow().strftime('%a, %d %b %Y %H:%M:%S +0000')
)

with open(config.OUTPUT_RSS_FILE, "w", encoding="utf-8") as f:
    f.write(rss_content)

print(f"✅ RSS feed written to {config.OUTPUT_RSS_FILE}")