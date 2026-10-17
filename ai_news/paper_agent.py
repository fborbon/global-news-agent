"""Fetches the top-cited AI papers published in a given month, has Amazon Nova
classify which ones are actually about the development of foundation models
and core AI technology (as opposed to applying AI to some other domain), and
summarises the top foundational ones in plain English.

Data source: the Semantic Scholar Graph API (free, no API key required).
"""
from __future__ import annotations

import calendar
import json
import re
import time
from datetime import date, timedelta

import boto3
import httpx
from botocore.exceptions import ClientError
from rich.console import Console

from ai_news.config import (
    BEDROCK_REGION,
    PAPER_CLASSIFY_POOL,
    PAPER_FIELDS_OF_STUDY,
    PAPER_MODEL,
    PAPER_QUERY,
    SEMANTIC_SCHOLAR_API,
    TOP_PAPERS_PER_MONTH,
)

console = Console()

_SYSTEM_PROMPT = """You are an AI research editor curating a monthly digest
about the DEVELOPMENT OF FOUNDATION MODELS AND CORE AI TECHNOLOGY: model
architecture (transformers, attention, mixture of experts, ...), training
methods (pretraining, RLHF, instruction tuning, scaling laws, ...),
generative AI techniques, agentic AI, and artificial general intelligence
research. Papers that merely APPLY existing AI/ML techniques to a specific
external domain (e.g. healthcare diagnostics, wireless networks, robotics
control for a physical task, finance, biology, traffic forecasting) are OUT
OF SCOPE even if they mention "LLM" or "generative AI" — only flag a paper
as core if its main contribution is to the model/technology itself.

You are given a JSON array of candidate papers (paper_id, title, abstract,
citationCount). For EACH paper return an object with:
  - "paper_id"
  - "is_core": true if the paper's main contribution is to AI model
    architecture, training methodology, or general-purpose AI capability;
    false if it is primarily an application of AI to an external domain.
  - "plain_summary": if is_core is true, 2-3 sentences explaining what the
    paper does and why it matters, in plain English for a technically
    literate but non-specialist reader. If is_core is false, use "".
  - "key_contribution": if is_core is true, one short sentence (max ~15
    words) naming the single biggest contribution or result. If is_core is
    false, use "".

Return ONLY a raw JSON array, no markdown fences, one object per input paper
in the same order. Do not invent facts not supported by the abstract."""


