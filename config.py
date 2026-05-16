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

BEDROCK_REGION     = os.getenv("BEDROCK_REGION", "us-east-1")

# Amazon Nova models via AWS Bedrock — no Anthropic API key required
ORCHESTRATOR_MODEL = ""  # orchestrator is pure Python, no LLM needed
SUMMARIZER_MODEL   = "us.amazon.nova-lite-v1:0"   # $0.06/MTok in  · $0.24/MTok out
SCRAPER_MODEL      = ""  # scraper is pure RSS/HTTP, no LLM needed
BREAKING_MODEL     = "us.amazon.nova-pro-v1:0"    # $0.80/MTok in  · $3.20/MTok out

# 22 countries — educational scope, cost-optimised
REGIONS = [
    # Americas
    "usa", "canada", "mexico", "costa_rica", "brazil", "argentina",
    # Europe
    "uk", "france", "germany", "spain", "italy", "russia",
    # Asia-Pacific
    "china", "japan", "india", "australia", "south_korea", "taiwan", "singapore",
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
    "argentina":    {"label": "Argentina",      "flag": "🇦🇷", "lang": "Spanish/English",   "group": "Americas"},
    "colombia":     {"label": "Colombia",       "flag": "🇨🇴", "lang": "Spanish/English",   "group": "Americas"},
    "chile":        {"label": "Chile",          "flag": "🇨🇱", "lang": "Spanish/English",   "group": "Americas"},
    "peru":         {"label": "Peru",           "flag": "🇵🇪", "lang": "Spanish/English",   "group": "Americas"},
    # Asia-Pacific
    "india":        {"label": "India",          "flag": "🇮🇳", "lang": "English/Hindi",    "group": "Asia-Pacific"},
    "australia":    {"label": "Australia",      "flag": "🇦🇺", "lang": "English",          "group": "Asia-Pacific"},
    "taiwan":       {"label": "Taiwan",         "flag": "🇹🇼", "lang": "English/Chinese",  "group": "Asia-Pacific"},
    "singapore":    {"label": "Singapore",      "flag": "🇸🇬", "lang": "English",          "group": "Asia-Pacific"},
    "south_korea":  {"label": "South Korea",    "flag": "🇰🇷", "lang": "English/Korean",   "group": "Asia-Pacific"},
    "indonesia":    {"label": "Indonesia",      "flag": "🇮🇩", "lang": "Indonesian/English", "group": "Asia-Pacific"},
    "pakistan":     {"label": "Pakistan",       "flag": "🇵🇰", "lang": "Urdu/English",      "group": "Asia-Pacific"},
    "thailand":     {"label": "Thailand",       "flag": "🇹🇭", "lang": "Thai/English",      "group": "Asia-Pacific"},
    "vietnam":      {"label": "Vietnam",        "flag": "🇻🇳", "lang": "Vietnamese/English", "group": "Asia-Pacific"},
    "malaysia":     {"label": "Malaysia",       "flag": "🇲🇾", "lang": "Malay/English",     "group": "Asia-Pacific"},
    "philippines":  {"label": "Philippines",    "flag": "🇵🇭", "lang": "Filipino/English",  "group": "Asia-Pacific"},
    "bangladesh":   {"label": "Bangladesh",     "flag": "🇧🇩", "lang": "Bengali/English",   "group": "Asia-Pacific"},
    "new_zealand":  {"label": "New Zealand",    "flag": "🇳🇿", "lang": "English",           "group": "Asia-Pacific"},
    # Europe / Eurasia
    "russia":       {"label": "Russia",         "flag": "🇷🇺", "lang": "English/Russian",  "group": "Europe"},
    "ukraine":      {"label": "Ukraine",        "flag": "🇺🇦", "lang": "English/Ukrainian", "group": "Europe"},
    "turkey":       {"label": "Turkey",         "flag": "🇹🇷", "lang": "Turkish/English",  "group": "Europe"},
    "netherlands":  {"label": "Netherlands",    "flag": "🇳🇱", "lang": "Dutch/English",    "group": "Europe"},
    "portugal":     {"label": "Portugal",       "flag": "🇵🇹", "lang": "Portuguese/English", "group": "Europe"},
    "poland":       {"label": "Poland",         "flag": "🇵🇱", "lang": "Polish/English",   "group": "Europe"},
    "sweden":       {"label": "Sweden",         "flag": "🇸🇪", "lang": "Swedish/English",  "group": "Europe"},
    "norway":       {"label": "Norway",         "flag": "🇳🇴", "lang": "Norwegian/English", "group": "Europe"},
    "denmark":      {"label": "Denmark",        "flag": "🇩🇰", "lang": "Danish/English",   "group": "Europe"},
    "switzerland":  {"label": "Switzerland",    "flag": "🇨🇭", "lang": "German/French/English", "group": "Europe"},
    "austria":      {"label": "Austria",        "flag": "🇦🇹", "lang": "German/English",   "group": "Europe"},
    "belgium":      {"label": "Belgium",        "flag": "🇧🇪", "lang": "French/Dutch/English", "group": "Europe"},
    "greece":       {"label": "Greece",         "flag": "🇬🇷", "lang": "Greek/English",    "group": "Europe"},
    # Middle East
    "saudi_arabia": {"label": "Saudi Arabia",   "flag": "🇸🇦", "lang": "Arabic/English",   "group": "Middle East"},
    "iran":         {"label": "Iran",           "flag": "🇮🇷", "lang": "English/Persian",  "group": "Middle East"},
    "uae":          {"label": "UAE",            "flag": "🇦🇪", "lang": "Arabic/English",   "group": "Middle East"},
    "israel":       {"label": "Israel",         "flag": "🇮🇱", "lang": "Hebrew/English",   "group": "Middle East"},
    "iraq":         {"label": "Iraq",           "flag": "🇮🇶", "lang": "Arabic/English",   "group": "Middle East"},
    "qatar":        {"label": "Qatar",          "flag": "🇶🇦", "lang": "Arabic/English",   "group": "Middle East"},
    # Africa
    "south_africa": {"label": "South Africa",   "flag": "🇿🇦", "lang": "English",          "group": "Africa"},
    "morocco":      {"label": "Morocco",        "flag": "🇲🇦", "lang": "French/Arabic",    "group": "Africa"},
    "egypt":        {"label": "Egypt",          "flag": "🇪🇬", "lang": "English/Arabic",   "group": "Africa"},
    "nigeria":      {"label": "Nigeria",        "flag": "🇳🇬", "lang": "English",          "group": "Africa"},
    "kenya":        {"label": "Kenya",          "flag": "🇰🇪", "lang": "English/Swahili",  "group": "Africa"},
    "ethiopia":     {"label": "Ethiopia",       "flag": "🇪🇹", "lang": "Amharic/English",  "group": "Africa"},
    "ghana":        {"label": "Ghana",          "flag": "🇬🇭", "lang": "English",          "group": "Africa"},
    "algeria":      {"label": "Algeria",        "flag": "🇩🇿", "lang": "Arabic/French",    "group": "Africa"},
    "tunisia":      {"label": "Tunisia",        "flag": "🇹🇳", "lang": "Arabic/French",    "group": "Africa"},
}

