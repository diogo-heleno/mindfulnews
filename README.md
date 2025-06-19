
# Mindful News

**Mindful News** — [https://MindfulNews.media](https://MindfulNews.media) — is a project to create a *calm, constructive, non-alarmist news feed* — for people who want to stay informed without being overwhelmed by fear, negativity, clickbait, or outrage.
 
👉 Live feed: [https://diogo-heleno.github.io/mindfulnews/mindfulnews.xml](https://diogo-heleno.github.io/mindfulnews/mindfulnews.xml)

---

## Why I created this

In today's world:

- The news cycle is full of negativity, anxiety triggers, political outrage, and doomsday narratives
- Many people (myself included) have stopped following news entirely — it feels toxic
- But **being uninformed is not the solution** — we need news that informs calmly and constructively
- The *Mindful News* project is my attempt to create that kind of feed — as a public service and for my own peace of mind

---

## Project goals

✅ Filter out:

- Far-right / racist / inflammatory content  
- Clickbait, gossip, sports, crime, disaster porn  
- Doomscrolling, "what if", worst-case speculation

✅ Rewrite:

- Headlines → calm, neutral tone  
- Summaries → informative, factual, include hope/solutions when possible  
- Always in **English**  
- Include country or region in headline when relevant

✅ Provide:

- International and national news  
- Culture, science, technology  
- Positive human interest stories  
- A daily feed of news you can read with a **calm mind**

---

## How it works

🛠️ The system:

1. Fetches a list of European news feeds (`feeds.json`)  
2. For each article:
    - Classifies → is it acceptable? If not, skip
    - Rewrites headline and summary → calm, neutral tone
    - Assigns category → strict allowed list
    - Fetches first image (RSS, og:image, or first `<img>`)
3. Generates a clean RSS feed (`mindfulnews.xml`)  
4. Published via GitHub Pages → can be imported into WordPress (via WPeMatico) or any RSS reader

---

## Allowed categories

- Politics  
- Economy  
- Environment  
- Social Progress  
- Health  
- War and Conflicts  
- EU Affairs  
- Science and Innovation  
- Other

---

## How to run / update

### Run manually (local):


```bash
python main.py
```

### GitHub Actions:

- Manual trigger (via Actions tab)  
- Or scheduled (`run.yml`) → every 2 hours

---

## Prompts used

- `prompts/filter_prompt.txt`  
  → Decides if article is acceptable (rejects far-right, gossip, sports, etc)

- `prompts/title_prompt.txt`  
  → Rewrites headline → calm tone, English, country/region if relevant

- `prompts/rewrite_prompt.txt`  
  → Rewrites summary → calm, informative, positive if possible

- `prompts/category_prompt.txt`  
  → Classifies article → must match allowed list exactly

---

## Technologies used

- Python 3.10  
- OpenAI API (gpt-4o)  
- Feedparser  
- BeautifulSoup4 (for fetching first image)  
- Jinja2  
- GitHub Actions  
- GitHub Pages

---

## Future ideas

☑️ Fallback for images → done (og:image / first img)  
☐ Enrich categories → sub-topics  
☐ Push feed directly to WordPress via REST API  
☐ Allow email digest of the feed  
☐ Build a nice frontend website (MindfulNews.media)  
☐ Add more high-quality European feeds  
☐ Tune prompts further to avoid occasional noisy articles

---

## Credits

Project by **Diogo Heleno** — [https://MindfulNews.media](https://MindfulNews.media)

Inspired by:

- [Constructive Journalism](https://constructiveinstitute.org/)  
- [Solutions Journalism](https://www.solutionsjournalism.org/)  
- A personal need to consume news without anxiety

---

## License

MIT — free to use, adapt, and improve

---

**Stay centered. Stay connected. Stay informed.** 🌿  
#MindfulNews — [https://MindfulNews.media](https://MindfulNews.media)
