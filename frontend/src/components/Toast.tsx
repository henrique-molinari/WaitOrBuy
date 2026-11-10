import { useEffect, useState } from "react";
import { Verdict } from "./Verdict";

// Aviso na tela: entra por baixo, some sozinho em 8s, sai pelo mesmo caminho. Fecha com Esc.
export function Toast({ n, onClose }: { n: { game_id: number; title: string; body: string }; onClose: () => void }) {
  const [out, setOut] = useState(false);
  const close = () => { setOut(true); setTimeout(onClose, 220); };
  useEffect(() => { setOut(false); const t = setTimeout(close, 8000); const k = (e: KeyboardEvent) => e.key === "Escape" && close(); addEventListener("keydown", k); return () => { clearTimeout(t); removeEventListener("keydown", k); }; }, [n]);
  return (
    <div className={`toast${out ? " toast--out" : ""}`} role="status">
      <Verdict verdict="COMPRAR_AGORA" small />
      <div className="toast-t"><b>{n.title}</b><small>{n.body}</small></div>
      <a className="wob-btn wob-btn--primary tbtn" href={`#/jogo/${n.game_id}`} onClick={close}>Ver jogo</a>
      <button className="wob-btn wob-btn--text" onClick={close} aria-label="Fechar aviso">Fechar</button>
    </div>
  );
}
