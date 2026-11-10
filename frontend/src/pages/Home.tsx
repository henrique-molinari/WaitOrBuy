import { useEffect, useState } from "react";
import { api, brl } from "../api";
import { PushPrompt } from "../push";
import { clearRecent, getRecent, type Recent } from "../recent";
import type { User } from "../session";
import { Cap, CardsSkeleton, Err, Loadable, stag, Verdict, Words, type Offer } from "../ui";

type Card = { game_id: number; title: string; thumb: string | null; offer: Offer; stores?: number; verdict?: string | null };
type Me = { wl: Card[]; alerts: any[]; prices: Record<number, number | null> };

function GameCard({ c, i, tag }: { c: Card; i: number; tag?: string }) {
  return (
    <a className="wob-card gcard rise" style={stag(i)} href={`#/jogo/${c.game_id}`}>
      {c.thumb && <div className="gthumb"><img src={c.thumb} alt="" loading="lazy" /></div>}
      <h3>{c.title}</h3>
      <div className="line" style={{ justifyContent: "space-between" }}>
        <span className="t-price-lg wob-num">{brl(c.offer.price_brl)}</span>
        <span className="wob-data">{Math.round(c.offer.discount_pct) > 0 && <span className="wob-off">−{Math.round(c.offer.discount_pct)}%</span>}</span>
      </div>
      {c.verdict && <Verdict verdict={c.verdict} small />}
      <span className="wob-cap">{c.offer.store_name}{c.stores ? ` · ${c.stores} lojas` : ""}{c.offer.is_estimated ? " · estimado" : ""}</span>
      {tag && <span className="wob-cap gtag">{tag}</span>}
    </a>
  );
}

const greet = () => { const h = new Date().getHours(); return h < 12 ? "Bom dia" : h < 18 ? "Boa tarde" : "Boa noite"; };
const firstName = (email: string | null) => { const n = (email ?? "").split("@")[0].split(/[._\-+\d]+/)[0]; return n ? n[0].toUpperCase() + n.slice(1) : ""; };

function Personal({ user, notifs, me, err }: { user: User; notifs: any[]; me: Me | null; err: string | null }) {
  const unread = notifs.filter((n) => !n.read), hit = unread[0];
  const name = firstName(user.email);
  return (
    <section className="tight" aria-label="Para você">
      <Cap>{greet().toUpperCase()}{name ? `, ${name.toUpperCase()}` : ""}</Cap>
      <h2 className="t-display-md">Para você</h2>
      {hit && <a className="notice notice--buy hitbar rise" href={`#/jogo/${hit.game_id}`}><Verdict verdict="COMPRAR_AGORA" small /><span><b>{hit.title}</b>. {hit.body}</span></a>}
      <Err e={err} />
      <Loadable ready={me !== null || !!err} skeleton={<div className="tiles" aria-hidden="true">{[0, 1, 2].map((i) => <div key={i} className="sk sk--card" style={{ height: 112 }} />)}</div>}>{() => me && <>
        <div className="tiles">
          <a className={`wob-card tile rise${unread.length ? " tile--hit" : ""}`} style={stag(0)} href="#/avisos"><span className="t-price-lg wob-num">{unread.length}</span><Cap>AVISOS NÃO LIDOS</Cap></a>
          <a className="wob-card tile rise" style={stag(1)} href="#/wishlist"><span className="t-price-lg wob-num">{me.alerts.length}</span><Cap>ALERTAS ATIVOS</Cap></a>
          <a className="wob-card tile rise" style={stag(2)} href="#/wishlist"><span className="t-price-lg wob-num">{me.wl.length}</span><Cap>NA WISHLIST</Cap></a>
        </div>
        {me.alerts.length > 0 && <PushPrompt uid={user.uid} title="Receba os avisos no celular"
          body={me.alerts.length === 1 ? `Você tem 1 alerta ativo (${me.alerts[0].title}). Ative as notificações e avisamos assim que chegar a ${brl(me.alerts[0].target_price_brl)}.` : `Você tem ${me.alerts.length} alertas ativos. Ative as notificações e avisamos assim que algum chegar ao preço que você definiu.`} />}
        <h3 className="t-price-md wob-num sub">Seus alertas</h3>
        {me.alerts.length === 0 ? <p className="wob-hint">Nenhum alerta ainda. Abra um jogo e diga a que preço quer ser avisado.</p> : <div className="alist">
          {me.alerts.slice(0, 4).map((a, i) => {
            const p = me.prices[a.game_id], ok = p != null && p <= a.target_price_brl;
            return (
              <a key={a.alert_id} className={`item rise${ok ? " item--hit" : ""}`} style={stag(i)} href={`#/jogo/${a.game_id}`}>
                <div className="grow"><strong>{a.title}</strong><small>Alvo {brl(a.target_price_brl)}{p != null && ` · agora ${brl(p)}`}</small></div>
                {ok ? <Verdict verdict="COMPRAR_AGORA" small /> : p != null ? <span className="wob-data gap">faltam {brl(p - a.target_price_brl)}</span> : null}
              </a>);
          })}
        </div>}
        <h3 className="t-price-md wob-num sub">Sua wishlist</h3>
        {me.wl.length === 0 ? <p className="wob-hint">Sua wishlist está vazia. Adicione jogos na página deles para acompanhar o preço aqui.</p> : <>
          <div className="grid">{me.wl.slice(0, 3).map((c, i) => <GameCard key={c.game_id} c={c} i={i} />)}</div>
          {me.wl.length > 3 && <a className="plain more" href="#/wishlist">Ver os {me.wl.length} jogos da wishlist</a>}
        </>}
      </>}</Loadable>
    </section>
  );
}

