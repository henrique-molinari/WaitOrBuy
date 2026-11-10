import { useState } from "react";

// Campo de senha com olho: a barra "risca" o olho (traço desenhado), a pupila encolhe. Um só gesto contínuo.
export function PasswordField({ id, label, value, onChange, autoComplete, minLength, describedBy }: { id: string; label: string; value: string; onChange: (v: string) => void; autoComplete: string; minLength?: number; describedBy?: string }) {
  const [show, setShow] = useState(false);
  return (
    <div className="wob-field"><label htmlFor={id}>{label}</label>
      <div className="wob-input wob-input--text">
        <input id={id} type={show ? "text" : "password"} autoComplete={autoComplete} value={value} onChange={(e) => onChange(e.target.value)} required minLength={minLength} aria-describedby={describedBy} />
        <button type="button" className="eye-btn" aria-label={show ? "Ocultar senha" : "Mostrar senha"} aria-pressed={show} aria-controls={id} onClick={() => setShow(!show)}>
          <svg viewBox="0 0 24 24" aria-hidden="true" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinejoin="miter" data-off={!show}>
            <path d="M2 12s3.6-7 10-7 10 7 10 7-3.6 7-10 7S2 12 2 12z" />
            <circle className="eye-pupil" cx="12" cy="12" r="3" />
            <path className="eye-cut" pathLength={1} d="M4 4L20 20" />
            <path className="eye-slash" pathLength={1} d="M4 4L20 20" />
          </svg>
        </button>
      </div>
    </div>
  );
}
