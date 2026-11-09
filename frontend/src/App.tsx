// Protótipo MÍNIMO só para exercitar a API. A interface final será feita por outra pessoa.
// Todo texto vindo da API é renderizado como texto (sem dangerouslySetInnerHTML).
import { useEffect, useState } from "react";
import { CartesianGrid, Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { createUserWithEmailAndPassword, onAuthStateChanged, signInWithEmailAndPassword, signOut, type User } from "firebase/auth";
import { collection, onSnapshot, orderBy, query } from "firebase/firestore";
import { auth, db } from "./firebase";
import { api, brl } from "./api";

type Offer = { store_id: number; store_name: string; price_brl: number; discount_pct: number; price_origin: string; deal_url: string | null };
type View = { name: "home" } | { name: "game"; id: number } | { name: "wishlist" } | { name: "login" } | { name: "notifs" };

function Err({ e }: { e: string | null }) { return e ? <p role="alert" style={{ color: "#b00020" }}>{e}</p> : null; }

function OfferTable({ offers }: { offers: Offer[] }) {
  if (!offers.length) return <p>Sem ofertas no momento.</p>;
  return (
    <table><thead><tr><th>Loja</th><th>Preço</th><th>Desc.</th><th>Origem</th></tr></thead><tbody>
      {offers.map((o, i) => (
        <tr key={o.store_id}>
          <td>{i === 0 ? "★ " : ""}{o.deal_url ? <a href={o.deal_url} target="_blank" rel="sponsored noopener">{o.store_name}</a> : o.store_name}</td>
          <td>{brl(o.price_brl)}</td><td>{o.discount_pct}%</td>
          <td>{o.price_origin === "steam_brl" ? "preço real em R$ (Steam)" : "preço estimado (convertido pelo dólar PTAX)"}</td>
        </tr>))}
    </tbody></table>);
}

function Home({ go }: { go: (v: View) => void }) {
  const [q, setQ] = useState(""); const [res, setRes] = useState<any[] | null>(null); const [deals, setDeals] = useState<any[]>([]); const [err, setErr] = useState<string | null>(null);
  useEffect(() => { api("/api/deals/home").then((d) => setDeals(d.deals)).catch((e) => setErr(e.message)); }, []);
  const search = async (e: React.FormEvent) => { e.preventDefault(); setErr(null); try { setRes((await api(`/api/search?q=${encodeURIComponent(q)}`)).results); } catch (x: any) { setErr(x.message); } };
  const link = (id: number, text: string) => <a href="#" onClick={(e) => { e.preventDefault(); go({ name: "game", id }); }}>{text}</a>;
  return (<div>
    <form onSubmit={search}><input aria-label="Buscar jogo" placeholder="Buscar jogo…" value={q} onChange={(e) => setQ(e.target.value)} /> <button>Buscar</button></form>
    <Err e={err} />
    {res && (res.length === 0 ? <p>Nenhum jogo encontrado.</p> : res.map((r) => (
      <section key={r.game_id}><h3>{link(r.game_id, r.title)}</h3><OfferTable offers={r.offers} /></section>)))}
    {!res && <><h3>Em promoção</h3><ul>{deals.map((d) => (<li key={d.game_id}>{link(d.game_id, d.title)} — {brl(d.offer.price_brl)} (−{d.offer.discount_pct}% na {d.offer.store_name}{d.offer.is_estimated ? ", preço estimado" : ""})</li>))}</ul></>}
  </div>);
}

function Game({ id, user, go }: { id: number; user: User | null; go: (v: View) => void }) {
  const [g, setG] = useState<any>(null); const [h, setH] = useState<any>(null); const [days, setDays] = useState(90); const [err, setErr] = useState<string | null>(null); const [msg, setMsg] = useState<string | null>(null); const [target, setTarget] = useState("");
  useEffect(() => { api(`/api/games/${id}`).then(setG).catch((e) => setErr(e.message)); }, [id]);
  useEffect(() => { api(`/api/games/${id}/history?days=${days}`).then(setH).catch((e) => setErr(e.message)); }, [id, days]);
  if (err && !g) return <Err e={err} />;
  if (!g) return <p>Carregando…</p>;
  const act = async (fn: () => Promise<unknown>, ok: string) => { setErr(null); setMsg(null); try { await fn(); setMsg(ok); } catch (e: any) { setErr(e.message); } };
  return (<div>
    <h2>{g.title}</h2>
    {g.meta.is_fixture && <p><em>Catálogo de exemplo (dados de fixture): gêneros e tempo de jogo são estimativas.</em></p>}
    <p>Gêneros: {g.meta.genres.join(", ") || "—"} · Tempo médio: {g.playtime_hours ?? "—"} h · Preço por hora: {brl(g.price_per_hour)}</p>
    <OfferTable offers={g.offers} />
    {g.stats && <p>Menor preço histórico: <b>{brl(g.stats.min_price_brl)}</b> · Média: <b>{brl(g.stats.avg_price_brl)}</b> · {g.stats.history_days} dias de histórico{g.stats.has_simulated_history ? " (inclui dias simulados para demonstração)" : ""}</p>}
    <div style={{ border: "1px solid #888", padding: 8 }}><b>Vale esperar? {g.verdict.verdict}</b> (confiança {g.verdict.confidence})<ul>{g.verdict.reasons.map((r: string, i: number) => <li key={i}>{r}</li>)}</ul>
      {g.next_sale && <small>Próxima liquidação: {g.next_sale.name} em {g.next_sale.days} dia(s) — {g.next_sale.note}</small>}</div>
    <h3>Histórico (melhor preço do dia) {[30, 90, 180].map((d) => <button key={d} disabled={d === days} onClick={() => setDays(d)}>{d}d</button>)}</h3>
    {h?.has_simulated && <p><em>Histórico simulado para demonstração.</em></p>}
    <div style={{ height: 260 }}><ResponsiveContainer><LineChart data={h?.points ?? []}><CartesianGrid strokeDasharray="3 3" /><XAxis dataKey="date" minTickGap={40} /><YAxis domain={["auto", "auto"]} /><Tooltip /><Line type="monotone" dataKey="price_brl" dot={false} /></LineChart></ResponsiveContainer></div>
    <Err e={err} />{msg && <p role="status">{msg}</p>}
    {user ? (<p><button onClick={() => act(() => api("/api/me/wishlist", { method: "POST", body: { game_id: id }, authed: true }), "Adicionado à wishlist.")}>＋ Wishlist</button>{" "}
      <input aria-label="Preço alvo" placeholder="alvo R$" value={target} onChange={(e) => setTarget(e.target.value)} size={8} />
      <button onClick={() => act(() => api("/api/me/alerts", { method: "POST", body: { game_id: id, target_price_brl: Number(target.replace(",", ".")) }, authed: true }), "Alerta criado.")}>Criar alerta</button></p>)
      : <p><a href="#" onClick={(e) => { e.preventDefault(); go({ name: "login" }); }}>Entre</a> para usar wishlist e alertas.</p>}
  </div>);
}

function Wishlist({ go }: { go: (v: View) => void }) {
  const [wl, setWl] = useState<any[] | null>(null); const [cart, setCart] = useState<any>(null); const [alerts, setAlerts] = useState<any[]>([]); const [err, setErr] = useState<string | null>(null);
  const load = () => Promise.all([api("/api/me/wishlist", { authed: true }), api("/api/me/wishlist/cart", { authed: true }), api("/api/me/alerts", { authed: true })])
    .then(([w, c, a]) => { setWl(w.items); setCart(c); setAlerts(a.items); }).catch((e) => setErr(e.message));
  useEffect(() => { load(); }, []);
  const del = (path: string) => api(path, { method: "DELETE", authed: true }).then(load).catch((e) => setErr(e.message));
  if (!wl) return <><Err e={err} /><p>Carregando…</p></>;
  return (<div><Err e={err} />
    <h2>Wishlist</h2>{wl.length === 0 && <p>Vazia. Busque um jogo e adicione.</p>}
    <ul>{wl.map((i) => <li key={i.game_id}><a href="#" onClick={(e) => { e.preventDefault(); go({ name: "game", id: i.game_id }); }}>{i.title}</a> — {i.best_offer ? `${brl(i.best_offer.price_brl)} (${i.best_offer.store_name})` : "sem oferta"} <button onClick={() => del(`/api/me/wishlist/${i.game_id}`)}>remover</button></li>)}</ul>
    {cart && cart.stores.length > 0 && <><h3>Custo total por loja (valores de lojas não-Steam são estimados pelo dólar)</h3><ul>{cart.stores.map((s: any) => <li key={s.store_id}>{s.store_name}: {brl(s.total_brl)} {s.complete ? "" : `(incompleta, falta: ${s.missing_games.map((m: any) => m.title).join(", ")})`}</li>)}</ul>
      <p>Melhor combinação: <b>{brl(cart.best_mix.total_brl)}</b>{cart.best_mix.savings_vs_best_store_brl != null && ` — economia de ${brl(cart.best_mix.savings_vs_best_store_brl)} sobre a melhor loja única`}</p></>}
    <h3>Alertas</h3>{alerts.length === 0 && <p>Nenhum alerta.</p>}
    <ul>{alerts.map((a) => <li key={a.alert_id}>{a.title}: alvo {brl(a.target_price_brl)} {a.last_triggered_price != null ? `(disparado a ${brl(a.last_triggered_price)})` : ""} <button onClick={() => del(`/api/me/alerts/${a.alert_id}`)}>remover</button></li>)}</ul>
  </div>);
}

function Notifs({ items }: { items: any[] }) {
  const read = (id: string) => api(`/api/me/notifications/${id}/read`, { method: "POST", authed: true });
  return (<div><h2>Notificações</h2>{items.length === 0 && <p>Nenhuma notificação.</p>}
    <ul>{items.map((n) => <li key={n.id} style={{ fontWeight: n.read ? "normal" : "bold" }}>{n.title} — {n.body} {!n.read && <button onClick={() => read(n.id)}>marcar como lida</button>}</li>)}</ul></div>);
}

function Login({ done }: { done: () => void }) {
  const [email, setEmail] = useState("demo@waitorbuy.test"); const [pw, setPw] = useState(""); const [err, setErr] = useState<string | null>(null);
  const run = (signup: boolean) => async (e: React.SyntheticEvent) => {
    e.preventDefault(); setErr(null);
    try { await (signup ? createUserWithEmailAndPassword : signInWithEmailAndPassword)(auth, email, pw); done(); }
    catch { setErr("Não foi possível entrar: confira e-mail e senha (mín. 6 caracteres)."); }
  };
  return (<form onSubmit={run(false)}><h2>Entrar / Cadastrar</h2><input aria-label="E-mail" value={email} onChange={(e) => setEmail(e.target.value)} /> <input aria-label="Senha" type="password" value={pw} onChange={(e) => setPw(e.target.value)} /> <button>Entrar</button> <button onClick={run(true)}>Cadastrar</button><Err e={err} /></form>);
}

export default function App() {
  const [view, setView] = useState<View>({ name: "home" }); const [user, setUser] = useState<User | null>(null); const [notifs, setNotifs] = useState<any[]>([]);
  useEffect(() => onAuthStateChanged(auth, setUser), []);
  useEffect(() => { // notificações em tempo real (listener do Firestore)
    if (!user) { setNotifs([]); return; }
    return onSnapshot(query(collection(db, "users", user.uid, "notifications"), orderBy("created_at", "desc")), (s) => setNotifs(s.docs.map((d) => ({ id: d.id, ...d.data() }))), () => setNotifs([]));
  }, [user]);
  const unread = notifs.filter((n) => !n.read).length;
  const go = (v: View) => setView(v);
  const nav = (v: View, text: string, label?: string) => <a href="#" aria-label={label} onClick={(e) => { e.preventDefault(); go(v); }}>{text}</a>;
  return (<div style={{ maxWidth: 800, margin: "0 auto", padding: 16, fontFamily: "system-ui, sans-serif" }}>
    <header style={{ display: "flex", gap: 12, alignItems: "center", flexWrap: "wrap" }}>
      <b>WaitOrBuy</b><small>(protótipo)</small>
      {nav({ name: "home" }, "Início")}
      {user && nav({ name: "wishlist" }, "Wishlist")}
      {user && nav({ name: "notifs" }, `🔔 ${unread}`, `Notificações, ${unread} não lidas`)}
      <span style={{ marginLeft: "auto" }}>{user ? <>{user.email} <button onClick={() => signOut(auth)}>sair</button></> : nav({ name: "login" }, "Entrar")}</span>
    </header><hr />
    {view.name === "home" && <Home go={go} />}
    {view.name === "game" && <Game id={view.id} user={user} go={go} />}
    {view.name === "wishlist" && (user ? <Wishlist go={go} /> : <p>Faça login.</p>)}
    {view.name === "notifs" && <Notifs items={notifs} />}
    {view.name === "login" && <Login done={() => go({ name: "home" })} />}
    <hr /><small>Preços convertidos do dólar são estimativas; histórico inicial é simulado para demonstração.</small>
  </div>);
}
