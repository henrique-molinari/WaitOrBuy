import logging
import os
import time

from fastapi import Depends, FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app import db, errors, firebase
from app.auth import require_admin
from app.config import settings
from app.routers import me, public
from app.services import alerts

logging.basicConfig(level=logging.INFO)

RATE_LIMIT_PER_MIN = int(os.getenv("RATE_LIMIT_PER_MIN", "300"))
_HITS: dict[str, list[float]] = {}

app = FastAPI(title="WaitOrBuy API", version="1.0.0",
              description="Comparador de preços de jogos com histórico, alertas e indicador 'vale esperar?'.")
app.add_middleware(CORSMiddleware, allow_origins=[o.strip() for o in settings.frontend_origin.split(",") if o.strip()], allow_credentials=True,
                   allow_methods=["GET", "POST", "DELETE"], allow_headers=["Authorization", "Content-Type"])
errors.install(app)


@app.middleware("http")
async def rate_limit(request: Request, call_next):
    """Limite básico por IP (janela deslizante de 60 s). /health e preflight CORS ficam de fora."""
    if request.url.path != "/health" and request.method != "OPTIONS":
        ip = request.client.host if request.client else "?"
        now = time.monotonic()
        hits = [t for t in _HITS.get(ip, []) if now - t < 60]
        if len(hits) >= RATE_LIMIT_PER_MIN:
            _HITS[ip] = hits
            return JSONResponse({"error": {"code": "rate_limited", "message": "Muitas requisições; tente novamente em instantes."}},
                                status_code=429, headers={"Retry-After": "30"})
        hits.append(now)
        _HITS[ip] = hits
    return await call_next(request)

app.include_router(public.router)
app.include_router(me.router)


@app.get("/health", tags=["infra"])
def health():
    status = {"postgres": False, "mongo": False, "firestore": False}
    try:
        with db.pool().connection() as c:
            c.execute("SELECT 1")
        status["postgres"] = True
    except Exception:
        pass
    try:
        db.mongo_games().database.client.admin.command("ping")
        status["mongo"] = True
    except Exception:
        pass
    try:
        list(firebase.firestore_client().collection("_health").limit(1).stream())
        status["firestore"] = True
    except Exception:
        pass
    ok = all(status.values())
    return JSONResponse({"status": "ok" if ok else "degraded", **status}, status_code=200 if ok else 503)


@app.post("/api/admin/alerts/evaluate", tags=["interno"], dependencies=[Depends(require_admin)])
def evaluate_alerts(uid: str | None = None):
    with db.pool().connection() as conn:
        return alerts.evaluate(conn, only_uid=uid)
