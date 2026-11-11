"""Configuração central: variáveis de ambiente e limiares da regra "vale esperar?" (único lugar)."""
import os
from dataclasses import dataclass
from zoneinfo import ZoneInfo

TZ = ZoneInfo("America/Sao_Paulo")


@dataclass(frozen=True)
class VerdictConfig:
    near_min_factor: float = 1.05        # A: preço ≤ 1,05 × mínimo histórico → COMPRAR_AGORA
    wait_sale_min_factor: float = 1.15   # B: preço > 1,15 × mínimo com liquidação próxima → ESPERAR
    sale_window_days: int = 30           # "liquidação próxima" = em até 30 dias
    above_avg90_factor: float = 0.95     # C: preço ≥ 0,95 × média 90 dias ...
    low_discount_pct: float = 20.0       # ... e desconto < 20%
    min_history_days: int = 5            # abaixo disso: INSUFICIENTE
    confidence_low_days: int = 14        # < 14 baixa
    confidence_high_days: int = 90       # > 90 alta (14..90 média)
    minor_sales: tuple[str, ...] = ("Steam Lunar New Year Sale",)  # não contam como "liquidação grande"


VERDICT = VerdictConfig()


class Settings:
    database_url = os.getenv("DATABASE_URL", "postgresql://waitorbuy:waitorbuy@localhost:5432/waitorbuy")
    mongo_url = os.getenv("MONGO_URL", "mongodb://localhost:27017")
    mongo_db = os.getenv("MONGO_DB", "waitorbuy")
    admin_token = os.getenv("ADMIN_TOKEN", "")
    affiliate_tag = os.getenv("AFFILIATE_TAG", "").strip()
    frontend_origin = os.getenv("FRONTEND_ORIGIN", "http://localhost:5173")
    # Endereço público do site, usado nos links dos e-mails. Sem PUBLIC_URL, usa o primeiro de FRONTEND_ORIGIN.
    public_url = (os.getenv("PUBLIC_URL", "").strip() or os.getenv("FRONTEND_ORIGIN", "http://localhost:5173").split(",")[0].strip()).rstrip("/")
    project_id = os.getenv("FIREBASE_PROJECT_ID", "demo-waitorbuy")
    firebase_credentials = os.getenv("FIREBASE_CREDENTIALS", "").strip()


settings = Settings()
