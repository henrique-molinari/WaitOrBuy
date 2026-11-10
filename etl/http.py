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
        self._transport = transport
        self._client = httpx.Client(
            timeout=httpx.Timeout(20.0), headers={"User-Agent": config.USER_AGENT},
            transport=transport, follow_redirects=True,
        )

    def clone(self) -> "HttpClient":
        """Cliente independente com a mesma configuração (um por thread; o httpx.Client compartilhado não é a melhor ideia)."""
        return HttpClient(pause=self.pause, retries=self.retries, transport=self._transport, backoff_base=self.backoff_base)

    def get_json(self, url: str, params: dict | None = None):
        return self._get(url, params, as_json=True)

    def get_text(self, url: str, params: dict | None = None):
        """Texto da resposta; None em 404 (página inexistente não é falha)."""
        return self._get(url, params, as_json=False)

    def post_json(self, url: str, body: dict):
        """POST com corpo JSON (GraphQL); mesma política de retry e pausa do GET."""
        return self._request("POST", url, None, True, body)

    def _get(self, url: str, params: dict | None, as_json: bool):
        return self._request("GET", url, params, as_json, None)

    def _request(self, method: str, url: str, params: dict | None, as_json: bool, body: dict | None):
        last: Exception | None = None
        for attempt in range(self.retries + 1):
            if self.pause:
                time.sleep(self.pause)
            try:
                resp = self._client.get(url, params=params) if method == "GET" else self._client.post(url, json=body)
                if resp.status_code == 429:
                    ra = resp.headers.get("retry-after", "")
                    if ra.isdigit() and int(ra) > MAX_WAIT:
                        raise RateLimited(url, int(ra))
                if resp.status_code in RETRY_STATUS:
                    raise httpx.HTTPStatusError(f"status {resp.status_code}", request=resp.request, response=resp)
                if resp.status_code == 404 and not as_json:
                    return None
                resp.raise_for_status()
                return resp.json() if as_json else resp.text
            except RateLimited:
                raise
            except (httpx.TransportError, httpx.HTTPStatusError, ValueError) as exc:
                last = exc
                if isinstance(exc, httpx.HTTPStatusError) and exc.response.status_code not in RETRY_STATUS:
                    break  # 4xx (ex.: 404 em JSON) não melhora tentando de novo
                if attempt < self.retries:
                    wait = self.backoff_base * (2 ** attempt)
                    log.warning("GET %s falhou (%s); tentativa %d/%d em %.1fs", url, exc, attempt + 1, self.retries, wait)
                    time.sleep(wait)
        raise RuntimeError(f"GET {url} falhou após {self.retries + 1} tentativas: {last}")
