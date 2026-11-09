import logging

from app import db, errors, firebase
from app.auth import require_admin
from app.config import settings
from app.routers import me, public
from app.services import alerts
from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

logging.basicConfig(level=logging.INFO)

app = FastAPI(title="WaitOrBuy API", version="1.0.0",
              description="Comparador de preços de jogos com histórico, alertas e indicador 'vale esperar?'.")
app.add_middleware(CORSMiddleware, allow_origins=[settings.frontend_origin], allow_credentials=True,
                   allow_methods=["GET", "POST", "DELETE"], allow_headers=["Authorization", "Content-Type"])
errors.install(app)
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
def evaluate_alerts():
    with db.pool().connection() as conn:
        return alerts.evaluate(conn)
