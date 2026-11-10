import { stag } from "./Motion";
import type { Offer } from "../types";
import { brl } from "../api";

// Ranking de lojas: 1º é o menor preço (ponto do logo); número = posição; diferença para o menor à direita.
export function StoreRows({ offers }: { offers: Offer[] }) {
  if (!offers.length) return <p className="wob-hint">Sem ofertas no momento.</p>;
  const best = offers[0].price_brl;
  return (
    <ol className="rank">
      {offers.map((o, i) => {
        const off = Math.round(o.discount_pct) > 0 ? ` · −${Math.round(o.discount_pct)}%` : "";
        return (
          <li key={o.store_id} className={`rk rise${i === 0 ? " rk--best" : ""}`} style={stag(i)}>
            <span className="rk-n" aria-label={`${i + 1}º lugar`}>{i + 1}</span>
            <div className="rk-store">
              {o.deal_url ? <a className="plain" href={o.deal_url} target="_blank" rel="sponsored noopener">{o.store_name}</a> : <b>{o.store_name}</b>}
              <small>{o.is_estimated ? "Preço estimado" : "Preço real em R$"}{off}</small>
            </div>
            <div className="rk-price">
              <span className="wob-num">{brl(o.price_brl)}</span>
              <small>{i === 0 ? "MENOR PREÇO" : `+${brl(o.price_brl - best)}`}</small>
            </div>
          </li>
        );
      })}
    </ol>
  );
}
