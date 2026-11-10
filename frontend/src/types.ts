// Tipos do contrato da API (docs/CONTRACTS.md). Um só lugar para páginas e componentes.
export type Offer = { store_id: number; store_name: string; price_brl: number; normal_price_brl: number | null; discount_pct: number; price_origin: string; is_estimated: boolean; deal_url: string | null };
export type Point = { date: string; price_brl: number };
export type SearchResult = { game_id: number; slug: string; title: string; thumb: string | null; best_offer: Offer | null; offers: Offer[]; genres?: string[]; discovered?: boolean };
export type Facet = { store_id: number; name: string; count: number };
export type SearchResponse = { query: string; count: number; results: SearchResult[]; facets: Facet[]; discovered: number; live_error: string | null };
export type Platform = { store_id: number; name: string; domain: string | null; price_kind: "brl_real" | "usd_converted" | "mixed"; source: string; games: number; last_captured_at: string | null };
export type Provider = { name: string; role: string; needs_key: boolean; enabled: boolean };
export type PlatformsResponse = { count: number; platforms: Platform[]; providers: Provider[]; total_games: number };
export type SortKey = "relevance" | "price" | "discount" | "title" | "stores";
export type Filters = { stores: number[]; maxPrice: string; minDiscount: number; sort: SortKey };
export const NO_FILTERS: Filters = { stores: [], maxPrice: "", minDiscount: 0, sort: "relevance" };
