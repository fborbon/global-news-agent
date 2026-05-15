#!/usr/bin/env python3
"""
News Intelligence Agent — main entry point.

Usage:
  python main.py          # Run once immediately, then start daily scheduler
  python main.py --now    # Run once immediately and exit
  python main.py --demo   # Run with mock data (no API calls) to preview the site
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import date
from pathlib import Path

from rich.console import Console
from rich.panel import Panel

from config import ANTHROPIC_API_KEY, SCHEDULE_HOUR, SCHEDULE_MINUTE, WEB_OUTPUT_DIR
from agents.orchestrator import OrchestratorAgent
from web.generator import WebGenerator

_DEPLOY_KEY  = Path.home() / ".ssh" / "forwardforecasting.pem"
_DEPLOY_DEST = "ubuntu@54.78.82.101:/var/www/forwardforecasting/newssummary/"


def _deploy() -> None:
    if not _DEPLOY_KEY.exists():
        console.print("[yellow]Deploy skipped — SSH key not found.[/yellow]")
        return
    result = subprocess.run(
        [
            "rsync", "-az", "--delete",
            "-e", f"ssh -o StrictHostKeyChecking=no -i {_DEPLOY_KEY}",
            f"{WEB_OUTPUT_DIR}/",
            _DEPLOY_DEST,
        ],
        capture_output=True, text=True,
    )
    if result.returncode == 0:
        console.print("[green]✓ Deployed → forwardforecasting.eu/newssummary/[/green]")
    else:
        console.print(f"[yellow]Deploy warning:[/yellow] {result.stderr.strip()}")

console = Console()


# ── Demo / mock data ──────────────────────────────────────────────────────────

def _load_demo_data() -> tuple[dict, list]:
    """Return lightweight mock data so the site can be previewed without API calls."""
    today = date.today().isoformat()
    region_summaries = {
        "usa": {
            "region": "usa", "date": today,
            "overview": "The US Congress passed a new infrastructure bill while the Federal Reserve held interest rates steady. Tech earnings season kicked off with mixed results.",
            "stories": [
                {"headline": "Congress Passes Infrastructure Bill", "source": "AP News", "url": "#", "summary": "The bipartisan bill allocates $1.2 trillion toward roads, bridges, and broadband.", "category": "politics"},
                {"headline": "Fed Holds Rates Steady", "source": "NPR", "url": "#", "summary": "The Federal Reserve voted unanimously to maintain current interest rates amid cooling inflation.", "category": "economy"},
                {"headline": "Tech Giants Post Mixed Q1 Results", "source": "Washington Post", "url": "#", "summary": "Major technology companies reported quarterly earnings with diverging results across sectors.", "category": "technology"},
            ],
        },
        "uk": {
            "region": "uk", "date": today,
            "overview": "The UK government announced new climate commitments ahead of a G7 summit. Health service reforms dominated parliamentary debate.",
            "stories": [
                {"headline": "UK Sets Net-Zero Targets for 2040", "source": "BBC News", "url": "#", "summary": "The government pledged accelerated decarbonisation across transport and energy sectors.", "category": "environment"},
                {"headline": "NHS Reform Bill Passes Second Reading", "source": "The Guardian", "url": "#", "summary": "MPs voted in favour of the NHS Modernisation Bill with amendments on funding timelines.", "category": "health"},
            ],
        },
        "france": {
            "region": "france", "date": today,
            "overview": "France held regional elections with historic turnout. The government announced new economic stimulus measures.",
            "stories": [
                {"headline": "Regional Elections Show Shift in Voter Patterns", "source": "Le Monde", "url": "#", "summary": "Turnout reached a decade high as centrist and green parties gained ground across metropolitan areas.", "category": "politics"},
                {"headline": "France Announces €40bn Stimulus Plan", "source": "France 24", "url": "#", "summary": "The package targets industrial reindustrialisation and renewable energy investments.", "category": "economy"},
            ],
        },
        "germany": {
            "region": "germany", "date": today,
            "overview": "Germany's coalition government faced a budget vote while automotive exports hit a three-year high.",
            "stories": [
                {"headline": "Bundestag Approves Coalition Budget", "source": "Deutsche Welle", "url": "#", "summary": "The budget passed with a slim majority, allocating record spending on defence and digital infrastructure.", "category": "politics"},
                {"headline": "German Auto Exports at Three-Year High", "source": "Der Spiegel", "url": "#", "summary": "Electric vehicle exports drove the surge, with demand growing strongly in Asia and North America.", "category": "economy"},
            ],
        },
        "spain": {
            "region": "spain", "date": today,
            "overview": "Spain's tourism sector posted record spring numbers while wildfire warnings were issued across the south.",
            "stories": [
                {"headline": "Spring Tourism Breaks Records in Spain", "source": "El País", "url": "#", "summary": "Arrivals exceeded pre-pandemic levels by 12%, with strong growth from US and Asian markets.", "category": "economy"},
                {"headline": "Wildfire Alert Issued for Southern Regions", "source": "El Mundo", "url": "#", "summary": "Authorities placed Andalucía and Murcia on high alert as temperatures soared above seasonal averages.", "category": "environment"},
            ],
        },
        "japan": {
            "region": "japan", "date": today,
            "overview": "Japan's central bank signalled a gradual shift in monetary policy. A magnitude 5.8 earthquake struck northern Honshu.",
            "stories": [
                {"headline": "Bank of Japan Signals Rate Path Adjustment", "source": "Japan Times", "url": "#", "summary": "Officials indicated a cautious move away from ultra-loose policy as inflation edges above the 2% target.", "category": "economy"},
                {"headline": "Earthquake Strikes Northern Honshu", "source": "NHK World", "url": "#", "summary": "The 5.8-magnitude quake caused minor damage; no tsunami warning was issued.", "category": "other"},
            ],
        },
        "china": {
            "region": "china", "date": today,
            "overview": "China's trade surplus widened as exports accelerated. Diplomatic talks with Southeast Asian neighbours resumed.",
            "stories": [
                {"headline": "China Trade Surplus Widens in April", "source": "South China Morning Post", "url": "#", "summary": "Exports grew 8.5% year-on-year driven by electronics and electric vehicles.", "category": "economy"},
                {"headline": "ASEAN Diplomatic Talks Resume in Beijing", "source": "China Daily", "url": "#", "summary": "Representatives from six nations met to discuss maritime safety and trade route frameworks.", "category": "politics"},
            ],
        },
        "italy": {
            "region": "italy", "date": today,
            "overview": "Italy's government secured EU approval for recovery funds. Mount Etna registered increased volcanic activity.",
            "stories": [
                {"headline": "EU Approves Italy's Recovery Plan Tranche", "source": "ANSA", "url": "#", "summary": "Brussels released €18bn in recovery funds tied to judicial and public administration reforms.", "category": "politics"},
                {"headline": "Etna Volcanic Activity Increases", "source": "La Repubblica", "url": "#", "summary": "Authorities issued aviation warnings and restricted access within a 5km radius of the crater.", "category": "environment"},
            ],
        },
    }
    breaking_events = [
        {
            "id": "demo-earthquake-japan",
            "category": "natural_disaster",
            "title": "Magnitude 5.8 Earthquake Strikes Northern Japan",
            "summary": "A 5.8-magnitude earthquake struck Aomori Prefecture in northern Japan early Tuesday. Minor structural damage was reported in two villages; no tsunami warning was issued. Around 12,000 residents were advised to stay indoors as aftershock surveys began.",
            "analysis": "Japanese domestic outlets (NHK) focused on preparedness and community resilience, while international sources (Reuters, AP) emphasised seismic patterns and regional disaster risk.",
            "sources": [
                {"name": "NHK World", "url": "#", "angle": "Localised community impact and emergency response"},
                {"name": "Japan Times", "url": "#", "angle": "Seismic data and aftershock risk assessment"},
                {"name": "Reuters", "url": "#", "angle": "International situational overview"},
            ],
            "severity": "moderate",
        },
        {
            "id": "demo-etna-eruption",
            "category": "natural_disaster",
            "title": "Mount Etna Eruption Disrupts Sicilian Airspace",
            "summary": "Mount Etna on Sicily entered a new eruptive phase overnight, sending ash columns up to 5,000 metres. Catania airport suspended flights for six hours. Italian civil protection agencies deployed teams to monitor lava flows on the volcano's eastern flank.",
            "analysis": "Italian media focused on aviation disruption and tourist access, while European outlets highlighted climate-linked volcanic activity research.",
            "sources": [
                {"name": "ANSA", "url": "#", "angle": "Airport closures and civil protection response"},
                {"name": "La Repubblica", "url": "#", "angle": "Tourism impact and local community"},
                {"name": "BBC News", "url": "#", "angle": "European aviation network effects"},
            ],
            "severity": "high",
        },
    ]
    return region_summaries, breaking_events


# ── Pipeline runner ───────────────────────────────────────────────────────────

def run_pipeline(resume: bool = False) -> None:
    """Execute the full multi-agent pipeline and generate the static site."""
    console.print(Panel.fit(
        "[bold cyan]News Intelligence Agent[/bold cyan]\n"
        "Multi-source · Multi-region · AI-powered",
        border_style="cyan",
    ))

    if not ANTHROPIC_API_KEY:
        console.print("[red]ERROR: ANTHROPIC_API_KEY not set. Copy .env.example → .env and add your key.[/red]")
        sys.exit(1)

    orchestrator = OrchestratorAgent()
    pipeline_result = orchestrator.run_pipeline(resume=resume)

    generator = WebGenerator()
    generator.generate(
        region_summaries=pipeline_result["region_summaries"],
        breaking_events=pipeline_result["breaking_events"],
        today=pipeline_result["date"],
    )

    console.print(Panel.fit(
        f"[green]✓ Pipeline complete[/green]\n"
        f"Regions: {len(pipeline_result['region_summaries'])} | "
        f"Breaking: {len(pipeline_result['breaking_events'])} events\n"
        f"[dim]Site → web/output/index.html[/dim]",
        border_style="green",
    ))
    _deploy()


def run_demo() -> None:
    """Generate the site with mock data — no API calls required."""
    console.print(Panel.fit(
        "[bold yellow]Demo Mode[/bold yellow] — mock data, no API calls",
        border_style="yellow",
    ))
    today = date.today().isoformat()
    region_summaries, breaking_events = _load_demo_data()
    generator = WebGenerator()
    generator.generate(region_summaries=region_summaries, breaking_events=breaking_events, today=today)
    console.print(f"[green]✓ Demo site ready → web/output/index.html[/green]")
    _deploy()


# ── CLI ───────────────────────────────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser(description="News Intelligence Agent")
    parser.add_argument("--now",    action="store_true", help="Run once and exit")
    parser.add_argument("--resume", action="store_true", help="Skip completed regions, only redo missing steps")
    parser.add_argument("--demo",   action="store_true", help="Run with mock data (no API calls)")
    args = parser.parse_args()

    if args.demo:
        run_demo()
        return

    if args.now or args.resume:
        run_pipeline(resume=args.resume)
        return

    # Default: run immediately, then start daily scheduler
    run_pipeline()
    from scheduler import start_scheduler
    start_scheduler(run_pipeline)


if __name__ == "__main__":
    main()
