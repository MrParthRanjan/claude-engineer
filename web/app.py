"""SCMP Daily Reader — FastAPI web application."""

import asyncio
import os
import sys
from pathlib import Path

# ── Resolve project root & load .env FIRST, before any other import ──────────
# Path(__file__) = claude-engineer/web/app.py
# .parent.parent = claude-engineer/
_PROJECT_ROOT = Path(__file__).parent.parent
_ENV_FILE = _PROJECT_ROOT / ".env"

from dotenv import load_dotenv
# override=True ensures .env always wins over stale shell env vars
load_dotenv(_ENV_FILE, override=True)

sys.path.insert(0, str(_PROJECT_ROOT))
# ─────────────────────────────────────────────────────────────────────────────

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from loguru import logger

from scmp_daily.fetcher import get_articles, load_cache, save_cache
from scmp_daily.summarizer import summarize_all
from scmp_daily.config import CONFIG

BASE_DIR = Path(__file__).parent

app = FastAPI(title="SCMP Daily Intelligence")
app.mount("/static", StaticFiles(directory=str(BASE_DIR / "static")), name="static")
templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))


# ── Startup ───────────────────────────────────────────────────────────────────

@app.on_event("startup")
async def _startup():
    _log_env_diagnostics()
    asyncio.create_task(_warm_cache())


def _log_env_diagnostics():
    """Log clear diagnostics so 401 problems are obvious immediately."""
    api_key = os.getenv("ANTHROPIC_API_KEY", "")
    env_exists = _ENV_FILE.exists()

    if not env_exists:
        logger.warning(f".env file NOT found at {_ENV_FILE}  →  copy .env.example to .env and add your key")
    else:
        logger.info(f".env loaded from {_ENV_FILE}")

    if not api_key:
        logger.warning("ANTHROPIC_API_KEY is not set — AI summaries and deep analysis will be skipped")
    elif not api_key.startswith("sk-ant-"):
        logger.error(
            f"ANTHROPIC_API_KEY looks wrong (prefix: {api_key[:8]}...) — "
            "Anthropic keys start with 'sk-ant-'; this will cause 401 errors"
        )
    else:
        logger.info(f"ANTHROPIC_API_KEY loaded — prefix {api_key[:14]}...")


async def _warm_cache():
    data = await asyncio.to_thread(get_articles)
    if os.getenv("ANTHROPIC_API_KEY"):
        data = await _ensure_summaries(data)


# ── Helpers ───────────────────────────────────────────────────────────────────

def _needs_summaries(data: dict) -> bool:
    """True when articles exist but none have AI summaries yet."""
    all_articles = [a for arts in data.values() for a in arts]
    return bool(all_articles) and not any(a.ai_summary for a in all_articles)


async def _ensure_summaries(data: dict) -> dict:
    """Run summarization and persist only if summaries were actually written."""
    if not _needs_summaries(data):
        return data
    data = await asyncio.to_thread(summarize_all, data)
    # Only save to cache when at least one summary was generated
    has_summaries = any(a.ai_summary for arts in data.values() for a in arts)
    if has_summaries:
        await asyncio.to_thread(save_cache, data)
    return data


# ── Routes ────────────────────────────────────────────────────────────────────

@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})


@app.get("/api/articles")
async def api_articles(refresh: bool = False):
    data = await asyncio.to_thread(get_articles, refresh)
    if os.getenv("ANTHROPIC_API_KEY"):
        data = await _ensure_summaries(data)
    return {cat: [a.to_dict() for a in arts] for cat, arts in data.items()}


@app.post("/api/refresh")
async def api_refresh():
    data = await asyncio.to_thread(get_articles, True)
    if os.getenv("ANTHROPIC_API_KEY"):
        data = await asyncio.to_thread(summarize_all, data)
        has_summaries = any(a.ai_summary for arts in data.values() for a in arts)
        if has_summaries:
            await asyncio.to_thread(save_cache, data)
    total = sum(len(v) for v in data.values())
    return {"status": "ok", "total": total}


@app.get("/api/analysis")
async def api_analysis(title: str, description: str = "", category: str = ""):
    from web.analyzer import deep_analyze_article
    try:
        result = await deep_analyze_article(title, description, category)
        return result
    except Exception as exc:
        return JSONResponse(status_code=500, content={"error": str(exc)})


@app.get("/api/status")
async def api_status():
    """Diagnostics: API key health, .env file, cache state."""
    api_key = os.getenv("ANTHROPIC_API_KEY", "")

    if not api_key:
        key_status = "not_set"
        key_hint   = "Add ANTHROPIC_API_KEY=sk-ant-... to your .env file"
        key_preview = "—"
    elif not api_key.startswith("sk-ant-"):
        key_status  = "wrong_format"
        key_hint    = "Anthropic keys start with 'sk-ant-' — check for typos or a copied .env.example value"
        key_preview = api_key[:8] + "..."
    else:
        key_status  = "ok"
        key_hint    = ""
        key_preview = api_key[:16] + "..."

    cache = load_cache()
    cache_info = {
        "fresh_today": cache is not None,
        "categories": list(cache.keys()) if cache else [],
        "total_articles": sum(len(v) for v in cache.values()) if cache else 0,
        "has_ai_summaries": bool(
            cache and any(a.ai_summary for arts in cache.values() for a in arts)
        ),
    }

    return {
        "api_key": {"status": key_status, "preview": key_preview, "hint": key_hint},
        "env_file": {"path": str(_ENV_FILE), "exists": _ENV_FILE.exists()},
        "cache": cache_info,
        "model": CONFIG.claude_model,
    }
