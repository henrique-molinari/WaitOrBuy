import type React from "react";

// Escalonamento: --i limitado a 8 para listas longas não demorarem a aparecer.
export const stag = (i: number) => ({ "--i": Math.min(i, 8) }) as React.CSSProperties;

// Título palavra a palavra (máscara). Texto acessível fica no aria-label.
export const Words = ({ text }: { text: string }) => (
  <span className="words" aria-label={text}>{text.split(" ").map((w, i) => <span key={i} aria-hidden="true"><span className="w" style={stag(i)}><span>{w}</span></span>{" "}</span>)}</span>
);
