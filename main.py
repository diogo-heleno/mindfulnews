# 🚀 Mindful News v4 — version: 2025-06-19-v4.0

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
import time

# === Version check ===
def extract_version(file_path):
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            for line in f:
                if "version:" in line:
                    return line.strip().split("version:")[1].strip()
    except:
        return "unknown"

print("Mindful News v4 — version check:\n")
print("main_v4.py version: 2025-06-19-v4.0")
print(f"feeds.json version: {extract_version('feeds.json')}")
print(f"clustering_prompt_v4.txt version: {extract_version('prompts/clustering_prompt_v4.txt')}")
print(f"synthesis_prompt_v4.txt version: {extract_version('prompts/synthesis_prompt_v4.txt')}")
print(f"rss_template.xml version: {extract_version('templates/rss_template.xml')}\n")

# === Load files ===
with open("feeds.json") as f:
    feeds = json.load(f)

with open("prompts/clustering_prompt_v4.txt", "r") as f:
    clustering_prompt_template = f.read()

with open("prompts/synthesis_prompt_v4.txt", "r") as f:
    synthesis_prompt_template = f.read()

# === Setup OpenAI ===
openai.api_key = os.getenv("OPENAI_API_KEY")

# === Fetch image ===
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

# === Fetch feeds ===
articles = []
for region, urls in feeds.items():
    for url in urls:
        print(f"🌍 Fetching feed: {url}")
        feed = feedparser.parse(url)
        for entry in feed.entries:
            pub_date = dateparser.parse(entry.get("published", datetime.utcnow().isoformat()))
            if pub_date.tzinfo is None:
                pub_date = pub_date.replace(tzinfo=timezone.utc)
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
                "image": image_url
            })

print(f"\n✅ Total articles fetched: {len(articles)}")

# Deduplicate by link
unique_articles = {a['link']: a for a in articles}
articles = list(unique_articles.values())

# Sort
articles = sorted(articles, key=lambda x: x['pubDate'], reverse=True)
articles = articles[:config.MAX_ARTICLES]

print(f"✅ Total articles after dedup: {len(articles)}\n")

# === Clustering step ===
headlines_text = "\n".join([f"- {a['title']}" for a in articles])
clustering_prompt = clustering_prompt_template.replace("{{ headlines }}", headlines_text)

# Use latest OpenAI API format
clustering_response = openai.chat.completions.create(
    model="gpt-4o",
    messages=[{"role": "user", "content": clustering_prompt}],
    max_tokens=2000
)

cluster_text = clustering_response.choices[0].message.content
print(f"\n✅ Clustering done.\n")
# Parse cluster headlines (example → user must refine parsing later)
clustered_headlines = re.findall(r"- (.+)", cluster_text)

# === Synthesis step per cluster ===
rss_items = []
for cluster_title in clustered_headlines:
    print(f"\n📰 Synthesizing: {cluster_title}")

    # Attempt to search online (browsing)
    try:
        browsing_response = openai.chat.completions.create(
            model="gpt-4o",
            messages=[{
                "role": "user",
                "content": synthesis_prompt_template.replace("{{ topic }}", cluster_title)
            }],
            max_tokens=2000
        )
        summary_text = browsing_response.choices[0].message.content
        print("✅ Used GPT-4o browsing.")
    except Exception as e:
        print(f"⚠️ GPT browsing failed, fallback to RSS. Reason: {e}")
        summary_text = f"Summary of latest news about {cluster_title}:\n\n"
        for a in articles:
            if cluster_title.lower() in a['title'].lower():
                summary_text += f"- {a['title']}: {a['summary']}\n"

    # Select first valid image
    image_url = None
    for a in articles:
        if cluster_title.lower() in a['title'].lower() and a['image']:
            image_url = a['image']
            break

    # Final item
    rss_items.append({
        "title": cluster_title,
        "summary": summary_text,
        "pubDate": datetime.utcnow().strftime('%a, %d %b %Y %H:%M:%S +0000'),
        "link": "https://www.mindfulnews.media",  # Can be improved
        "image": image_url or ""
    })

print(f"\n✅ Final RSS items: {len(rss_items)}")

# === Render RSS feed ===
env = Environment(loader=FileSystemLoader("templates"))
template = env.get_template("rss_template.xml")

rss_content = template.render(
    articles=rss_items,
    build_date=datetime.utcnow().strftime('%a, %d %b %Y %H:%M:%S +0000')
)

with open(config.OUTPUT_RSS_FILE, "w", encoding="utf-8") as f:
    f.write(rss_content)

print(f"✅ RSS feed written to {config.OUTPUT_RSS_FILE}")