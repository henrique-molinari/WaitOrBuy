import { brl } from "../api";
import type { Offer } from "../types";
import { StoreBadge } from "./StoreBadge";
import { stag } from "./Motion";
import { Verdict } from "./Verdict";

export type Card = { game_id: number; title: string; thumb: string | null; offer: Offer; stores?: number; verdict?: string | null; genres?: string[]; discovered?: boolean };

export function GameCard({ c, i, tag }: { c: Card; i: number; tag?: string }) {
  const off = Math.round(c.offer.discount_pct);
  return (
    <a className="wob-card gcard rise" style={stag(i)} href={`#/jogo/${c.game_id}`}>
      {c.thumb && <div className="gthumb"><img src={c.thumb} alt="" loading="lazy" /></div>}
      <h3>{c.title}</h3>
      <div className="line" style={{ justifyContent: "space-between" }}>
        <span className="t-price-lg wob-num">{brl(c.offer.price_brl)}</span>
        <span className="wob-data">{off > 0 && <span className="wob-off">−{off}%</span>}</span>
      </div>
      {c.verdict && <Verdict verdict={c.verdict} small />}
      <span className="wob-cap"><StoreBadge id={c.offer.store_id} name={c.offer.store_name} estimated={c.offer.is_estimated} />{c.stores ? ` · ${c.stores} lojas` : ""}{c.offer.is_estimated ? " · estimado" : ""}</span>
      {c.genres && c.genres.length > 0 && <span className="wob-cap gtag">{c.genres.slice(0, 2).join(" · ")}</span>}
      {tag && <span className="wob-cap gtag">{tag}</span>}
    </a>
  );
}
