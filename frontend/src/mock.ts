// Backend FICTÍCIO para desenvolver o front sem API. Segue docs/CONTRACTS.md (formatos, erros, regra "vale esperar?").
// Ativo só com `npm run dev:mock` (VITE_MOCK=1). Estado (wishlist, alertas, avisos, login) persiste em localStorage.
type Opts = { method?: string; body?: any; authed?: boolean };
export type MockUser = { uid: string; email: string | null };

const brl = (v: number) => "R$ " + v.toFixed(2).replace(".", ",");
const err = (m: string) => new Error(m);
const iso = (d: Date) => d.toISOString().slice(0, 10);
const rng = (seed: number) => () => { seed = (seed + 0x6d2b79f5) | 0; let t = Math.imul(seed ^ (seed >>> 15), 1 | seed); t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t; return ((t ^ (t >>> 14)) >>> 0) / 4294967296; };

const STORES = [{ id: 1, name: "Steam" }, { id: 25, name: "Epic Games Store" }, { id: 7, name: "GOG" }, { id: 11, name: "Humble Store" }, { id: 15, name: "Fanatical" }];
type Def = { id: number; title: string; app: number; genres: string[]; hours: number | null; base: number; profile: "low" | "high" | "mid" | "short" | "none" };
const DEFS: Def[] = [
  { id: 1, title: "Hades", app: 1145360, genres: ["Roguelike", "Ação"], hours: 22, base: 73.99, profile: "low" },
  { id: 2, title: "Celeste", app: 504230, genres: ["Plataforma", "Indie"], hours: 8, base: 36.99, profile: "mid" },
  { id: 3, title: "Hollow Knight", app: 367520, genres: ["Metroidvania", "Indie"], hours: 27, base: 46.99, profile: "high" },
  { id: 4, title: "Stardew Valley", app: 413150, genres: ["Simulação", "Indie"], hours: 53, base: 24.99, profile: "mid" },
  { id: 5, title: "Elden Ring", app: 1245620, genres: ["RPG de ação", "Mundo aberto"], hours: 60, base: 229.9, profile: "high" },
  { id: 6, title: "Cyberpunk 2077", app: 1091500, genres: ["RPG", "Mundo aberto"], hours: 25, base: 199.9, profile: "low" },
  { id: 7, title: "Baldur's Gate 3", app: 1086940, genres: ["RPG", "Estratégia"], hours: 75, base: 199.9, profile: "high" },
  { id: 8, title: "Disco Elysium", app: 632470, genres: ["RPG", "Narrativo"], hours: 25, base: 119.9, profile: "short" },
  { id: 9, title: "Dead Cells", app: 588650, genres: ["Roguelike", "Ação"], hours: 14, base: 69.99, profile: "mid" },
  { id: 10, title: "Outer Wilds", app: 753640, genres: ["Aventura", "Exploração"], hours: null, base: 59.99, profile: "none" },
];
const WINDOWS: Record<string, [number, number, number][]> = {
  low: [[145, 8, 0.6], [90, 6, 0.5], [40, 10, 0.7], [0, 12, 0.34]],
  high: [[133, 7, 0.5], [67, 8, 0.6], [26, 4, 0.65], [0, 30, 0.95]],
  mid: [[110, 10, 0.5], [52, 8, 0.6], [0, 20, 0.75]],
  short: [],
};
const price = (x: number) => Math.max(4.9, Math.floor(x) + 0.9);

function nextBlackFriday(now: Date) {
  for (let y = now.getFullYear(); ; y++) {
    const nov1 = new Date(Date.UTC(y, 10, 1)).getUTCDay(); // 4ª quinta + 1 dia
    const bf = new Date(Date.UTC(y, 10, 1 + ((4 - nov1 + 7) % 7) + 21 + 1));
    if (bf.getTime() >= now.getTime() - 864e5) return bf;
  }
}

