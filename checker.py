import asyncio
import aiohttp
import time
from urllib.parse import urlparse
from models import CheckResult, LinkStatus

SLOW_THRESHOLD = 2.0

# Lista de User-Agents para rotacionar
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:125.0) Gecko/20100101 Firefox/125.0",
]

BOT_BLOCK_CODES = {403, 405, 406, 429, 503, 401}

import random

def get_headers():
    return {
        "User-Agent": random.choice(USER_AGENTS),
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
        "Accept-Language": "pt-BR,pt;q=0.9,en-US;q=0.8,en;q=0.7",
        "Accept-Encoding": "gzip, deflate, br",
        "Connection": "keep-alive",
        "Upgrade-Insecure-Requests": "1",
        "Cache-Control": "max-age=0",
    }


async def tcp_check(host: str, port: int, timeout: float = 5.0) -> tuple[bool, float]:
    """Verifica conexão TCP. Retorna (sucesso, tempo_ms)"""
    start = time.monotonic()
    try:
        _, writer = await asyncio.wait_for(
            asyncio.open_connection(host, port),
            timeout=timeout
        )
        elapsed = (time.monotonic() - start) * 1000
        writer.close()
        await writer.wait_closed()
        return True, elapsed
    except Exception:
        return False, 0.0


async def check_url(session: aiohttp.ClientSession, url: str, name: str) -> CheckResult:
    start_time = time.monotonic()
    parsed = urlparse(url)
    host   = parsed.hostname or ""
    port   = 443 if parsed.scheme == "https" else 80

    # ── Tentativa 1: HTTP normal ──────────────────────────────────────
    try:
        async with session.get(url, headers=get_headers(), allow_redirects=True) as response:
            elapsed = (time.monotonic() - start_time) * 1000

            if response.status in BOT_BLOCK_CODES:
                # Bloqueou o bot mas está online
                return CheckResult(
                    url=url, name=name, status=LinkStatus.ONLINE,
                    status_code=response.status,
                    response_time_ms=round(elapsed, 2),
                )
            elif response.status < 400:
                status = LinkStatus.SLOW if elapsed > (SLOW_THRESHOLD * 1000) else LinkStatus.ONLINE
                return CheckResult(
                    url=url, name=name, status=status,
                    status_code=response.status,
                    response_time_ms=round(elapsed, 2),
                )
            # Status 4xx/5xx — tenta TCP antes de desistir
    except Exception:
        pass

    # ── Tentativa 2: HTTP sem SSL ─────────────────────────────────────
    try:
        connector = aiohttp.TCPConnector(ssl=False)
        async with aiohttp.ClientSession(connector=connector) as sess:
            timeout_cfg = aiohttp.ClientTimeout(total=8)
            async with sess.get(url, headers=get_headers(), allow_redirects=True, timeout=timeout_cfg) as response:
                elapsed = (time.monotonic() - start_time) * 1000
                if response.status in BOT_BLOCK_CODES or response.status < 400:
                    status = LinkStatus.SLOW if elapsed > (SLOW_THRESHOLD * 1000) else LinkStatus.ONLINE
                    return CheckResult(
                        url=url, name=name, status=status,
                        status_code=response.status,
                        response_time_ms=round(elapsed, 2),
                    )
    except Exception:
        pass

    # ── Tentativa 3: TCP direto ───────────────────────────────────────
    is_up, tcp_ms = await tcp_check(host, port)
    if is_up:
        elapsed = (time.monotonic() - start_time) * 1000
        return CheckResult(
            url=url, name=name,
            status=LinkStatus.SLOW if tcp_ms > (SLOW_THRESHOLD * 1000) else LinkStatus.ONLINE,
            status_code=None,
            response_time_ms=round(tcp_ms, 2),
            error_message="Online via TCP (WAF bloqueia HTTP)",
        )

    # ── Tentativa 4: porta 80 se falhou na 443 ────────────────────────
    if port == 443:
        is_up_80, tcp_ms_80 = await tcp_check(host, 80)
        if is_up_80:
            return CheckResult(
                url=url, name=name, status=LinkStatus.ONLINE,
                status_code=None,
                response_time_ms=round(tcp_ms_80, 2),
                error_message="Online via TCP porta 80",
            )

    # ── Todas as tentativas falharam ──────────────────────────────────
    elapsed = (time.monotonic() - start_time) * 1000
    return CheckResult(
        url=url, name=name, status=LinkStatus.OFFLINE,
        error_message="Sem resposta HTTP nem TCP",
    )


async def check_all_urls(urls: list[dict], timeout: int = 10) -> list[CheckResult]:
    timeout_cfg = aiohttp.ClientTimeout(total=timeout)
    connector   = aiohttp.TCPConnector(limit=50)
    async with aiohttp.ClientSession(timeout=timeout_cfg, connector=connector) as session:
        tasks   = [check_url(session, item["url"], item["name"]) for item in urls]
        results = await asyncio.gather(*tasks)
    return list(results)
