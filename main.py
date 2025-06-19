# main_v3.py - Mindful News v3 engine
# version: 2025-06-19-v3.4

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
feeds_version = feeds.get("version", "unknown")

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