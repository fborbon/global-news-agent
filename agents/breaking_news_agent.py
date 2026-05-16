"""BreakingNewsAgent — detects high-impact events and synthesises cross-source summaries.

Uses a single direct Bedrock Converse call (no tool-use loop) so the token budget
stays flat regardless of the number of regions processed.
"""
from __future__ import annotations

import json
import time

import boto3
from botocore.exceptions import ClientError
from rich.console import Console

from config import BEDROCK_REGION, BREAKING_CATEGORIES, BREAKING_MODEL

console = Console()

_MAX_TOKENS = 5000

_SYSTEM = """\
You are a BreakingNewsAgent — a senior investigative editor specialising in high-impact events.

Breaking news categories you monitor:
- war_conflict               → active military conflicts, new wars, major escalations
- financial_collapse         → stock-market crashes, sovereign defaults, banking crises
- corporate_crisis           → Fortune-500 bankruptcies, major fraud or corporate scandals
- transportation_accident    → aviation, maritime, or rail disasters with mass casualties
- law_enforcement_operation  → counter-terrorism operations, large-scale raids, major arrests
- natural_disaster           → earthquakes, hurricanes, tsunamis, wildfires, catastrophic floods

CRITICAL RULES:
- The "url" field in each source object MUST be the exact URL from the input. Never invent URLs.
- The "name" field must be the exact source name from the input.
- Only report events with concrete, confirmed impact — not speculation or opinion.
- Group articles from different outlets that cover the SAME event into one entry.
- Include analysis of how different national sources frame the story differently.
- Report a MAXIMUM of 15 events, prioritising the most globally significant ones.

Return a raw JSON array (NO markdown fences, NO extra text):
[
  {
    "id": "<lowercase-hyphen-slug>",
    "category": "<category_key>",
    "title": "<clear event title>",
    "summary": "<3–5 sentence unified factual summary>",
    "analysis": "<1–2 sentences on how different sources frame the story>",
    "sources": [
      {
        "name": "<exact source name from input>",
        "url":  "<exact article URL from input>",
        "angle": "<brief framing note>"
      }
    ],
    "severity": "<critical|high|moderate>"
  }
]

Return [] (empty JSON array) if no qualifying breaking events are found.
"""


class BreakingNewsAgent:
    """Single-call breaking news detector — no tool-use loop, no multi-turn context."""

    def __init__(self) -> None:
        self.client = boto3.client("bedrock-runtime", region_name=BEDROCK_REGION)

    def detect(self, region_summaries: dict[str, dict], date: str) -> list[dict]:
        stories = []
        for region, digest in region_summaries.items():
            for s in digest.get("stories", []):
                if s.get("headline"):
                    stories.append({
                        "headline": s.get("headline", ""),
                        "source":   s.get("source", ""),
                        "url":      s.get("url", ""),
                        "region":   region,
                        "summary":  s.get("summary", "")[:100],
                    })

        prompt = (
            f"Today is {date}. Analyse the {len(stories)} curated stories below "
            f"from {len(region_summaries)} country feeds. "
            "Identify high-impact breaking events, synthesise cross-source coverage, "
            "and return the JSON array.\n\n"
            "Stories:\n" + json.dumps(stories, ensure_ascii=False)
        )

        delay = 60
        response = None
        for attempt in range(4):
            try:
                response = self.client.converse(
                    modelId=BREAKING_MODEL,
                    system=[{"text": _SYSTEM}],
                    messages=[{"role": "user", "content": [{"text": prompt}]}],
                    inferenceConfig={"maxTokens": _MAX_TOKENS},
                )
                break
            except ClientError as exc:
                code = exc.response["Error"]["Code"]
                if code in ("ThrottlingException", "ServiceUnavailableException") and attempt < 3:
                    console.log(
                        f"[yellow][BreakingNewsAgent] throttled — "
                        f"waiting {delay}s (attempt {attempt+1}/4)[/yellow]"
                    )
                    time.sleep(delay)
                    delay = min(delay * 2, 300)
                else:
                    raise

        if response is None:
            return []

        text = ""
        for block in response["output"]["message"]["content"]:
            if "text" in block:
                text = block["text"].strip()
                break

        if text.startswith("```"):
            text = text.split("\n", 1)[-1]
            text = text.rsplit("```", 1)[0].strip()

        try:
            result = json.loads(text)
            if isinstance(result, list):
                return result
        except (json.JSONDecodeError, TypeError):
            console.log("[red][BreakingNewsAgent] JSON parse failed — returning empty list[/red]")
        return []
