"""Static HTML site generator — converts pipeline output into web pages."""
from __future__ import annotations

import json
import shutil
from pathlib import Path

from jinja2 import Environment, FileSystemLoader
from rich.console import Console

from config import (
    BREAKING_CATEGORIES,
    REGION_META,
    REGIONS,
    STORY_CATEGORIES,
    TEMPLATES_DIR,
    WEB_OUTPUT_DIR,
    STATIC_DIR,
)

console = Console()

# Only the actively monitored countries — keeps nav flags in sync with config
_ACTIVE_REGION_META = {r: REGION_META[r] for r in REGIONS if r in REGION_META}

# Common template context passed to every page
_BASE_CTX = dict(
    region_meta=_ACTIVE_REGION_META,
    breaking_categories=BREAKING_CATEGORIES,
    story_categories=STORY_CATEGORIES,
)

# Keywords used to match stories when the category tag is from the old schema
_TOPIC_KEYWORDS: dict[str, list[str]] = {
    "politics":                ["election", "government", "parliament", "congress", "president", "prime minister", "policy", "senate", "democrat", "republican"],
    "world_news":              ["international", "global", "united nations", "diplomatic", "foreign affairs", "summit", "bilateral", "treaty"],
    "business_economy":        ["economy", "gdp", "trade", "economic", "revenue", "fiscal", "deficit", "exports", "imports", "commerce"],
    "technology":              ["technology", "tech", "software", "hardware", "digital", "app", "platform", "cyber"],
    "health":                  ["health", "medical", "hospital", "disease", "vaccine", "pandemic", "mental health", "cancer", "drug", "clinical"],
    "science_environment":     ["science", "research", "study", "discovery", "space", "nasa", "biodiversity", "ecosystem", "species"],
    "crime_safety":            ["crime", "arrest", "police", "murder", "theft", "fraud", "shooting", "prison", "trafficking", "gang"],
    "entertainment_culture":   ["entertainment", "culture", "award", "celebrity", "festival", "exhibition", "theatre", "museum"],
    "sports":                  ["sport", "football", "soccer", "basketball", "tennis", "olympic", "championship", "league", "athlete", "tournament"],
    "lifestyle":               ["lifestyle", "travel", "food", "wellness", "fashion", "trend", "family", "parenting", "relationship"],
    "artificial_intelligence": ["artificial intelligence", " ai ", "machine learning", "chatgpt", "openai", "deepmind", "llm", "large language", "chatbot", "generative ai", "neural network"],
    "wall_street":             ["stock market", "wall street", "s&p", "nasdaq", "dow jones", "federal reserve", "interest rate", "hedge fund", "ipo", "bond market", "fed rate", "equity market"],
    "silicon_valley":          ["silicon valley", "apple inc", "google", "alphabet", "meta ", "microsoft", "amazon", "tesla", "startup", "big tech", "venture capital", "zuckerberg", "elon musk"],
    "social_networks":         ["twitter", " x.com", "instagram", "tiktok", "facebook", "youtube", "social media", "influencer", "viral", "online platform"],
    "global_warming":          ["climate change", "global warming", "carbon", "emissions", "fossil fuel", "renewable energy", "greenhouse", "net zero", "paris agreement", "cop3"],
    "cost_of_living":          ["inflation", "cost of living", "housing", "rent", "consumer price", "affordability", "mortgage", "groceries", "purchasing power", "cpi"],
    "employment":              ["job", "employment", "unemployment", "hiring", "layoff", "remote work", "workforce", "salary", "wage", "labour market", "labor market"],
    "gender_equity":           ["gender", "women's rights", "feminist", "gender equality", "lgbtq", "reproductive", "pay gap", "diversity", "inclusion", "gender-based"],
    "pets_animals":            [" pet", " dog ", " cat ", " animal", "wildlife", "conservation", "endangered", " zoo", "veterinary", "shelter", "rescue"],
    "music_movies":            ["music", " film", " movie", "cinema", "grammy", "oscar", "album", "concert", "netflix", "box office", "streaming", "spotify", "record label"],
}


