# 🌍 Global News Intelligence Agent

**🔴 Live site → [https://www.forwardforecasting.eu/newssummary/](https://www.forwardforecasting.eu/newssummary/)**

> A multi-agent AI system that scrapes, summarises, and analyses the world's top newspapers every day — covering **57 countries · 171 RSS sources** — and publishing a fully static news website powered by Claude. Features an interactive world map with hover-to-preview news popups.

![Python](https://img.shields.io/badge/Python-3.11+-3776ab?logo=python&logoColor=white)
![Claude](https://img.shields.io/badge/Claude-Sonnet%204.6-7c3aed?logo=anthropic&logoColor=white)
![Agents](https://img.shields.io/badge/Agentic%20AI-Tool%20Use-16a085)
![License](https://img.shields.io/badge/License-MIT-22c55e)

---

## Table of Contents

1. [Project Overview](#1-project-overview)
2. [AI Technologies Used in this Project](#2-ai-technologies-used-in-this-project)
3. [Models — Selection, Strengths & Configuration](#3-models--selection-strengths--configuration)
4. [Data Processing Pipeline — Step by Step](#4-data-processing-pipeline--step-by-step)
5. [Libraries Reference](#5-libraries-reference)
6. [Architecture & Data-Flow Diagrams](#6-architecture--data-flow-diagrams)
7. [Breaking News Detection](#7-breaking-news-detection)
8. [Project Structure](#8-project-structure)
9. [Setup & Usage](#9-setup--usage)
10. [Configuration Reference](#10-configuration-reference)

---

## 1. Project Overview

This portfolio project demonstrates a **production-grade agentic AI pipeline** built on AWS Bedrock (Amazon Nova models). The system runs once daily at 07:15 UTC, ingesting live news from 22 countries across all continents, and publishes a fully static HTML news site featuring an interactive world map, 5-story-per-country digests, and per-region deep-dive pages. Regions are processed in parallel (4 concurrent workers). Summarisation uses Nova Lite ($0.06/MTok); breaking-news detection uses Nova Pro ($0.80/MTok). Estimated cost: ~$0.95/month.

### What it does every day

| Step | Agent / Component | Output |
|------|-------------------|--------|
| **Scrape** | `ScraperAgent` | Up to 330 raw articles (15/country × 22) |
| **Extract** | `ScraperAgent` | Full article text via trafilatura |
| **Summarise** | `SummarizerAgent` + Claude Haiku | 5 curated stories per country, topic diversity |
| **Detect** | `BreakingNewsAgent` + Claude Sonnet | Up to 15 cross-source breaking events |
| **Publish** | `WebGenerator` + Jinja2 | 24 static HTML pages + dated archives + world_news.json |
| **Deploy** | `rsync` → EC2 | Auto-pushes to forwardforecasting.eu/newssummary/ |

### Monitored countries — 3 sources each

| Region | Countries |
|--------|-----------|
| 🌎 Americas (6) | 🇺🇸 USA · 🇨🇦 Canada · 🇲🇽 Mexico · 🇨🇷 Costa Rica · 🇧🇷 Brazil · 🇦🇷 Argentina |
| 🌍 Europe (6) | 🇬🇧 UK · 🇫🇷 France · 🇩🇪 Germany · 🇪🇸 Spain · 🇮🇹 Italy · 🇷🇺 Russia |
| 🌏 Asia-Pacific (7) | 🇨🇳 China · 🇯🇵 Japan · 🇮🇳 India · 🇦🇺 Australia · 🇰🇷 South Korea · 🇹🇼 Taiwan · 🇸🇬 Singapore |
| 🌍 Africa (3) | 🇿🇦 South Africa · 🇲🇦 Morocco · 🇪🇬 Egypt |

---

## 2. AI Technologies Used in this Project

> **Scope note:** Only technologies actually present in the codebase are explained here.
> Speech-to-text, image diffusion, image classification, RAG, and fine-tuning are **not** used.

---

### 2.1 Generative AI (GenAI)

**Generative AI** refers to models that can produce new content — text, images, audio, code — rather than just classifying or predicting from existing patterns. These models are trained on vast corpora and learn to generate statistically plausible, coherent output conditioned on a prompt.

**How this project uses GenAI:**
Claude generates every summary, digest, and breaking-news analysis in the pipeline. Given a set of raw article texts, Claude *writes* editorial-quality journalism: thematic overviews, concise story summaries in English (regardless of the source language), severity assessments, and cross-source perspective analyses. This is pure generative output — not retrieved from a database, not templated, and not reproducible by rule-based code.

---

### 2.2 Large Language Models (LLMs)

A **Large Language Model** is a Transformer-based neural network trained on internet-scale text corpora using the **next-token prediction** objective. The Transformer's **self-attention mechanism** allows every token in the context to attend to every other token simultaneously, capturing arbitrarily long-range dependencies. Through training at scale, LLMs acquire emergent abilities: reading comprehension, translation, summarisation, reasoning, and instruction following.

At inference time the model receives a **context window** — a flat sequence of tokens containing the system prompt, conversation history, tool definitions, and user messages — and auto-regressively samples the most likely continuation until a stopping condition is met.

**Key LLM properties used in this project:**

| Property | How it's exploited |
|----------|--------------------|
| **Multilingual comprehension** | Claude reads French, Spanish, Italian, German, Portuguese, Arabic, Turkish, Korean feeds and summarises them in English without a separate translation step |
| **200 K-token context window** | The SummarizerAgent fits 30 articles (≈15 K tokens) in a single call; the BreakingNewsAgent fits 200 curated stories (≈10 K tokens) in one call |
| **Instruction following** | System-prompt contracts ("return ONLY raw JSON, no markdown fences") are obeyed reliably enough to build automated pipelines on top |
| **Parametric world knowledge** | Claude knows that *The Japan Times* is Japanese, that a Hormuz blockade affects oil prices, that ICBM stands for intercontinental ballistic missile — so summaries are contextually correct without extra retrieval |

---

### 2.3 Agentic AI

**Agentic AI** is the paradigm of deploying LLMs not as single-turn question-answerers but as autonomous agents that plan, take actions (calling tools or other agents), observe results, and iterate — all within a single logical task.

The core mechanism is the **agentic loop**:

```
prompt → LLM reasons → emits tool_use → tool executes → result returned → LLM continues
         ↑___________________________ repeat until end_turn __________________________|
```

This project implements two established agentic design patterns:

**Pattern A — Tool-Use Loop (`BaseAgent.run`)**
The `SummarizerAgent` inherits `BaseAgent` and drives Claude through a multi-turn conversation: it sends articles, Claude calls `build_regional_digest` (a deliberate reasoning scaffold), Python returns an acknowledgment, and Claude then emits the final JSON digest. The loop retries automatically on rate-limit errors with exponential back-off (60 s → 120 s → 240 s → 300 s cap).

**Pattern B — Agents-as-Tools (Orchestrator)**
The `OrchestratorAgent` treats each specialist (`ScraperAgent`, `SummarizerAgent`, `BreakingNewsAgent`) as a callable sub-system. Regions are processed in **parallel** via `ThreadPoolExecutor` (4 workers) — each region's scrape + summarise runs concurrently, with a `threading.Lock` protecting shared state. Breaking-news detection runs sequentially after all regions complete. This mirrors the pattern used inside Claude's own computer-use and multi-step task features — higher-level coordinators delegate to specialised workers.

**Why not a single monolithic prompt?**
Splitting work across agents gives: independent failure recovery (each region saved to disk immediately), model routing (cheap model for I/O, capable model for reasoning), and clean separation of concerns that makes the codebase testable.

---

### 2.4 Tool Use / Function Calling

**Tool use** (also called *function calling*) is the API mechanism by which an LLM mid-conversation requests the execution of external code. The model returns a structured `tool_use` block — a JSON object with a function name and typed arguments. The calling application executes the function, returns a `tool_result`, and the model continues reasoning.

```
User message
    ↓
Claude reasons
    ↓
{ "type": "tool_use", "name": "build_regional_digest", "input": {...} }   ← LLM output
    ↓
Python executes _dispatch_tool("build_regional_digest", input)
    ↓
{ "type": "tool_result", "content": "{\"status\": \"ready\"}" }            ← Python output
    ↓
Claude resumes and emits final JSON digest
```

**Tools defined in this project:**

| Agent | Tool | Purpose |
|-------|------|---------|
| `SummarizerAgent` | `build_regional_digest` | Forces Claude to commit to a "ready" state before writing the digest — acts as a deliberate reasoning step, not computation |

> **Design note:** The `BreakingNewsAgent` was originally designed with `report_event` / `finish_detection` tools. In production the multi-turn context (25 countries × articles payload + accumulated tool-call history) repeatedly exceeded the 30 K token/minute rate limit. It was redesigned as a **single direct call** — sending the 200 curated digest stories and receiving the complete JSON event array in one response. This is documented honestly because real-world engineering always involves such trade-offs.

---

### 2.5 Structured Output via Prompt Contracts

Claude is an LLM — it generates text token by token. Getting reliable JSON requires two complementary techniques:

1. **System-prompt schema contracts:** every agent's system prompt specifies the exact JSON structure with concrete examples and hard rules (`"Return ONLY raw JSON — no markdown fences"`, `"The 'url' field MUST be the exact URL from the input article"`).
2. **Fence stripping:** despite the instruction, Claude occasionally wraps output in markdown code fences. `BaseAgent._parse_result()` and `BreakingNewsAgent.detect()` both strip `` ```json … ``` `` wrappers before `json.loads()`.

---

## 3. Models — Selection, Strengths & Configuration

### 3.1 Claude Sonnet 4.6

**Used by:** `SummarizerAgent` (per-region digests) and `BreakingNewsAgent` (global event detection)

Claude Sonnet 4.6 is Anthropic's mid-tier frontier model — positioned between the fastest (Haiku) and most capable (Opus) models. It is trained with **Constitutional AI (CAI)** and **RLHF** (Reinforcement Learning from Human Feedback) to follow instructions precisely, produce safe outputs, and reason accurately across long contexts.

**Why Sonnet and not Opus or Haiku?**

| Criterion | Haiku | **Sonnet 4.6** | Opus |
|-----------|-------|----------------|------|
| Editorial summary quality | Too terse, schema violations | ✅ Excellent | Marginally better |
| Multilingual comprehension | Adequate | ✅ Strong | Strong |
| Instruction following (JSON) | Unreliable | ✅ Reliable | Very reliable |
| Cost per region call | Cheapest | ✅ Balanced | 5× more expensive |
| Speed | Fastest | ✅ Fast enough | Slowest |

**Strengths relevant to this project:**
- **200 K-token context window** — fits entire regional article batches without chunking
- **Multilingual** — reads French, Arabic, Japanese, Korean, Portuguese, Turkish without translation
- **Consistent schema adherence** — reliably follows the system-prompt JSON contract
- **Long-form coherent output** — 15-event JSON arrays with multi-paragraph summaries

**Configuration per agent:**

| Parameter | SummarizerAgent | BreakingNewsAgent | Rationale |
|-----------|:--------------:|:-----------------:|-----------|
| `model` | `claude-sonnet-4-6` | `claude-sonnet-4-6` | Best cost/quality for editorial reasoning |
| `max_tokens` | `4096` | `16 000` | Breaking news for 25 countries can yield 15 events × ~1 500 chars ≈ 22 500 chars; 16 K tokens prevents truncation |
| `temperature` | API default | API default | Not overridden — default is appropriate for factual summarisation constrained by system prompt |
| `tools` | `[build_regional_digest]` | *(none — single call)* | Minimal toolsets reduce prompt tokens and ambiguity |
| Retry strategy | Exponential back-off | Exponential back-off | 60 s → 120 s → 240 s → 300 s cap on `RateLimitError` |

**Key system-prompt design decisions:**

- **URL-preservation rule** (`"The 'url' field MUST be the exact URL from the input article. Never invent URLs."`) — exploits Claude's instruction following to prevent hallucinated links in 100% of tested runs.
- **Language normalisation** (`"Write in clear, journalistic English regardless of the source language."`) — eliminates a separate translation step across 14 non-English feed languages.
- **Concrete schema examples** in the prompt outperform abstract descriptions for JSON fidelity.
- **15-event cap** in the BreakingNewsAgent system prompt prevents response truncation under the `max_tokens` budget.

### 3.2 Claude Haiku 4.5

**Defined in `config.SCRAPER_MODEL`; reserved for future use.**
Haiku is Anthropic's fastest and cheapest model. It is pre-wired as the scraping model for potential future tasks such as per-article topic classification or paywall detection. In the current implementation, scraping is pure Python — no LLM overhead needed for I/O work.

---

## 4. Data Processing Pipeline — Step by Step

### Step 1 — Trigger (`scheduler.py`)

`APScheduler` fires a `BlockingScheduler` with three `CronTrigger` jobs at **07:15, 12:15, and 17:15 UTC** daily.
`misfire_grace_time=3600` allows each job to execute up to one hour late (after a restart).

```
APScheduler.CronTrigger(hour=7,  minute=15, timezone="UTC") ─┐
APScheduler.CronTrigger(hour=12, minute=15, timezone="UTC") ─┼─► OrchestratorAgent.run_pipeline(resume=False)
APScheduler.CronTrigger(hour=17, minute=15, timezone="UTC") ─┘
```

---

### Step 2 — RSS Ingestion (`ScraperAgent._fetch_rss`) — *Python only*

`feedparser.parse(url)` fetches and parses each RSS/Atom feed. It handles RSS 0.9x / 2.0 / Atom 1.0 dialect differences, encoding detection (UTF-8, Latin-1, Windows-1252), and malformed XML — all transparently.

**Extracted per entry:** `title`, `link` (article URL), `published`, `summary` (first 800 chars of feed description).

**Parameters:** up to `MAX_ARTICLES_PER_SOURCE = 10` entries per source · `User-Agent: NewsAgent/1.0` · `RSS_TIMEOUT = 15 s`.

**File:** `agents/scraper_agent.py:44`

---

### Step 3 — Article Content Extraction (`ScraperAgent._extract_content`) — *Python only*

For the top `FULL_CONTENT_LIMIT = 5` articles per source:

1. `httpx.Client.get(url)` downloads raw HTML with redirect following and a 15-second timeout.
2. `trafilatura.extract(html)` strips navigation bars, ads, cookie banners, sidebars, and comment sections, returning clean article body text.
3. Output is capped at `MAX_ARTICLE_CHARS = 4 000` characters.

**Fallback:** if extraction fails (paywall, JavaScript-only, timeout), the RSS `summary` field is used instead.

**File:** `agents/scraper_agent.py:65`

---

### Step 4 — Article Slimming (in-memory, before LLM)

Before handing articles to Claude, `SummarizerAgent.summarize_region()` trims each article to 2 000 characters and retains only the fields Claude needs:

```python
slim = [{"title": …, "source": …, "url": …, "source_home": …, "content": content[:2000]}
        for article in articles]
```

This keeps the per-region Claude input under **~15 K tokens** — comfortably within one API call and under the 30 K token/minute rate limit.

**File:** `agents/summarizer_agent.py:74`

---

### Step 5 — Regional Summarisation (`SummarizerAgent.summarize_region`) — ⚡ *LLM + Tool Use*

`SummarizerAgent` inherits `BaseAgent` and drives a Claude Sonnet 4.6 **agentic tool-use loop**:

1. Sends slim articles for the region with system-prompt schema contract.
2. Claude calls `build_regional_digest(region, article_count)` — a lightweight acknowledgment tool that signals all data has been read.
3. `BaseAgent._dispatch_tool()` returns a `{"status": "ready"}` acknowledgment.
4. Claude emits the structured digest JSON as its `end_turn` text response.
5. `BaseAgent._parse_result()` strips any markdown fences and calls `json.loads()`.

The digest is **immediately written to disk** (`data/processed/DATE/region.json`) so a later crash does not lose completed work.

**Output per region:**
```json
{
  "region": "canada",
  "date": "2026-05-13",
  "overview": "2–3 sentence thematic overview…",
  "stories": [
    { "headline": "…", "source": "CBC News", "url": "https://…", "source_home": "…",
      "summary": "2–4 sentence factual summary…", "category": "politics" }
  ]
}
```

Up to **10 stories** per region. Claude is instructed to maximise topic diversity, covering as many of the 20 topic categories as possible given available articles.

**20 topic categories:**

| Category | Category | Category | Category |
|----------|----------|----------|----------|
| 🏛️ Politics | 🌐 World News | 💼 Business & Economy | 💻 Technology |
| 🏥 Health | 🔬 Science & Environment | 🚔 Crime & Public Safety | 🎭 Entertainment & Culture |
| ⚽ Sports | 🌟 Lifestyle & Human Interest | 🤖 Artificial Intelligence | 📈 Wall Street |
| 🏔️ Silicon Valley | 📱 Social Networks | 🌡️ Global Warming | 💸 Cost of Living |
| 👷 Employment & Work | ⚖️ Gender Equity | 🐾 Pets & Animal Kingdom | 🎬 Music & Movies |

The **index page** shows a "Today by Topic" grid — one representative story per topic aggregated from all 26 regions, guaranteeing every topic has at least one story visible on the homepage.

**File:** `agents/summarizer_agent.py:72`

---

### Step 6 — Digest Slimming (before Breaking News call)

After all 25 regions are summarised, the digests are flattened into a compact detection payload:

```python
stories = [
    {"headline": …, "source": …, "url": …, "region": …, "summary": summary[:100]}
    for region, digest in region_summaries.items()
    for story in digest["stories"]
]
# → 25 regions × 8 stories = 200 items × ~50 tokens each ≈ 10 K tokens total
```

**Why digests and not raw articles?**
Raw articles (750 items × 80-char blurbs) produce a ~42 K-token payload. The first API call alone would exceed the 30 K token/minute rate limit. Digest stories are already Claude-curated, higher signal, and only ~10 K tokens total.

**File:** `agents/breaking_news_agent.py:78`

---

### Step 7 — Breaking News Detection (`BreakingNewsAgent.detect`) — ⚡ *LLM, single call*

`BreakingNewsAgent` uses a **single direct API call** (no tool-use loop) to detect, group, and synthesise breaking events across all 25 countries simultaneously:

1. Sends the 200-story compact payload in one `messages.create()` call.
2. Claude scans for all 6 breaking-news categories, groups cross-country coverage of the same event, writes a 3–5 sentence unified summary, notes how different national outlets frame the story differently, and assigns severity.
3. The response is a raw JSON array of up to **15 events** (capped to prevent `max_tokens` truncation).
4. `detect()` strips any markdown fences and calls `json.loads()`.

The result is saved to `data/processed/DATE/breaking.json`.

**Why single-call instead of tool-use?**
During development with 25 countries the multi-turn tool-use approach accumulated context across turns (initial 10 K tokens + tool-call history), pushing the second API call above the 30 K token/minute limit. A single call keeps the total at ~10 K tokens in and ~10 K tokens out — well within limits.

**File:** `agents/breaking_news_agent.py:71`

---

### Step 8 — Static Site Generation (`WebGenerator.generate`)

`WebGenerator` uses Jinja2 template inheritance to render all pages in a single pass:

| Method | Output file | Key data |
|--------|-------------|----------|
| `_render_index()` | `index.html` | 26 region cards grouped by continent + breaking news ticker + day dropdown |
| `_render_region()` × 26 | `regions/{country}.html` | Full digest + JS category filter tabs + grouped region switcher |
| `_render_breaking()` | `breaking.html` | Events by category, per-source verification links |
| `_save_json()` | `data/summaries_DATE.json` + `data/breaking_DATE.json` | Raw JSON for external consumption |
| `_save_archive_index()` | `index_DATE.html` | Dated snapshot of the index page for the day selector |
| `_save_dates_manifest()` | `data/available_dates.json` | Ordered list of available dates consumed by the JS day picker |

`shutil.copytree` refreshes the `static/` assets on every run. After generation, `main.py` rsyncs `web/output/` to the live EC2 server automatically.

**File:** `web/generator.py:36`

---

## 5. Libraries Reference

### 🤖 AI & LLM Stack

| Library | Version | AI Technology | Role in this project |
|---------|---------|---------------|----------------------|
| **anthropic** | ≥ 0.40 | **GenAI · LLM · Agentic AI · Tool Use** | Official Claude API client. `client.messages.create()` drives all generative steps. Handles tool_use / tool_result message construction, typed response objects, and streaming. |

```python
# Core usage — base_agent.py
response = client.messages.create(
    model="claude-sonnet-4-6",
    max_tokens=4096,
    system=system_prompt,   # editorial contract
    tools=tools,            # JSON-schema tool definitions
    messages=messages,      # full conversation history
)
# stop_reason ∈ {"end_turn", "tool_use", "max_tokens"}
```

---

### 🌐 Web Scraping & Content Extraction

| Library | Version | AI Technology | Role |
|---------|---------|---------------|------|
| **feedparser** | ≥ 6.0 | None | Parses RSS 0.9x / 2.0 and Atom 1.0 feeds. Handles encoding detection, malformed XML, and date normalisation across 75 newspaper feeds. |
| **trafilatura** | ≥ 1.12 | *Heuristic ML* | Extracts main article body from raw HTML. Uses text-density scoring and XPath/CSS heuristics to discard ads, navigation, and boilerplate. Not a deep-learning model but a lightweight statistical content classifier. |
| **httpx** | ≥ 0.27 | None | HTTP/1.1 + HTTP/2 client. Downloads article pages with redirect following, timeout control, and persistent connection pooling. |

```python
# scraper_agent.py — full extraction pipeline
feed   = feedparser.parse(rss_url, request_headers={"User-Agent": "NewsAgent/1.0"})
html   = httpx.Client(timeout=15).get(article_url).text
text   = trafilatura.extract(html, include_comments=False, include_tables=False)
```

---

### 🖥️ Web Generation

| Library | Version | AI Technology | Role |
|---------|---------|---------------|------|
| **Jinja2** | ≥ 3.1 | None | Server-side HTML templating with template inheritance (`base.html` → child pages), auto-escaping (XSS protection), and loop/conditional blocks. Renders the 27-page static site from structured JSON. |

---

### ⚙️ Infrastructure

| Library | Version | AI Technology | Role |
|---------|---------|---------------|------|
| **APScheduler** | ≥ 3.10 | None | `BlockingScheduler` with `CronTrigger` for daily 07:00 UTC pipeline execution. `misfire_grace_time=3600` tolerates late starts. |
| **python-dotenv** | ≥ 1.0 | None | Loads `ANTHROPIC_API_KEY` and schedule overrides from `.env` into `os.environ` at startup. |
| **rich** | ≥ 13.9 | None | Styled terminal output — timestamped agent logs, coloured region headers, completion panels. |

---

## 6. Architecture & Data-Flow Diagrams

### 6.1 Full System — High-Level Flow

```mermaid
flowchart TD
    A([🕐 APScheduler\nCronTrigger 07:00 UTC]) --> B

    subgraph ORCH["OrchestratorAgent  ·  orchestrator.py"]
        B[run_pipeline] --> C{resume?\ncheck disk}
        C -->|cached| CACHE[(data/processed/DATE/\nregion.json × 25)]
        C -->|fresh| LOOP[loop 25 regions]
        LOOP --> SC[ScraperAgent\n.scrape_region]
        SC --> SU[SummarizerAgent\n.summarize_region]
        SU --> SAVE1[(Save region.json\nimmediately)]
        SAVE1 --> LOOP
        CACHE --> BN
        SAVE1 --> BN
        BN[BreakingNewsAgent\n.detect]
        BN --> SAVE2[(Save breaking.json)]
        SAVE2 --> WG[WebGenerator\n.generate]
    end

    subgraph SCRAPER["ScraperAgent — Python only"]
        SC --> F1[feedparser.parse\n× 3 sources]
        F1 --> F2[httpx.get + trafilatura\ntop-5 articles/source]
        F2 --> F3[list of Article dicts]
    end

    subgraph SUMM["SummarizerAgent — Claude Sonnet 4.6 · Tool-Use Loop"]
        SU --> G1[slim articles\ncontent truncated 2 000 chars]
        G1 --> G2[messages.create\nsystem+tools+messages]
        G2 -->|tool_use: build_regional_digest| G3[_dispatch_tool\nreturn acknowledgment]
        G3 --> G2
        G2 -->|end_turn| G4[_parse_result\nstrip fences · json.loads]
        G4 --> G5[Digest dict\noverview + 8 stories]
    end

    subgraph BREAK["BreakingNewsAgent — Claude Sonnet 4.6 · Single Call"]
        BN --> H1[flatten 200 digest stories\n100-char summary each]
        H1 --> H2[messages.create\nsingle call · 16 000 max_tokens]
        H2 --> H3[strip markdown fences\njson.loads]
        H3 --> H4[list of Breaking Events\nmax 15]
    end

    subgraph WEB["WebGenerator — Jinja2"]
        WG --> W1[_render_index\nindex.html]
        WG --> W2[_render_region × 25\nregions/*.html]
        WG --> W3[_render_breaking\nbreaking.html]
        WG --> W4[_save_json\ndata/*.json]
    end

    W1 & W2 & W3 & W4 --> OUT[(web/output/\n27 HTML pages\n+ JSON data)]
    OUT --> LIVE[🌐 GitHub Pages\nfborbon.github.io/news_agent]
```

---

### 6.2 BaseAgent Agentic Loop (used by SummarizerAgent)

```mermaid
flowchart LR
    A([user_message]) --> B[messages =\n'user' turn]

    B --> C[_create_with_retry\nmessages.create\nmodel·system·tools·messages]

    C -->|RateLimitError| R[sleep 60→120→240→300s\nretry up to 4×]
    R --> C

    C --> D{stop_reason?}

    D -->|end_turn| E[extract text block\n_parse_result\nstrip fences · json.loads]
    E --> Z([return result])

    D -->|tool_use| F[_blocks_to_dicts\nPydantic → plain dict\npreserves exact IDs]
    F --> G[append assistant turn\nto messages history]
    G --> H[for each tool_use block]
    H --> I[_dispatch_tool\nblock.name · block.input]
    I -->|raises _StopAgent| J[append tool_result\nstatus=stopped · early return]
    J --> Z
    I -->|normal| K[append tool_result\njson.dumps result]
    K --> H
    H -->|all done| L[append user turn\nwith all tool_results]
    L --> C
```

---

### 6.3 Function-Level Data Flow — Full Pipeline

```mermaid
flowchart TD
    subgraph IN["Input — 75 RSS Feeds"]
        R1["🇺🇸 NYT · WashPost · NPR"]
        R2["🇬🇧 BBC · Guardian · Sky"]
        R3["🇫🇷 LeMonde · LeFigaro · France24"]
        RN["… 22 more country groups …"]
    end

    subgraph SCRAPE["scraper_agent.py"]
        S1["_fetch_rss(source)\nfeedparser.parse(url)\n→ up to 10 entries/source"]
        S2["_extract_content(url)\nhttpx.get → trafilatura.extract\n→ str ≤ 4 000 chars\nfallback: RSS summary"]
        S3["scrape_region(region)\n→ list[Article]\ntitle · url · source · content"]
        R1 & R2 & R3 & RN --> S1 --> S2 --> S3
    end

    subgraph SLIM1["Article slimming — summarizer_agent.py:74"]
        T1["content[:2 000]\n~15 K tokens per region"]
        S3 --> T1
    end

    subgraph SUMM["summarizer_agent.py — Claude Sonnet 4.6"]
        U1["summarize_region(region, articles, date)\nbuild prompt string"]
        U2["BaseAgent.run(prompt)\nCall #1 → tool_use: build_regional_digest\nCall #2 → end_turn: JSON digest"]
        U3["Digest dict saved to disk\noverview + 8 stories with URLs"]
        T1 --> U1 --> U2 --> U3
    end

    subgraph SLIM2["Digest slimming — breaking_news_agent.py:78"]
        V1["25 regions × 8 stories\n= 200 items × ~50 tokens\n≈ 10 K tokens total"]
        U3 --> V1
    end

    subgraph BREAK["breaking_news_agent.py — Claude Sonnet 4.6"]
        W1["detect(region_summaries, date)\nbuild 200-story prompt"]
        W2["client.messages.create\nsingle call · 16 000 max_tokens\nno tool-use loop"]
        W3["strip markdown fences\njson.loads → list[BreakingEvent]\nmax 15 events"]
        V1 --> W1 --> W2 --> W3
    end

    subgraph GEN["web/generator.py — Jinja2"]
        X1["_render_index\nindex.html\nregion cards by continent + ticker"]
        X2["_render_region × 25\nregions/*.html\nstory grid + JS filter tabs"]
        X3["_render_breaking\nbreaking.html\ncross-source detail + verify links"]
        X4["_save_json\nweb/output/data/\n*.json"]
        U3 --> X1 & X2
        W3 --> X1 & X3
        U3 & W3 --> X4
    end

    subgraph OUT["Output — Static Site"]
        Y1["🌐 index.html\n25 region cards grouped by continent"]
        Y2["🌐 regions/usa.html … egypt.html\n200 stories · 200 clickable source links"]
        Y3["🌐 breaking.html\n≤15 events · per-source verify links"]
        X1 --> Y1
        X2 --> Y2
        X3 --> Y3
    end
```

---

### 6.4 Token Budget — Why Every Payload Size Was Chosen

```mermaid
xychart-beta
    title "Input tokens per Claude API call  (rate limit: 30 000 / min)"
    x-axis ["Summariser\n(per region)", "Breaking News\n(single call)", "Breaking News\n(old multi-turn\ncall 2 — retired)"]
    y-axis "Tokens" 0 --> 50000
    bar  [15000, 10000, 42000]
    line [30000, 30000, 30000]
```

> The retired multi-turn approach sent 750 raw articles (42 K tokens) and accumulated tool-call history on the second turn, consistently exceeding the 30 K/min limit. The current single-call approach sends 200 digest stories (~10 K tokens) in one shot.

---

## 7. Breaking News Detection

`BreakingNewsAgent` monitors six high-impact event categories across all 25 country feeds simultaneously:

| Icon | Category key | Trigger criteria | Example |
|------|-------------|-----------------|---------|
| ⚔️ | `war_conflict` | Active military operations, new conflicts, major escalations | US-Iran War, Russia-Ukraine drone strikes |
| 📉 | `financial_collapse` | Market crashes (>5%), sovereign debt defaults, bank failures | Energy crisis from Hormuz blockade |
| 🏦 | `corporate_crisis` | Fortune-500 bankruptcies, major fraud or accounting scandals | ASML chip export restrictions |
| 🚨 | `transportation_accident` | Aviation, maritime or rail disasters with mass casualties | Japan expressway bus crash |
| 🚔 | `law_enforcement_operation` | Counter-terrorism ops, ICC arrests, large-scale raids | Philippine Senate ICC arrest |
| 🌪️ | `natural_disaster` | Earthquakes M5.5+, hurricanes, tsunamis, wildfires, floods | Hantavirus outbreak, Cape Town floods |

**Cross-source synthesis:** For each event, Claude identifies which stories from *different* outlets and *different* countries cover the same event, and notes how national framing differs — e.g. how US sources vs. Iranian sources describe the same military action. This is stored in the `analysis` field.

**Severity assignment** (Claude's editorial judgement, guided by system prompt):
- `critical` — imminent mass-casualty risk, active armed conflict, nuclear escalation
- `high` — confirmed casualties or significant economic disruption, major public health threat
- `moderate` — contained but noteworthy events, early-stage developing stories

---

## 8. Project Structure

```
News_agent/
│
├── agents/
│   ├── base_agent.py           # Agentic loop + retry + fence-strip JSON parsing
│   ├── orchestrator.py         # Pipeline coordinator: 25-region loop, crash recovery
│   ├── scraper_agent.py        # RSS ingestion (feedparser) + extraction (trafilatura)
│   ├── summarizer_agent.py     # Claude Sonnet 4.6 · tool-use loop · per-region digest
│   └── breaking_news_agent.py  # Claude Sonnet 4.6 · single call · global event detection
│
├── sources/
│   └── news_sources.py         # 75 verified RSS feeds across 25 countries
│
├── web/
│   ├── generator.py            # Jinja2 static site builder (27 pages)
│   ├── templates/
│   │   ├── base.html           # Shared layout: 25-flag nav, mobile toggle, footer
│   │   ├── index.html          # Home: continent-grouped region cards + breaking ticker
│   │   ├── region.html         # Country digest: story grid + JS category filter
│   │   └── breaking.html       # Breaking events: sidebar nav + source verify links
│   └── static/
│       ├── css/style.css       # Dark news-site theme (no external CSS frameworks)
│       └── js/main.js          # Mobile nav toggle + category filter + ticker loop
│
├── data/
│   └── processed/
│       └── YYYY-MM-DD/
│           ├── {region}.json       # Digest per country (persisted immediately)
│           ├── {region}_raw.json   # Raw scraped articles (for --resume / debug)
│           └── breaking.json       # Detected breaking events
│
├── docs/                       # GitHub Pages deployment (copy of web/output/)
│                               # Live: forwardforecasting.eu/newssummary/
│
├── config.py                   # All constants, model names, region metadata
├── main.py                     # CLI: --now · --resume · --demo
├── scheduler.py                # APScheduler daily cron
├── requirements.txt
└── .env.example
```

---

## 9. Setup & Usage

### Install

```bash
git clone https://github.com/fborbon/news_agent.git
cd news_agent
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env          # add your ANTHROPIC_API_KEY
```

### Run

```bash
# Preview with mock data — no API key needed
python main.py --demo

# Full live pipeline, run once and exit
python main.py --now

# Resume after a crash — reuse today's cached region digests,
# only re-run the steps that didn't complete
python main.py --resume

# Run once immediately, then start the daily 07:00 UTC scheduler
python main.py
```

### Serve locally

```bash
python -m http.server 8080 --directory web/output
# → http://localhost:8080
```

### Deploy — two modes

**Running on the EC2 (production):** set `DEPLOY_LOCAL_DIR` in `.env` and the output is copied directly to the web root — no SSH needed:

```bash
# .env on the EC2
ANTHROPIC_API_KEY=sk-ant-...
DEPLOY_LOCAL_DIR=/var/www/forwardforecasting/newssummary
```

**Running from your laptop:** leave `DEPLOY_LOCAL_DIR` unset. Output is rsynced over SSH using `~/.ssh/forwardforecasting.pem`. Deploy is skipped gracefully if the key is missing.

### Running on EC2 (production setup)

The agent runs on the existing `t3.small` EC2 via cron — zero additional AWS cost:

```
# /var/spool/cron/crontabs/ubuntu
15  0 * * *  cd ~/news_agent && .venv/bin/python main.py --now >> /var/log/news_agent.log 2>&1
15  7 * * *  cd ~/news_agent && .venv/bin/python main.py --now >> /var/log/news_agent.log 2>&1
15 12 * * *  cd ~/news_agent && .venv/bin/python main.py --now >> /var/log/news_agent.log 2>&1
15 18 * * *  cd ~/news_agent && .venv/bin/python main.py --now >> /var/log/news_agent.log 2>&1
```

Logs: `tail -f /var/log/news_agent.log`

### Deploy to GitHub Pages (manual)

```bash
cp -r web/output/* docs/
git add docs/
git commit -m "update news digest $(date +%Y-%m-%d)"
git push
```

---

## 10. Configuration Reference

All settings live in `config.py` and can be overridden via `.env`:

| Variable | Default | Description |
|----------|---------|-------------|
| `ANTHROPIC_API_KEY` | — | **Required.** Your Anthropic API key |
| `SUMMARIZER_MODEL` | `claude-sonnet-4-6` | Claude model for regional digests (tool-use loop) |
| `BREAKING_MODEL` | `claude-sonnet-4-6` | Claude model for breaking news (single call) |
| `SCRAPER_MODEL` | `claude-haiku-4-5-20251001` | Reserved for future LLM-assisted scraping enrichment |
| `SCHEDULE_TIMES` | `[(0,15),(7,15),(12,15),(18,15)]` | Four daily run times in UTC — hardcoded in `config.py` |
| `DEPLOY_LOCAL_DIR` | *(unset)* | If set, copies output here instead of rsync over SSH (use on EC2) |
| `MAX_ARTICLES_PER_SOURCE` | `10` | Max RSS entries fetched per source |
| `FULL_CONTENT_LIMIT` | `5` | Articles per source that get full trafilatura extraction |
| `MAX_ARTICLE_CHARS` | `4 000` | Character cap on extracted article text |
| `RSS_TIMEOUT` | `15` | HTTP timeout for article downloads (seconds) |
