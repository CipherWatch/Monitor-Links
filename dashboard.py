from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.columns import Columns
from rich.text import Text
from rich import box
from datetime import datetime
from models import LinkStatus
from db import get_stats, get_history

console = Console()


def status_badge(status: str) -> Text:
    """Retorna texto colorido para cada status"""
    badges = {
        "online":  Text("● ONLINE",  style="bold green"),
        "offline": Text("● OFFLINE", style="bold red"),
        "slow":    Text("● LENTO",   style="bold yellow"),
    }
    return badges.get(status, Text(status))


def build_results_table(results, items) -> Table:
    """Monta a tabela principal com os resultados do ciclo"""
    table = Table(
        box=box.ROUNDED,
        show_header=True,
        header_style="bold cyan",
        border_style="dim",
        expand=True,
    )

    table.add_column("Status",    width=12)
    table.add_column("Nome",      min_width=20)
    table.add_column("Código",    justify="center", width=8)
    table.add_column("Tempo",     justify="right",  width=10)
    table.add_column("Categoria", width=14)
    table.add_column("URL",       no_wrap=True)

    for item, result in zip(items, results):
        time_str = f"{result.response_time_ms}ms" if result.response_time_ms else "—"
        code_str = str(result.status_code) if result.status_code else "ERR"

        # Colore o tempo de resposta
        if result.response_time_ms is None:
            time_text = Text("—", style="dim")
        elif result.response_time_ms > 2000:
            time_text = Text(time_str, style="bold red")
        elif result.response_time_ms > 800:
            time_text = Text(time_str, style="yellow")
        else:
            time_text = Text(time_str, style="green")

        table.add_row(
            status_badge(result.status.value),
            result.name,
            code_str,
            time_text,
            item.get("category", "geral"),
            result.url,
        )

    return table


async def build_stats_table(items) -> Table:
    """Monta a tabela de métricas acumuladas"""
    table = Table(
        box=box.SIMPLE,
        show_header=True,
        header_style="bold magenta",
        border_style="dim",
        expand=True,
    )

    table.add_column("Site",     min_width=20)
    table.add_column("Uptime",   justify="center", width=10)
    table.add_column("Avg",      justify="right",  width=10)
    table.add_column("Checks",   justify="center", width=8)
    table.add_column("Último status", width=14)

    for item in items:
        stats = await get_stats(item["url"])
        history = await get_history(item["url"], limit=1)

        if not stats:
            continue

        avg_str = f"{stats['avg_ms']}ms" if stats['avg_ms'] else "—"

        # Colore o uptime
        uptime = stats['uptime_pct']
        if uptime >= 99:
            uptime_text = Text(f"{uptime}%", style="bold green")
        elif uptime >= 90:
            uptime_text = Text(f"{uptime}%", style="yellow")
        else:
            uptime_text = Text(f"{uptime}%", style="bold red")

        last_status = history[0]["status"] if history else "—"

        table.add_row(
            item["name"],
            uptime_text,
            avg_str,
            str(stats["total"]),
            status_badge(last_status),
        )

    return table


async def render_dashboard(results, items, cycle: int, alerts_fired: list):
    """Renderiza o dashboard completo no terminal"""
    console.clear()

    # Cabeçalho
    now = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
    header = Text(justify="center")
    header.append("🔍 Monitor de Links", style="bold white")
    header.append(f"   —   Ciclo #{cycle}   —   {now}", style="dim")
    console.print(Panel(header, border_style="cyan"))

    # Tabela de resultados
    console.print("\n[bold cyan]Verificação atual[/bold cyan]")
    results_table = build_results_table(results, items)
    console.print(results_table)

    # Alertas do ciclo
    if alerts_fired:
        console.print()
        for event in alerts_fired:
            if event.is_recovered():
                msg = f"[bold green]🟢 RECUPERADO:[/bold green] {event.name} voltou ao ar"
            else:
                msg = f"[bold red]🔴 ALERTA:[/bold red] {event.name} saiu do ar  ({event.old_status} → {event.new_status})"
            console.print(Panel(msg, border_style="red" if not event.is_recovered() else "green"))

    # Tabela de métricas
    console.print("\n[bold magenta]Métricas acumuladas[/bold magenta]")
    stats_table = await build_stats_table(items)
    console.print(stats_table)

    # Resumo rápido
    online  = sum(1 for r in results if r.status == LinkStatus.ONLINE)
    slow    = sum(1 for r in results if r.status == LinkStatus.SLOW)
    offline = sum(1 for r in results if r.status == LinkStatus.OFFLINE)

    summary_parts = []
    if online:
        summary_parts.append(f"[green]{online} online[/green]")
    if slow:
        summary_parts.append(f"[yellow]{slow} lentos[/yellow]")
    if offline:
        summary_parts.append(f"[red]{offline} offline[/red]")

    console.print(f"\n📊 {' · '.join(summary_parts)}")
    console.print("[dim]Pressione Ctrl+C para encerrar[/dim]\n")
