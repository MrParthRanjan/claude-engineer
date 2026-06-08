"""Deep AI analysis for individual SCMP articles."""

import asyncio
import hashlib
import json
import os
from pathlib import Path
from typing import Dict

CACHE_FILE = Path(".scmp_analysis_cache.json")

FALLBACK = {
    "tldr": "Analysis unavailable — set ANTHROPIC_API_KEY to enable.",
    "key_points": [],
    "why_it_matters": "",
    "india_asia_impact": "",
    "geopolitical_angle": "",
}


def _cache_key(title: str) -> str:
    return hashlib.md5(title.encode()).hexdigest()


def _load_cache() -> dict:
    try:
        return json.loads(CACHE_FILE.read_text())
    except (FileNotFoundError, json.JSONDecodeError):
        return {}


def _save_cache(cache: dict) -> None:
    CACHE_FILE.write_text(json.dumps(cache, indent=2))


def _sync_analyze(title: str, description: str, category: str) -> Dict:
    import anthropic

    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        return FALLBACK

    cache = _load_cache()
    key = _cache_key(title)
    if key in cache:
        return cache[key]

    client = anthropic.Anthropic(api_key=api_key)
    prompt = f"""Analyze this South China Morning Post article. Return ONLY a valid JSON object with these exact keys:

{{
  "tldr": "<one crisp sentence — the single most important takeaway>",
  "key_points": ["<point 1>", "<point 2>", "<point 3>"],
  "why_it_matters": "<2-3 sentences on global significance>",
  "india_asia_impact": "<2-3 sentences on impact for India and South/Southeast Asia>",
  "geopolitical_angle": "<2-3 sentences on geopolitical implications>"
}}

Article:
Category: {category}
Title: {title}
Context: {description[:600]}

Return ONLY the JSON object. No markdown fences, no extra text."""

    try:
        message = client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=700,
            messages=[{"role": "user", "content": prompt}],
        )
        raw = message.content[0].text.strip()
        # Strip markdown code fences if model adds them
        if raw.startswith("```"):
            raw = raw[raw.index("{") : raw.rindex("}") + 1]
        result = json.loads(raw)

        cache[key] = result
        _save_cache(cache)
        return result
    except Exception:
        return FALLBACK


async def deep_analyze_article(title: str, description: str, category: str) -> Dict:
    """Async wrapper — runs sync anthropic call in a thread pool."""
    return await asyncio.to_thread(_sync_analyze, title, description, category)
