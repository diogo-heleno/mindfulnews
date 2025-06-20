# Mindful News — editorial_filter.py v1.1

import feedparser
import openai
import os
from jinja2 import Environment, FileSystemLoader
from datetime import datetime, timezone
import re

# Setup
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
INPUT_RSS = os.path.join(BASE_DIR, "mindfulnews.xml")
OUTPUT_RSS = os.path.join(BASE_DIR, "mindfulnews_filtered.xml")
PROMPT_FILE = os.path.join(BASE_DIR, "prompts", "editorial_filter_prompt.txt")
RSS_TEMPLATE_FILE = "templates/rss_template.xml"

# Load prompt
with open(PROMPT_FILE, "r", encoding="utf-8") as f:
    editorial_prompt = f.read()

# Setup OpenAI API
openai.api_key = os.getenv("OPENAI_API_KEY")

# Helper: clean XML header
def clean_xml_headers(text):
    return re.sub(r'\s*<\?xml[^>]+?\?>\s*', '', text, flags=re.IGNORECASE)

# Load feed
print(f"\n📖 Loading feed: {INPUT_RSS}")
feed = feedparser.parse(INPUT_RSS)
print(f"✅ Total articles loaded: {len(feed.entries)}")

# Process articles
filtered_articles = []

for i, entry in enumerate(feed.entries):
    article_prompt = f"""{editorial_prompt}

Here is the article:

Title: {entry.title}
Category: {entry.get('category', '')}
Positivity: {entry.get('positivity', '')}
Summary:
{entry.summary}
"""

    print(f"\n🧠 [{i+1}/{len(feed.entries)}] Calling LLM for editorial decision...")
    response = openai.chat.completions.create(
        model="gpt-4o",
        messages=[{"role": "user", "content": article_prompt}],
        max_tokens=500
    )
    output = response.choices[0].message.content.strip()
    print(output)

    decision_match = re.search(r"Decision:\s*(Accept|Reject)", output, re.IGNORECASE)
    reason_match = re.search(r"Reason:\s*(.+)", output, re.IGNORECASE)

    if not decision_match:
        print("⚠️ No decision found — rejecting by default.")
        continue

    decision = decision_match.group(1).strip()
    reason = reason_match.group(1).strip() if reason_match else "No reason provided"

    if decision.lower() == "accept":
        print(f"✅ Accepted — reason: {reason}")
        filtered_articles.append(entry)
    else:
        print(f"❌ Rejected — reason: {reason}")

# Write new RSS
print(f"\n📝 Writing filtered RSS: {OUTPUT_RSS}")
env = Environment(loader=FileSystemLoader(BASE_DIR))
template = env.get_template(RSS_TEMPLATE_FILE)

rss_content = template.render(
    articles=[
        {
            "title": entry.title,
            "link": entry.link,
            "summary": entry.summary,
            "pubDate": entry.published,
            "category": entry.get("category", ""),
            "image": entry.get("media_content", [{}])[0].get("url", ""),
            "positivity": entry.get("positivity", "")
        }
        for entry in filtered_articles
    ],
    build_date=datetime.now(timezone.utc).strftime('%a, %d %b %Y %H:%M:%S +0000')
)

# Save
with open(OUTPUT_RSS, "w", encoding="utf-8") as f:
    f.write(rss_content)

print(f"\n✅ Filtered RSS written: {OUTPUT_RSS}")
print(f"✅ Total articles after filtering: {len(filtered_articles)}")