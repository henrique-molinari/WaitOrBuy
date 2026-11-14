import { useEffect, useState } from "react";
import { api, brl } from "../api";
import { Cap, Err, Verdict } from "../components";

export default function Wishlist() {
  const [wl, setWl] = useState<any[] | null>(null); const [cart, setCart] = useState<any>(null); const [alerts, setAlerts] = useState<any[]>([]); const [err, setErr] = useState<string | null>(null);
  const load = () => Promise.all([api("/api/me/wishlist", { authed: true }), api("/api/me/wishlist/cart", { authed: true }), api("/api/me/alerts", { authed: true })])
    .then(([w, c, a]) => { setWl(w.items); setCart(c); setAlerts(a.items); }).catch((e) => setErr(e.message));
  useEffect(() => { load(); }, []);
  const del = (path: string) => api(path, { method: "DELETE", authed: true }).then(load).catch((e) => setErr(e.message));
  if (!wl) return <><Err e={err} />{!err && <div className="skel" />}</>;
  const mix = cart?.best_mix;
  return (
    <div className="stack">
      <h1 className="t-display-lg">Wishlist</h1><Err e={err} />
      <section className="tight">
        {wl.length === 0 ? <p className="body">Nada por aqui. <a href="#/">Busque um jogo</a> e adicione.</p> : <div>
          {wl.map((i) => (
            <div className="item" key={i.game_id}>
              <div className="grow"><a className="plain" href={`#/jogo/${i.game_id}`}>{i.title}</a><small>{i.best_offer ? i.best_offer.store_name : "Sem oferta no momento"}</small></div>
              <span className="t-price-md wob-num">{i.best_offer ? brl(i.best_offer.price_brl) : "—"}</span>
              <button className="wob-btn wob-btn--text" aria-label={`Remover ${i.title}`} onClick={() => del(`/api/me/wishlist/${i.game_id}`)}>Remover</button>
            </div>))}
        </div>}
      </section>

      {cart?.stores.length > 0 && <section className="tight">
        <h2 className="t-display-md">Custo total por loja</h2>
        <div className="wob-card tight">
          <Cap>MELHOR COMBINAÇÃO</Cap>
          <span className="t-price-lg wob-num">{brl(mix.total_brl)}</span>
          {mix.savings_vs_best_store_brl != null && <p className="wob-hint">Economia de <b>{brl(mix.savings_vs_best_store_brl)}</b> sobre a melhor loja única.</p>}
        </div>
        <div>
          {cart.stores.map((s: any, i: number) => (
            <div className={`item${i === 0 && s.complete ? " item--hit" : ""}`} key={s.store_id}>
              <div className="grow"><strong>{s.store_name}</strong><small>{s.complete ? `${s.game_count} jogos` : `Incompleta, falta: ${s.missing_games.map((m: any) => m.title).join(", ")}`}</small></div>
              <span className="t-price-md wob-num">{brl(s.total_brl)}</span>
            </div>))}
        </div>
        <p className="wob-hint">Valores de lojas fora da Steam são estimados pelo dólar.</p>
      </section>}

      <section className="tight">
        <h2 className="t-display-md">Alertas</h2>
        {alerts.length === 0 ? <p className="body">Nenhum alerta. Crie um na página de um jogo.</p> : <div>
          {alerts.map((a) => (
            <div className={`item${a.last_triggered_price != null ? " item--hit" : ""}`} key={a.alert_id}>
              <div className="grow"><a className="plain" href={`#/jogo/${a.game_id}`}>{a.title}</a><small>Alvo {brl(a.target_price_brl)}{a.last_triggered_price != null && ` · disparado a ${brl(a.last_triggered_price)}`}</small></div>
              {a.last_triggered_price != null && <Verdict verdict="COMPRAR_AGORA" small />}
              <button className="wob-btn wob-btn--text" aria-label={`Remover alerta de ${a.title}`} onClick={() => del(`/api/me/alerts/${a.alert_id}`)}>Remover</button>
            </div>))}
        </div>}
      </section>
    </div>
  );
}
