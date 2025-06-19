mindfulnews — main.py (v4.2)

with LLM-based clustering — June 19 2025

import feedparser import openai import json import config import os import requests import re from bs4 import BeautifulSoup from jinja2 import Environment, FileSystemLoader from dateutil import parser as dateparser from datetime import datetime, timezone

Load feeds

with open("feeds.json") as f: feeds = json.load(f)

Load prompts

with open("prompts/clustering_prompt.txt", "r") as f: clustering_prompt_template = f.read()

with open("prompts/synthesis_prompt.txt", "r") as f: synthesis_prompt_template = f.read()

Setup OpenAI

openai.api_key = os.getenv("OPENAI_API_KEY")

Function to fetch first image from article page

def fetch_og_image(url): try: response = requests.get(url, timeout=10) if response.status_code != 200: return None

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

FETCH + PARSE

print("\nMindful News v4 — version check:\n") print("main.py version: 2025-06-19-v4.2")

articles = []

for region, region_feeds in feeds.items(): for url in region_feeds: print(f"🌍 Fetching feed: {url}") feed = feedparser.parse(url)

for entry in feed.entries:
        pub_date = dateparser.parse(entry.get("published", datetime.utcnow().isoformat()))
        pub_date = pub_date.astimezone(timezone.utc)

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

Dedup

unique_articles = {a['link']: a for a in articles} articles = list(unique_articles.values())

print(f"\n✅ Total articles fetched: {len(articles)}")

Sort

articles = sorted(articles, key=lambda x: x['pubDate'], reverse=True) articles = articles[:config.MAX_ARTICLES]

print(f"✅ Total articles after dedup: {len(articles)}")

LLM CLUSTERING

headlines_block = "\n".join([f"- {a['title']}" for a in articles])

clustering_prompt = f"{clustering_prompt_template}\n\n{headlines_block}"

response = openai.chat.completions.create( model="gpt-4o", messages=[{"role": "user", "content": clustering_prompt}], max_tokens=4000 )

clusters_raw = response.choices[0].message.content.strip()

Parse clusters

clusters = []

current_cluster = None for line in clusters_raw.splitlines(): if re.match(r'^\d+.', line): if current_cluster: clusters.append(current_cluster) current_cluster = {"headline": line, "items": []} elif line.startswith("-") and current_cluster: current_cluster["items"].append(line[1:].strip())

if current_cluster: clusters.append(current_cluster)

print(f"\n✅ Clustering done.") print(f"✅ Clusters found: {len(clusters)}\n")

SYNTHESIZE

rewritten_articles = []

for cluster in clusters: cluster_headline = cluster['headline']

# Find matching articles
matching_articles = [
    a for a in articles
    if any(title_fragment in a['title'] for title_fragment in cluster['items'])
]

if len(matching_articles) == 0:
    continue

cluster_text = "\n\n".join([
    f"Headline: {a['title']}\nSummary: {a['summary']}\nLink: {a['link']}\nRegion: {a['region']}"
    for a in matching_articles
])

synthesis_prompt = f"{synthesis_prompt_template}\n\n{cluster_text}"

synthesis_response = openai.chat.completions.create(
    model="gpt-4o",
    messages=[{"role": "user", "content": synthesis_prompt}],
    max_tokens=2000
)

content = synthesis_response.choices[0].message.content.strip()

# Choose image (non-fearful: first image found)
chosen_image = ""
for a in matching_articles:
    if a['image']:
        chosen_image = a['image']
        break

rewritten_articles.append({
    "title": cluster_headline,
    "summary": content,
    "link": matching_articles[0]['link'],
    "pubDate": matching_articles[0]['pubDate'].strftime('%a, %d %b %Y %H:%M:%S +0000'),
    "category": "Other",
    "image": chosen_image
})

print(f"✅ Final RSS items: {len(rewritten_articles)}")

RENDER RSS

env = Environment(loader=FileSystemLoader("templates")) template = env.get_template("rss_template.xml")

rss_content = template.render( articles=rewritten_articles, build_date=datetime.utcnow().strftime('%a, %d %b %Y %H:%M:%S +0000') )

with open(config.OUTPUT_RSS_FILE, "w", encoding="utf-8") as f: f.write(rss_content)

print(f"✅ RSS feed written to {config.OUTPUT_RSS_FILE}")

