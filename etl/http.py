"""Cliente HTTP com timeout, retry com backoff exponencial, pausa entre chamadas e User-Agent."""
import logging
import time

import httpx

from etl import config

log = logging.getLogger("etl.http")
RETRY_STATUS = {429, 500, 502, 503, 504}


class RateLimited(RuntimeError):
    """429 com Retry-After longo: insistir só pioraria o bloqueio; o job deve parar e tentar no próximo ciclo."""

    def __init__(self, url: str, retry_after: int):
        super().__init__(f"{url} limitou a taxa (Retry-After {retry_after}s)")
        self.retry_after = retry_after


MAX_WAIT = 60


class HttpClient:
    def __init__(self, pause: float | None = None, retries: int = 4, transport: httpx.BaseTransport | None = None,
                 backoff_base: float = 3.0):
        self.pause = config.PAUSE_SECONDS if pause is None else pause
        self.retries = retries
        self.backoff_base = backoff_base
        self._client = httpx.Client(
            timeout=httpx.Timeout(20.0), headers={"User-Agent": config.USER_AGENT},
            transport=transport, follow_redirects=True,
        )

    def get_json(self, url: str, params: dict | None = None):
        last: Exception | None = None
        for attempt in range(self.retries + 1):
            if self.pause:
                time.sleep(self.pause)
            try:
                resp = self._client.get(url, params=params)
                if resp.status_code == 429:
                    ra = resp.headers.get("retry-after", "")
                    if ra.isdigit() and int(ra) > MAX_WAIT:
                        raise RateLimited(url, int(ra))
                if resp.status_code in RETRY_STATUS:
                    raise httpx.HTTPStatusError(f"status {resp.status_code}", request=resp.request, response=resp)
                resp.raise_for_status()
                return resp.json()
            except RateLimited:
                raise
            except (httpx.TransportError, httpx.HTTPStatusError, ValueError) as exc:
                last = exc
                if attempt < self.retries:
                    wait = self.backoff_base * (2 ** attempt)
                    log.warning("GET %s falhou (%s); tentativa %d/%d em %.1fs", url, exc, attempt + 1, self.retries, wait)
                    time.sleep(wait)
        raise RuntimeError(f"GET {url} falhou após {self.retries + 1} tentativas: {last}")
