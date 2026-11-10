import React from "react";
import { createRoot } from "react-dom/client";
import App from "./App";
import "./design/index.css";
import "./app.css";
import "./motion.css";

createRoot(document.getElementById("root")!).render(<React.StrictMode><App /></React.StrictMode>);

// Abertura: fica no mínimo o tempo da animação da marca e só sai com as fontes prontas (teto 2s).
const boot = document.getElementById("boot");
if (boot) {
  const first = !document.documentElement.classList.contains("booted");
  const fonts = Promise.race([document.fonts.ready, new Promise((r) => setTimeout(r, 2000))]);
  const min = new Promise((r) => setTimeout(r, first ? 1500 : 0));
  Promise.all([fonts, min]).then(() => {
    boot.classList.add("boot--out");
    boot.addEventListener("transitionend", () => boot.remove(), { once: true });
    setTimeout(() => boot.remove(), 800); // reduced-motion/aba em segundo plano
    try { sessionStorage.setItem("wob-booted", "1"); } catch { /* sem storage */ }
  });
}
