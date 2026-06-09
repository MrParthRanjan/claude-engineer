"""SCMP Daily Reader — Claude AI Summarizer"""

import os
import time
from typing import Dict, List, Optional

import anthropic
from loguru import logger

from .config import CONFIG
from .fetcher import Article


def _build_prompt(articles: List[Article], category: str) -> str:
    lines = [
        f"You are summarizing {category} news from South China Morning Post.\n",
        "For each article write:",
        "  [N]. <2-sentence crisp summary in plain English>",
        "  > <one punchy crux — the single most important takeaway, max 12 words>\n",
        "Example:",
        "  [1]. China and the US agreed to a 90-day tariff pause. Talks resume in Geneva.",
        "  > Trade war paused — both sides blink first.\n",
    ]
    for i, a in enumerate(articles, 1):
        lines.append(f"[{i}] TITLE: {a.title}")
        if a.description:
            lines.append(f"    SNIPPET: {a.description[:500]}")
        if a.full_text:
            lines.append(f"    BODY: {a.full_text[:800]}")
        lines.append("")
    return "\n".join(lines)


def _parse_response(raw: str, articles: List[Article]) -> List[Article]:
    summaries: Dict[int, str] = {}
    cruxes: Dict[int, str] = {}
    current_idx: Optional[int] = None
    current_lines: List[str] = []

    for line in raw.splitlines():
        line = line.strip()
        if not line:
            continue
        if line.startswith("[") and "]" in line[:4]:
            if current_idx is not None:
                summaries[current_idx] = " ".join(current_lines).strip()
            bracket_end = line.index("]")
            try:
                current_idx = int(line[1:bracket_end])
            except ValueError:
                current_idx = None
                current_lines = []
                continue
            rest = line[bracket_end + 1:].lstrip(". ").strip()
            current_lines = [rest] if rest else []
        elif line.startswith(">") and current_idx is not None:
            cruxes[current_idx] = line[1:].strip()
        else:
            if current_idx is not None:
                current_lines.append(line)

    if current_idx is not None:
        summaries[current_idx] = " ".join(current_lines).strip()

    for i, article in enumerate(articles, 1):
        if i in summaries:
            article.ai_summary = summaries[i]
        if i in cruxes:
            article.crux = cruxes[i]

    return articles


def summarize_category(articles: List[Article], category: str) -> List[Article]:
    """Add AI summaries and crux to a list of articles in one API call.

    Errors:
    - AuthenticationError (401): logged as ERROR, not retried — key is wrong.
    - RateLimitError / InternalServerError: retried up to 3× with backoff.
    - Other API errors: logged as WARNING, no retry.
    """
    if not articles:
        return articles

    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        logger.warning(f"[{category}] ANTHROPIC_API_KEY not set — skipping AI summaries")
        return articles

    client = anthropic.Anthropic(api_key=api_key)
    prompt = _build_prompt(articles, category)
    max_attempts = 3

    for attempt in range(1, max_attempts + 1):
        try:
            message = client.messages.create(
                model=CONFIG.claude_model,
                max_tokens=1200,
                messages=[{"role": "user", "content": prompt}],
            )
            raw = message.content[0].text.strip()
            return _parse_response(raw, articles)

        except anthropic.AuthenticationError as exc:
            # 401 — key is definitively wrong; retrying won't help
            logger.error(
                f"[{category}] Anthropic 401 — INVALID API KEY. "
                f"Check ANTHROPIC_API_KEY in your .env file. ({exc})"
            )
            return articles  # return without summaries; don't retry

        except (anthropic.RateLimitError, anthropic.InternalServerError) as exc:
            # Transient — backoff and retry
            if attempt == max_attempts:
                logger.warning(f"[{category}] Transient error after {max_attempts} attempts: {exc}")
                return articles
            wait = 2 ** (attempt - 1)  # 1s, 2s
            logger.warning(
                f"[{category}] Transient error (attempt {attempt}/{max_attempts}), "
                f"retrying in {wait}s: {exc}"
            )
            time.sleep(wait)

        except anthropic.APIStatusError as exc:
            # Other 4xx / 5xx — log and bail
            logger.warning(f"[{category}] API error {exc.status_code}: {exc.message}")
            return articles

        except Exception as exc:
            logger.warning(f"[{category}] Unexpected summarizer error: {exc}")
            return articles

    return articles  # unreachable but satisfies type checker


def summarize_all(data: Dict[str, List[Article]]) -> Dict[str, List[Article]]:
    """Run AI summarization for every category."""
    if not CONFIG.enable_ai_summary:
        return data
    result = {}
    for cat, articles in data.items():
        result[cat] = summarize_category(articles, cat)
    return result
