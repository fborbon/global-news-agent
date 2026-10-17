"""Fetches each blog's RSS/Atom feed and summarises the last 7 days of posts
in plain English via Amazon Nova (AWS Bedrock).
"""
from __future__ import annotations

import json
import re
import time
from datetime import datetime, timedelta, timezone

import boto3
import feedparser
from botocore.exceptions import ClientError
from rich.console import Console

from ai_news.config import (
    BEDROCK_REGION,
    BLOG_FALLBACK_POSTS,
    BLOG_MODEL,
    BLOG_SUMMARY_DAYS,
    BLOG_SUMMARY_MAX_CHARS,
    BLOGS,
)

console = Console()

_SYSTEM_PROMPT = f"""You are an AI news editor. You are given a JSON array of
blogs, each with a list of that blog's posts (title + short description) and a
"recent" flag: true means these posts were published in the last {BLOG_SUMMARY_DAYS}
days, false means the blog had nothing that recent so these are just its most
recent posts regardless of date. For EACH blog, write a "weekly_summary": one
paragraph, at most {BLOG_SUMMARY_MAX_CHARS} characters, describing what those
posts covered — name the concrete topics/post titles, do not invent anything
not present in the input. If "recent" is true you may frame it as recent/this
week; if false, describe the posts themselves without implying they are recent
(e.g. "Their last posts covered..." not "This week...").

Return ONLY a raw JSON array, no markdown fences, one object per input blog in
the same order, each with exactly these fields: "name", "weekly_summary"."""