REGION_GROUPS = ["Americas", "Asia-Pacific", "Europe", "Middle East", "Africa"]

STORY_CATEGORIES = {
    "politics":                {"label": "Politics",                  "icon": "🏛️"},
    "world_news":              {"label": "World News",                "icon": "🌐"},
    "business_economy":        {"label": "Business & Economy",        "icon": "💼"},
    "technology":              {"label": "Technology",                "icon": "💻"},
    "health":                  {"label": "Health",                    "icon": "🏥"},
    "science_environment":     {"label": "Science & Environment",     "icon": "🔬"},
    "crime_safety":            {"label": "Crime & Public Safety",     "icon": "🚔"},
    "entertainment_culture":   {"label": "Entertainment & Culture",   "icon": "🎭"},
    "sports":                  {"label": "Sports",                    "icon": "⚽"},
    "lifestyle":               {"label": "Lifestyle & Human Interest","icon": "🌟"},
    "artificial_intelligence": {"label": "Artificial Intelligence",   "icon": "🤖"},
    "wall_street":             {"label": "Wall Street",               "icon": "📈"},
    "silicon_valley":          {"label": "Silicon Valley",            "icon": "🏔️"},
    "social_networks":         {"label": "Social Networks",           "icon": "📱"},
    "global_warming":          {"label": "Global Warming",            "icon": "🌡️"},
    "cost_of_living":          {"label": "Cost of Living",            "icon": "💸"},
    "employment":              {"label": "Employment & Work",         "icon": "👷"},
    "gender_equity":           {"label": "Gender Equity",             "icon": "⚖️"},
    "pets_animals":            {"label": "Pets & Animal Kingdom",     "icon": "🐾"},
    "music_movies":            {"label": "Music & Movies",            "icon": "🎬"},
}

BREAKING_CATEGORIES = {
    "war_conflict":              {"label": "War & Conflict",          "icon": "⚔️",  "color": "#c0392b"},
    "financial_collapse":        {"label": "Financial Crisis",        "icon": "📉",  "color": "#e67e22"},
    "corporate_crisis":          {"label": "Corporate Crisis",        "icon": "🏦",  "color": "#8e44ad"},
    "transportation_accident":   {"label": "Transportation Accident", "icon": "🚨",  "color": "#2980b9"},
    "law_enforcement_operation": {"label": "Law Enforcement",         "icon": "🚔",  "color": "#16a085"},
    "natural_disaster":          {"label": "Natural Disaster",        "icon": "🌪️",  "color": "#27ae60"},
}

SCHEDULE_TIMES = [(7, 15)]  # (hour, minute) UTC — single daily run

# When set, output is copied here locally instead of rsynced over SSH.
# Use on the EC2 itself: DEPLOY_LOCAL_DIR=/var/www/forwardforecasting/newssummary
DEPLOY_LOCAL_DIR = os.getenv("DEPLOY_LOCAL_DIR", "")

MAX_ARTICLES_PER_SOURCE = 5
MAX_ARTICLE_CHARS       = 1500
RSS_TIMEOUT             = 15
