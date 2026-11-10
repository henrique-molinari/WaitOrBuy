import { useEffect, useState } from "react";
import type { User } from "../session";
import { api, brl } from "../api";
import { PushPrompt } from "../push";
import { pushRecent } from "../recent";
import { Cap, Err, GameSkeleton, Loadable, PriceChart, StoreRows, stag, Verdict } from "../components";

export default function Game({ id, user }: { id: number; user: User | null }) {
  const [g, setG] = useState<any>(null); const [h, setH] = useState<any>(null); const [days, setDays] = useState(90);
  const [err, setErr] = useState<string | null>(null); const [msg, setMsg] = useState<string | null>(null); const [target, setTarget] = useState(""); const [made, setMade] = useState<number | null>(null);
  useEffect(() => { setG(null); setErr(null); api(`/api/games/${id}`).then(setG).catch((e) => setErr(e.message)); }, [id]);
  useEffect(() => { if (g) pushRecent({ id, title: g.title, thumb: g.thumb ?? null }); }, [g, id]);
  useEffect(() => { api(`/api/games/${id}/history?days=${days}`).then(setH).catch((e) => setErr(e.message)); }, [id, days]);
  if (err && !g) return <Err e={err} />;
  const view = () => {
  const act = async (fn: () => Promise<unknown>, ok: string): Promise<boolean> => { setErr(null); setMsg(null); try { await fn(); setMsg(ok); return true; } catch (e: any) { setErr(e.message); return false; } };
  const best = g.best_offer, v = g.verdict, s = g.stats;
  const tnum = Number(target.replace(",", "."));
  const hint = s && tnum > 0 && (tnum <= s.min_price_brl
    ? <>Seu alvo está no menor preço já visto (<b>{brl(s.min_price_brl)}</b>): pode demorar.</>
    : <>O menor preço já visto foi <b>{brl(s.min_price_brl)}</b>; seu alvo está {brl(tnum - s.min_price_brl)} acima.</>);
  return (
    <div className="stack">
      <div className="tight">
        <a className="plain" href="#/">← Voltar</a>
        <h1 className="t-display-lg">{g.title}</h1>
        <span className="wob-cap">{g.meta.genres.join(" · ") || "Gênero não informado"}{g.playtime_hours != null && ` · ${g.playtime_hours} h de jogo`}{g.price_per_hour != null && ` · ${brl(g.price_per_hour)} por hora`}</span>
      </div>

      {(g.meta.background_image ?? g.thumb) && <img className="cover" src={g.meta.background_image ?? g.thumb} alt={`Capa de ${g.title}`} onError={(e) => { e.currentTarget.style.display = "none"; }} />}

      <section className="tight" aria-label="Veredito">
        <div className="price-line">
          <div className="tight" style={{ gap: "var(--space-2)" }}>
            <Cap>MENOR PREÇO AGORA{best ? ` · ${best.store_name.toUpperCase()}` : ""}</Cap>
            <span className="t-price-hero wob-num rise" style={{ animationDelay: "120ms" }}>{brl(best?.price_brl)}</span>
          </div>
          <span style={{ "--vd": "350ms" } as React.CSSProperties}><Verdict verdict={v.verdict} /></span>
        </div>
        <p className="t-body-lg reason rise" style={{ animationDelay: "450ms" }}>{v.reasons[0]}</p>
        {v.reasons.slice(1).map((r: string, i: number) => <p key={i} className="wob-hint">{r}</p>)}
        <Cap>CONFIANÇA {String(v.confidence).toUpperCase()}{g.next_sale ? ` · ${g.next_sale.name.toUpperCase()} EM ${g.next_sale.days} DIAS` : ""}</Cap>
      </section>

      <section className="tight">
        <h2 className="t-display-md">Onde comprar</h2><p className="wob-hint">Ranking do menor ao maior preço, em reais.</p>
        <StoreRows offers={g.offers} />
        <p className="wob-hint">Steam, Nuuvem e Instant Gaming informam o preço real em reais; nas demais lojas o valor é estimado pelo dólar PTAX e pode divergir.</p>
      </section>

      <section className="tight">
        <div className="head">
          <h2 className="t-display-md">Histórico de preço</h2>
          <div className="seg" role="group" aria-label="Período">
            {[30, 90, 180].map((d) => <button key={d} className={`wob-btn ${d === days ? "wob-btn--primary" : "wob-btn--secondary"}`} aria-pressed={d === days} onClick={() => setDays(d)}>{d} dias</button>)}
          </div>
        </div>
        <div className="wob-card"><PriceChart points={h?.points ?? []} /></div>
        {s && <div className="stats"><div><Cap>MENOR PREÇO HISTÓRICO</Cap><span className="t-price-md wob-num">{brl(s.min_price_brl)}</span></div><div><Cap>MÉDIA HISTÓRICA</Cap><span className="t-price-md wob-num">{brl(s.avg_price_brl)}</span></div><div><Cap>DIAS DE HISTÓRICO</Cap><span className="t-price-md wob-num">{s.history_days}</span></div></div>}
        {(h?.has_simulated || g.meta.is_fixture) && <p className="wob-hint">{h?.has_simulated && "Parte do histórico é simulada para demonstração. "}{g.meta.is_fixture && "Gêneros e tempo de jogo são estimativas editoriais."}</p>}
      </section>

      <section className="wob-card tight" aria-label="Alerta de preço">
        <h2 className="t-display-md">Avise-me</h2>
        {!user ? <p className="body"><a href="#/entrar">Entre</a> para criar alertas e guardar este jogo na wishlist.</p> : <>
          <div className="wob-field"><label htmlFor="alvo">Avisar quando chegar a</label>
            <div className="wob-input"><span>R$</span><input id="alvo" inputMode="decimal" value={target} onChange={(e) => setTarget(e.target.value)} /></div></div>
          {hint && <p className="wob-hint">{hint}</p>}
          <div className="line">
            <button className="wob-btn wob-btn--primary" disabled={!(tnum > 0)} onClick={() => act(() => api("/api/me/alerts", { method: "POST", body: { game_id: id, target_price_brl: tnum }, authed: true }), `Alerta criado: avisamos quando chegar a ${brl(tnum)}.`).then((done) => done && setMade(tnum))}>Criar alerta</button>
            <button className="wob-btn wob-btn--secondary" onClick={() => act(() => api("/api/me/wishlist", { method: "POST", body: { game_id: id }, authed: true }), "Adicionado à wishlist.")}>Adicionar à wishlist</button>
          </div>
        </>}
        {user && made !== null && <PushPrompt uid={user.uid} title="Avisar também neste dispositivo?" body={`Ative as notificações para saber na hora quando ${g.title} chegar a ${brl(made)}.`} />}
        <Err e={err} />{msg && <p role="status" className="notice notice--buy">{msg}</p>}
      </section>
    </div>
  );
  };
  return <Loadable ready={!!g} skeleton={<GameSkeleton />}>{view}</Loadable>;
}
