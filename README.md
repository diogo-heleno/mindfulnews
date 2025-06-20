# Mindful News

**A calm, positive, and constructive RSS news feed generator.**

Mindful News fetches international news articles, clusters them into themes, rewrites them in a balanced and mindful tone using OpenAI, and generates a ready-to-use RSS feed (`mindfulnews.xml`).

---

## Features

- ✨ Calm, constructive rewriting of global news
- ✨ Positive tagging: `<Positive>`, `<Constructive>`, `<Cautionary>`
- ✨ Thematic clustering of articles
- ✨ Non-sensational, international, mindful tone
- ✨ Fully automated pipeline (GitHub Actions-ready)

---

## Project Structure

```text
.github/workflows/          # GitHub Action workflows
docs/                       # Documentation (optional)
prompts/
    clustering_prompt.txt   # LLM prompt for article clustering
    synthesis_prompt.txt    # LLM prompt for article synthesis

templates/
    rss_template.xml        # RSS template with positivity tags

config.py                   # Config options (run interval, max articles)
feeds.json                  # List of source feeds (international + positive)
main.py                     # Full pipeline
main_v4.py                  # Archive of older version
requirements.txt            # Python dependencies
```

---

## How it works

1. **Fetch**: loads all articles from `feeds.json` (international & positive feeds)
2. **Deduplicate**: removes duplicate links
3. **Cluster**: uses GPT-4o to group articles into themes
4. **Synthesize**: uses GPT-4o to rewrite stories in calm, constructive tone with positivity tag
5. **Output**: generates `mindfulnews.xml` — ready RSS feed

---

## Usage

### Local run:

```bash
python main.py
```

Requires:

- Python 3.10+
- API key in environment: `OPENAI_API_KEY`
- Dependencies:

```bash
pip install -r requirements.txt
```

### GitHub Actions:

- Add `OPENAI_API_KEY` as GitHub Secret
- Set workflow schedule as needed (daily, hourly...)

---

## Output example

```xml
<item>
  <title>European Diplomacy and Climate Action</title>
  <positivity>&lt;Positive&gt;</positivity>
  <description><![CDATA[
    **Headline:**
    European Union leads new climate resilience fund...

    **Summary:**
    International leaders announce...
  ]]></description>
  ...
</item>
```

---

## Current versions

- main.py: v4.9
- clustering\_prompt.txt: v4.4
- synthesis\_prompt.txt: v4.2
- rss\_template.xml: v1.1

---

## Roadmap

-

---

**License**: MIT (open source)

---

Built with ❤️ by Diogo and ChatGPT.

