"""Social Pulse: what tech communities, researchers and regulators are talking about today.

Runs once a day inside the Global News pipeline (no long-running service). It pulls the
public, keyless feeds of six communities, keeps the posts that match a tracked topic,
merges near-duplicates, ranks by score and freshness, tags a rule-based sentiment and asks
Amazon Nova Micro for a 2-3 sentence briefing per busy topic. The result is a small JSON
file that the static site renders and that the search Lambda (lambda/social_pulse_search)
reads to answer questions.

Pure Python + httpx on purpose: the original stand-alone service kept scikit-learn, FastAPI
and GraphQL loaded around the clock (~150 MB of RAM) for a job that runs once a day.
"""
from __future__ import annotations

import json
import math
import re
import time
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone

import boto3
import feedparser
import httpx
from rich.console import Console

console = Console()

BEDROCK_REGION = "eu-west-1"
BRIEFING_MODEL = "eu.amazon.nova-micro-v1:0"      # $0.035/MTok in · $0.14/MTok out
MAX_POSTS = 150
MAX_BRIEFINGS = 8
MIN_POSTS_FOR_BRIEFING = 3
UA = {"User-Agent": "forwardforecasting-social-pulse/2.0 (+https://www.forwardforecasting.eu/global-news-agent/)"}

PLATFORMS = {
    "hackernews":       "Hacker News",
    "lobsters":         "Lobste.rs",
    "devto":            "Dev.to",
    "lemmy":            "Lemmy",
    "arxiv":            "arXiv",
    "federal_register": "Federal Register",
}

# Topic vocabularies: a post is assigned to the topic whose words it shares most (weighted
# by how specific each word is across topics), if the match is strong enough.
TOPICS = {
    "artificial intelligence": "artificial intelligence machine learning neural deep llm llms gpt model models inference ai chatbot agent agents agentic robotics generative transformers openai anthropic claude gemini llama gguf benchmark benchmarks",
    "software & engineering":  "software programming code coding developer developers rust python javascript typescript golang java c++ compiler compilers database postgres sqlite linux kernel gnome open-source github api framework library refactoring debugging rendering functions",
    "security & privacy":      "security vulnerability exploit breach hack hacked hacker malware ransomware privacy encryption password cve attack phishing surveillance zero-day",
    "cloud & infrastructure":  "cloud aws azure gcp kubernetes docker server servers datacenter infrastructure networking ipv4 ipv6 dns tcp rfc protocol outage latency storage serverless devops",
    "science & research":      "science research study researchers physics chemistry biology quantum astronomy space nasa experiment paper university discovery",
    "business & startups":     "startup startups funding venture capital acquisition ipo revenue layoffs company companies market valuation founder ceo earnings",
    "policy & regulation":     "regulation rule rules law policy government federal agency compliance antitrust court lawsuit ftc fcc eu act proposed comment",
    "health & medicine":       "health medical medicine drug drugs fda clinical disease patients hospital vaccine cancer treatment",
    "climate & energy":        "climate energy emissions carbon solar wind battery batteries renewable grid electricity nuclear environmental epa",
    "hardware & devices":      "hardware chip chips cpu gpu semiconductor nvidia intel amd apple iphone android device devices laptop keyboard pcb pcs ps5 console robots radio",
}

_POS = {"good", "great", "breakthrough", "progress", "success", "win", "hope", "innovative", "exciting",
        "positive", "benefit", "improve", "improved", "launch", "faster", "free", "open", "release", "new"}
_NEG = {"bad", "crash", "fail", "failure", "crisis", "danger", "threat", "corrupt", "scandal", "loss",
        "worse", "terrible", "disaster", "breach", "attack", "bug", "broken", "outage", "layoffs", "ban", "lawsuit"}
_STOP = set("the a an and or but is are was were in on at to for of with by from that this it its be been "
            "as how why what when who your you we our their they not no can will just more new now".split())


def _tokens(text: str) -> list[str]:
    return [w for w in re.findall(r"[a-z][a-z0-9+#.-]{1,}", (text or "").lower()) if w not in _STOP]


def _iso(ts) -> str:
    try:
        if isinstance(ts, (int, float)):
            return datetime.fromtimestamp(ts, tz=timezone.utc).isoformat()
        return datetime.fromisoformat(str(ts).replace("Z", "+00:00")).astimezone(timezone.utc).isoformat()
    except Exception:
        return datetime.now(timezone.utc).isoformat()


# ── Sources (all public, no API key) ──────────────────────────────────────────

def _hackernews(client: httpx.Client) -> list[dict]:
    ids = client.get("https://hacker-news.firebaseio.com/v0/topstories.json").json()[:40]

    def item(i):
        try:
            return client.get(f"https://hacker-news.firebaseio.com/v0/item/{i}.json").json()
        except Exception:
            return None
    with ThreadPoolExecutor(8) as ex:
        items = [x for x in ex.map(item, ids) if x and x.get("title")]
    return [{"platform": "hackernews", "title": x["title"], "body": re.sub("<[^>]+>", " ", x.get("text") or ""),
             "url": x.get("url") or f"https://news.ycombinator.com/item?id={x['id']}",
             "author": x.get("by"), "score": x.get("score", 0), "timestamp": _iso(x.get("time", 0))} for x in items]


