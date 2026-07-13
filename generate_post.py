#!/usr/bin/env python3
"""
The Settlement Docket — daily auto-publisher.

Runs on a schedule (see .github/workflows/daily-post.yml). It:
  1. Reads a list of free RSS feeds (Google Alerts, legal-news feeds).
  2. Skips anything already published (tracked in posts.json).
  3. Sends each new raw item to Google's Gemini API (free tier) with a
     strict "verified-facts-only, cite the source, flag if unsure" prompt.
  4. Writes a static HTML case-file page, updates posts.json, and
     rewrites the case-file list on index.html.

Zero paid services required:
  - Hosting: GitHub Pages (free)
  - Scheduler: GitHub Actions (free for public repos)
  - Writer model: Gemini API free tier (no credit card) — get a key at
    https://aistudio.google.com/app/apikey and store it as the
    GEMINI_API_KEY repo secret.

IMPORTANT — read before turning this fully loose:
  Google's free tier may use your prompts/outputs to improve their
  models, and free-tier quotas/model names change over time (this
  script uses gemini-2.5-flash-lite; check aistudio.google.com if calls
  start failing with 404, the model name may have moved on).
  This script drafts posts about legal claim deadlines. Wrong dates or
  wrong administrator links actively hurt real people. Treat the
  DRAFT_REVIEW_NEEDED flag below as mandatory, not optional, until
  you've watched it run correctly for a few weeks.
"""

import json
import os
import re
import sys
import hashlib
import datetime
from pathlib import Path
from urllib.parse import quote

import requests
import feedparser

ROOT = Path(__file__).resolve().parent.parent
POSTS_JSON = ROOT / "posts.json"
POSTS_DIR = ROOT / "posts"
INDEX_HTML = ROOT / "index.html"

# ---- Configure your free sources here (all free, no login needed) ----
# Tip: create Google Alerts at google.com/alerts for terms like
# "Canada class action settlement" and "Canada claims administrator",
# choose "RSS feed" as the delivery method, and paste the feed URL here.
FEEDS = [
    os.environ.get("ALERT_RSS_URL_1", "").strip(),
    os.environ.get("ALERT_RSS_URL_2", "").strip(),
]
FEEDS = [f for f in FEEDS if f]

GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "")
GEMINI_MODEL = "gemini-2.5-flash-lite"
GEMINI_URL = (
    f"https://generativelanguage.googleapis.com/v1beta/models/"
    f"{GEMINI_MODEL}:generateContent?key={GEMINI_API_KEY}"
)

SYSTEM_PROMPT = """You write short, factual case-file entries for a Canadian \
class action settlement tracker called "The Settlement Docket". Rules:
- Only use facts present in the supplied source text. Never invent a dollar \
figure, deadline, or eligibility detail that isn't in the source.
- If the source text doesn't clearly state a claim deadline, dollar amount, \
or administrator, write "not specified in source — verify directly" instead \
of guessing.
- Tone: plain, calm, useful. No hype, no "act now" urgency language.
- Structure your reply as JSON with these exact keys: title, case_number \
(format YYYY-MMDD-XX using today's date and a 2-letter slug from the topic), \
stamp_type (one of "verified", "deadline", "alert"), summary (one sentence), \
body_paragraphs (array of 2-4 short paragraphs), source_note (one sentence \
naming what to verify directly and where).
Return ONLY the JSON object, no markdown fences, no extra text."""

POST_TEMPLATE = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{title} — The Settlement Docket</title>
<meta name="description" content="{summary}">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link href="https://fonts.googleapis.com/css2?family=Source+Serif+4:wght@400;600;700&family=Courier+Prime:wght@400;700&display=swap" rel="stylesheet">
<link rel="stylesheet" href="../assets/style.css">
</head>
<body>
<div class="wrap">
  <header class="masthead" style="border-bottom:none;padding-bottom:0;">
    <div class="eyebrow"><a href="../index.html">&larr; The Settlement Docket</a></div>
  </header>

  <article class="post">
    <div class="case-number">CASE FILE NO. {case_number}</div>
    <span class="stamp {stamp_type}">{stamp_label}</span>
    <h1>{title}</h1>
    <div class="meta-row">Auto-drafted {date} · DRAFT_REVIEW_NEEDED until manually checked</div>

    <div class="body">
{body_html}
    </div>

    <div class="verify-box">
      <strong>Verify before relying on this:</strong> {source_note}
    </div>
  </article>

  <footer>
    <p>Not legal advice. Independent tracker, not affiliated with any court, law firm, or claims administrator.</p>
  </footer>
