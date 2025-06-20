# Mindful News — main.py v5.3

import feedparser
import openai
import json
import config
import os
import requests
import html
from bs4 import BeautifulSoup
from jinja2 import Environment, FileSystemLoader
from dateutil import parser as dateparser
from datetime import datetime, timezone
import re

# Version check
MAIN_VERSION = "2025-06-20-v5.3"

# Detect BASE_DIR
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# Load feeds
with open(os.path.join(BASE_DIR, "feeds.json")) as f:
    feeds = json.load(f)

# Load prompts
def load_prompt(path):
    with open(os.path.join(BASE_DIR, path), "r") as f:
        return f.read()

clustering_prompt_template = load_prompt("prompts/clustering_prompt.txt")
synthesis_prompt_template = load_prompt("prompts/synthesis_prompt.txt")

# Load rss_template.xml first line
with open(os.path.join(BASE_DIR, "templates/rss_template.xml"), "r") as f:
    rss_template_version = f.readline().strip()

# Setup OpenAI — use env variable
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

print("\nMindful News v5.3 — version check:\n")
print(f"main.py version: {MAIN_VERSION}")
print(f"feeds.json version: unknown")
print(f"clustering_prompt.txt version: {clustering_prompt_template.splitlines()[0]}")
print(f"synthesis_prompt.txt version: {synthesis_prompt_template.splitlines()[0]}")
print(f"rss_template.xml version: {rss_template_version}\n")

for url in sum(feeds.values(), []):
    print(f"🌍 Fetching feed: {url}")
    feed = feedparser.parse(url)
    for entry in feed.entries:
        try:
            pub_date = dateparser.parse(
                entry.get("published", datetime.now(timezone.utc).isoformat())
            )
        except Exception:
            pub_date = datetime.now(timezone.utc)

        if pub_date.tzinfo is None:
            pub_date = pub_date.replace(tzinfo=timezone.utc)

        if (datetime.now(timezone.utc) - pub_date).days > (config.RUN_INTERVAL_HOURS / 24):
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

# Prepare list for clustering
titles = [a['title'] for a in articles]

if not titles:
    print("⚠️ No articles found — exiting.")
    exit(0)

# Clustering
clustering_input = clustering_prompt_template + "\n\n" + json.dumps(titles, indent=2)

print("\n🧠 Calling OpenAI to cluster articles...")
clustering_response = openai.chat.completions.create(
    model="gpt-4o",
    messages=[{"role": "user", "content": clustering_input}],
    max_tokens=4000
)
clustering_output = clustering_response.choices[0].message.content

try:
    json_start = clustering_output.find("[")
    json_end = clustering_output.rfind("]") + 1
    clustering_json = json.loads(clustering_output[json_start:json_end])
    print(f"✅ Clustering done — {len(clustering_json)} clusters found.\n")
except Exception as e:
    print(f"⚠️ Error parsing clustering JSON: {e}")
    clustering_json = []

if not clustering_json:
    print("⚠️ No clusters returned — using fallback General News.")
    clustering_json = [{"theme": "General News", "articles": titles}]

def json_safe_article(a):
    return {
        "title": a["title"],
        "link": a["link"],
        "summary": a["summary"],
        "pubDate": a["pubDate"].isoformat(),
        "image": a["image"]
    }

# Synthesis
rss_items = []
for cluster in clustering_json:
    cluster_titles = cluster["articles"]
    selected_articles = [a for a in articles if a["title"] in cluster_titles]

    json_articles = [json_safe_article(a) for a in selected_articles]

    synthesis_input = synthesis_prompt_template + "\n\n" + json.dumps(json_articles, indent=2)
    synthesis_response = openai.chat.completions.create(
        model="gpt-4o",
        messages=[{"role": "user", "content": synthesis_input}],
        max_tokens=4000
    )
    synthesis_output = synthesis_response.choices[0].message.content

    article_blocks = re.split(r"\n\s*\n(?=<Positive>|<Constructive>|<Cautionary>)", synthesis_output.strip())

    print(f"✅ Synthesized {len(article_blocks)} articles for theme: {cluster['theme']}")

    for block in article_blocks:
        # Strong cleaning: remove accidental <?xml ...?> anywhere
        block = re.sub(r'\s*<\?xml[^>]+?\?>\s*', '', block, flags=re.IGNORECASE)

        lines = block.strip().splitlines()
        if len(lines) < 3:
            continue

        positivity_line = lines[0].strip()
        headline_line = next((l for l in lines if l.startswith("**Headline:**")), "")
        summary_index = lines.index("**Summary:**") if "**Summary:**" in lines else None

        if summary_index is not None:
            summary_text = "\n".join(lines[summary_index + 1:]).strip()
        else:
            summary_text = "\n".join(lines[1:]).strip()

        rss_items.append({
            "title": html.escape(headline_line.replace("**Headline:**", "").strip() or cluster["theme"]),
            "link": "",
            "summary": summary_text,
            "pubDate": datetime.now(timezone.utc).strftime('%a, %d %b %Y %H:%M:%S +0000'),
            "category": html.escape(cluster["theme"]),
            "image": "",
            "positivity": positivity_line
        })

# Render RSS
env = Environment(loader=FileSystemLoader(os.path.join(BASE_DIR, "templates")))
template = env.get_template("rss_template.xml")

rss_content = template.render(
    articles=rss_items,
    build_date=datetime.now(timezone.utc).strftime('%a, %d %b %Y %H:%M:%S +0000')
)

with open(os.path.join(BASE_DIR, config.OUTPUT_RSS_FILE), "w", encoding="utf-8") as f:
    f.write(rss_content)

print(f"\n✅ Final RSS items: {len(rss_items)}")
print(f"✅ RSS feed written to {config.OUTPUT_RSS_FILE}")