def _lobsters(client: httpx.Client) -> list[dict]:
    return [{"platform": "lobsters", "title": x["title"], "body": x.get("description_plain") or "",
             "url": x.get("url") or x.get("short_id_url"), "author": (x.get("submitter_user") or {}).get("username")
             if isinstance(x.get("submitter_user"), dict) else x.get("submitter_user"),
             "score": x.get("score", 0), "timestamp": _iso(x.get("created_at"))}
            for x in client.get("https://lobste.rs/hottest.json").json()[:25] if x.get("title")]


def _devto(client: httpx.Client) -> list[dict]:
    return [{"platform": "devto", "title": x["title"], "body": x.get("description") or "", "url": x.get("url"),
             "author": (x.get("user") or {}).get("username"),
             "score": x.get("positive_reactions_count", 0) + x.get("comments_count", 0),
             "timestamp": _iso(x.get("published_at"))}
            for x in client.get("https://dev.to/api/articles", params={"per_page": 25, "top": 1}).json() if x.get("title")]


def _lemmy(client: httpx.Client) -> list[dict]:
    data = client.get("https://lemmy.world/api/v3/post/list", params={"community_name": "technology", "sort": "Hot", "limit": 25}).json()
    out = []
    for item in data.get("posts", []):
        p = item.get("post", {})
        if p.get("name"):
            out.append({"platform": "lemmy", "title": p["name"], "body": p.get("body") or "",
                        "url": p.get("url") or f"https://lemmy.world/post/{p['id']}",
                        "author": (item.get("creator") or {}).get("name"),
                        "score": (item.get("counts") or {}).get("score", 0), "timestamp": _iso(p.get("published"))})
    return out


def _arxiv(client: httpx.Client) -> list[dict]:
    out, seen = [], set()
    for i, term in enumerate(["artificial intelligence", "machine learning", "computer security",
                              "climate change", "quantum computing"]):
        if i:
            time.sleep(3)                     # arXiv asks for a pause between API calls
        feed = feedparser.parse(client.get("https://export.arxiv.org/api/query", params={
            "search_query": f"all:{term}", "max_results": 4, "sortBy": "submittedDate", "sortOrder": "descending"}).text)
        for e in feed.entries:
            if e.get("id") in seen:
                continue
            seen.add(e.get("id"))
            out.append({"platform": "arxiv", "title": " ".join(e.get("title", "").split()),
                        "body": " ".join(e.get("summary", "").split())[:600], "url": e.get("id"),
                        "author": ", ".join(a.get("name", "") for a in e.get("authors", [])[:3]),
                        "score": 0, "timestamp": _iso(e.get("published"))})
    return out


def _federal_register(client: httpx.Client) -> list[dict]:
    out, seen = [], set()
    for term in ["artificial intelligence", "cybersecurity", "technology", "energy", "health"]:
        data = client.get("https://www.federalregister.gov/api/v1/articles.json", params={
            "per_page": 4, "order": "newest", "conditions[term]": term,
            "fields[]": ["title", "abstract", "agency_names", "publication_date", "html_url", "document_number"]}).json()
        for a in data.get("results", []):
            if a.get("document_number") in seen or not a.get("title"):
                continue
            seen.add(a.get("document_number"))
            out.append({"platform": "federal_register", "title": a["title"], "body": (a.get("abstract") or "")[:600],
                        "url": a.get("html_url"), "author": ", ".join((a.get("agency_names") or [])[:2]),
                        "score": 0, "timestamp": _iso(a.get("publication_date"))})
    return out


SOURCES = [_hackernews, _lobsters, _devto, _lemmy, _arxiv, _federal_register]


def fetch_all() -> tuple[list[dict], dict]:
    posts, counts = [], {}
    with httpx.Client(timeout=15, headers=UA, follow_redirects=True) as client:
        def run(fn):
            try:
                return fn.__name__.lstrip("_"), fn(client)
            except Exception as e:                       # one broken source must not stop the rest
                console.log(f"[yellow]social pulse: {fn.__name__} failed: {type(e).__name__}: {e}[/yellow]")
                return fn.__name__.lstrip("_"), []
        with ThreadPoolExecutor(len(SOURCES)) as ex:
            for name, items in ex.map(run, SOURCES):
                counts[name] = len(items)
                posts.extend(items)
    return posts, counts


# ── Processing ────────────────────────────────────────────────────────────────

OTHER = "other tech & culture"               # shown in the feed, never gets a briefing
_TOPIC_WORDS = {t: set(_tokens(v)) for t, v in TOPICS.items()}
_WORD_DF = Counter(w for ws in _TOPIC_WORDS.values() for w in ws)
_WORD_W = {w: math.log(1 + len(TOPICS) / df) for w, df in _WORD_DF.items()}   # rarer across topics = more telling


