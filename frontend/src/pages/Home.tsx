import { useEffect, useState } from "react";
import { api, brl } from "../api";
import { Err, type Offer } from "../ui";

type Card = { game_id: number; title: string; thumb: string | null; offer: Offer; stores?: number };

function GameCard({ c }: { c: Card }) {
  return (
    <a className="wob-card gcard" href={`#/jogo/${c.game_id}`}>
      {c.thumb && <img src={c.thumb} alt="" loading="lazy" />}
      <h3>{c.title}</h3>
      <div className="line" style={{ justifyContent: "space-between" }}>
        <span className="t-price-lg wob-num">{brl(c.offer.price_brl)}</span>
        <span className="wob-data">{Math.round(c.offer.discount_pct) > 0 && <span className="wob-off">−{Math.round(c.offer.discount_pct)}%</span>}</span>
      </div>
      <span className="wob-cap">{c.offer.store_name}{c.stores ? ` · ${c.stores} lojas` : ""}{c.offer.is_estimated ? " · estimado" : ""}</span>
    </a>
  );
}

export default function Home() {
  const [q, setQ] = useState(""); const [res, setRes] = useState<Card[] | null>(null);
  const [deals, setDeals] = useState<Card[] | null>(null); const [err, setErr] = useState<string | null>(null);
  useEffect(() => { api("/api/deals/home").then((d) => setDeals(d.deals.map((x: any) => ({ ...x, offer: x.offer })))).catch((e) => setErr(e.message)); }, []);
  const search = async (e: React.FormEvent) => {
    e.preventDefault(); setErr(null);
    if (!q.trim()) { setRes(null); return; }
    try { setRes((await api(`/api/search?q=${encodeURIComponent(q.trim())}`)).results.map((r: any) => ({ game_id: r.game_id, title: r.title, thumb: r.thumb, offer: r.best_offer, stores: r.offers.length })).filter((r: Card) => r.offer)); }
    catch (x: any) { setErr(x.message); }
  };
  const list = res ?? deals;
  return (
    <>
      <section className="hero">
        <h1 className="t-display-xl">Espere ou compre?</h1>
        <form className="search" onSubmit={search} role="search">
          <div className="wob-field" style={{ flex: 1, maxWidth: "none" }}>
            <label htmlFor="q">Buscar jogo</label>
            <div className="wob-input"><input id="q" value={q} onChange={(e) => setQ(e.target.value)} autoComplete="off" /></div>
          </div>
          <button className="wob-btn wob-btn--primary" style={{ alignSelf: "flex-end", height: 64 }}>Buscar</button>
        </form>
        <p className="wob-hint" style={{ marginTop: "var(--space-3)" }}>Comparamos as lojas, convertemos para reais e dizemos se vale esperar.</p>
      </section>
      <Err e={err} />
      <section className="tight" aria-live="polite">
        <h2 className="t-display-md">{res ? `Resultados para “${q.trim()}”` : "Em promoção agora"}</h2>
        {list === null && !err && <div className="skel" />}
        {list?.length === 0 && <p className="body">Nenhum jogo encontrado. Tente outro nome.</p>}
        {list && list.length > 0 && <div className="grid" style={{ marginTop: "var(--space-3)" }}>{list.map((c) => <GameCard key={c.game_id} c={c} />)}</div>}
      </section>
    </>
  );
}
