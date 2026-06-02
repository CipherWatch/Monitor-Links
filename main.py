import asyncio
import json
import sys
from checker import check_all_urls
from models import LinkStatus
from db import init_db, upsert_link, save_check, get_stats
from scheduler import start_scheduler
from report import export_csv, export_summary_json, print_filtered
from rich.console import Console

console = Console()


def load_config(path: str = "config.json") -> dict:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def print_help():
    console.print("""
[bold cyan]Monitor de Links — Comandos disponíveis[/bold cyan]

  [green]python main.py[/green]                        Verificação única
  [green]python main.py watch[/green]                  Scheduler contínuo
  [green]python main.py filter[/green]                 Lista todo o histórico
  [green]python main.py filter --status offline[/green]    Filtra por status
  [green]python main.py filter --category testes[/green]   Filtra por categoria
  [green]python main.py filter --name Google[/green]       Filtra por nome
  [green]python main.py export[/green]                 Exporta CSV completo
  [green]python main.py export --status offline[/green]    Exporta só os offline
  [green]python main.py summary[/green]                Exporta resumo JSON
""")


def parse_args(args: list[str]) -> dict:
    """Parser simples de argumentos --chave valor"""
    result = {}
    i = 0
    while i < len(args):
        if args[i].startswith("--") and i + 1 < len(args):
            key = args[i][2:]
            result[key] = args[i + 1]
            i += 2
        else:
            i += 1
    return result


async def run_once(config: dict):
    urls = config["urls"]
    await init_db()

    console.print(f"\n[bold]🔍 Verificando {len(urls)} URL(s)...[/bold]\n")
    results = await check_all_urls(urls, timeout=config["timeout_seconds"])

    from rich.table import Table
    from rich import box
    table = Table(box=box.ROUNDED, header_style="bold cyan", expand=True)
    table.add_column("Status",  width=12)
    table.add_column("Nome",    min_width=18)
    table.add_column("Código",  justify="center", width=8)
    table.add_column("Tempo",   justify="right",  width=10)
    table.add_column("URL")

    for item, result in zip(urls, results):
        icons = {LinkStatus.ONLINE: "✅", LinkStatus.OFFLINE: "❌", LinkStatus.SLOW: "🟡"}
        time_str = f"{result.response_time_ms}ms" if result.response_time_ms else "—"
        code_str = str(result.status_code) if result.status_code else "ERR"
        table.add_row(
            icons[result.status] + f" {result.status.value}",
            result.name, code_str, time_str, result.url
        )
        link_id = await upsert_link(item["url"], item["name"], item["category"])
        await save_check(link_id, result)

    console.print(table)

    online  = sum(1 for r in results if r.status == LinkStatus.ONLINE)
    slow    = sum(1 for r in results if r.status == LinkStatus.SLOW)
    offline = sum(1 for r in results if r.status == LinkStatus.OFFLINE)
    console.print(f"\n📊 [green]{online} online[/green] · [yellow]{slow} lentos[/yellow] · [red]{offline} offline[/red]\n")


async def main():
    config = load_config()
    args = sys.argv[1:]
    mode = args[0] if args else "once"
    opts = parse_args(args[1:])

    if mode == "watch":
        try:
            await start_scheduler(
                urls=config["urls"],
                interval=config["check_interval_seconds"],
                timeout=config["timeout_seconds"],
            )
        except KeyboardInterrupt:
            console.print("\n[bold]👋 Monitor encerrado.[/bold]\n")

    elif mode == "once":
        await run_once(config)

    elif mode == "filter":
        await init_db()
        await print_filtered(
            status=opts.get("status"),
            category=opts.get("category"),
            name=opts.get("name"),
        )

    elif mode == "export":
        await init_db()
        path = await export_csv(
            status=opts.get("status"),
            category=opts.get("category"),
            name=opts.get("name"),
        )
        if path:
            console.print(f"\n✅ CSV exportado: [green]{path}[/green]\n")
        else:
            console.print("\n[yellow]Nenhum dado encontrado para exportar.[/yellow]\n")

    elif mode == "summary":
        await init_db()
        path = await export_summary_json()
        console.print(f"\n✅ Resumo JSON exportado: [green]{path}[/green]\n")

    else:
        print_help()


if __name__ == "__main__":
    asyncio.run(main())
