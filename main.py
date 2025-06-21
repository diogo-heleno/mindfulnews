# Mindful News — main.py v5.10

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
MAIN_VERSION = "2025-06-21-v5.10"

# Minimum characters required per article
MIN_CHARACTERS = 3000

# Detect BASE_DIR
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# Load feeds
with open(os.path.join(BASE_DIR, "feeds.json"), encoding="utf-8") as f:
    feeds = json.load(f)

# Load prompts
def load_prompt(path):
    with open(os.path.join(BASE_DIR, path), "r", encoding="utf-8") as f:
        return f.read()

clustering_prompt_template = load_prompt("prompts/clustering_prompt.txt")
synthesis_prompt_template = load_prompt("prompts/synthesis_prompt.txt")

# Load rss_template.xml first line
with open(os.path.join(BASE_DIR, "templates/rss_template.xml"), encoding="utf-8") as f:
    rss_template_version = f.readline().strip()

# Setup OpenAI — use env variable
openai.api_key = os.getenv("OPENAI_API_KEY")

# Helpers
def clean_xml_headers(text):
    return re.sub(r'\s*<\?xml[^>]+?\?>\s*', '', text, flags=re.IGNORECASE)

def strip_rss_tags(text):
    text = re.sub(r'<\/?rss[^>]*>', '', text, flags=re.IGNORECASE)
    text = re.sub(r'<\/?channel[^>]*>', '', text, flags=re.IGNORECASE)
    return text.strip()

def fetch_og_image(url):
    try:
        response = requests.get(url, timeout=10)
        if response.status_code == 200:
            soup = BeautifulSoup(response.text, "html.parser")
            og_image = soup.find("meta", property="og:image")
            if og_image and og_image.get("content"):
                return og_image["content"]
            first_img = soup.find("img")
            if first_img and first_img.get("src"):
                return first_img.get("src")
    except Exception as e:
        print(f"⚠️ Error fetching image from {url}: {e}")
    return None

def filter_recent_articles(articles, now):
    recent = []
    for entry in articles:
        pub_date = entry.get("pubDate")
        if isinstance(pub_date, str):
            try:
                pub_date = dateparser.parse(pub_date)
            except Exception:
                pub_date = now
        if pub_date.tzinfo is None:
            pub_date = pub_date.replace(tzinfo=timezone.utc)
        age_hours = (now - pub_date).total_seconds() / 3600
        if age_hours <= config.RUN_INTERVAL_HOURS:
            recent.append(entry)
    return recent

def enforce_max_articles(articles):
    return articles[: config.MAX_ARTICLES]

def generate_synthesis(json_articles, max_attempts=3):
    prompt_body = synthesis_prompt_template + "\n\n" + json.dumps(json_articles, indent=2)
    attempts = 1
    while attempts <= max_attempts:
        response = openai.chat.completions.create(
            model="gpt-4o",
            messages=[{"role": "user", "content": prompt_body}],
            max_tokens=4000
        )
        output = response.choices[0].message.content.strip()
        output = clean_xml_headers(output)
        output = strip_rss_tags(output)
        if len(output) >= MIN_CHARACTERS or attempts == max_attempts:
            return output
        extra = (
            f"\n\nPlease expand the above synthesis to reach at least {MIN_CHARACTERS} characters, "
            "maintaining a calm and mindful tone."
        )
        prompt_body += extra
        attempts += 1
    return output

def main():
    now = datetime.now(timezone.utc)

    print(f"\nMindful News v5.10 — version check:\n")
    print(f"main.py version: {MAIN_VERSION}")
    print(f"feeds.json version: unknown")
    print(f"clustering_prompt.txt version: {clustering_prompt_template.splitlines()[0]}")
    print(f"synthesis_prompt.txt version: {synthesis_prompt_template.splitlines()[0]}")
    print(f"rss_template.xml version: {rss_template_version}\n")

    # Fetch and parse feeds
    raw_articles = []
    for url in sum(feeds.values(), []):
        print(f"🌍 Fetching feed: {url}")
        try:
            feed = feedparser.parse(url)
        except Exception as e:
            print(f"⚠️ Error fetching feed {url}: {e}")
            continue

        for entry in feed.entries:
            try:
                pub_date = dateparser.parse(
                    entry.get("published", now.isoformat())
                )
            except Exception:
                pub_date = now
            if pub_date.tzinfo is None:
                pub_date = pub_date.replace(tzinfo=timezone.utc)
            # Filter by recency (hours)
            age_hours = (now - pub_date).total_seconds() / 3600
            if age_hours > config.RUN_INTERVAL_HOURS:
                continue

            # Fetch image URL
            image_url = None
            if 'media_content' in entry:
                image_url = entry.media_content[0].get('url')
            elif 'media_thumbnail' in entry:
                image_url = entry.media_thumbnail[0].get('url')
            if not image_url:
                image_url = fetch_og_image(entry.link)

            raw_articles.append({
                "title": entry.title,
                "link": entry.link,
                "summary": clean_xml_headers(entry.get("summary", "")),
                "pubDate": pub_date,
                "image": image_url or ""
            })

    print(f"\n✅ Total articles fetched: {len(raw_articles)}")

    # Deduplicate
    unique = {a['link']: a for a in raw_articles}
    articles = list(unique.values())
    print(f"✅ Total articles after dedup: {len(articles)}")

    # Enforce maximum cap
    articles = enforce_max_articles(articles)
    print(f"✅ Total articles after cap ({config.MAX_ARTICLES}): {len(articles)}")

    if not articles:
        print("⚠️ No articles to process — exiting.")
        return

    # Optional second recency filter
    articles = filter_recent_articles(articles, now)

    # Prepare clustering
    titles = [a['title'] for a in articles]
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
        clustering_json = [{"theme": "General News", "articles": titles}]

    # Synthesis and build RSS items
    rss_items = []
    for cluster in clustering_json:
        cluster_titles = cluster.get("articles", [])
        selected = [a for a in articles if a["title"] in cluster_titles]
        json_articles = [{
            "title": a["title"],
            "link": a["link"],
            "summary": a["summary"],
            "pubDate": a["pubDate"].isoformat(),
            "image": a["image"]
        } for a in selected]
        synthesis_output = generate_synthesis(json_articles)
        print(f"✅ Synthesized article for theme: {cluster.get('theme')}")

        # Carry link and image from first article
        link = selected[0]["link"] if selected else ""
        image = selected[0]["image"] if selected else ""

        rss_items.append({
            "title": html.escape(cluster.get("theme", "")),
            "link": link,
            "summary": synthesis_output,
            "pubDate": now.strftime('%a, %d %b %Y %H:%M:%S +0000'),
            "category": html.escape(cluster.get("theme", "")),
            "image": image,
            "positivity": "Constructive"
        })

    # Render RSS
    env = Environment(loader=FileSystemLoader(os.path.join(BASE_DIR, "templates")))
    template = env.get_template("rss_template.xml")
    rss_content = template.render(
        articles=rss_items,
        build_date=now.strftime('%a, %d %b %Y %H:%M:%S +0000')
    )

    # Write RSS
    rss_output = os.path.join(BASE_DIR, config.OUTPUT_RSS_FILE)
    try:
        os.remove(rss_output)
        print(f"ℹ️ Previous {config.OUTPUT_RSS_FILE} removed.")
    except FileNotFoundError:
        pass

    with open(rss_output, "w", encoding="utf-8") as f:
        f.write(rss_content)

    print(f"\n✅ Final RSS items: {len(rss_items)}")
    print(f"✅ RSS feed written to {config.OUTPUT_RSS_FILE}")

if __name__ == "__main__":
    main()