def assign_topic(post: dict) -> str | None:
    words = set(_tokens(post["title"] + " " + post["title"] + " " + post.get("body", "")[:400]))
    scores = {t: sum(_WORD_W[w] for w in words & vocab) for t, vocab in _TOPIC_WORDS.items()}
    topic, best = max(scores.items(), key=lambda kv: kv[1])
    return topic if best >= 1.2 else OTHER


def sentiment(text: str) -> str:
    words = set(re.findall(r"[a-z]+", text.lower()))
    s = len(words & _POS) - len(words & _NEG)
    return "positive" if s > 0 else "negative" if s < 0 else "neutral"


def deduplicate(posts: list[dict]) -> list[dict]:
    """Merge posts whose titles share most of their words (the same story on several sites)."""
    kept: list[dict] = []
    for p in sorted(posts, key=lambda x: x["rank"], reverse=True):
        t = set(_tokens(p["title"]))
        dup = next((k for k in kept if t and len(t & k["_t"]) / len(t | k["_t"]) >= 0.6), None)
        if dup:
            if p["platform"] not in dup["also_on"] and p["platform"] != dup["platform"]:
                dup["also_on"].append(p["platform"])
            continue
        kept.append({**p, "_t": t, "also_on": []})
    for k in kept:
        k.pop("_t")
    return kept


def rank(p: dict, now: datetime) -> float:
    try:
        age_h = max((now - datetime.fromisoformat(p["timestamp"])).total_seconds() / 3600, 0.5)
    except Exception:
        age_h = 24.0
    community = math.log1p(max(p.get("score", 0), 0)) if p["platform"] in ("hackernews", "lobsters", "devto", "lemmy") else 2.5
    return round((1 + community) / (age_h + 2) ** 0.6, 4)


def briefing(client, topic: str, posts: list[dict]) -> str:
    lines = "\n".join(f"- [{PLATFORMS[p['platform']]}] {p['title']}" for p in posts[:15])
    try:
        resp = client.converse(
            modelId=BRIEFING_MODEL,
            system=[{"text": "You write concise, neutral daily briefings about what technical communities, "
                             "researchers and regulators discussed today. 2-3 sentences, no preamble, no bullet points."}],
            messages=[{"role": "user", "content": [{"text": f"Topic: {topic}\nToday's posts:\n{lines}\n\nWrite the briefing."}]}],
            inferenceConfig={"maxTokens": 220, "temperature": 0.3},
        )
        return resp["output"]["message"]["content"][0]["text"].strip()
    except Exception as e:
        console.log(f"[yellow]social pulse: briefing for {topic} failed: {e}[/yellow]")
        top = ", ".join(p["title"] for p in posts[:3])
        return f"{len(posts)} posts today. Most discussed: {top}."


def run(today: str) -> dict:
    """Collect, process and summarise; returns the data the site and the search Lambda use."""
    console.log("[cyan]Social Pulse: collecting …[/cyan]")
    now = datetime.now(timezone.utc)
    raw, counts = fetch_all()
    posts = []
    for p in raw:
        p["title"] = p["title"].strip()
        topic = assign_topic(p)
        if not topic or not p.get("url"):
            continue
        posts.append({**p, "topic": topic, "sentiment": sentiment(p["title"] + " " + p.get("body", "")),
                      "rank": rank(p, now) * (0.5 if topic == OTHER else 1.0), "body": (p.get("body") or "")[:500]})
    posts = deduplicate(posts)[:MAX_POSTS]

    by_topic: dict[str, list] = {}
    for p in posts:
        by_topic.setdefault(p["topic"], []).append(p)
    busy = sorted((t for t, ps in by_topic.items() if len(ps) >= MIN_POSTS_FOR_BRIEFING and t != OTHER),
                  key=lambda t: -len(by_topic[t]))[:MAX_BRIEFINGS]
    bedrock = boto3.client("bedrock-runtime", region_name=BEDROCK_REGION)
    briefings = []
    for t in busy:
        ps = by_topic[t]
        mood = Counter(p["sentiment"] for p in ps)
        briefings.append({"topic": t, "posts": len(ps), "summary": briefing(bedrock, t, ps),
                          "sentiment": {k: round(100 * mood[k] / len(ps)) for k in ("positive", "neutral", "negative")}})
    console.log(f"[green]✓ Social Pulse: {len(raw)} fetched → {len(posts)} kept, {len(briefings)} briefings[/green]")
    return {"date": today, "generated_at": now.strftime("%Y-%m-%d %H:%M UTC"), "sources": counts,
            "platforms": PLATFORMS, "topics": sorted(by_topic, key=lambda t: (t == OTHER, -len(by_topic[t]))),
            "briefings": briefings, "posts": posts}


if __name__ == "__main__":
    data = run(datetime.now(timezone.utc).date().isoformat())
    print(json.dumps({k: v for k, v in data.items() if k != "posts"}, indent=2)[:3000])
