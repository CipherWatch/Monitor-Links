import csv
import json
from datetime import datetime
from pathlib import Path
from db import get_all_checks, get_stats


REPORTS_DIR = Path("data/reports")


def ensure_reports_dir():
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)


async def export_csv(
    status: str | None = None,
    category: str | None = None,
    name: str | None = None,
) -> str:
    """
    Exporta histórico para CSV com filtros opcionais.
    Retorna o caminho do arquivo gerado.
    """
    ensure_reports_dir()

    rows = await get_all_checks(status=status, category=category, name=name)

    if not rows:
        return None

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = REPORTS_DIR / f"relatorio_{timestamp}.csv"

    with open(filename, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=[
            "name", "url", "category", "status",
            "status_code", "response_time_ms", "error_message", "checked_at"
        ])
        writer.writeheader()
        writer.writerows(rows)

    return str(filename)


async def export_summary_json() -> str:
    """
    Exporta um resumo de métricas de todas as URLs em JSON.
    Útil para integrar com outras ferramentas.
    """
    ensure_reports_dir()

    from db import get_all_checks
    import aiosqlite
    from db import DB_PATH

    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT url, name, category FROM links") as cur:
            links = [dict(r) for r in await cur.fetchall()]

    summary = []
    for link in links:
        stats = await get_stats(link["url"])
        summary.append({
            "name": link["name"],
            "url": link["url"],
            "category": link["category"],
            "uptime_pct": stats.get("uptime_pct") if stats else None,
            "avg_ms": stats.get("avg_ms") if stats else None,
            "total_checks": stats.get("total") if stats else 0,
        })

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = REPORTS_DIR / f"summary_{timestamp}.json"

    with open(filename, "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2, ensure_ascii=False)

    return str(filename)


async def print_filtered(
    status: str | None = None,
    category: str | None = None,
    name: str | None = None,
):
    """Imprime resultados filtrados no terminal com Rich"""
    from rich.console import Console
    from rich.table import Table
    from rich import box

    console = Console()
    rows = await get_all_checks(status=status, category=category, name=name, limit=50)

    if not rows:
        console.print("[yellow]Nenhum resultado encontrado com esses filtros.[/yellow]")
        return

    table = Table(box=box.ROUNDED, header_style="bold cyan", expand=True)
    table.add_column("Nome",      min_width=18)
    table.add_column("Status",    width=10)
    table.add_column("Código",    justify="center", width=7)
    table.add_column("Tempo",     justify="right",  width=10)
    table.add_column("Categoria", width=14)
    table.add_column("Verificado em", width=20)

    status_colors = {"online": "green", "offline": "red", "slow": "yellow"}

    for row in rows:
        color = status_colors.get(row["status"], "white")
        time_str = f"{row['response_time_ms']}ms" if row["response_time_ms"] else "—"
        code_str = str(row["status_code"]) if row["status_code"] else "ERR"
        table.add_row(
            row["name"],
            f"[{color}]{row['status']}[/{color}]",
            code_str,
            time_str,
            row["category"],
            row["checked_at"][:19],
        )

    filtros = []
    if status:   filtros.append(f"status={status}")
    if category: filtros.append(f"categoria={category}")
    if name:     filtros.append(f"nome contém '{name}'")
    filtro_str = " · ".join(filtros) if filtros else "sem filtros"

    console.print(f"\n[bold]Histórico[/bold] [dim]({filtro_str} · {len(rows)} resultados)[/dim]")
    console.print(table)
