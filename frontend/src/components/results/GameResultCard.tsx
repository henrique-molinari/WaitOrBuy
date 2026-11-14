import { brl } from "../../api";
import type { Offer } from "../../types";
import { stag } from "../Motion";
import { StoreBadge } from "../StoreBadge";

export type GameResult = { game_id: number; title: string; thumb: string | null; offer: Offer; stores?: number; genres?: string[]; tag?: string };

// Opção da lista de resultados: nome do jogo e, logo abaixo, o MENOR preço entre as lojas.
export function GameResultCard({ g, i }: { g: GameResult; i: number }) {
  const off = Math.round(g.offer.discount_pct);
  return (
    <a className="wob-card rcard rise" style={stag(i)} href={`#/jogo/${g.game_id}`}>
      <div className="rthumb">{g.thumb ? <img src={g.thumb} alt="" loading="lazy" /> : <span className="sk-img" />}</div>
      <h3 className="rtitle">{g.title}</h3>
      <div className="rprice">
        <span className="wob-cap">{g.stores && g.stores > 1 ? "A PARTIR DE" : "PREÇO"}</span>
        <span className="line" style={{ justifyContent: "space-between" }}>
          <span className="t-price-lg wob-num">{brl(g.offer.price_brl)}</span>
          {off > 0 && <span className="wob-off">−{off}%</span>}
        </span>
      </div>
      <span className="wob-cap">
        <StoreBadge id={g.offer.store_id} name={g.offer.store_name} estimated={g.offer.is_estimated} />
        {g.stores ? ` · ${g.stores} ${g.stores === 1 ? "loja" : "lojas"}` : ""}{g.offer.is_estimated ? " · estimado" : ""}
      </span>
      {g.tag && <span className="wob-cap gtag">{g.tag}</span>}
    </a>
  );
}
