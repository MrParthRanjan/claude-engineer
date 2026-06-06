#!/usr/bin/env python3
"""
SCMP Daily Reader — main entry point.

Usage:
    python -m scmp_daily            # Full digest (uses cache if available)
    python -m scmp_daily --refresh  # Force fresh fetch
    python -m scmp_daily --brief    # One-line-per-headline compact view
    python -m scmp_daily --no-ai    # Skip AI summaries (faster)
"""

import argparse
import os
import sys

from dotenv import load_dotenv
from loguru import logger

# Silence verbose loguru output for normal runs
logger.remove()
logger.add(sys.stderr, level="WARNING")


def main() -> None:
    load_dotenv()

    parser = argparse.ArgumentParser(description="SCMP Daily Digest in your terminal")
    parser.add_argument("--refresh", action="store_true", help="Bypass cache and re-fetch all feeds")
    parser.add_argument("--brief",   action="store_true", help="One-line compact headline view")
    parser.add_argument("--no-ai",   action="store_true", help="Skip Claude AI summaries")
    args = parser.parse_args()

    # Local imports after dotenv is loaded
    from scmp_daily.config import CONFIG
    from scmp_daily.fetcher import get_articles, load_cache
    from scmp_daily.summarizer import summarize_all
    from scmp_daily.display import render, render_brief, console

    if args.no_ai:
        CONFIG.enable_ai_summary = False

    # Determine data source label
    cached = load_cache()
    source = "cached" if (cached and not args.refresh) else "live"

    console.print("[dim]Fetching SCMP feeds...[/dim]") if source == "live" else None

    data = get_articles(force_refresh=args.refresh)

    if not data:
        console.print("[bold red]Could not fetch any SCMP articles. Check your network.[/bold red]")
        sys.exit(1)

    # Only run AI summary when data is freshly fetched (not cached with summaries)
    if CONFIG.enable_ai_summary and os.getenv("ANTHROPIC_API_KEY"):
        first_cat = next(iter(data.values()), [])
        needs_summary = first_cat and not first_cat[0].ai_summary
        if needs_summary:
            from scmp_daily.fetcher import save_cache
            console.print("[dim]Generating AI summaries...[/dim]")
            data = summarize_all(data)
            save_cache(data)  # persist with summaries so cache reuse includes them

    if args.brief:
        render_brief(data)
    else:
        render(data, source=source)


if __name__ == "__main__":
    main()
