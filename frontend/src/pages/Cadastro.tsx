import { useState } from "react";
import { signIn } from "../session";
import { Err, PasswordField } from "../ui";

const MIN = 6; // mínimo do Firebase Auth

export default function Cadastro({ done }: { done: () => void }) {
  const [email, setEmail] = useState(""); const [pw, setPw] = useState(""); const [pw2, setPw2] = useState("");
  const [err, setErr] = useState<string | null>(null); const [busy, setBusy] = useState(false);
  const long = pw.length >= MIN, same = pw2.length > 0 && pw === pw2, diff = pw2.length > 0 && pw !== pw2;
  const submit = async (e: React.FormEvent) => {
    e.preventDefault(); if (!long || !same) return; setErr(null); setBusy(true);
    try { await signIn(email, pw, true); done(); }
    catch { setErr("Não foi possível criar a conta. Este e-mail pode já estar em uso."); setBusy(false); }
  };
  return (
    <form className="wob-card auth" onSubmit={submit}>
      <div className="tight"><h1 className="t-display-lg">Criar conta</h1><p className="wob-hint">Crie alertas de preço e guarde jogos na wishlist.</p></div>
      <div className="wob-field"><label htmlFor="email">E-mail</label><div className="wob-input wob-input--text"><input id="email" type="email" autoComplete="email" value={email} onChange={(e) => setEmail(e.target.value)} required /></div></div>
      <PasswordField id="pw" label="Senha" value={pw} onChange={setPw} autoComplete="new-password" minLength={MIN} describedBy="pw-rule" />
      <p id="pw-rule" className={`rule${long ? " rule--ok" : ""}`}><i aria-hidden="true" />Mínimo de {MIN} caracteres</p>
      <PasswordField id="pw2" label="Confirmar senha" value={pw2} onChange={setPw2} autoComplete="new-password" describedBy="pw2-rule" />
      <p id="pw2-rule" className={`rule${same ? " rule--ok" : diff ? " rule--bad" : ""}`} role="status"><i aria-hidden="true" />{diff ? "As senhas não conferem" : "Senhas iguais"}</p>
      <Err e={err} />
      <button className="wob-btn wob-btn--primary btn-block" disabled={busy || !long || !same}>{busy ? "Criando…" : "Criar conta"}</button>
      <p className="wob-hint">Já tem conta? <a href="#/entrar">Entrar</a></p>
    </form>
  );
}
