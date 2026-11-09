import { useState } from "react";
import { signIn } from "../session";
import { Err } from "../ui";

export default function Login({ done }: { done: () => void }) {
  const [email, setEmail] = useState(""); const [pw, setPw] = useState(""); const [err, setErr] = useState<string | null>(null);
  const run = (signup: boolean) => async (e: React.SyntheticEvent) => {
    e.preventDefault(); setErr(null);
    try { await signIn(email, pw, signup); done(); }
    catch { setErr("Não foi possível entrar. Confira o e-mail e a senha (mínimo de 6 caracteres)."); }
  };
  return (
    <form className="stack" onSubmit={run(false)} style={{ maxWidth: 420 }}>
      <h1 className="t-display-lg">Entrar</h1>
      <div className="wob-field"><label htmlFor="email">E-mail</label><div className="wob-input wob-input--text"><input id="email" type="email" autoComplete="email" value={email} onChange={(e) => setEmail(e.target.value)} required /></div></div>
      <div className="wob-field"><label htmlFor="pw">Senha</label><div className="wob-input wob-input--text"><input id="pw" type="password" autoComplete="current-password" value={pw} onChange={(e) => setPw(e.target.value)} required minLength={6} /></div></div>
      <Err e={err} />
      <div className="line"><button className="wob-btn wob-btn--primary">Entrar</button><button type="button" className="wob-btn wob-btn--secondary" onClick={run(true)}>Criar conta</button></div>
      <p className="wob-hint">Demonstração: demo@waitorbuy.test / demo-123456</p>
    </form>
  );
}