class PaperAgent:
    def __init__(self) -> None:
        self.client = boto3.client("bedrock-runtime", region_name=BEDROCK_REGION)

    # ------------------------------------------------------------------
    # Step 1 — fetch candidates from Semantic Scholar, sorted by citations
    # ------------------------------------------------------------------

    def fetch_top_papers(self, year: int, month: int) -> list[dict]:
        last_day = calendar.monthrange(year, month)[1]
        date_range = f"{year}-{month:02d}-01:{year}-{month:02d}-{last_day:02d}"

        params = {
            "query": PAPER_QUERY,
            "fields": "title,abstract,url,citationCount,publicationDate,authors,venue",
            "sort": "citationCount:desc",
            "publicationDateOrYear": date_range,
            "fieldsOfStudy": PAPER_FIELDS_OF_STUDY,
        }

        console.log(f"[cyan][PaperAgent][/cyan] fetching candidates for {year}-{month:02d}")
        data = self._get_with_retry(SEMANTIC_SCHOLAR_API, params)
        candidates = data.get("data", [])

        seen_titles: set[str] = set()
        ranked: list[dict] = []
        for p in candidates:
            title = (p.get("title") or "").strip()
            abstract = (p.get("abstract") or "").strip()
            if not title or not abstract:
                continue
            key = title.lower()
            if key in seen_titles:
                continue
            seen_titles.add(key)
            ranked.append({
                "paper_id": p["paperId"],
                "title": title,
                "abstract": abstract[:2000],
                "url": p.get("url") or f"https://www.semanticscholar.org/paper/{p['paperId']}",
                "citation_count": p.get("citationCount") or 0,
                "publication_date": p.get("publicationDate") or f"{year}-{month:02d}",
                "authors": [a["name"] for a in (p.get("authors") or [])[:5]],
                "venue": p.get("venue") or "",
            })

        # Sorted by citation count, highest first — this order is preserved
        # through classification so "top 5 core" == "top 5 by citations
        # among the ones Nova judged to be core AI-technology papers".
        ranked.sort(key=lambda x: x["citation_count"], reverse=True)
        return ranked[:PAPER_CLASSIFY_POOL]

    def _get_with_retry(self, url: str, params: dict, max_retries: int = 5) -> dict:
        delay = 5
        for attempt in range(max_retries):
            resp = httpx.get(url, params=params, timeout=30)
            if resp.status_code == 200:
                return resp.json()
            if resp.status_code in (429, 500, 502, 503) and attempt < max_retries - 1:
                console.log(f"[yellow][PaperAgent][/yellow] {resp.status_code} — waiting {delay}s")
                time.sleep(delay)
                delay = min(delay * 2, 60)
                continue
            resp.raise_for_status()
        raise RuntimeError("Semantic Scholar request failed after retries")

    # ------------------------------------------------------------------
    # Step 2 — classify (core vs. applied) and summarise with Amazon Nova
    # ------------------------------------------------------------------

    def classify_and_summarize(self, papers: list[dict]) -> list[dict]:
        if not papers:
            return []

        payload = [
            {
                "paper_id": p["paper_id"],
                "title": p["title"],
                "abstract": p["abstract"],
                "citationCount": p["citation_count"],
            }
            for p in papers
        ]
        user_message = json.dumps(payload, ensure_ascii=False)

        console.log(f"[cyan][PaperAgent][/cyan] classifying + summarising {len(papers)} candidates with Nova")
        results = self._converse_with_retry(user_message)
        by_id = {r["paper_id"]: r for r in results if "paper_id" in r}

        enriched = []
        for p in papers:
            r = by_id.get(p["paper_id"], {})
            enriched.append({
                **p,
                "is_core": bool(r.get("is_core", False)),
                "plain_summary": r.get("plain_summary", ""),
                "key_contribution": r.get("key_contribution", ""),
            })
        return enriched

    def _converse_with_retry(self, user_message: str, max_retries: int = 4) -> list[dict]:
        delay = 60
        for attempt in range(max_retries):
            try:
                response = self.client.converse(
                    modelId=PAPER_MODEL,
                    system=[{"text": _SYSTEM_PROMPT}],
                    messages=[{"role": "user", "content": [{"text": user_message}]}],
                    inferenceConfig={"maxTokens": 6000},
                )
                text = response["output"]["message"]["content"][0]["text"]
                return self._parse_json_array(text)
            except ClientError as exc:
                code = exc.response["Error"]["Code"]
                if code in ("ThrottlingException", "ServiceUnavailableException") and attempt < max_retries - 1:
                    console.log(f"[yellow][PaperAgent][/yellow] throttled — waiting {delay}s")
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

    def build_monthly_digest(self, year: int | None = None, month: int | None = None) -> dict:
        # Default to the most recently *completed* calendar month, so citation
        # counts have had time to accumulate before we rank papers.
        if year is None or month is None:
            last_month_end = date.today().replace(day=1) - timedelta(days=1)
            year = year or last_month_end.year
            month = month or last_month_end.month

        candidates = self.fetch_top_papers(year, month)
        classified = self.classify_and_summarize(candidates)
        # citation order was preserved through classification — just keep the
        # core ones and take the top N.
        core_papers = [p for p in classified if p["is_core"]][:TOP_PAPERS_PER_MONTH]

        return {
            "year": year,
            "month": month,
            "month_label": date(year, month, 1).strftime("%B %Y"),
            "papers": core_papers,
        }