class WebGenerator:
    def __init__(self) -> None:
        self.env = Environment(
            loader=FileSystemLoader(str(TEMPLATES_DIR)),
            autoescape=True,
        )
        self.out = WEB_OUTPUT_DIR
        self.out.mkdir(parents=True, exist_ok=True)
        (self.out / "regions").mkdir(exist_ok=True)

    # ------------------------------------------------------------------
    # Public entry point
    # ------------------------------------------------------------------

    def generate(self, region_summaries: dict[str, dict], breaking_events: list[dict], today: str) -> None:
        console.log("[cyan]Generating static site …[/cyan]")
        # Clear stale region pages so removed countries don't persist
        regions_dir = self.out / "regions"
        if regions_dir.exists():
            shutil.rmtree(regions_dir)
        regions_dir.mkdir()
        self._copy_static()
        topic_highlights = self._build_topic_highlights(region_summaries)
        self._render_index(region_summaries, breaking_events, today, topic_highlights)
        for region, digest in region_summaries.items():
            self._render_region(region, digest, today)
        self._render_breaking(breaking_events, today)
        self._save_json(region_summaries, breaking_events, today)
        self._save_world_news(region_summaries)
        self._save_archive_index(today)
        self._save_dates_manifest(today)
        console.log(f"[green]✓ Site generated → {self.out}[/green]")

    # ------------------------------------------------------------------
    # Page renderers
    # ------------------------------------------------------------------

    def _render_index(self, summaries: dict, breaking: list, today: str,
                      topic_highlights: dict) -> None:
        tmpl = self.env.get_template("index.html")
        region_cards = []
        for region, meta in REGION_META.items():
            digest = summaries.get(region, {})
            region_cards.append({
                "key":      region,
                "label":    meta["label"],
                "flag":     meta["flag"],
                "overview": digest.get("overview", "No data available for this region."),
                "stories":  digest.get("stories", [])[:3],
            })

        html = tmpl.render(
            **_BASE_CTX,
            today=today,
            region_cards=region_cards,
            breaking_events=breaking,
            critical_count=sum(1 for e in breaking if e.get("severity") == "critical"),
            topic_highlights=topic_highlights,
            static_root="static",
            root="",
            active_region=None,
        )
        (self.out / "index.html").write_text(html, encoding="utf-8")

    def _render_region(self, region: str, digest: dict, today: str) -> None:
        tmpl = self.env.get_template("region.html")
        meta = REGION_META.get(region, {"label": region, "flag": "", "lang": "", "group": ""})
        html = tmpl.render(
            **_BASE_CTX,
            today=today,
            region=region,
            meta=meta,
            digest=digest,
            static_root="../static",
            root="../",
            active_region=region,
        )
        (self.out / "regions" / f"{region}.html").write_text(html, encoding="utf-8")

    def _render_breaking(self, events: list, today: str) -> None:
        tmpl = self.env.get_template("breaking.html")
        grouped: dict[str, list] = {k: [] for k in BREAKING_CATEGORIES}
        for event in events:
            cat = event.get("category", "")
            if cat in grouped:
                grouped[cat].append(event)

        html = tmpl.render(
            **_BASE_CTX,
            today=today,
            events=events,
            grouped=grouped,
            static_root="static",
            root="",
            active_region=None,
        )
        (self.out / "breaking.html").write_text(html, encoding="utf-8")

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _copy_static(self) -> None:
        dest = self.out / "static"
        if dest.exists():
            shutil.rmtree(dest)
        shutil.copytree(str(STATIC_DIR), str(dest))

    def _build_topic_highlights(self, region_summaries: dict) -> dict:
        """Return one representative story per STORY_CATEGORIES topic."""
        all_stories: list[dict] = []
        for region, digest in region_summaries.items():
            meta = REGION_META.get(region, {})
            for story in digest.get("stories", []):
                all_stories.append({
                    **story,
                    "region_key":   region,
                    "region_label": meta.get("label", region),
                    "region_flag":  meta.get("flag", ""),
                })

        used: set[str] = set()

        def _claim(story: dict) -> bool:
            key = story.get("url") or story.get("headline", "")
            if not key or key in used:
                return False
            used.add(key)
            return True

        highlights: dict[str, dict] = {}
        for topic_key in STORY_CATEGORIES:
            # 1. Exact new-schema category match
            for s in all_stories:
                if s.get("category") == topic_key and _claim(s):
                    highlights[topic_key] = s
                    break
            if topic_key in highlights:
                continue
            # 2. Keyword fallback (handles old-schema stories)
            keywords = _TOPIC_KEYWORDS.get(topic_key, [])
            for s in all_stories:
                text = (s.get("headline", "") + " " + s.get("summary", "")).lower()
                if any(kw in text for kw in keywords) and _claim(s):
                    highlights[topic_key] = s
                    break
        return highlights

    def _save_json(self, summaries: dict, breaking: list, today: str) -> None:
        data_dir = self.out / "data"
        data_dir.mkdir(exist_ok=True)
        (data_dir / f"summaries_{today}.json").write_text(
            json.dumps(summaries, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        (data_dir / f"breaking_{today}.json").write_text(
            json.dumps(breaking, ensure_ascii=False, indent=2), encoding="utf-8"
        )

    def _save_world_news(self, summaries: dict) -> None:
        """Write data/world_news.json with up to 3 stories per covered region."""
        world: dict[str, dict] = {}
        for region, digest in summaries.items():
            meta = REGION_META.get(region, {})
            stories_raw = digest.get("stories", [])[:3]
            stories = [
                {
                    "headline": s.get("headline", ""),
                    "url":      s.get("url", ""),
                    "source":   s.get("source", ""),
                }
                for s in stories_raw
            ]
            world[region] = {
                "label":   meta.get("label", region),
                "flag":    meta.get("flag", ""),
                "stories": stories,
            }
        data_dir = self.out / "data"
        data_dir.mkdir(exist_ok=True)
        (data_dir / "world_news.json").write_text(
            json.dumps(world, ensure_ascii=False, indent=2), encoding="utf-8"
        )

    def _save_archive_index(self, today: str) -> None:
        src = self.out / "index.html"
        if src.exists():
            shutil.copy2(src, self.out / f"index_{today}.html")

    def _save_dates_manifest(self, today: str) -> None:
        dates = [{"date": today, "path": "index.html"}]
        for f in sorted(self.out.glob("index_*.html"), reverse=True):
            d = f.stem[len("index_"):]
            if d != today:
                dates.append({"date": d, "path": f.name})
        data_dir = self.out / "data"
        data_dir.mkdir(exist_ok=True)
        (data_dir / "available_dates.json").write_text(
            json.dumps(dates, ensure_ascii=False), encoding="utf-8"
        )
