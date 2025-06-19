# main_v3.py - Mindful News v3 engine
# version: 2025-06-19-v3.2

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

# --- Version checker ---
def get_file_version(filepath):
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            for line in f:
                version_match = re.search(r'version.*?:\s*(.*)', line, re.IGNORECASE)
                if version_match:
                    return version_match.group(1).strip()
    except Exception as e:
        return "unknown"
    return "unknown"

# --- Load files ---
with open("feeds.json") as f:
    feeds = json.load(f)
feeds_version = get_file_version("feeds.json")

with open("prompts/clustering_prompt.txt", "r") as f:
    clustering_prompt_template = f.read()
clustering_version = get_file_version("prompts/clustering_prompt.txt")

with open("prompts/synthesis_prompt.txt", "r") as f:
    synthesis_prompt_template = f.read()
synthesis_version = get_file_version("prompts/synthesis_prompt.txt")

template_version = get_file_version("templates/rss_template.xml")

# --- Print version info ---
print("\n🚀 Mindful News v3 — version check:\n")
print(f"feeds.json version: {feeds_version}")
print(f"clustering_prompt.txt version: {clustering_version}")
print(f"synthesis_prompt.txt version: {synthesis_version}")
print(f"rss_template.xml version: {template_version}\n")

# Setup OpenAI
openai.api_key = os.getenv("OPENAI_API_KEY")

# Fetch first image from article page
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

for region, url_list in feeds.items():
    for url in url_list:
        print(f"🌍 Fetching feed: {url}")
        feed = feedparser.parse(url)
        for entry in feed.entries:
            pub_date = dateparser.parse(entry.get("published", datetime.utcnow().isoformat()))
            if (datetime.now(pub_date.tzinfo) - pub_date).days > config.RUN_INTERVAL_HOURS:
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
                "image": image_url or ""
            })

# Deduplicate by link
unique_articles = {a['link']: a for a in articles}
articles = list(unique_articles.values())

# Sort by date
articles = sorted(articles, key=lambda x: x['pubDate'], reverse=True)
articles = articles[:config.MAX_ARTICLES]

print(f"✅ Total articles fetched after dedup: {len(articles)}")

# Step 1: Run clustering
clustering_input = ""

for a in articles:
    clustering_input += f"- {a['region']}: {a['title']} ({a['link']})\n"

clustering_prompt = f"{clustering_prompt_template}\n\n{clustering_input}"

clustering_response = openai.ChatCompletion.create(
    model="gpt-4o",
    messages=[{"role": "user", "content": clustering_prompt}],
    max_tokens=4000
)

clustering_result = clustering_response.choices[0].message.content.strip()
print("🔍 Clustering result:\n", clustering_result)

# Step 2: Parse clustering result
topic_groups = {}
current_topic = None

for line in clustering_result.splitlines():
    line = line.strip()
    if line.lower().startswith("topic:"):
        current_topic = line.split(":", 1)[1].strip()
        topic_groups[current_topic] = []
    elif line.startswith("- ") or line.startswith("* ") or re.match(r"^\d+\.", line):
        url_match = re.search(r'(https?://[^\s\)\]]+)', line)
        if url_match and current_topic:
            topic_groups[current_topic].append(url_match.group(1))

print(f"✅ Parsed {len(topic_groups)} topic groups")

# Step 3: Synthesize per topic
rewritten_topics = []

for topic, url_list in topic_groups.items():
    topic_articles = [a for a in articles if a['link'] in url_list]
    if not topic_articles:
        continue

    print(f"📝 Synthesizing topic: {topic} ({len(topic_articles)} articles)")

    synthesis_input = ""
    for art in topic_articles:
        synthesis_input += f"Region: {art['region']}\nTitle: {art['title']}\nSummary: {art['summary']}\n\n"

    synthesis_prompt = f"{synthesis_prompt_template}\n\n{synthesis_input}"

    synthesis_response = openai.ChatCompletion.create(
        model="gpt-4o",
        messages=[{"role": "user", "content": synthesis_prompt}],
        max_tokens=1000
    )
    synthesis_output = synthesis_response.choices[0].message.content.strip()

    # Parse synthesis result
    headline = "Untitled"
    summary = ""
    headline_match = re.search(r"Headline:\s*(.*)", synthesis_output)
    summary_match = re.search(r"Summary:\s*(.*)", synthesis_output, re.DOTALL)

    if headline_match:
        headline = headline_match.group(1).strip()
    if summary_match:
        summary = summary_match.group(1).strip()

    chosen_image = topic_articles[0]['image']
    latest_date = max([a['pubDate'] for a in topic_articles])

    # IMPORTANT — escape & in image URL for XML
    if chosen_image:
        chosen_image = chosen_image.replace("&", "&amp;")

    rewritten_topics.append({
        "title": headline,
        "summary": summary,
        "pubDate": latest_date.strftime('%a, %d %b %Y %H:%M:%S +0000'),
        "category": "Other",
        "link": topic_articles[0]['link'],
        "image": chosen_image
    })

# Render RSS feed
env = Environment(loader=FileSystemLoader("templates"))
template = env.get_template("rss_template.xml")

rss_content = template.render(
    articles=rewritten_topics,
    build_date=datetime.utcnow().strftime('%a, %d %b %Y %H:%M:%S +0000')
)

with open(config.OUTPUT_RSS_FILE, "w", encoding="utf-8") as f:
    f.write(rss_content)

print(f"✅ {len(rewritten_topics)} topics written to {config.OUTPUT_RSS_FILE}")