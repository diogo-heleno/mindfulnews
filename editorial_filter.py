# Mindful News — editorial_filter.py v1.2

import sys
import os
import re
import feedparser
import openai
from jinja2 import Environment, FileSystemLoader
from datetime import datetime, timezone

# Parse command-line arguments for input/output paths
# Usage: python editorial_filter.py [input_rss] [output_rss]
args = sys.argv[1:]
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
INPUT_RSS = args[0] if len(args) >= 1 else os.path.join(BASE_DIR, "mindfulnews.xml")
OUTPUT_RSS = args[1] if len(args) >= 2 else os.path.join(BASE_DIR, "mindfulnews_filtered.xml")

PROMPT_FILE = os.path.join(BASE_DIR, "prompts", "editorial_filter_prompt.txt")
RSS_TEMPLATE_FILE = os.path.join(BASE_DIR, "templates", "rss_template.xml")

def load_prompt(path):
    with open(path, "r", encoding="utf-8") as f:
        return f.read().strip()

editorial_prompt = load_prompt(PROMPT_FILE)

# Setup OpenAI API
openai.api_key = os.getenv("OPENAI_API_KEY")

def clean_xml_headers(text):
    return re.sub(r'\s*<\?xml[^>]+?\?>\s*', '', text, flags=re.IGNORECASE)

# Load input feed
print(f"\n📖 Loading feed: {INPUT_RSS}")
feed = feedparser.parse(INPUT_RSS)
print(f"✅ Total articles loaded: {len(feed.entries)}")

# Process articles
filtered = []
for idx, entry in enumerate(feed.entries, start=1):
    prompt = (
        f"{editorial_prompt}\n\n"
        "Here is the article:\n"
        f"Title: {entry.title}\n"
        f"Category: {entry.get('category', '')}\n"
        f"Positivity: {entry.get('positivity', '')}\n"
        f"Summary:\n{entry.summary}\n"
    )

    print(f"\n🧠 [{idx}/{len(feed.entries)}] Calling LLM for editorial decision...")
    response = openai.chat.completions.create(
        model="gpt-4o",
        messages=[{"role": "user", "content": prompt}],
        max_tokens=500
    )
    result = response.choices[0].message.content.strip()
    print(result)

    dec_match = re.search(r"Decision:\s*(Accept|Reject)", result, re.IGNORECASE)
    reason_match = re.search(r"Reason:\s*(.*)", result, re.IGNORECASE)
    if not dec_match:
        print("⚠️ No decision found — defaulting to Reject.")
        continue

    decision = dec_match.group(1).lower()
    reason = reason_match.group(1).strip() if reason_match else "No reason provided"
    if decision == "accept":
        print(f"✅ Accepted — reason: {reason}")
        filtered.append(entry)
    else:
        print(f"❌ Rejected — reason: {reason}")

# Render filtered RSS
print(f"\n📝 Writing filtered RSS: {OUTPUT_RSS}")
env = Environment(loader=FileSystemLoader(BASE_DIR))
template = env.get_template(RSS_TEMPLATE_FILE)

rss_content = template.render(
    articles=[
        {
            "title": e.title,
            "link": e.link,
            "summary": e.summary,
            "pubDate": e.published,
            "category": e.get("category", ""),
            "image": (e.media_content[0]["url"] if hasattr(e, "media_content") and e.media_content else ""),
            "positivity": e.get("positivity", "")
        }
        for e in filtered
    ],
    build_date=datetime.now(timezone.utc).strftime('%a, %d %b %Y %H:%M:%S +0000')
)

with open(OUTPUT_RSS, "w", encoding="utf-8") as f:
    f.write(clean_xml_headers(rss_content))

print(f"\n✅ Filtered RSS written: {OUTPUT_RSS}")
print(f"✅ Total articles after filtering: {len(filtered)}")