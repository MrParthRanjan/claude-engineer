"""SCMP Daily Reader — Claude AI Summarizer"""

import os
from typing import Dict, List

import anthropic
from loguru import logger

from .config import CONFIG
from .fetcher import Article


def _build_prompt(articles: List[Article], category: str) -> str:
    lines = [f"You are summarizing {category} news from South China Morning Post.\n"]
    lines.append("For each article below write a 2-sentence crisp summary in plain English.")
    lines.append("Format: [N]. <2-sentence summary>\n")
    for i, a in enumerate(articles, 1):
        lines.append(f"[{i}] TITLE: {a.title}")
        if a.description:
            lines.append(f"    SNIPPET: {a.description[:500]}")
        if a.full_text:
            lines.append(f"    BODY: {a.full_text[:800]}")
        lines.append("")
    return "\n".join(lines)


def summarize_category(articles: List[Article], category: str) -> List[Article]:
    """Add AI summaries to a list of articles in one API call."""
    if not articles:
        return articles

    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        logger.warning("ANTHROPIC_API_KEY not set — skipping AI summaries.")
        return articles

    client = anthropic.Anthropic(api_key=api_key)
    prompt = _build_prompt(articles, category)

    try:
        message = client.messages.create(
            model=CONFIG.claude_model,
            max_tokens=1024,
            messages=[{"role": "user", "content": prompt}],
        )
        raw = message.content[0].text.strip()
        # Parse "[N]. <summary>" lines
        summaries: Dict[int, str] = {}
        current_idx: int | None = None
        current_lines: List[str] = []

        for line in raw.splitlines():
            line = line.strip()
            if not line:
                continue
            # Match lines like "[1]. ..." or "[1] ..."
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
                rest = line[bracket_end + 1 :].lstrip(". ").strip()
                current_lines = [rest] if rest else []
            else:
                if current_idx is not None:
                    current_lines.append(line)

        if current_idx is not None:
            summaries[current_idx] = " ".join(current_lines).strip()

        for i, article in enumerate(articles, 1):
            if i in summaries:
                article.ai_summary = summaries[i]

    except Exception as exc:
        logger.warning(f"AI summary failed for {category}: {exc}")

    return articles


def summarize_all(data: Dict[str, List[Article]]) -> Dict[str, List[Article]]:
    """Run AI summarization for every category."""
    if not CONFIG.enable_ai_summary:
        return data
    result = {}
    for cat, articles in data.items():
        result[cat] = summarize_category(articles, cat)
    return result