function RecentRow() {
  const [items, setItems] = useState<Recent[]>(getRecent);
  if (!items.length) return null;
  return (
    <section className="tight" aria-label="Vistos recentemente">
      <h2 className="t-display-md">Vistos recentemente</h2>
      <div className="recent">{items.map((r, i) => (
        <a key={r.id} className="recent-item rise" style={stag(i)} href={`#/jogo/${r.id}`}>
          {r.thumb ? <img src={r.thumb} alt="" loading="lazy" /> : <span className="sk-img" />}<span>{r.title}</span>
        </a>))}</div>
      <button className="wob-btn wob-btn--text more" onClick={() => { clearRecent(); setItems([]); }}>Limpar histórico</button>
    </section>
  );
}

const STEPS = [
  ["Compare as lojas", "Steam, Epic Games, GOG, Humble e Fanatical lado a lado, tudo em reais."],
  ["Veja o histórico", "O gráfico mostra o menor preço, a média e quanto o jogo costuma custar."],
  ["Receba o veredito", "COMPRE AGORA ou VALE ESPERAR, sempre com o número que sustenta."],
];
const HowItWorks = () => (
  <section className="tight" aria-label="Como funciona">
    <h2 className="t-display-md">Como funciona</h2>
    <ol className="steps">{STEPS.map(([t, b], i) => (
      <li key={t} className="wob-card step rise" style={stag(i)}><span className="rk-n" aria-hidden="true">{i + 1}</span><h3 className="t-price-md wob-num">{t}</h3><p className="wob-hint">{b}</p></li>))}</ol>
  </section>
);

const Invite = () => (
  <section className="wob-card tight invite" aria-label="Criar conta">
    <h2 className="t-display-md">Avise-me quando baixar</h2>
    <p className="body">Crie uma conta, defina o preço que quer pagar e acompanhe tudo em um só lugar.</p>
    <div className="line"><a className="wob-btn wob-btn--primary" href="#/cadastro">Criar conta</a><a className="wob-btn wob-btn--secondary" href="#/entrar">Entrar</a></div>
  </section>
);

