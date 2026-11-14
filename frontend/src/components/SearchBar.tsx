import { useEffect, useRef, useState } from "react";
import { api } from "../api";

type Sug = { game_id: number | null; title: string; live?: boolean };  // live = ainda fora do banco: buscar pelo título cadastra

// Campo de busca com autocomplete (banco local, rápido). Enter busca em todas as lojas.
export function SearchBar({ initial = "", onSubmit, autoFocus }: { initial?: string; onSubmit: (q: string) => void; autoFocus?: boolean }) {
  const [q, setQ] = useState(initial); const [sug, setSug] = useState<Sug[]>([]); const [open, setOpen] = useState(false); const [act, setAct] = useState(-1);
  const seq = useRef(0);
  useEffect(() => setQ(initial), [initial]);
  useEffect(() => {
    const t = q.trim();
    if (t.length < 2) { setSug([]); return; }
    const id = ++seq.current, h = setTimeout(() => api(`/api/suggest?q=${encodeURIComponent(t)}`).then((d) => { if (id === seq.current) setSug(d.suggestions); }).catch(() => setSug([])), 180);
    return () => clearTimeout(h);
  }, [q]);
  const go = (v: string) => { setOpen(false); setAct(-1); onSubmit(v.trim()); };
  const key = (e: React.KeyboardEvent) => {
    if (e.key === "ArrowDown") { e.preventDefault(); setAct((a) => Math.min(sug.length - 1, a + 1)); }
    else if (e.key === "ArrowUp") { e.preventDefault(); setAct((a) => Math.max(-1, a - 1)); }
    else if (e.key === "Escape") setOpen(false);
    else if (e.key === "Enter" && act >= 0 && sug[act]) { e.preventDefault(); const s = sug[act]; if (s.game_id) { setOpen(false); location.hash = `#/jogo/${s.game_id}`; } else go(s.title); }
  };
  return (
    <form className="search rise" style={{ animationDelay: "520ms" }} role="search" onSubmit={(e) => { e.preventDefault(); go(q); }}>
      <div className="wob-field sbox" style={{ flex: 1, maxWidth: "none" }}>
        <label htmlFor="q">Buscar jogo</label>
        <div className="wob-input">
          <input id="q" value={q} autoFocus={autoFocus} autoComplete="off" role="combobox" aria-expanded={open && sug.length > 0} aria-controls="q-list" aria-activedescendant={act >= 0 ? `q-${act}` : undefined}
            onChange={(e) => { setQ(e.target.value); setOpen(true); setAct(-1); }} onFocus={() => setOpen(true)} onBlur={() => setTimeout(() => setOpen(false), 120)} onKeyDown={key} />
        </div>
        {open && sug.length > 0 && <ul id="q-list" className="sug" role="listbox">{sug.map((s, i) => (
          <li key={s.game_id ?? s.title} id={`q-${i}`} role="option" aria-selected={i === act}><a href={s.game_id ? `#/jogo/${s.game_id}` : `#/busca?q=${encodeURIComponent(s.title)}`} onMouseDown={(e) => e.preventDefault()}>{s.title}{s.live && <span className="wob-cap sug-new"> · buscar nas lojas</span>}</a></li>))}</ul>}
      </div>
      <button className="wob-btn wob-btn--primary search-btn">Buscar</button>
    </form>
  );
}
