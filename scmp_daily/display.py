"""SCMP Daily Reader — Rich Terminal Display"""

from datetime import date
from typing import Dict, List

from rich import box
from rich.columns import Columns
from rich.console import Console
from rich.panel import Panel
from rich.rule import Rule
from rich.table import Table
from rich.text import Text

from .config import CONFIG
from .fetcher import Article

console = Console()


def _header() -> None:
    today = date.today().strftime("%A, %d %B %Y")
    title = Text()
    title.append("📰  SOUTH CHINA MORNING POST", style="bold white on red")
    title.append(f"   Daily Digest — {today}", style="dim white")
    console.print(Panel(title, box=box.DOUBLE_EDGE, border_style="red"))
    console.print()


def _category_panel(category: str, articles: List[Article]) -> None:
    color = CONFIG.category_colors.get(category, "bold white")
    console.print(Rule(f"[{color}] {category.upper()} [/{color}]", style=color))

    for i, a in enumerate(articles, 1):
        # Article number + title
        title_text = Text()
        title_text.append(f"{i}. ", style="bold dim")
        title_text.append(a.title, style="bold white")
        console.print(title_text)

        # Published date
        if a.published:
            console.print(f"   [dim]{a.published}[/dim]")

        # AI Summary (preferred) or RSS description snippet
        body = a.ai_summary or a.description
        if body:
            # Wrap long lines neatly at ~90 chars
            console.print(f"   [italic]{body[:400]}[/italic]")

        # Article link (dim, clickable in most terminals)
        if a.link:
            console.print(f"   [dim blue underline]{a.link}[/dim blue underline]")

        console.print()

    console.print()


def _footer(total: int, source: str) -> None:
    console.print(
        Rule(
            f"[dim]{total} articles · scmp.com · {source}[/dim]",
            style="dim",
        )
    )


def render(data: Dict[str, List[Article]], source: str = "live") -> None:
    """Render the complete daily digest to the terminal."""
    _header()

    total = 0
    for cat in CONFIG.display_order:
        articles = data.get(cat)
        if not articles:
            continue
        _category_panel(cat, articles)
        total += len(articles)

    _footer(total, source)


def render_brief(data: Dict[str, List[Article]]) -> None:
    """One-line-per-article compact view (good for quick glance)."""
    today = date.today().strftime("%d %b %Y")
    console.print(
        Panel(
            f"[bold red]SCMP[/bold red] [dim]Quick Headlines — {today}[/dim]",
            box=box.SIMPLE,
        )
    )
    table = Table(box=box.SIMPLE_HEAD, show_header=True, expand=True)
    table.add_column("Category", style="dim", width=14)
    table.add_column("Headline", style="white")

    for cat in CONFIG.display_order:
        for a in data.get(cat, []):
            color = CONFIG.category_colors.get(cat, "white")
            table.add_row(
                Text(cat, style=color),
                Text(a.title),
            )
    console.print(table)
