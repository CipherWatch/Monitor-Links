import asyncio
from datetime import datetime
from checker import check_all_urls
from db import init_db, upsert_link, save_check, get_last_status
from models import LinkStatus
from alerts import check_alert, save_alert
from dashboard import console, render_dashboard


async def run_cycle(urls: list[dict], timeout: int, cycle: int):
    results = await check_all_urls(urls, timeout=timeout)
    alerts_fired = []

    for item, result in zip(urls, results):
        old_status = await get_last_status(item["url"])
        link_id = await upsert_link(item["url"], item["name"], item["category"])
        await save_check(link_id, result)

        event = check_alert(
            name=item["name"],
            url=item["url"],
            old_status=old_status,
            new_status=result.status.value,
        )
        if event:
            alerts_fired.append(event)
            await save_alert(event)

    await render_dashboard(results, urls, cycle, alerts_fired)


async def start_scheduler(urls: list[dict], interval: int, timeout: int):
    await init_db()

    console.print("[bold cyan]🚀 Iniciando Monitor de Links...[/bold cyan]")
    console.print(f"   [dim]Monitorando {len(urls)} URL(s) · Intervalo: {interval}s[/dim]\n")

    cycle = 0
    while True:
        cycle += 1
        try:
            await run_cycle(urls, timeout, cycle)
        except Exception as e:
            console.print(f"[red]⚠️  Erro no ciclo: {e}[/red]")

        console.print(f"[dim]⏳ Próxima verificação em {interval}s...[/dim]")
        await asyncio.sleep(interval)
