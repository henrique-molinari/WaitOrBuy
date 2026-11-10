import { useState } from "react";
import { signIn } from "../session";
import { Err, PasswordField } from "../ui";

export default function Login({ done }: { done: () => void }) {
  const [email, setEmail] = useState(""); const [pw, setPw] = useState(""); const [err, setErr] = useState<string | null>(null); const [busy, setBusy] = useState(false);
  const submit = async (e: React.FormEvent) => {
    e.preventDefault(); setErr(null); setBusy(true);
    try { await signIn(email, pw); done(); }
    catch { setErr("Não foi possível entrar. Confira o e-mail e a senha."); setBusy(false); }
  };
  return (
    <form className="wob-card auth" onSubmit={submit}>
      <div className="tight"><h1 className="t-display-lg">Entrar</h1><p className="wob-hint">Veja seus alertas e a wishlist.</p></div>
      <div className="wob-field"><label htmlFor="email">E-mail</label><div className="wob-input wob-input--text"><input id="email" type="email" autoComplete="email" value={email} onChange={(e) => setEmail(e.target.value)} required /></div></div>
      <PasswordField id="pw" label="Senha" value={pw} onChange={setPw} autoComplete="current-password" />
      <Err e={err} />
      <button className="wob-btn wob-btn--primary btn-block" disabled={busy}>{busy ? "Entrando…" : "Entrar"}</button>
      <p className="wob-hint">Ainda não tem conta? <a href="#/cadastro">Criar conta</a></p>
      <p className="wob-hint">Demonstração: demo@waitorbuy.test / demo-123456</p>
    </form>
  );
}