function build(d: Def) {
  const r = rng(d.id * 7919), now = new Date();
  const N = d.profile === "short" ? 3 : d.profile === "none" ? 0 : 180;
  const series: { date: string; price_brl: number }[] = [];
  for (let i = N - 1; i >= 0; i--) { // i = dias atrás
    let m = 1; for (const [ago, len, mult] of WINDOWS[d.profile] ?? []) if (i >= ago && i < ago + len) m = mult; // ago = dia mais recente da janela
    if (d.profile === "short") m = 1 - i * 0.05;
    series.push({ date: iso(new Date(now.getTime() - i * 864e5)), price_brl: price(d.base * m) });
  }
  const best = series.length ? series[series.length - 1].price_brl : null;
  const order = [...STORES].sort(() => r() - 0.5); if (!order.some((s) => s.id === 1)) order[0] = STORES[0];
  const offers = best == null ? [] : order.slice(0, 3 + Math.floor(r() * 3)).map((s, i) => {
    const p = i === 0 ? best : price(best * (1.04 + r() * 0.3));
    return { store_id: s.id, store_name: s.name, price_brl: p, normal_price_brl: d.base, discount_pct: Math.max(0, Math.round((1 - p / d.base) * 1000) / 10),
      price_origin: s.id === 1 ? "steam_brl" : "converted_usd", is_estimated: s.id !== 1, deal_url: `https://example.com/oferta/${d.id}/${s.id}`, captured_at: now.toISOString() };
  }).sort((a, b) => a.price_brl - b.price_brl);
  return { d, series, offers };
}
const DB = DEFS.map(build);
const find = (id: number) => DB.find((g) => g.d.id === id);
const thumb = (d: Def) => `https://cdn.cloudflare.steamstatic.com/steam/apps/${d.app}/header.jpg`;

function analyze(g: ReturnType<typeof build>) {
  const v = g.series.map((p) => p.price_brl), N = v.length, nowP = g.offers[0]?.price_brl ?? null;
  if (!N || nowP == null) return { stats: null, verdict: { verdict: "INSUFICIENTE", confidence: "baixa", based_on_simulated: false, reasons: ["Sem ofertas nem histórico para este jogo ainda."], metrics: {} }, next_sale: null };
  const min = Math.min(...v), avg = v.reduce((a, b) => a + b, 0) / N, l90 = v.slice(-90), avg90 = l90.reduce((a, b) => a + b, 0) / l90.length;
  const bf = nextBlackFriday(new Date()), days = Math.ceil((bf.getTime() - Date.now()) / 864e5), disc = Math.round((1 - nowP / g.d.base) * 100);
  let verdict = "NEUTRO", reasons = [`${brl(nowP)} está entre o mínimo (${brl(min)}) e a média (${brl(avg)}); sem sinal claro.`];
  if (N < 5) { verdict = "INSUFICIENTE"; reasons = [`Só ${N} dias de histórico: ainda é cedo para opinar.`]; }
  else if (nowP <= min * 1.05) { verdict = "COMPRAR_AGORA"; reasons = [`${brl(nowP)} está no menor preço histórico ou muito perto (mínimo ${brl(min)}).`]; }
  else if (days <= 30 && nowP > min * 1.15) { verdict = "ESPERAR"; reasons = [`A Black Friday começa em ${days} dia(s) e o preço atual (${brl(nowP)}) está ${Math.round((nowP / min - 1) * 100)}% acima do mínimo histórico (${brl(min)}).`]; }
  else if (nowP >= avg90 * 0.95 && disc < 20 && days > 30) { verdict = "ESPERAR"; reasons = [`${brl(nowP)} está perto da média dos últimos 90 dias (${brl(avg90)}) e o desconto é de só ${disc}%.`]; }
  if (N >= 5) reasons.push("O histórico usado inclui dias simulados para demonstração.");
  return {
    stats: { min_price_brl: min, avg_price_brl: Math.round(avg * 100) / 100, avg_90d_brl: Math.round(avg90 * 100) / 100, points: N, first_day: g.series[0].date, history_days: N, has_simulated_history: true },
    verdict: { verdict, confidence: N >= 90 ? "alta" : N >= 30 ? "media" : "baixa", based_on_simulated: true, reasons, metrics: { price_now: nowP, min_ever: min, avg_all: avg, avg_90d: avg90, discount_pct: disc, days_to_next_sale: days, sale_name: "Black Friday", history_days: N } },
    next_sale: { name: "Black Friday", start_date: iso(bf), days, note: "verificar calendário oficial" },
  };
}

/* ---------- estado persistente (wishlist, alertas, avisos, login) ---------- */
type Notif = { id: string; title: string; body: string; game_id: number; price_brl: number; store_id: number; created_at: string; read: boolean };
type State = { user: MockUser | null; wishlist: { game_id: number; added_at: string }[]; alerts: any[]; notifs: Notif[] };
const KEY = "wob-mock-state";
const seed = (): State => ({
  user: null,
  wishlist: [1, 3].map((game_id) => ({ game_id, added_at: new Date().toISOString() })),
  alerts: [{ alert_id: "a1", game_id: 3, target_price_brl: 25, store_id: null, active: true, last_triggered_price: null, last_triggered_at: null }],
  notifs: [{ id: "n1", title: "Hades chegou ao seu preço", body: `Hades por ${brl(find(1)!.offers[0].price_brl)} na ${find(1)!.offers[0].store_name} (alvo R$ 30,00).`, game_id: 1, price_brl: find(1)!.offers[0].price_brl, store_id: find(1)!.offers[0].store_id, created_at: new Date().toISOString(), read: false }],
});
let S: State = (() => { try { return JSON.parse(localStorage.getItem(KEY) ?? "") as State; } catch { return seed(); } })();
const save = () => { try { localStorage.setItem(KEY, JSON.stringify(S)); } catch { /* sem storage */ } listeners.forEach((f) => f()); };
const listeners = new Set<() => void>();
const notifList = () => [...S.notifs].sort((a, b) => b.created_at.localeCompare(a.created_at));

