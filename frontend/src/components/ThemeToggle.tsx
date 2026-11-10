
// Botão de tema: sol ↔ lua em traço reto, girando e trocando de escala (sem preenchimento).
export const ThemeToggle = ({ dark, onClick }: { dark: boolean; onClick: () => void }) => (
  <button type="button" className="icon-btn theme-btn" aria-pressed={dark} aria-label={dark ? "Tema Noite ativo. Trocar para Papel" : "Tema Papel ativo. Trocar para Noite"} title={dark ? "Tema Papel" : "Tema Noite"} onClick={onClick}>
    <svg viewBox="0 0 24 24" aria-hidden="true" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinejoin="miter">
      <g className="ti ti-sun" data-on={!dark}><circle cx="12" cy="12" r="4" />{[0, 45, 90, 135, 180, 225, 270, 315].map((a) => <path key={a} d="M12 2.5v3" transform={`rotate(${a} 12 12)`} />)}</g>
      <g className="ti ti-moon" data-on={dark}><path d="M20 14.5A8.5 8.5 0 0 1 9.5 4a8.5 8.5 0 1 0 10.5 10.5z" /></g>
    </svg>
  </button>
);