class BlogAgent:
    def __init__(self) -> None:
        self.client = boto3.client("bedrock-runtime", region_name=BEDROCK_REGION)

    # ------------------------------------------------------------------
    # Step 1 — fetch recent posts per blog
    # ------------------------------------------------------------------

    def fetch_recent_posts(self, rss_url: str) -> list[dict]:
        """Posts published within BLOG_SUMMARY_DAYS, newest first."""
        cutoff = datetime.now(timezone.utc) - timedelta(days=BLOG_SUMMARY_DAYS)
        posts = []
        for entry, published in self._iter_entries(rss_url):
            if published < cutoff:
                continue
            posts.append(self._entry_to_post(entry, published))
        return posts

    def fetch_latest_posts(self, rss_url: str, limit: int = BLOG_FALLBACK_POSTS) -> list[dict]:
        """Fallback for a quiet blog: its last N posts regardless of date."""
        posts = []
        for entry, published in self._iter_entries(rss_url):
            posts.append(self._entry_to_post(entry, published))
            if len(posts) >= limit:
                break
        return posts

    @staticmethod
    def _iter_entries(rss_url: str):
        feed = feedparser.parse(rss_url)
        for entry in feed.entries:
            parsed = entry.get("published_parsed") or entry.get("updated_parsed")
            if not parsed:
                continue
            yield entry, datetime(*parsed[:6], tzinfo=timezone.utc)

    @staticmethod
    def _entry_to_post(entry: dict, published: datetime) -> dict:
        raw_desc = entry.get("summary") or entry.get("description") or ""
        description = re.sub(r"<[^>]+>", " ", raw_desc)
        description = re.sub(r"\s+", " ", description).strip()[:400]
        return {
            "title": entry.get("title", "").strip(),
            "description": description,
            "published": published.date().isoformat(),
        }

    # ------------------------------------------------------------------
    # Step 2 — summarise with Amazon Nova (one batched call)
    # ------------------------------------------------------------------

    def summarize(self, blogs_with_posts: list[dict]) -> dict[str, str]:
        """blogs_with_posts: [{"name": ..., "posts": [...], "recent": bool}, ...]
        — only blogs with at least one post to summarise. Returns {name: weekly_summary}."""
        if not blogs_with_posts:
            return {}

        payload = [
            {
                "name": b["name"],
                "recent": b["recent"],
                "posts": [{"title": p["title"], "description": p["description"]} for p in b["posts"]],
            }
            for b in blogs_with_posts
        ]
        user_message = json.dumps(payload, ensure_ascii=False)

        console.log(f"[cyan][BlogAgent][/cyan] summarising {len(blogs_with_posts)} blogs with Nova")
        results = self._converse_with_retry(user_message)
        return {
            r["name"]: self._enforce_max_chars(r.get("weekly_summary", ""))
            for r in results if "name" in r
        }

    @staticmethod
    def _enforce_max_chars(text: str) -> str:
        # The model is instructed to stay under the limit but doesn't always
        # comply exactly, so this is a hard safety net, not the primary control.
        if len(text) <= BLOG_SUMMARY_MAX_CHARS:
            return text
        cut = text[:BLOG_SUMMARY_MAX_CHARS].rsplit(" ", 1)[0]
        return cut.rstrip(",.;: ") + "…"

    def _converse_with_retry(self, user_message: str, max_retries: int = 4) -> list[dict]:
        delay = 60
        for attempt in range(max_retries):
            try:
                response = self.client.converse(
                    modelId=BLOG_MODEL,
                    system=[{"text": _SYSTEM_PROMPT}],
                    messages=[{"role": "user", "content": [{"text": user_message}]}],
                    inferenceConfig={"maxTokens": 4000},
                )
                text = response["output"]["message"]["content"][0]["text"]
                return self._parse_json_array(text)
            except ClientError as exc:
                code = exc.response["Error"]["Code"]
                if code in ("ThrottlingException", "ServiceUnavailableException") and attempt < max_retries - 1:
                    console.log(f"[yellow][BlogAgent][/yellow] throttled — waiting {delay}s")
                    time.sleep(delay)
                    delay = min(delay * 2, 300)
                    continue
                raise
        raise RuntimeError("Bedrock request failed after retries")

    @staticmethod
    def _parse_json_array(text: str) -> list[dict]:
        t = (text or "").strip()
        t = re.sub(r"<thinking>.*?</thinking>", "", t, flags=re.DOTALL).strip()
        if t.startswith("```"):
            t = t.split("\n", 1)[-1]
            t = t.rsplit("```", 1)[0].strip()
        idx = t.find("[")
        if idx != -1:
            try:
                return json.loads(t[idx:])
            except json.JSONDecodeError:
                pass
        try:
            return json.loads(t)
        except json.JSONDecodeError:
            return []

    # ------------------------------------------------------------------
    # Public entry point
    # ------------------------------------------------------------------

    def build_blog_digest(self) -> list[dict]:
        """Returns BLOGS enriched with weekly_summary, is_recent, and updated_at.

        For each blog: try the last BLOG_SUMMARY_DAYS days first; if nothing was
        published in that window, fall back to summarising its last
        BLOG_FALLBACK_POSTS posts regardless of date, so the card is never just
        a dead "nothing happened" message as long as the blog has ever posted.
        """
        blogs_with_posts = []
        recent_by_name: dict[str, bool] = {}
        for blog in BLOGS:
            if not blog.get("rss"):
                continue
            try:
                posts = self.fetch_recent_posts(blog["rss"])
                recent = True
                if not posts:
                    posts = self.fetch_latest_posts(blog["rss"])
                    recent = False
            except Exception as exc:  # feed can be temporarily down/malformed
                console.log(f"[yellow][BlogAgent][/yellow] {blog['name']} feed error: {exc}")
                posts, recent = [], True
            if posts:
                blogs_with_posts.append({"name": blog["name"], "posts": posts, "recent": recent})
                recent_by_name[blog["name"]] = recent

        summaries = self.summarize(blogs_with_posts)

        now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
        enriched = []
        for blog in BLOGS:
            summary = summaries.get(blog["name"], "")
            is_recent = recent_by_name.get(blog["name"], True)
            if not summary:
                summary = "No RSS feed available for this blog." if not blog.get("rss") else "No posts found for this blog."
            enriched.append({**blog, "weekly_summary": summary, "is_recent": is_recent, "updated_at": now})
        return enriched
