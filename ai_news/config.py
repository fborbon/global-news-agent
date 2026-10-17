"""AI News tab: curated AI blogs with a weekly AI summary, and the month's most-cited foundational
AI papers. Folded in from the former stand-alone AI News Hub (2026-10-18); its agents keep their own
model settings: Amazon Nova Lite through Bedrock's EU cross-region profile."""
import os

# own variable: the news pipeline's BEDROCK_REGION may point elsewhere; these agents use the EU profile
BEDROCK_REGION = os.getenv("AI_NEWS_BEDROCK_REGION", "eu-west-1")

# Amazon Nova via AWS Bedrock — no Anthropic API key required
PAPER_MODEL = "eu.amazon.nova-lite-v1:0"   # $0.06/MTok in · $0.24/MTok out — EU cross-region profile
BLOG_MODEL  = PAPER_MODEL

# ── Tab 1 — curated AI blogs ────────────────────────────────────────────────
# "rss": None means no feed could be found for that blog — the weekly summary
# is skipped and the card just links out, no fabricated content.
BLOGS = [
    {
        "name": "Simon Willison",
        "url": "https://simonwillison.net/",
        "best_for": "LLMs, agents, MCP, coding, practical experiments",
        "rss": "https://simonwillison.net/atom/everything/",
    },
    {
        "name": "Chip Huyen",
        "url": "https://huyenchip.com/",
        "best_for": "AI engineering, production ML, LLM systems",
        "rss": "https://huyenchip.com/feed.xml",
    },
    {
        "name": "Sebastian Raschka / Ahead of AI",
        "url": "https://sebastianraschka.com/",
        "best_for": "LLM architecture, training, fine-tuning, PyTorch",
        "rss": "https://sebastianraschka.com/rss_feed.xml",
    },
    {
        "name": "Lilian Weng / Lil'Log",
        "url": "https://lilianweng.github.io/",
        "best_for": "Agents, RL, LLMs, deep research explanations",
        "rss": "https://lilianweng.github.io/index.xml",
    },
    {
        "name": "Eugene Yan",
        "url": "https://eugeneyan.com/",
        "best_for": "Applied AI/ML, recommendation systems, production",
        "rss": "https://eugeneyan.com/rss/",
    },
    {
        "name": "Hamel Husain",
        "url": "https://hamel.dev/",
        "best_for": "LLM evaluation, AI engineering, practical systems",
        "rss": "https://hamel.dev/index.xml",
    },
    {
        "name": "Hugging Face Blog",
        "url": "https://huggingface.co/blog",
        "best_for": "Open-source models, fine-tuning, transformers",
        "rss": "https://huggingface.co/blog/feed.xml",
    },
    {
        "name": "Latent Space",
        "url": "https://www.latent.space/",
        "best_for": "AI engineering, agents, startups, frontier tooling",
        "rss": "https://www.latent.space/feed",
    },
    {
        "name": "Google DeepMind Blog",
        "url": "https://deepmind.google/discover/blog/",
        "best_for": "Frontier research",
        "rss": "https://deepmind.google/blog/rss.xml",
    },
    {
        "name": "Anthropic Research",
        "url": "https://www.anthropic.com/research",
        "best_for": "LLM research, agents, interpretability, safety",
        "rss": None,   # No RSS/Atom feed published for this site
    },
    {
        "name": "OpenAI Research",
        "url": "https://openai.com/research/",
        "best_for": "Frontier models and research",
        "rss": "https://openai.com/news/rss.xml",   # broader news feed; no research-only feed exists
    },
    {
        "name": "NVIDIA Technical Blog",
        "url": "https://developer.nvidia.com/blog/",
        "best_for": "GPUs, inference, CUDA, AI infrastructure",
        "rss": "https://developer.nvidia.com/blog/feed",
    },
    {
        "name": "The Batch (DeepLearning.AI)",
        "url": "https://www.deeplearning.ai/the-batch/",
        "best_for": "Weekly AI news, research highlights, industry trends",
        "rss": "https://charonhub.deeplearning.ai/rss/",   # Ghost backend behind the-batch; the www site publishes no feed
    },
]

BLOG_SUMMARY_DAYS       = 7
BLOG_SUMMARY_MAX_CHARS  = 500
BLOG_FALLBACK_POSTS     = 3   # when nothing published in BLOG_SUMMARY_DAYS, summarise the last N posts instead

# ── Tab 2 — top cited AI papers of the month ────────────────────────────────
SEMANTIC_SCHOLAR_API = "https://api.semanticscholar.org/graph/v1/paper/search/bulk"
PAPER_QUERY = (
    "artificial intelligence | large language model | machine learning | "
    "deep learning | neural network | generative AI | reinforcement learning"
)
PAPER_FIELDS_OF_STUDY = "Computer Science"
TOP_PAPERS_PER_MONTH = 5
# Semantic Scholar's query matching is fuzzy (keyword filtering alone can't
# reliably tell "paper about transformers" from "paper that uses a transformer
# to solve X"), so this is a broad recall query — precision comes from Nova
# classifying is_core vs. applied on the top-cited candidates (see PaperAgent).
PAPER_CLASSIFY_POOL = 25   # top-cited-with-abstract candidates sent to Nova for is_core classification