export default function Home({ user, notifs }: { user: User | null | undefined; notifs: any[] }) {
  const [q, setQ] = useState(""); const [res, setRes] = useState<Card[] | null>(null);
  const [deals, setDeals] = useState<Card[] | null>(null); const [err, setErr] = useState<string | null>(null);
  const [me, setMe] = useState<Me | null>(null); const [meErr, setMeErr] = useState<string | null>(null);
  useEffect(() => { api("/api/deals/home").then((d) => setDeals(d.deals.map((x: any) => ({ ...x, offer: x.offer })))).catch((e) => setErr(e.message)); }, []);
  useEffect(() => {
    setMe(null); setMeErr(null); if (!user) return; let dead = false;
    Promise.all([api("/api/me/wishlist", { authed: true }), api("/api/me/alerts", { authed: true })]).then(async ([w, a]) => {
      const alerts = a.items.filter((x: any) => x.active !== false), prices: Me["prices"] = {};
      await Promise.all(alerts.slice(0, 4).map((x: any) => x.current_price_brl !== undefined ? (prices[x.game_id] = x.current_price_brl) : api(`/api/games/${x.game_id}`).then((g: any) => { prices[x.game_id] = g.best_offer?.price_brl ?? null; }).catch(() => { prices[x.game_id] = null; })));
      if (!dead) setMe({ alerts, prices, wl: w.items.filter((i: any) => i.best_offer).map((i: any) => ({ game_id: i.game_id, title: i.title, thumb: i.thumb, offer: i.best_offer, verdict: i.verdict })) });
    }).catch((e) => { if (!dead) setMeErr(e.message); });
    return () => { dead = true; };
  }, [user?.uid]);
  const search = async (e: React.FormEvent) => {
    e.preventDefault(); setErr(null);
    if (!q.trim()) { setRes(null); return; }
    try { setRes((await api(`/api/search?q=${encodeURIComponent(q.trim())}`)).results.map((r: any) => ({ game_id: r.game_id, title: r.title, thumb: r.thumb, offer: r.best_offer, stores: r.offers.length })).filter((r: Card) => r.offer)); }
    catch (x: any) { setErr(x.message); }
  };
  const list = res ?? deals, wished = new Set(me?.wl.map((c) => c.game_id));
  return (
    <div className="stack">
      <section className="hero">
        <div className="hero-verdicts" aria-hidden="true">
          <span style={{ "--vd": "700ms" } as React.CSSProperties}><Verdict verdict="COMPRAR_AGORA" /></span>
          <span style={{ "--vd": "820ms" } as React.CSSProperties}><Verdict verdict="ESPERAR" /></span>
        </div>
        <h1 className="t-display-xl"><Words text="Espere ou compre?" /></h1>
        <form className="search rise" style={{ animationDelay: "520ms" }} onSubmit={search} role="search">
          <div className="wob-field" style={{ flex: 1, maxWidth: "none" }}>
            <label htmlFor="q">Buscar jogo</label>
            <div className="wob-input"><input id="q" value={q} onChange={(e) => setQ(e.target.value)} autoComplete="off" /></div>
          </div>
          <button className="wob-btn wob-btn--primary" style={{ alignSelf: "flex-end", height: 64 }}>Buscar</button>
        </form>
        <p className="wob-hint rise" style={{ marginTop: "var(--space-3)", animationDelay: "640ms" }}>Comparamos as lojas, convertemos para reais e dizemos se vale esperar.</p>
      </section>
      <Err e={err} />
      {!res && user && <Personal user={user} notifs={notifs} me={me} err={meErr} />}
      {!res && <RecentRow />}
      {!res && user === null && <HowItWorks />}
      <section className="tight" aria-live="polite">
        <h2 className="t-display-md">{res ? `Resultados para “${q.trim()}”` : "Em promoção agora"}</h2>
        <Loadable ready={list !== null || !!err} skeleton={<CardsSkeleton />}>{() => <>
          {list?.length === 0 && <p className="body">Nenhum jogo encontrado. Tente outro nome.</p>}
          {list && list.length > 0 && <div key={res ? q : "deals"} className="grid" style={{ marginTop: "var(--space-3)" }}>{list.map((c, i) => <GameCard key={c.game_id} c={c} i={i} tag={wished.has(c.game_id) ? "NA SUA WISHLIST" : undefined} />)}</div>}
        </>}</Loadable>
      </section>
      {!res && user === null && <Invite />}
    </div>
  );
}
