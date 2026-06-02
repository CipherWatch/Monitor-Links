import aiosqlite
from datetime import datetime
from models import CheckResult

DB_PATH = "data/links.db"

async def init_db():
    """
    Cria as tabelas se ainda não existirem.
    Chamado uma vez quando o programa inicia.
    """
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""
            CREATE TABLE IF NOT EXISTS links (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                url         TEXT UNIQUE NOT NULL,
                name        TEXT NOT NULL,
                category    TEXT DEFAULT 'geral',
                created_at  TEXT DEFAULT (datetime('now'))
            )
        """)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS checks (
                id               INTEGER PRIMARY KEY AUTOINCREMENT,
                link_id          INTEGER NOT NULL,
                status           TEXT NOT NULL,
                status_code      INTEGER,
                response_time_ms REAL,
                error_message    TEXT,
                checked_at       TEXT DEFAULT (datetime('now')),
                FOREIGN KEY (link_id) REFERENCES links(id)
            )
        """)
        await db.commit()
        await db.execute("""
            CREATE TABLE IF NOT EXISTS alerts (
                id           INTEGER PRIMARY KEY AUTOINCREMENT,
                name         TEXT,
                url          TEXT,
                old_status   TEXT,
                new_status   TEXT,
                triggered_at TEXT
            )
        """)
        await db.commit()


async def upsert_link(url: str, name: str, category: str) -> int:
    """
    Insere um link novo ou ignora se já existir.
    Retorna o id do link.
    'upsert' = insert + update combinados.
    """
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""
            INSERT OR IGNORE INTO links (url, name, category)
            VALUES (?, ?, ?)
        """, (url, name, category))
        await db.commit()

        async with db.execute("SELECT id FROM links WHERE url = ?", (url,)) as cursor:
            row = await cursor.fetchone()
            return row[0]


async def save_check(link_id: int, result: CheckResult):
    """
    Salva o resultado de uma verificação no banco.
    """
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""
            INSERT INTO checks (link_id, status, status_code, response_time_ms, error_message, checked_at)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (
            link_id,
            result.status.value,
            result.status_code,
            result.response_time_ms,
            result.error_message,
            result.checked_at.isoformat(),
        ))
        await db.commit()


async def get_history(url: str, limit: int = 10) -> list[dict]:
    """
    Retorna as últimas verificações de uma URL específica.
    """
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("""
            SELECT c.status, c.status_code, c.response_time_ms,
                   c.error_message, c.checked_at
            FROM checks c
            JOIN links l ON l.id = c.link_id
            WHERE l.url = ?
            ORDER BY c.checked_at DESC
            LIMIT ?
        """, (url, limit)) as cursor:
            rows = await cursor.fetchall()
            return [dict(row) for row in rows]


async def get_stats(url: str) -> dict:
    """
    Calcula métricas de uptime para uma URL:
    - total de verificações
    - quantas foram online
    - tempo médio de resposta
    - uptime em porcentagem
    """
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("""
            SELECT
                COUNT(*)                                        as total,
                SUM(CASE WHEN status = 'online' THEN 1 ELSE 0 END) as online_count,
                AVG(response_time_ms)                           as avg_ms
            FROM checks c
            JOIN links l ON l.id = c.link_id
            WHERE l.url = ?
        """, (url,)) as cursor:
            row = await cursor.fetchone()
            total, online_count, avg_ms = row
            if not total:
                return {}
            return {
                "total": total,
                "online_count": online_count,
                "uptime_pct": round((online_count / total) * 100, 1),
                "avg_ms": round(avg_ms, 1) if avg_ms else None,
            }


async def get_last_status(url: str) -> str | None:
    """
    Retorna o status da verificação mais recente de uma URL.
    Retorna None se nunca foi verificada antes.
    """
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("""
            SELECT c.status
            FROM checks c
            JOIN links l ON l.id = c.link_id
            WHERE l.url = ?
            ORDER BY c.checked_at DESC
            LIMIT 2
        """, (url,)) as cursor:
            rows = await cursor.fetchall()
            # rows[0] é o check atual (recém salvo)
            # rows[1] é o check anterior — é esse que queremos
            if len(rows) >= 2:
                return rows[1][0]
            return None


async def get_last_status(url: str) -> str | None:
    """
    Retorna o status da verificação mais recente de uma URL.
    Retorna None se nunca foi verificada antes.
    """
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("""
            SELECT c.status
            FROM checks c
            JOIN links l ON l.id = c.link_id
            WHERE l.url = ?
            ORDER BY c.checked_at DESC
            LIMIT 2
        """, (url,)) as cursor:
            rows = await cursor.fetchall()
            # rows[0] é o check atual (recém salvo)
            # rows[1] é o check anterior — é esse que queremos
            if len(rows) >= 2:
                return rows[1][0]
            return None


async def init_alerts_table():
    """Garante que a tabela de alertas existe desde o início"""
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""
            CREATE TABLE IF NOT EXISTS alerts (
                id           INTEGER PRIMARY KEY AUTOINCREMENT,
                name         TEXT,
                url          TEXT,
                old_status   TEXT,
                new_status   TEXT,
                triggered_at TEXT
            )
        """)
        await db.commit()


async def get_all_checks(
    status: str | None = None,
    category: str | None = None,
    name: str | None = None,
    limit: int = 500,
) -> list[dict]:
    """
    Retorna checks com filtros opcionais.
    Todos os parâmetros são opcionais — sem filtro retorna tudo.
    """
    query = """
        SELECT l.name, l.url, l.category,
               c.status, c.status_code, c.response_time_ms,
               c.error_message, c.checked_at
        FROM checks c
        JOIN links l ON l.id = c.link_id
        WHERE 1=1
    """
    params = []

    if status:
        query += " AND c.status = ?"
        params.append(status)
    if category:
        query += " AND l.category = ?"
        params.append(category)
    if name:
        query += " AND l.name LIKE ?"
        params.append(f"%{name}%")

    query += " ORDER BY c.checked_at DESC LIMIT ?"
    params.append(limit)

    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(query, params) as cursor:
            rows = await cursor.fetchall()
            return [dict(row) for row in rows]
