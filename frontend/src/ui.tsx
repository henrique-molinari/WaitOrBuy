// Componentes da identidade WaitOrBuy (classes wob-* de design/components.css). Só tokens.
import { useEffect, useRef, useState, type ReactNode } from "react";
import { brl } from "./api";

export type Offer = { store_id: number; store_name: string; price_brl: number; normal_price_brl: number | null; discount_pct: number; price_origin: string; is_estimated: boolean; deal_url: string | null };
export type Point = { date: string; price_brl: number };

export const Mark = ({ size = 28 }: { size?: number }) => (
  <svg className="wob-mark" width={size} height={size} viewBox="0 0 64 64" aria-hidden="true">
    <path d="M7 13 L22 51 L32 25 L42 51 L57 13" fill="none" stroke="var(--ink)" strokeWidth="7" strokeMiterlimit="4" />
    <circle cx="42" cy="51" r="8" fill="var(--buy)" stroke="var(--ink)" strokeWidth="3.5" />
  </svg>
);

export const Wordmark = ({ size = 28 }: { size?: number }) => (
  <span className="brand"><Mark size={size} /><span className="wob-word" style={{ fontSize: size }}>Wait<i>Or</i><u>Buy</u></span></span>
);

const ICON = {
  buy: <path d="M9 2v11M3 8l6 6 6-6" fill="none" stroke="currentColor" strokeWidth="3" />,
  wait: <path d="M5 2v14M13 2v14" fill="none" stroke="currentColor" strokeWidth="3.5" />,
};

// API: COMPRAR_AGORA | ESPERAR | NEUTRO | INSUFICIENTE. NEUTRO/INSUFICIENTE não ganham verde nem vermelho.
export function Verdict({ verdict, small }: { verdict: string; small?: boolean }) {
  const sm = small ? " wob-verdict--sm" : "";
  if (verdict === "COMPRAR_AGORA") return <span className={`wob-verdict wob-verdict--buy${sm}`}><svg viewBox="0 0 18 18" aria-hidden="true">{ICON.buy}</svg>{small ? "Compre" : "Compre agora"}</span>;
  if (verdict === "ESPERAR") return <span className={`wob-verdict wob-verdict--wait${sm}`}><svg viewBox="0 0 18 18" aria-hidden="true">{ICON.wait}</svg>{small ? "Espere" : "Vale esperar"}</span>;
  return <span className={`wob-verdict wob-verdict--none${sm}`}>{verdict === "INSUFICIENTE" ? "Pouco histórico" : "Sem veredito claro"}</span>;
}

export const Err = ({ e }: { e: string | null }) => (e ? <p role="alert" className="notice notice--wait">{e}</p> : null);
export const Cap = ({ children }: { children: ReactNode }) => <span className="wob-cap">{children}</span>;

// Ranking de lojas: 1º é o menor preço (ponto do logo); número = posição; diferença para o menor à direita.
export function StoreRows({ offers }: { offers: Offer[] }) {
  if (!offers.length) return <p className="wob-hint">Sem ofertas no momento.</p>;
  const best = offers[0].price_brl;
  return (
    <ol className="rank">
      {offers.map((o, i) => {
        const off = Math.round(o.discount_pct) > 0 ? ` · −${Math.round(o.discount_pct)}%` : "";
        return (
          <li key={o.store_id} className={`rk${i === 0 ? " rk--best" : ""}`}>
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

// Histórico: degraus retos (o preço vale até a próxima leitura), rótulos diretos no gráfico, largura real do contêiner.
export function PriceChart({ points }: { points: Point[] }) {
  const box = useRef<HTMLDivElement>(null); const [W, setW] = useState(720);
  useEffect(() => { const el = box.current; if (!el) return; const ro = new ResizeObserver(() => setW(Math.max(260, el.clientWidth))); ro.observe(el); setW(Math.max(260, el.clientWidth)); return () => ro.disconnect(); }, [points.length < 2]); // o contêiner só existe depois de haver dados
  if (points.length < 2) return <p className="wob-hint">Histórico ainda curto: volte em alguns dias.</p>;
  const H = W < 520 ? 240 : 300, L = 52, R = 16, T = 40, B = 32;
  const vals = points.map((p) => p.price_brl), min = Math.min(...vals), last = points.length - 1;
  const avg = vals.reduce((a, b) => a + b, 0) / vals.length; // média do período mostrado
  const lo = Math.min(min, avg), hi = Math.max(...vals, avg), pad = (hi - lo) * 0.15 || 1, y0 = Math.max(0, lo - pad), y1 = hi + pad;
  const x = (i: number) => L + (i / last) * (W - L - R), y = (v: number) => T + (1 - (v - y0) / (y1 - y0)) * (H - T - B);
  let d = `M${x(0)} ${y(vals[0])}`; for (let i = 1; i <= last; i++) d += ` H${x(i)} V${y(vals[i])}`;
  const li = vals.lastIndexOf(min), nowIsLow = li >= last - 1;
  const ticks = [0, 1, 2].map((k) => y0 + ((y1 - y0) * (k + 0.5)) / 3);
  const dt = (i: number) => points[i].date.split("-").reverse().slice(0, 2).join("/");
  const anchor = (px: number) => (px < W * 0.3 ? "start" : px > W * 0.7 ? "end" : "middle");
  return (
    <div className="chartbox">
      <div ref={box} className="chartbox-in" style={{ height: H }}>
      <svg className="wob-chart" width={W} height={H} role="img" aria-label={`Histórico de preços: menor ${brl(min)}, agora ${brl(vals[last])}`}>
        {ticks.map((t) => <g key={t}><line className="grid" x1={L} x2={W - R} y1={y(t)} y2={y(t)} /><text x={L - 8} y={y(t) + 4} textAnchor="end">R$ {Math.round(t)}</text></g>)}
        <path className="avg" d={`M${L} ${y(avg)} H${W - R}`} /><text className="lbl" x={L + 6} y={y(avg) - 6} textAnchor="start">MÉDIA {brl(avg)}</text>
        <path className="line" d={d} />
        {!nowIsLow && <><circle className="low" cx={x(li)} cy={y(min)} r="8" /><text className="lbl" x={x(li)} y={y(min) - 16} textAnchor={anchor(x(li))}>MENOR {brl(min)}</text></>}
        {nowIsLow ? <circle className="low" cx={x(last)} cy={y(vals[last])} r="8" /> : <circle className="now" cx={x(last)} cy={y(vals[last])} r="5" />}
        <text className="lbl lbl--now" x={x(last)} y={y(vals[last]) + (Math.abs(y(vals[last]) - y(avg)) < 22 ? 26 : -16)} textAnchor="end">{nowIsLow ? "AGORA · MENOR PREÇO" : "AGORA"} {brl(vals[last])}</text>
        {[0, Math.round(last / 2), last].map((i) => <text key={i} x={x(i)} y={H - 8} textAnchor={i === 0 ? "start" : i === last ? "end" : "middle"}>{dt(i)}</text>)}
      </svg>
      </div>
      <ul className="legend"><li><i className="sw sw--line" />Melhor preço do dia</li><li><i className="sw sw--avg" />Média do período</li><li><i className="sw sw--low" />Menor preço</li></ul>
    </div>
  );
}
