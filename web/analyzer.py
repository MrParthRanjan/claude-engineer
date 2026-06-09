"""Deep AI analysis for individual SCMP articles."""

import asyncio
import hashlib
import json
import os
import time
from pathlib import Path
from typing import Dict

# Cache lives at project root — always, regardless of CWD
_PROJECT_ROOT = Path(__file__).parent.parent
CACHE_FILE = _PROJECT_ROOT / ".scmp_analysis_cache.json"

FALLBACK = {
    "tldr": "Analysis unavailable — set ANTHROPIC_API_KEY to enable.",
    "key_points": [],
    "why_it_matters": "",
    "india_asia_impact": "",
    "geopolitical_angle": "",
}

_KEY_ERROR = {
    "tldr": "API key error — check ANTHROPIC_API_KEY in your .env file (should start with sk-ant-).",
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

    # Return cached result immediately if available
    cache = _load_cache()
    key = _cache_key(title)
    if key in cache:
        return cache[key]

    client = anthropic.Anthropic(api_key=api_key)
    prompt = f"""Analyze this South China Morning Post article. Return ONLY a valid JSON object:

{{
  "tldr": "<one crisp sentence — the single most important takeaway>",
  "key_points": ["<point 1>", "<point 2>", "<point 3>"],
  "why_it_matters": "<2-3 sentences on global significance>",
  "india_asia_impact": "<2-3 sentences on impact for India and South/Southeast Asia>",
  "geopolitical_angle": "<2-3 sentences on geopolitical implications>"
}}

Category: {category}
Title: {title}
Context: {description[:600]}

Return ONLY the JSON. No markdown fences, no extra text."""

    max_attempts = 3
    for attempt in range(1, max_attempts + 1):
        try:
            message = client.messages.create(
                model="claude-haiku-4-5-20251001",
                max_tokens=700,
                messages=[{"role": "user", "content": prompt}],
            )
            raw = message.content[0].text.strip()
            if raw.startswith("```"):
                raw = raw[raw.index("{"):raw.rindex("}") + 1]
            result = json.loads(raw)
            cache[key] = result
            _save_cache(cache)
            return result

        except anthropic.AuthenticationError:
            # 401 — key is wrong; don't retry, don't cache, return helpful error
            return _KEY_ERROR

        except (anthropic.RateLimitError, anthropic.InternalServerError) as exc:
            if attempt == max_attempts:
                return FALLBACK
            time.sleep(2 ** (attempt - 1))  # 1s, 2s

        except (json.JSONDecodeError, ValueError):
            # Model returned malformed JSON — not an API problem
            return FALLBACK

        except Exception:
            return FALLBACK

    return FALLBACK


async def deep_analyze_article(title: str, description: str, category: str) -> Dict:
    """Async wrapper — runs blocking anthropic call in a thread pool."""
    return await asyncio.to_thread(_sync_analyze, title, description, category)
