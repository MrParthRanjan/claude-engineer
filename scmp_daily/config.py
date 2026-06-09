"""SCMP Daily Reader — Configuration"""

from dataclasses import dataclass, field
from typing import Dict

@dataclass
class SCMPConfig:
    # Primary: SCMP's own RSS feeds (works on home/office networks)
    # Fallback: Google News RSS aggregates SCMP articles (no auth needed)
    feeds: Dict[str, str] = field(default_factory=lambda: {
        "Top Stories": "https://www.scmp.com/rss/91/feed",
        "Hong Kong":   "https://www.scmp.com/rss/2/feed",
        "China":       "https://www.scmp.com/rss/4/feed",
        "Asia":        "https://www.scmp.com/rss/3/feed",
        "World":       "https://www.scmp.com/rss/5/feed",
        "Business":    "https://www.scmp.com/rss/92/feed",
        "Technology":  "https://www.scmp.com/rss/36/feed",
    })

    # Google News fallback (used when SCMP RSS returns non-200)
    fallback_feeds: Dict[str, str] = field(default_factory=lambda: {
        "Top Stories": "https://news.google.com/rss/search?q=site:scmp.com&hl=en-US&gl=US&ceid=US:en",
        "Hong Kong":   "https://news.google.com/rss/search?q=site:scmp.com+%22hong+kong%22&hl=en-US&gl=US&ceid=US:en",
        "China":       "https://news.google.com/rss/search?q=site:scmp.com+china&hl=en-US&gl=US&ceid=US:en",
        "Asia":        "https://news.google.com/rss/search?q=site:scmp.com+asia&hl=en-US&gl=US&ceid=US:en",
        "World":       "https://news.google.com/rss/search?q=site:scmp.com+world&hl=en-US&gl=US&ceid=US:en",
        "Business":    "https://news.google.com/rss/search?q=site:scmp.com+business&hl=en-US&gl=US&ceid=US:en",
        "Technology":  "https://news.google.com/rss/search?q=site:scmp.com+technology&hl=en-US&gl=US&ceid=US:en",
    })

    # How many articles to show per category
    articles_per_category: int = 5

    # Use Claude AI for summaries
    enable_ai_summary: bool = True

    # Claude model for summaries
    claude_model: str = "claude-haiku-4-5-20251001"

    # Cache file path (avoids re-fetching same day)
    cache_file: str = ".scmp_cache.json"

    # Request timeout in seconds
    request_timeout: int = 15

    # Category display order
    display_order: list = field(default_factory=lambda: [
        "Top Stories", "Hong Kong", "China", "Asia",
        "World", "Business", "Technology"
    ])

    # Category color codes for rich terminal
    category_colors: Dict[str, str] = field(default_factory=lambda: {
        "Top Stories": "bold red",
        "Hong Kong":   "bold yellow",
        "China":       "bold red1",
        "Asia":        "bold orange3",
        "World":       "bold cyan",
        "Business":    "bold green",
        "Technology":  "bold blue",
    })


CONFIG = SCMPConfig()
