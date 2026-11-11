import type { SearchResult } from "../../types";
import { GameResultCard, type GameResult } from "./GameResultCard";

export const toResult = (r: SearchResult, tag?: string): GameResult | null =>
  r.best_offer ? { game_id: r.game_id, title: r.title, thumb: r.thumb, offer: r.best_offer, stores: r.offers.length, genres: r.genres, tag } : null;

// Grade de jogos achados pela busca (toda a franquia, não só o primeiro).
export function GameResultList({ results, wished }: { results: SearchResult[]; wished?: Set<number> }) {
  const items = results.map((r) => toResult(r, wished?.has(r.game_id) ? "NA SUA WISHLIST" : r.discovered ? "ENCONTRADO AGORA" : undefined)).filter((g): g is GameResult => g !== null);
  if (!items.length) return <p className="body">Nenhum jogo encontrado com esses filtros. Tente outro nome ou afrouxe os filtros.</p>;
  return <ul className="rlist" aria-label="Jogos encontrados">{items.map((g, i) => <li key={g.game_id}><GameResultCard g={g} i={i} /></li>)}</ul>;
}