export const mockSession = {
  onAuth(cb: (u: MockUser | null) => void) { cb(S.user); const f = () => cb(S.user); authL.add(f); return () => { authL.delete(f); }; },
  async signIn(email: string, pw: string) { await wait(); if (email === "demo@waitorbuy.test" && pw === "demo-123456") return setUser(email); throw err("auth/invalid-credential"); },
  async signUp(email: string, pw: string) { await wait(); if (pw.length < 6) throw err("auth/weak-password"); return setUser(email); },
  async logOut() { S.user = null; save(); authL.forEach((f) => f()); },
  getToken: async () => (S.user ? "mock-token" : undefined),
  subscribeNotifs(cb: (items: Notif[]) => void) { const f = () => cb(notifList()); listeners.add(f); f(); return () => { listeners.delete(f); }; },
};
const authL = new Set<() => void>();
const setUser = (email: string) => { S.user = { uid: "mock-user", email }; save(); authL.forEach((f) => f()); };
const wait = (ms = 250) => new Promise((r) => setTimeout(r, ms));
const norm = (s: string) => s.normalize("NFD").replace(/[̀-ͯ]/g, "").toLowerCase();
const card = (g: ReturnType<typeof build>) => ({ game_id: g.d.id, slug: norm(g.d.title).replace(/\W+/g, "-"), title: g.d.title, thumb: thumb(g.d) });

