"""AI News tab pipeline: refreshes the blog summaries every day and the papers digest once a month.

Runs inside the daily news pipeline (main.py), so the tab needs no schedule of its own:
  - blogs: BlogAgent reads each curated blog's RSS/Atom feed and has Amazon Nova Lite summarise the
    last 7 days of posts (data/ai_news_blogs.json).
  - papers: when the digest for the last completed month is missing, PaperAgent pulls the month's
    most-cited candidates from Semantic Scholar, has Nova Lite keep only foundational AI research
    (not applied use-cases) and summarise the top 5 (data/ai_news_papers_YYYY-MM.json). Older months
    stay available through the month picker (data/ai_news_months.json).
Any failure keeps the previous data, so the tab and the news site are never broken by it.
"""
from __future__ import annotations

import json
from datetime import date, timedelta
from pathlib import Path

from rich.console import Console

from ai_news.config import BLOGS

console = Console()


def _data_dir(output_dir: Path) -> Path:
    d = output_dir / "data"
    d.mkdir(parents=True, exist_ok=True)
    return d


def last_completed_month(today: date | None = None) -> str:
    end = (today or date.today()).replace(day=1) - timedelta(days=1)
    return f"{end.year}-{end.month:02d}"


def save_digest(output_dir: Path, digest: dict) -> None:
    key = f"{digest['year']}-{digest['month']:02d}"
    (_data_dir(output_dir) / f"ai_news_papers_{key}.json").write_text(
        json.dumps(digest, ensure_ascii=False, indent=2), encoding="utf-8")
    write_months_manifest(output_dir)


def write_months_manifest(output_dir: Path) -> None:
    data = _data_dir(output_dir)
    months = []
    for f in sorted(data.glob("ai_news_papers_*.json"), reverse=True):
        key = f.stem[len("ai_news_papers_"):]
        label = json.loads(f.read_text(encoding="utf-8")).get("month_label", key)
        months.append({"key": key, "label": label, "path": f"data/{f.name}"})
    (data / "ai_news_months.json").write_text(json.dumps(months, ensure_ascii=False), encoding="utf-8")


def refresh(output_dir: Path, blogs: bool = True, papers: bool = True) -> None:
    data = _data_dir(output_dir)
    if blogs:
        try:
            from ai_news.blog_agent import BlogAgent
            result = BlogAgent().build_blog_digest()
            (data / "ai_news_blogs.json").write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
            console.log(f"[green]✓ AI News: blog summaries for {len(result)} blogs[/green]")
        except Exception as e:
            console.print(f"[yellow]AI News blogs skipped: {type(e).__name__}: {e}[/yellow]")
    month = last_completed_month()
    if papers and not (data / f"ai_news_papers_{month}.json").exists():
        try:
            from ai_news.paper_agent import PaperAgent
            digest = PaperAgent().build_monthly_digest()
            save_digest(output_dir, digest)
            console.log(f"[green]✓ AI News: papers digest for {digest['month_label']}[/green]")
        except Exception as e:
            console.print(f"[yellow]AI News papers skipped: {type(e).__name__}: {e}[/yellow]")


def load(output_dir: Path) -> dict | None:
    """What the tab renders: blogs, the latest papers digest and the list of months."""
    data = output_dir / "data"
    blogs_file = data / "ai_news_blogs.json"
    blogs = json.loads(blogs_file.read_text(encoding="utf-8")) if blogs_file.exists() else BLOGS
    months_file = data / "ai_news_months.json"
    months = json.loads(months_file.read_text(encoding="utf-8")) if months_file.exists() else []
    digest = None
    if months:
        p = data / Path(months[0]["path"]).name
        if p.exists():
            digest = json.loads(p.read_text(encoding="utf-8"))
    if not blogs_file.exists() and digest is None:
        return None
    return {"blogs": blogs, "digest": digest, "months": months}
