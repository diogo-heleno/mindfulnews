# Mindful News

A personal project by [Diogo Heleno](https://github.com/diogo-heleno), designed to create a calmer, more constructive way to read world news — away from sensationalism, fear, or clickbait.

---

## 🌍 Why I built this

I am personally prone to anxiety.  
Like many people, I noticed that reading "normal" news feeds — especially in today's world — can easily trigger negative emotions and stress:

- Excessive sensationalism  
- Catastrophic tone  
- Focus on fear, hate, and polarisation  
- Repetitive cycles of outrage

I wanted to create a news service that would:

✅ Filter out extreme negativity  
✅ Rewrite articles in a calmer, more hopeful, more constructive tone  
✅ Prioritise balanced information and possible solutions  
✅ Help readers stay informed **without being overwhelmed**

This is not about "fake good news" — it is about **calm, balanced journalism** for mental well-being.

---

## 🛠️ What this project is

At this stage, it is a **proof of concept**, built entirely using:

✅ Public RSS feeds from high-quality international sources  
✅ An automated pipeline (GitHub Actions)  
✅ AI (LLM) to cluster, summarise and rewrite the news into a calmer tone  
✅ An automated validator to ensure valid RSS output  
✅ Editorial filtering using AI  
✅ An RSS feed you can subscribe to

**Important:**  
I am not a programmer. I built this as an experiment to see if I could — and it works.

---

## 🤖 The tech stack

- **Language:** Python  
- **AI:** OpenAI GPT-4o  
- **Feeds:** International RSS feeds  
- **Pipeline:** GitHub Actions  
- **Template engine:** Jinja2  
- **RSS validator:** Simple script  
- **No server-side components** — everything is built automatically by GitHub Actions

---

## 🚧 What difficulties we faced

- Handling inconsistent RSS formats from different sources  
- Dealing with invalid XML and RSS validation errors  
- Ensuring that the AI output was correctly formatted and consistent  
- Getting the AI to write **cohesive, calm, longer articles** instead of fragmented pieces  
- Learning to tune the AI prompts to reflect the "Mindful News" philosophy  
- Balancing automation with editorial control  
- Achieving this **without being a programmer** — learning by doing!

---

## ⏳ How long it took (so far)

Roughly **20 hours of work**, spread across a few weeks — including:

- Designing the architecture  
- Writing prompts  
- Testing AI outputs  
- Debugging RSS issues  
- Learning GitHub Actions  
- Iterating multiple versions of the pipeline

---

## 🚀 Current status (June 2025)

- **Main pipeline is working**  
- Feeds are fetched, deduplicated, clustered  
- AI rewrites articles in a calm tone (target: minimum 3000 characters per article)  
- Editorial filtering is in place  
- RSS feed is validated  
- GitHub Actions runs the pipeline automatically  
- Outputs are ready for both RSS readers and a future website

---

## 🎯 Final goal

To launch **Mindful News** as a public service:  

✅ Public website: **https://mindfulnews.media** (in preparation)  
✅ RSS feed: **https://mindfulnews.media/mindfulnews.xml** (in preparation — current feed output is being tested)

The goal is:

- To offer an alternative way to stay informed  
- To reduce news-related anxiety  
- To promote balanced, constructive, international journalism  
- To help other people who — like me — prefer to read the news without constant stress or negativity

---

## 🙏 Credits and thanks

This project would not have been possible without the help of [ChatGPT](https://openai.com/chatgpt), which helped me think through architecture, prompts, debugging — and learning Python and GitHub Actions step by step.

---

## 🚧 Work in progress

Mindful News is still **a work in progress**:

- The website is not yet live  
- The pipeline will keep evolving (tone improvements, better editorial control, web-based enhancements)  
- Feedback is very welcome!

---

## 📫 Contact

If you like this project or want to help, you can reach me via:

- GitHub: [github.com/diogo-heleno](https://github.com/diogo-heleno)  
- Website: [https://mindfulnews.media](https://mindfulnews.media) (coming soon)

---

Thank you for reading — and stay mindful 🚀.