/* ---------- roteador: mesmos caminhos e formatos do CONTRACTS.md ---------- */
export async function mockApi(path: string, o: Opts = {}): Promise<any> {
  await wait();
  const url = new URL(path, "http://mock"), p = url.pathname, q = url.searchParams, m = (o.method ?? "GET").toUpperCase();
  if (o.authed && !S.user) throw err("Faça login para continuar.");
  let r: RegExpMatchArray | null;

  if (p === "/api/search") {
    const t = (q.get("q") ?? "").trim(); if (!t) throw err("Digite pelo menos 1 caractere para buscar.");
    const res = DB.filter((g) => norm(g.d.title).includes(norm(t))).slice(0, Number(q.get("limit") ?? 20)).map((g) => ({ ...card(g), best_offer: g.offers[0] ?? null, offers: g.offers, is_fixture: true }));
    return { query: t, count: res.length, results: res };
  }
  if (p === "/api/deals/home") {
    const deals = DB.filter((g) => g.offers.length).map((g) => ({ ...card(g), offer: g.offers[0] })).sort((a, b) => b.offer.discount_pct - a.offer.discount_pct).slice(0, Number(q.get("limit") ?? 12));
    return { count: deals.length, deals };
  }
  if ((r = p.match(/^\/api\/games\/(\d+)$/))) {
    const g = find(Number(r[1])); if (!g) throw err("Jogo não encontrado.");
    const a = analyze(g), best = g.offers[0] ?? null;
    return { ...card(g), meta: { background_image: thumb(g.d), genres: g.d.genres, platforms: ["PC"], rating: null, metacritic: null, released: null, description: null, playtime_hours: g.d.hours, is_fixture: true },
      offers: g.offers, best_offer: best, stats: a.stats, verdict: a.verdict, next_sale: a.next_sale, playtime_hours: g.d.hours, price_per_hour: best && g.d.hours ? Math.round((best.price_brl / g.d.hours) * 100) / 100 : null };
  }
  if ((r = p.match(/^\/api\/games\/(\d+)\/history$/))) {
    const g = find(Number(r[1])); if (!g) throw err("Jogo não encontrado.");
    const days = Number(q.get("days") ?? 180);
    return { game_id: g.d.id, store_id: null, days, has_simulated: true, points: g.series.slice(-days).map((pt) => ({ ...pt, store_id: g.offers[0]?.store_id ?? null, is_simulated: true })) };
  }
  if (p === "/api/fx") return { rate_date: iso(new Date()), usd_brl_buy: 5.5007, usd_brl_sell: 5.5013, source: "BCB PTAX (fictício)", fetched_at: new Date().toISOString() };

  if (p === "/api/me/wishlist" && m === "GET") return { items: S.wishlist.map((w) => { const g = find(w.game_id)!; return { ...card(g), added_at: w.added_at, best_offer: g.offers[0] ?? null, verdict: g.offers.length ? analyze(g).verdict.verdict : null }; }) };
  if (p === "/api/me/wishlist" && m === "POST") {
    const id = Number(o.body?.game_id); if (!find(id)) throw err("Jogo não encontrado.");
    if (!S.wishlist.some((w) => w.game_id === id)) S.wishlist.push({ game_id: id, added_at: new Date().toISOString() }); save(); return { game_id: id, added: true };
  }
  if ((r = p.match(/^\/api\/me\/wishlist\/(\d+)$/)) && m === "DELETE") { const id = Number(r[1]); S.wishlist = S.wishlist.filter((w) => w.game_id !== id); save(); return { game_id: id, removed: true }; }
  if (p === "/api/me/wishlist/cart") {
    const gs = S.wishlist.map((w) => find(w.game_id)!), per = (x: (typeof gs)[number]) => x.offers.map((of) => ({ of, g: x }));
    const stores = STORES.map((s) => {
      const items = gs.flatMap(per).filter((e) => e.of.store_id === s.id).map((e) => ({ game_id: e.g.d.id, title: e.g.d.title, price_brl: e.of.price_brl, price_origin: e.of.price_origin, deal_url: e.of.deal_url }));
      return { store_id: s.id, store_name: s.name, total_brl: Math.round(items.reduce((a, i) => a + i.price_brl, 0) * 100) / 100, complete: items.length === gs.length, missing_games: gs.filter((x) => !items.some((i) => i.game_id === x.d.id)).map((x) => ({ game_id: x.d.id, title: x.d.title })), game_count: items.length, items };
    }).filter((s) => s.game_count > 0).sort((a, b) => Number(b.complete) - Number(a.complete) || a.total_brl - b.total_brl);
    const mix = gs.filter((x) => x.offers.length).map((x) => ({ game_id: x.d.id, title: x.d.title, store_id: x.offers[0].store_id, store_name: x.offers[0].store_name, price_brl: x.offers[0].price_brl, price_origin: x.offers[0].price_origin, deal_url: x.offers[0].deal_url }));
    const total = Math.round(mix.reduce((a, i) => a + i.price_brl, 0) * 100) / 100, bestComplete = stores.find((s) => s.complete);
    return { game_count: gs.length, stores, best_mix: { total_brl: total, items: mix, missing_games: gs.filter((x) => !x.offers.length).map((x) => ({ game_id: x.d.id, title: x.d.title })), savings_vs_best_store_brl: bestComplete ? Math.round((bestComplete.total_brl - total) * 100) / 100 : null } };
  }
  if (p === "/api/me/alerts" && m === "GET") return { items: S.alerts.map((a) => ({ ...a, title: find(a.game_id)!.d.title, current_price_brl: find(a.game_id)!.offers[0]?.price_brl ?? null })) };
  if (p === "/api/me/alerts" && m === "POST") {
    const id = Number(o.body?.game_id), t = Number(o.body?.target_price_brl), g = find(id);
    if (!g) throw err("Jogo não encontrado."); if (!(t > 0)) throw err("O preço alvo deve ser maior que zero.");
    const alert = { alert_id: "a" + Date.now(), game_id: id, target_price_brl: t, store_id: null, active: true, last_triggered_price: null as number | null, last_triggered_at: null as string | null };
    const best = g.offers[0];
    if (best && best.price_brl <= t) { // simula a avaliação de alertas do backend: já está no alvo, então avisa
      alert.last_triggered_price = best.price_brl; alert.last_triggered_at = new Date().toISOString();
      S.notifs.push({ id: "n" + Date.now(), title: `${g.d.title} chegou ao seu preço`, body: `${g.d.title} por ${brl(best.price_brl)} na ${best.store_name} (alvo ${brl(t)}).`, game_id: id, price_brl: best.price_brl, store_id: best.store_id, created_at: new Date().toISOString(), read: false });
    }
    S.alerts.push(alert); save(); return { ...alert, title: g.d.title };
  }
  if ((r = p.match(/^\/api\/me\/alerts\/(.+)$/)) && m === "DELETE") { if (!S.alerts.some((a) => a.alert_id === r![1])) throw err("Alerta não encontrado."); S.alerts = S.alerts.filter((a) => a.alert_id !== r![1]); save(); return { alert_id: r[1], removed: true }; }
  if (p === "/api/me/notifications") { const items = notifList(); return { unread: items.filter((n) => !n.read).length, items }; }
  if ((r = p.match(/^\/api\/me\/notifications\/(.+)\/read$/)) && m === "POST") { const n = S.notifs.find((x) => x.id === r![1]); if (!n) throw err("Aviso não encontrado."); n.read = true; save(); return { id: n.id, read: true }; }
  if (p === "/api/me/devices") return { registered: true };
  throw err("Rota não encontrada no mock.");
}
