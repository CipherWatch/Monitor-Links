from datetime import datetime
from models import LinkStatus


class AlertEvent:
    """Representa um evento de mudança de status"""
    def __init__(self, name: str, url: str, old_status: str, new_status: str):
        self.name = name
        self.url = url
        self.old_status = old_status
        self.new_status = new_status
        self.timestamp = datetime.now()

    def is_down(self) -> bool:
        return self.new_status in (LinkStatus.OFFLINE, LinkStatus.SLOW)

    def is_recovered(self) -> bool:
        return (self.old_status == LinkStatus.OFFLINE
                and self.new_status == LinkStatus.ONLINE)


def check_alert(name: str, url: str, old_status: str | None, new_status: str) -> AlertEvent | None:
    """
    Compara o status anterior com o atual.
    Retorna um AlertEvent se houve mudança, None se ficou igual.
    """
    if old_status is None:
        # Primeira verificação — sem alerta
        return None

    if old_status == new_status:
        # Nada mudou — sem alerta
        return None

    return AlertEvent(
        name=name,
        url=url,
        old_status=old_status,
        new_status=new_status,
    )


def format_alert(event: AlertEvent) -> str:
    """Formata o alerta para exibição no terminal"""
    time_str = event.timestamp.strftime("%H:%M:%S")

    if event.is_recovered():
        return (
            f"\n{'='*60}\n"
            f"  🟢 RECUPERADO às {time_str}\n"
            f"  Site:   {event.name}\n"
            f"  URL:    {event.url}\n"
            f"  Status: {event.old_status} → {event.new_status}\n"
            f"{'='*60}\n"
        )
    else:
        return (
            f"\n{'='*60}\n"
            f"  🔴 ALERTA às {time_str}\n"
            f"  Site:   {event.name}\n"
            f"  URL:    {event.url}\n"
            f"  Status: {event.old_status} → {event.new_status}\n"
            f"{'='*60}\n"
        )


async def save_alert(event: AlertEvent):
    """
    Salva o alerta no banco de dados.
    Vamos criar a tabela de alertas agora.
    """
    import aiosqlite
    from db import DB_PATH
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""
            CREATE TABLE IF NOT EXISTS alerts (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                name        TEXT,
                url         TEXT,
                old_status  TEXT,
                new_status  TEXT,
                triggered_at TEXT
            )
        """)
        await db.execute("""
            INSERT INTO alerts (name, url, old_status, new_status, triggered_at)
            VALUES (?, ?, ?, ?, ?)
        """, (
            event.name,
            event.url,
            event.old_status,
            event.new_status,
            event.timestamp.isoformat(),
        ))
        await db.commit()
