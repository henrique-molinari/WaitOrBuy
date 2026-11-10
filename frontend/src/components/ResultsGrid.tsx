import type { SearchResult } from "../types";
import { GameCard, type Card } from "./GameCard";

export const toCard = (r: SearchResult): Card | null =>
  r.best_offer ? { game_id: r.game_id, title: r.title, thumb: r.thumb, offer: r.best_offer, stores: r.offers.length, genres: r.genres, discovered: r.discovered } : null;

export function ResultsGrid({ results, wished }: { results: SearchResult[]; wished?: Set<number> }) {
  const cards = results.map(toCard).filter((c): c is Card => c !== null);
  if (!cards.length) return <p className="body">Nenhum jogo encontrado com esses filtros. Tente outro nome ou afrouxe os filtros.</p>;
  return <div className="grid" style={{ marginTop: "var(--space-3)" }}>{cards.map((c, i) => <GameCard key={c.game_id} c={c} i={i} tag={wished?.has(c.game_id) ? "NA SUA WISHLIST" : c.discovered ? "ENCONTRADO AGORA" : undefined} />)}</div>;
}
