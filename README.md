
# Mindful News v3

**Mindful News** is an open project to create a _calm, constructive, non-alarmist news digest_ — for people who want to stay informed without being overwhelmed by fear, clickbait, outrage or doomscrolling.

👉 Live feed: [https://diogo-heleno.github.io/mindfulnews/mindfulnews.xml](https://diogo-heleno.github.io/mindfulnews/mindfulnews.xml)  
👉 Website: [https://www.mindfulnews.media](https://www.mindfulnews.media)

---

## Why I created this

- The modern news cycle is often toxic — full of outrage, catastrophes, political doom and clickbait.
- Many people (myself included) stopped following news — but this leads to disconnection and lack of awareness.
- I wanted to build an alternative:  
  → _Mindful, calm, constructive news_  
  → _Global & balanced_  
  → _With positive or solution-oriented tone when possible_  
  → _Reducing fear-based reporting_

---

## Mindful News v3 — What's new?

✅ Global feeds — covering Europe, Americas, Africa, Asia, Pacific  
✅ "Positive news" section (Reasons to be Cheerful, Positive.News, etc.)  
✅ Article clustering — multiple feeds → single topic  
✅ GPT synthesis per topic — clear, calm summaries  
✅ No duplicates — no "5 stories about same war"  
✅ Balanced — international, science, environment, solutions  
✅ RSS output — easy to use in WordPress, RSS readers, apps

---

## How it works (v3 architecture)

1️⃣ `feeds.json` defines **regional feeds**:

```json
{
  "Europe": [list of feeds],
  "Middle East": [feeds],
  ...
  "Positive News": [feeds]
}
```

2️⃣ `main_v3.py`:

- Fetches all feeds  
- Filters articles (avoiding racism, far right, gossip, doomscroll)  
- Sends full list to GPT with `clustering_prompt.txt`  
- GPT returns:  
  → Topics  
  → Article URLs per topic

3️⃣ For each topic:

- Fetch article data  
- Sends to `synthesis_prompt.txt`  
- GPT returns:  
  → Calm headline  
  → Balanced summary  
  → Picks 1 image (for now: first image)

4️⃣ Final output:

✅ **One RSS item per topic**  
✅ Headlines in English  
✅ No clickbait  
✅ Calm, global digest

---

## Example prompts used

### `clustering_prompt.txt`

Groups articles into topics — asks GPT to structure result:

```text
Topic: [name]
Articles:
- URL
- URL
```
---

### `synthesis_prompt.txt`

For each topic, synthesizes a single calm news item:

```text
Headline: [calm headline]

Summary: [calm, balanced summary paragraph]
```

---

## Current files

✅ `main_v3.py` — the v3 engine  
✅ `feeds.json` — regional feeds  
✅ `prompts/` — prompts for clustering + synthesis  
✅ `templates/rss_template.xml` — generates RSS v3  
✅ GitHub Actions — automated runs

---

## Roadmap

- [x] v3 — clustering + synthesis (done)
- [ ] Better image selection (least fear image)  
- [ ] Add tone analysis (reduce doom, increase positive bias)  
- [ ] Improve category classification  
- [ ] Option to generate "weekly mindful digest"  
- [ ] Option to email to subscribers  
- [ ] API for apps (mobile, web)

---

## License

MIT — free to use, adapt, improve 🌿

---

## Why open source?

Because I believe we need a **better way to stay informed**:

- Calm  
- Constructive  
- Global  
- Without fear and outrage  

If this helps others — even better 🙏.

---
