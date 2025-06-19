# Mindful News

**Mindful News** is an experimental project to create a *calm, constructive, non-alarmist news feed* â€” for people who want to stay informed without being overwhelmed by fear, negativity, clickbait, or outrage.

ðŸ‘‰ Live feed: [https://www.mindfulnews.media](https://www.mindfulnews.media)

---

## Why I created this

In today's world:

- The news cycle is full of negativity, anxiety triggers, political outrage, and doomsday narratives
- Many people (myself included) have stopped following news entirely â€” it feels toxic
- But **being uninformed is not the solution** â€” we need news that informs calmly and constructively
- The *Mindful News* project is my attempt to create that kind of feed

---

## Project goals

âœ… Filter out:

- Far-right / racist / inflammatory content  
- Clickbait, gossip, sports, crime, disaster porn  
- Doomscrolling, "what if", worst-case speculation

âœ… Rewrite and synthesize:

- Cluster articles on the same topic  
- Rewrite as **one single calm, neutral, factual article**  
- Include hopeful elements or constructive actions when possible  
- Headlines â†’ calm, neutral tone  
- Summaries â†’ informative, factual  
- Always in **English**  
- Include country or region in headline when relevant

âœ… Provide:

- International and national news  
- Positive human interest stories  
- Culture, science, environment, technology  
- A daily feed of news you can read with a **calm mind**

---

## How it works

ðŸ› ï¸ The system:

1. Fetches a list of curated RSS feeds (`feeds.json`)  
2. For each article:  
    - Classifies â†’ is it acceptable? If not, skip  
3. Clusters articles on similar topics  
4. Synthesizes a *new* calm, neutral news article per cluster  
    - Uses GPT-4o + fallback web search  
    - Chooses the best image (non-fearful)  
5. Generates a clean RSS feed (`mindfulnews.xml`)  
6. Published via GitHub Pages â†’ can be imported into WordPress (via WPeMatico) or any RSS reader

---

## Architecture (V4)

- `main.py` â†’ clustering and synthesis engine  
- `feeds.json` â†’ curated feeds from all regions of the world  
- `clustering_prompt.txt` â†’ groups articles  
- `synthesis_prompt.txt` â†’ writes the mindful news story  
- `rss_template.xml` â†’ generates the RSS feed  
- GitHub Action â†’ runs once a day, publishes feed

---

## Positive Journalism Sources

This project includes sources with positive journalism and solutions journalism â€” to balance the tone of the feed:

- [positive.news](https://www.positive.news)  
- [reasonstobecheerful.world](https://reasonstobecheerful.world)  
- [goodgoodgood.co](https://www.goodgoodgood.co)  
- [sciencedaily.com](https://www.sciencedaily.com)  

---

## About this project

This project was entirely developed in collaboration with **ChatGPT**.

- The main author of the project is **Diogo** â€” who had no previous experience in coding.
- All the architecture, code, prompts, clustering logic, and fixes were written step by step in interaction with ChatGPT (GPT-4o).
- We estimate that we have worked **about 20 hours total** together so far (June 18â€“19, 2025).
- The project evolved from simple feed rewriting â†’ to advanced **clustering and synthesis** (V4), with many iterations.

ðŸ’¬ Diogo brings the **vision, ideas, and persistence** to push the project forward â€” always aiming for a mindful, positive, non-anxiety-driven experience.

ðŸ’» ChatGPT brings **coding knowledge, architecture design, and technical support** â€” adapting to Diogoâ€™s ideas.

---

## License

MIT License.

---

## Acknowledgements

Thanks to:

- **ChatGPT** for its help building this entire project
- **GitHub Actions** for easy automation
- **The international journalists and sources** whose calm, factual reporting we aim to amplify.

---

_Version generated on 2025-06-19 22:07:38 UTC_