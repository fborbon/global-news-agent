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
    TEMPLATES_DIR,
    WEB_OUTPUT_DIR,
    STATIC_DIR,
)

console = Console()

# Common template context passed to every page
_BASE_CTX = dict(region_meta=REGION_META, breaking_categories=BREAKING_CATEGORIES)


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
        self._copy_static()
        self._render_index(region_summaries, breaking_events, today)
        for region, digest in region_summaries.items():
            self._render_region(region, digest, today)
        self._render_breaking(breaking_events, today)
        self._save_json(region_summaries, breaking_events, today)
        self._save_archive_index(today)
        self._save_dates_manifest(today)
        console.log(f"[green]✓ Site generated → {self.out}[/green]")

    # ------------------------------------------------------------------
    # Page renderers
    # ------------------------------------------------------------------

    def _render_index(self, summaries: dict, breaking: list, today: str) -> None:
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

    def _save_json(self, summaries: dict, breaking: list, today: str) -> None:
        data_dir = self.out / "data"
        data_dir.mkdir(exist_ok=True)
        (data_dir / f"summaries_{today}.json").write_text(
            json.dumps(summaries, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        (data_dir / f"breaking_{today}.json").write_text(
            json.dumps(breaking, ensure_ascii=False, indent=2), encoding="utf-8"
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