</div>
</body>
</html>
"""


def slugify(text: str) -> str:
    s = re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")
    return s[:60]


def load_manifest() -> list:
    if POSTS_JSON.exists():
        return json.loads(POSTS_JSON.read_text())
    return []


def save_manifest(manifest: list) -> None:
    POSTS_JSON.write_text(json.dumps(manifest, indent=2))


def already_seen(manifest: list, url: str) -> bool:
    h = hashlib.sha256(url.encode()).hexdigest()
    return any(item.get("source_hash") == h for item in manifest)


def fetch_new_items(manifest: list) -> list:
    items = []
    for feed_url in FEEDS:
        parsed = feedparser.parse(feed_url)
        for entry in parsed.entries[:10]:
            link = entry.get("link", "")
            if not link or already_seen(manifest, link):
                continue
            items.append({
                "title": entry.get("title", ""),
                "summary": entry.get("summary", ""),
                "link": link,
            })
    return items


def call_gemini(item: dict) -> dict | None:
    if not GEMINI_API_KEY:
        print("No GEMINI_API_KEY set — skipping generation.", file=sys.stderr)
        return None
    source_text = f"HEADLINE: {item['title']}\nSNIPPET: {item['summary']}\nURL: {item['link']}"
    payload = {
        "contents": [{"parts": [{"text": source_text}]}],
        "systemInstruction": {"parts": [{"text": SYSTEM_PROMPT}]},
        "generationConfig": {"temperature": 0.3, "responseMimeType": "application/json"},
    }
    resp = requests.post(GEMINI_URL, json=payload, timeout=60)
    if resp.status_code != 200:
        print(f"Gemini API error {resp.status_code}: {resp.text[:300]}", file=sys.stderr)
        return None
    data = resp.json()
    try:
        text = data["candidates"][0]["content"]["parts"][0]["text"]
        return json.loads(text)
    except (KeyError, IndexError, json.JSONDecodeError) as e:
        print(f"Could not parse Gemini response: {e}", file=sys.stderr)
        return None


def write_post(draft: dict, source_url: str, slug: str) -> None:
    stamp_label = {"verified": "Verified", "deadline": "Deadline", "alert": "Scam Alert"}.get(
        draft["stamp_type"], "Unverified"
    )
    body_html = "\n".join(f"      <p>{p}</p>" for p in draft["body_paragraphs"])
    html = POST_TEMPLATE.format(
        title=draft["title"],
        summary=draft["summary"],
        case_number=draft["case_number"],
        stamp_type=draft["stamp_type"],
        stamp_label=stamp_label,
        date=datetime.date.today().isoformat(),
        body_html=body_html,
        source_note=draft["source_note"],
    )
    (POSTS_DIR / f"{slug}.html").write_text(html)


def rebuild_index_cards(manifest: list) -> None:
    cards = []
    for item in reversed(manifest):  # newest first
        stamps_html = " ".join(
            f'<span class="stamp {s.split(":")[0]}">{s.split(":")[-1] if ":" in s else s.split(":")[0].capitalize()}</span>'
            for s in item["stamps"]
        )
        cards.append(f"""    <div class="case-file">
      <div class="case-number">CASE FILE NO. {item['case_number']}</div>
      {stamps_html}
      <h2><a href="posts/{item['slug']}.html">{item['title']}</a></h2>
      <p class="summary">{item['summary']}</p>
    </div>""")
    block = "\n".join(cards)
    html = INDEX_HTML.read_text()
    html = re.sub(
        r"<!-- CASE_FILES_START -->.*?<!-- CASE_FILES_END -->",
        f"<!-- CASE_FILES_START -->\n{block}\n    <!-- CASE_FILES_END -->",
        html,
        flags=re.DOTALL,
    )
    INDEX_HTML.write_text(html)


def main():
    manifest = load_manifest()
    new_items = fetch_new_items(manifest)
    print(f"Found {len(new_items)} new item(s) across {len(FEEDS)} feed(s).")

    for item in new_items:
        draft = call_gemini(item)
        if draft is None:
            continue
        slug = slugify(draft["title"])
        write_post(draft, item["link"], slug)
        manifest.append({
            "slug": slug,
            "title": draft["title"],
            "summary": draft["summary"],
            "case_number": draft["case_number"],
            "stamps": [draft["stamp_type"]],
            "source_url": item["link"],
            "source_hash": hashlib.sha256(item["link"].encode()).hexdigest(),
            "date_added": datetime.date.today().isoformat(),
            "type": "case",
        })
        print(f"Published draft: {draft['title']}")

    save_manifest(manifest)
    rebuild_index_cards(manifest)


if __name__ == "__main__":
    main()
