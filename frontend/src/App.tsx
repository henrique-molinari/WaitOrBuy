import { useEffect, useRef, useState } from "react";
import { flushSync } from "react-dom";
import { logOut, MOCK, onAuth, subscribeNotifs, type User } from "./session";
import { Toast, ThemeToggle, Wordmark } from "./ui";
import Home from "./pages/Home";
import Game from "./pages/Game";
import Wishlist from "./pages/Wishlist";
import Avisos from "./pages/Avisos";
import Login from "./pages/Login";
import Cadastro from "./pages/Cadastro";

const useHash = () => {
  const [h, setH] = useState(location.hash || "#/");
  useEffect(() => { const f = () => { setH(location.hash || "#/"); scrollTo(0, 0); }; addEventListener("hashchange", f); return () => removeEventListener("hashchange", f); }, []);
  return h;
};

export default function App() {
  const hash = useHash(); const [user, setUser] = useState<User | null | undefined>(undefined); const [notifs, setNotifs] = useState<any[]>([]);
  const [dark, setDark] = useState(() => { try { return localStorage.getItem("wob-theme") ? localStorage.getItem("wob-theme") === "dark" : matchMedia("(prefers-color-scheme: dark)").matches; } catch { return false; } });
  useEffect(() => { document.documentElement.dataset.theme = dark ? "dark" : "light"; try { localStorage.setItem("wob-theme", dark ? "dark" : "light"); } catch { /* sem storage */ } }, [dark]);
  useEffect(() => onAuth(setUser), []);
  useEffect(() => { // avisos em tempo real (Firestore)
    if (!user) { setNotifs([]); return; }
    return subscribeNotifs(user, setNotifs);
  }, [user]);
  const toggleTheme = () => { // dissolve entre temas; sem suporte ou com reduced-motion, troca direta
    const go = () => setDark((d) => !d), vt = (document as any).startViewTransition?.bind(document);
    if (!vt || matchMedia("(prefers-reduced-motion: reduce)").matches) return go();
    vt(() => flushSync(go));
  };
  // Aviso na tela quando um alerta dispara com o app aberto (só para notificações recentes e ainda não vistas).
  const seen = useRef(new Set<string>()); const [toast, setToast] = useState<any | null>(null);
  useEffect(() => {
    if (!user) { seen.current.clear(); return; }
    const t = (n: any) => { const c = n.created_at; return (c?.toDate?.() ?? new Date(c)).getTime(); };
    const fresh = notifs.find((n) => !n.read && !seen.current.has(n.id) && Date.now() - t(n) < 60000);
    notifs.forEach((n) => seen.current.add(n.id));
    if (fresh) setToast(fresh);
  }, [notifs, user]);
  const unread = notifs.filter((n) => !n.read).length;
  const gm = hash.match(/^#\/jogo\/(\d+)/);
  const route = gm ? "jogo" : hash.replace(/^#\//, "");
  const nav = (to: string, text: string, label?: string) => <a className="nav" href={`#/${to}`} aria-current={route === to ? "page" : undefined} aria-label={label}>{text}</a>;
  const needLogin = <p className="body"><a href="#/entrar">Entre</a> para ver esta página.</p>;
  return (
    <div className="shell">
      {MOCK && <p className="notice notice--info" role="status" style={{ marginTop: "var(--space-2)" }}>Modo demonstração: dados fictícios, sem API.</p>}
      <header className="top">
        <a className="top-brand" href="#/" aria-label="WaitOrBuy, início"><Wordmark /></a>
        <nav aria-label="Principal">
          {nav("", "Início")}
          {user === null && <span className="nav-m">{nav("entrar", "Entrar")}</span>}
          {user && nav("wishlist", "Wishlist")}
          {user && nav("avisos", `Avisos${unread ? ` (${unread})` : ""}`, `Avisos, ${unread} não lidos`)}
        </nav>
        <div className="top-end">
          {user ? <><span className="wob-data top-mail" title={user.email ?? undefined}>{user.email}</span><button className="wob-btn wob-btn--secondary tbtn" onClick={() => logOut()}>Sair</button></>
            : user === null && <><a className="wob-btn wob-btn--secondary tbtn tbtn--login fadein" href="#/entrar">Entrar</a><a className="wob-btn wob-btn--primary tbtn fadein" href="#/cadastro">Criar conta</a></>}
          <ThemeToggle dark={dark} onClick={toggleTheme} />
        </div>
      </header>
      <main key={hash} className="page">
        {route === "" && <Home user={user} notifs={notifs} />}
        {gm && <Game id={Number(gm[1])} user={user ?? null} />}
        {route === "wishlist" && (user ? <Wishlist /> : needLogin)}
        {route === "avisos" && (user ? <Avisos items={notifs} user={user} /> : needLogin)}
        {route === "entrar" && <Login done={() => { location.hash = "#/"; }} />}
        {route === "cadastro" && <Cadastro done={() => { location.hash = "#/"; }} />}
      </main>
      {toast && <Toast n={toast} onClose={() => setToast(null)} />}
      <footer className="foot wob-hint">Preços de lojas fora da Steam são estimativas convertidas do dólar (PTAX). Histórico inicial simulado para demonstração.</footer>
    </div>
  );
}
