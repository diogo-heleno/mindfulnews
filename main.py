# Mindful News v3 — main.py version: 2025-06-19-v3.7

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
from dateutil import tz
from datetime import datetime, timedelta

# --- Load versions ---
def extract_version(file_path, marker="version:"):
    with open(file_path, "r", encoding="utf-8") as f:
        content = f.read()
    match = re.search(rf"{marker}\s*([^\s<]+)", content)
    return match.group(1) if match else "unknown"

# --- Parse pubDate: force naive UTC ---
def parse_pubdate(pub_date_raw):
    dt = dateparser.parse(pub_date_raw)
    if dt.tzinfo is not None:
        dt = dt.astimezone(tz.UTC).replace(tzinfo=None)
    return dt

# --- Load feeds ---
with open("feeds.json", "r", encoding="utf-8") as f:
    feeds_data = json.load(f)

# --- Load prompts ---
def load_prompt(path):
    with open(path, "r", encoding="utf-8") as f:
        return f.read()

prompt_clustering = load_prompt("prompts/clustering_prompt.txt")
prompt_synthesis   = load_prompt("prompts/synthesis_prompt.txt")

# --- Version check ---
print("\nMindful News v3 — version check:\n")
print(f"main.py version: 2025-06-19-v3.7")
print(f"feeds.json version: {extract_version('feeds.json')}")
print(f"clustering_prompt.txt version: {extract_version('prompts/clustering_prompt.txt')}")
print(f"synthesis_prompt.txt version: {extract_version('prompts/synthesis_prompt.txt')}")
print(f"rss_template.xml version: {extract_version('templates/rss_template.xml')}\n")

# --- Setup OpenAI ---
openai.api_key = os.getenv("OPENAI_API_KEY")

# --- Fetch image ---
def fetch_og_image(url):
    try:
        response = requests.get(url, timeout=10)
        if response.status_code != 200:
            return None
        soup = BeautifulSoup(response.text, "html.parser")
        og = soup.find("meta", property="og:image")
        if og and og.get("content"):
            return og["content"]
        img = soup.find("img")
        if img and img.get("src"):
            return img["src"]
    except Exception as e:
        print(f"⚠️ Error fetching image from {url}: {e}")
    return None

# --- Fetch feeds ---
articles = []

for region, feed_list in feeds_data.items():
    for feed_url in feed_list:
        print(f"🌍 Fetching feed: {feed_url}")
        feed = feedparser.parse(feed_url)
        for entry in feed.entries:
            pub_date_raw = entry.get("published", datetime.utcnow().isoformat())
            pub_date = parse_pubdate(pub_date_raw)

            if (datetime.utcnow() - pub_date).days > config.RUN_INTERVAL_HOURS:
                continue

            image_url = None
            if 'media_content' in entry:
                image_url = entry.media_content[0].get('url', None)
            elif 'media_thumbnail' in entry:
                image_url = entry.media_thumbnail[0].get('url', None)
            if not image_url:
                image_url = fetch_og_image(entry.link)

            articles.append({
                "region": region,
                "title": entry.title,
                "link": entry.link,
                "summary": entry.get("summary", ""),
                "pubDate": pub_date,
                "image": image_url
            })

print(f"\n✅ Total articles fetched: {len(articles)}")

# --- Deduplicate ---
unique_articles = {a["link"]: a for a in articles}
articles = list(unique_articles.values())

# --- Sort by date ---
articles = sorted(articles, key=lambda x: x["pubDate"], reverse=True)
articles = articles[:config.MAX_ARTICLES]

print(f"✅ Total articles after dedup: {len(articles)}\n")

# --- Clustering prompt ---
clustering_input = "\n\n".join([f"Title: {a['title']}\nSummary: {a['summary']}" for a in articles])

clustering_response = openai.chat.completions.create(
    model="gpt-4o",
    messages=[
        {"role": "user", "content": f"{prompt_clustering}\n\n{clustering_input}"}
    ],
    max_tokens=2000
)

clusters_raw = clustering_response.choices[0].message.content
print("✅ Clustering done.")

# --- Extract clusters ---
clusters = re.split(r"\n\s*---\s*\n", clusters_raw.strip())

# --- Final RSS items ---
rss_items = []

for cluster in clusters:
    synthesis_prompt = f"{prompt_synthesis}\n\n{cluster}"
    synthesis_response = openai.chat.completions.create(
        model="gpt-4o",
        messages=[{"role": "user", "content": synthesis_prompt}],
        max_tokens=1200
    )
    article = synthesis_response.choices[0].message.content.strip()

    # Attempt to parse fields
    title_match = re.search(r"\*\*Headline:\*\*\s*(.+)", article)
    summary_match = re.search(r"\*\*Summary:\*\*\s*(.+)", article, re.DOTALL)
    category_match = re.search(r"\*\*Category:\*\*\s*(.+)", article)

    title = title_match.group(1).strip() if title_match else "Untitled"
    summary = summary_match.group(1).strip() if summary_match else "No summary."
    category = category_match.group(1).strip() if category_match else "Other"

    # Choose one image (for now: first from cluster)
    cluster_links = re.findall(r"https?://[^\s)]+", cluster)
    first_link = cluster_links[0] if cluster_links else "https://mindfulnews.media"
    first_image = None
    for a in articles:
        if a["link"] in cluster_links and a["image"]:
            first_image = a["image"]
            break

    rss_items.append({
        "title": title,
        "link": first_link,
        "summary": summary,
        "pubDate": datetime.utcnow().strftime('%a, %d %b %Y %H:%M:%S +0000'),
        "category": category,
        "image": first_image or ""
    })

print(f"\n✅ Final RSS items: {len(rss_items)}")

# --- Render RSS ---
env = Environment(loader=FileSystemLoader("templates"))
template = env.get_template("rss_template.xml")

rss_content = template.render(
    articles=rss_items,
    build_date=datetime.utcnow().strftime('%a, %d %b %Y %H:%M:%S +0000')
)

with open(config.OUTPUT_RSS_FILE, "w", encoding="utf-8") as f:
    f.write(rss_content)

print(f"✅ RSS feed written to {config.OUTPUT_RSS_FILE}")