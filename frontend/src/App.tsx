import { useEffect, useState } from "react";
import { logOut, MOCK, onAuth, subscribeNotifs, type User } from "./session";
import { Wordmark } from "./ui";
import Home from "./pages/Home";
import Game from "./pages/Game";
import Wishlist from "./pages/Wishlist";
import Avisos from "./pages/Avisos";
import Login from "./pages/Login";

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
  const unread = notifs.filter((n) => !n.read).length;
  const gm = hash.match(/^#\/jogo\/(\d+)/);
  const route = gm ? "jogo" : hash.replace(/^#\//, "");
  const nav = (to: string, text: string, label?: string) => <a className="nav" href={`#/${to}`} aria-current={route === to ? "page" : undefined} aria-label={label}>{text}</a>;
  const needLogin = <p className="body"><a href="#/entrar">Entre</a> para ver esta página.</p>;
  return (
    <div className="shell">
      {MOCK && <p className="notice notice--info" role="status" style={{ marginTop: "var(--space-2)" }}>Modo demonstração: dados fictícios, sem API.</p>}
      <header className="top">
        <a href="#/" aria-label="WaitOrBuy, início" style={{ textDecoration: "none" }}><Wordmark /></a>
        <nav aria-label="Principal">
          {nav("", "Início")}
          {user && nav("wishlist", "Wishlist")}
          {user && nav("avisos", `Avisos${unread ? ` (${unread})` : ""}`, `Avisos, ${unread} não lidos`)}
          {user ? <><span className="wob-data">{user.email}</span><button className="wob-btn wob-btn--text" onClick={() => logOut()}>Sair</button></> : user === null && nav("entrar", "Entrar")}
          <button className="wob-btn wob-btn--secondary" style={{ height: 36 }} aria-pressed={dark} onClick={() => setDark(!dark)}>{dark ? "Tema Papel" : "Tema Noite"}</button>
        </nav>
      </header>
      <main>
        {route === "" && <Home />}
        {gm && <Game id={Number(gm[1])} user={user ?? null} />}
        {route === "wishlist" && (user ? <Wishlist /> : needLogin)}
        {route === "avisos" && (user ? <Avisos items={notifs} /> : needLogin)}
        {route === "entrar" && <Login done={() => { location.hash = "#/"; }} />}
      </main>
      <footer className="foot wob-hint">Preços de lojas fora da Steam são estimativas convertidas do dólar (PTAX). Histórico inicial simulado para demonstração.</footer>
    </div>
  );
}
