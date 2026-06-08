"""SCMP Daily Reader — FastAPI web application."""

import asyncio
import sys
from pathlib import Path

from dotenv import load_dotenv
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

load_dotenv()
sys.path.insert(0, str(Path(__file__).parent.parent))

from scmp_daily.fetcher import get_articles
from scmp_daily.summarizer import summarize_all
from scmp_daily.config import CONFIG

BASE_DIR = Path(__file__).parent

app = FastAPI(title="SCMP Daily Intelligence")
app.mount("/static", StaticFiles(directory=str(BASE_DIR / "static")), name="static")
templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))


@app.on_event("startup")
async def _startup():
    """Warm the cache on startup so first page load is instant."""
    asyncio.create_task(_warm_cache())


async def _warm_cache():
    data = await asyncio.to_thread(get_articles)
    import os
    if os.getenv("ANTHROPIC_API_KEY"):
        first = next(iter(data.values()), [])
        if first and not first[0].ai_summary:
            data = await asyncio.to_thread(summarize_all, data)
            from scmp_daily.fetcher import save_cache
            await asyncio.to_thread(save_cache, data)


@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})


@app.get("/api/articles")
async def api_articles(refresh: bool = False):
    data = await asyncio.to_thread(get_articles, refresh)
    import os
    if os.getenv("ANTHROPIC_API_KEY"):
        first = next(iter(data.values()), [])
        if first and not first[0].ai_summary:
            data = await asyncio.to_thread(summarize_all, data)
            from scmp_daily.fetcher import save_cache
            await asyncio.to_thread(save_cache, data)
    return {cat: [a.to_dict() for a in arts] for cat, arts in data.items()}


@app.post("/api/refresh")
async def api_refresh():
    data = await asyncio.to_thread(get_articles, True)
    import os
    if os.getenv("ANTHROPIC_API_KEY"):
        data = await asyncio.to_thread(summarize_all, data)
        from scmp_daily.fetcher import save_cache
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
