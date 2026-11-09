"""Modelos pydantic = contrato de resposta da API (ver docs/CONTRACTS.md)."""
from datetime import date
from typing import Literal

from pydantic import BaseModel, Field


class Offer(BaseModel):
    store_id: int
    store_name: str
    price_brl: float
    normal_price_brl: float | None
    discount_pct: float
    price_origin: Literal["steam_brl", "converted_usd"]
    is_estimated: bool
    deal_url: str | None
    captured_at: str


class SearchResult(BaseModel):
    game_id: int
    slug: str
    title: str
    thumb: str | None
    best_offer: Offer | None
    offers: list[Offer]
    is_fixture: bool | None


class SearchResponse(BaseModel):
    query: str
    count: int
    results: list[SearchResult]


class GameMeta(BaseModel):
    background_image: str | None = None
    genres: list[str] = []
    platforms: list[str] = []
    rating: float | None = None
    metacritic: int | None = None
    released: str | None = None
    description: str | None = None
    playtime_hours: float | None = None
    is_fixture: bool | None = None


class Stats(BaseModel):
    min_price_brl: float | None
    avg_price_brl: float | None
    avg_90d_brl: float | None
    points: int
    first_day: str
    history_days: int
    has_simulated_history: bool


class VerdictOut(BaseModel):
    verdict: Literal["COMPRAR_AGORA", "ESPERAR", "NEUTRO", "INSUFICIENTE"]
    confidence: Literal["baixa", "media", "alta"]
    reasons: list[str]
    metrics: dict


class NextSale(BaseModel):
    name: str
    start_date: date
    days: int
    note: str


class GameDetail(BaseModel):
    game_id: int
    slug: str
    title: str
    meta: GameMeta
    offers: list[Offer]
    best_offer: Offer | None
    stats: Stats | None
    verdict: VerdictOut
    next_sale: NextSale | None
    playtime_hours: float | None
    price_per_hour: float | None


class HistoryPoint(BaseModel):
    date: str
    price_brl: float
    store_id: int
    is_simulated: bool


class History(BaseModel):
    game_id: int
    store_id: int | None
    days: int
    has_simulated: bool
    points: list[HistoryPoint]


class Deal(BaseModel):
    game_id: int
    slug: str
    title: str
    thumb: str | None
    offer: Offer


class DealsResponse(BaseModel):
    count: int
    deals: list[Deal]


class FxOut(BaseModel):
    rate_date: str
    usd_brl_buy: float
    usd_brl_sell: float
    source: str
    fetched_at: str


# ---- autenticados ----
class WishlistAdd(BaseModel):
    game_id: int = Field(gt=0)


class WishlistItem(BaseModel):
    game_id: int
    slug: str
    title: str
    thumb: str | None
    added_at: str | None
    best_offer: Offer | None


class WishlistOut(BaseModel):
    items: list[WishlistItem]


class AlertCreate(BaseModel):
    game_id: int = Field(gt=0)
    target_price_brl: float = Field(gt=0, lt=100000)
    store_id: int | None = Field(default=None, gt=0)


class AlertOut(BaseModel):
    alert_id: str
    game_id: int
    title: str
    target_price_brl: float
    store_id: int | None
    active: bool
    last_triggered_price: float | None
    last_triggered_at: str | None


class AlertsOut(BaseModel):
    items: list[AlertOut]


class NotificationOut(BaseModel):
    id: str
    title: str
    body: str
    game_id: int
    price_brl: float
    store_id: int
    created_at: str
    read: bool


class NotificationsOut(BaseModel):
    unread: int
    items: list[NotificationOut]


class DeviceIn(BaseModel):
    token: str = Field(min_length=10, max_length=4096)
    platform: str | None = Field(default=None, max_length=32)
