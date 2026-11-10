import { useEffect, useRef, useState, type ReactNode } from "react";
import { stag } from "./Motion";

// Skeletons com a forma do conteúdo real (evita salto de layout).
export const CardsSkeleton = ({ n = 6 }: { n?: number }) => (
  <div className="grid" aria-hidden="true">{Array.from({ length: n }, (_, i) => (
    <div key={i} className="sk-card rise" style={stag(i)}><div className="sk sk-img" /><div className="sk sk-t" /><div className="sk sk-p" /><div className="sk sk-c" /></div>
  ))}</div>
);
export const GameSkeleton = () => (
  <div className="stack" role="status" aria-label="Carregando jogo">
    <div className="tight" style={{ alignItems: "center" }}><div className="sk sk-line" style={{ width: 72 }} /><div className="sk" style={{ height: 60, width: "min(420px,80%)" }} /><div className="sk sk-line" style={{ width: 220 }} /></div>
    <div className="sk sk--card" style={{ width: "100%", maxWidth: 460, aspectRatio: "460/215", margin: "0 auto" }} />
    <div className="tight" style={{ alignItems: "center" }}><div className="sk sk-line" style={{ width: 180 }} /><div className="sk" style={{ height: 80, width: 260 }} /><div className="sk" style={{ height: 40, width: 180, borderRadius: "var(--radius-pill)" }} /></div>
    <div className="sk-rows">{[0, 1, 2, 3].map((i) => <div key={i} className="sk" />)}</div>
  </div>
);

// Evita o flicker do skeleton: só aparece se a resposta passar de `delay`; uma vez visível, fica ao menos `min`;
// na saída dissolve para o conteúdo (os dois ocupam a mesma célula). Resposta rápida = nenhum skeleton.
export function Loadable({ ready, skeleton, children, delay = 160, min = 500 }: { ready: boolean; skeleton: ReactNode; children: () => ReactNode; delay?: number; min?: number }) {
  const [phase, setPhase] = useState<"wait" | "skel" | "out" | "done">(ready ? "done" : "wait"); const at = useRef(0);
  useEffect(() => {
    if (phase === "wait") { if (ready) { setPhase("done"); return; } const t = setTimeout(() => { at.current = Date.now(); setPhase("skel"); }, delay); return () => clearTimeout(t); }
    if (phase === "skel" && ready) { const t = setTimeout(() => setPhase("out"), Math.max(0, min - (Date.now() - at.current))); return () => clearTimeout(t); }
    if (phase === "out") { const t = setTimeout(() => setPhase("done"), 240); return () => clearTimeout(t); }
  }, [phase, ready, delay, min]);
  if (phase === "wait") return <div style={{ minHeight: "50vh" }} />;
  if (phase === "done") return <>{children()}</>;
  return <div className="xf">{phase === "out" && <div>{children()}</div>}<div className={phase === "out" ? "xf-leave" : undefined}>{skeleton}</div></div>;
}
