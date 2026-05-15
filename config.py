import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

BASE_DIR      = Path(__file__).parent
DATA_DIR      = BASE_DIR / "data"
RAW_DIR       = DATA_DIR / "raw"
PROCESSED_DIR = DATA_DIR / "processed"
WEB_OUTPUT_DIR = BASE_DIR / "web" / "output"
TEMPLATES_DIR  = BASE_DIR / "web" / "templates"
STATIC_DIR     = BASE_DIR / "web" / "static"

ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")

ORCHESTRATOR_MODEL = "claude-sonnet-4-6"
SUMMARIZER_MODEL   = "claude-sonnet-4-6"
SCRAPER_MODEL      = "claude-haiku-4-5-20251001"
BREAKING_MODEL     = "claude-sonnet-4-6"

# Ordered for display grouping: original 8, Americas, Asia-Pacific, Europe/Eurasia, Middle East, Africa
REGIONS = [
    # Original
    "usa", "uk", "france", "germany", "spain", "japan", "china", "italy",
    # Americas
    "canada", "mexico", "brazil", "costa_rica",
    # Asia-Pacific
    "india", "australia", "taiwan", "singapore", "south_korea",
    # Europe / Eurasia
    "russia", "ukraine", "turkey",
    # Middle East
    "saudi_arabia", "iran", "uae",
    # Africa
    "south_africa", "morocco", "egypt",
]

REGION_META = {
    # Original 8
    "usa":          {"label": "United States",  "flag": "🇺🇸", "lang": "English",          "group": "Original"},
    "uk":           {"label": "United Kingdom", "flag": "🇬🇧", "lang": "English",          "group": "Original"},
    "france":       {"label": "France",         "flag": "🇫🇷", "lang": "French/English",   "group": "Original"},
    "germany":      {"label": "Germany",        "flag": "🇩🇪", "lang": "German/English",   "group": "Original"},
    "spain":        {"label": "Spain",          "flag": "🇪🇸", "lang": "Spanish/English",  "group": "Original"},
    "japan":        {"label": "Japan",          "flag": "🇯🇵", "lang": "English/Japanese", "group": "Original"},
    "china":        {"label": "China",          "flag": "🇨🇳", "lang": "English/Chinese",  "group": "Original"},
    "italy":        {"label": "Italy",          "flag": "🇮🇹", "lang": "Italian/English",  "group": "Original"},
    # Americas
    "canada":       {"label": "Canada",         "flag": "🇨🇦", "lang": "English/French",    "group": "Americas"},
    "mexico":       {"label": "Mexico",         "flag": "🇲🇽", "lang": "Spanish/English",   "group": "Americas"},
    "brazil":       {"label": "Brazil",         "flag": "🇧🇷", "lang": "Portuguese/English", "group": "Americas"},
    "costa_rica":   {"label": "Costa Rica",     "flag": "🇨🇷", "lang": "Spanish/English",   "group": "Americas"},
    # Asia-Pacific
    "india":        {"label": "India",          "flag": "🇮🇳", "lang": "English/Hindi",    "group": "Asia-Pacific"},
    "australia":    {"label": "Australia",      "flag": "🇦🇺", "lang": "English",          "group": "Asia-Pacific"},
    "taiwan":       {"label": "Taiwan",         "flag": "🇹🇼", "lang": "English/Chinese",  "group": "Asia-Pacific"},
    "singapore":    {"label": "Singapore",      "flag": "🇸🇬", "lang": "English",          "group": "Asia-Pacific"},
    "south_korea":  {"label": "South Korea",    "flag": "🇰🇷", "lang": "English/Korean",   "group": "Asia-Pacific"},
    # Europe / Eurasia
    "russia":       {"label": "Russia",         "flag": "🇷🇺", "lang": "English/Russian",  "group": "Europe"},
    "ukraine":      {"label": "Ukraine",        "flag": "🇺🇦", "lang": "English/Ukrainian", "group": "Europe"},
    "turkey":       {"label": "Turkey",         "flag": "🇹🇷", "lang": "Turkish/English",  "group": "Europe"},
    # Middle East
    "saudi_arabia": {"label": "Saudi Arabia",   "flag": "🇸🇦", "lang": "Arabic/English",   "group": "Middle East"},
    "iran":         {"label": "Iran",           "flag": "🇮🇷", "lang": "English/Persian",  "group": "Middle East"},
    "uae":          {"label": "UAE",            "flag": "🇦🇪", "lang": "Arabic/English",   "group": "Middle East"},
    # Africa
    "south_africa": {"label": "South Africa",   "flag": "🇿🇦", "lang": "English",          "group": "Africa"},
    "morocco":      {"label": "Morocco",        "flag": "🇲🇦", "lang": "French/Arabic",    "group": "Africa"},
    "egypt":        {"label": "Egypt",          "flag": "🇪🇬", "lang": "English/Arabic",   "group": "Africa"},
}

REGION_GROUPS = ["Americas", "Asia-Pacific", "Europe", "Middle East", "Africa"]

BREAKING_CATEGORIES = {
    "war_conflict":              {"label": "War & Conflict",          "icon": "⚔️",  "color": "#c0392b"},
    "financial_collapse":        {"label": "Financial Crisis",        "icon": "📉",  "color": "#e67e22"},
    "corporate_crisis":          {"label": "Corporate Crisis",        "icon": "🏦",  "color": "#8e44ad"},
    "transportation_accident":   {"label": "Transportation Accident", "icon": "🚨",  "color": "#2980b9"},
    "law_enforcement_operation": {"label": "Law Enforcement",         "icon": "🚔",  "color": "#16a085"},
    "natural_disaster":          {"label": "Natural Disaster",        "icon": "🌪️",  "color": "#27ae60"},
}

SCHEDULE_HOUR   = int(os.getenv("SCHEDULE_HOUR",   "7"))
SCHEDULE_MINUTE = int(os.getenv("SCHEDULE_MINUTE", "0"))

MAX_ARTICLES_PER_SOURCE = 10
MAX_ARTICLE_CHARS       = 4000
RSS_TIMEOUT             = 15
