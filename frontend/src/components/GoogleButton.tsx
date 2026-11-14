import { useState } from "react";
import { signInGoogle } from "../session";

const MSG: Record<string, string> = {
  "auth/popup-blocked": "O navegador bloqueou a janela do Google. Libere pop-ups para este site e tente de novo.",
  "auth/unauthorized-domain": "Este endereço ainda não está autorizado no login com Google. Avise o administrador do site.",
  "auth/operation-not-allowed": "O login com Google não está ativado neste projeto. Avise o administrador do site.",
  "auth/account-exists-with-different-credential": "Já existe uma conta com este e-mail usando outro método. Entre com e-mail e senha.",
  "auth/network-request-failed": "Sem conexão com o Google agora. Verifique a internet e tente de novo.",
};

/** Botão "Continuar com Google", usado no login e no cadastro. */
export function GoogleButton({ done, onError }: { done: () => void; onError: (msg: string) => void }) {
  const [busy, setBusy] = useState(false);
  const click = async () => {
    setBusy(true); onError("");
    try { if (await signInGoogle()) { done(); return; } }
    catch (e: any) { onError(MSG[e?.code] ?? "Não foi possível entrar com o Google agora. Tente de novo ou use e-mail e senha."); }
    setBusy(false);
  };
  return (
    <>
      <button type="button" className="wob-btn btn-block btn-google" onClick={click} disabled={busy}>
        <svg width="18" height="18" viewBox="0 0 48 48" aria-hidden="true"><path fill="#EA4335" d="M24 9.5c3.5 0 6.6 1.2 9.1 3.6l6.8-6.8C35.8 2.4 30.3 0 24 0 14.6 0 6.5 5.4 2.6 13.2l7.9 6.1C12.4 13.6 17.7 9.5 24 9.5z" /><path fill="#4285F4" d="M46.5 24.5c0-1.6-.1-3.1-.4-4.5H24v9h12.7c-.6 3-2.3 5.5-4.8 7.2l7.5 5.8c4.4-4.1 7.1-10.1 7.1-17.5z" /><path fill="#FBBC05" d="M10.5 28.7c-.5-1.5-.8-3-.8-4.7s.3-3.2.8-4.7l-7.9-6.1C.9 16.4 0 20.1 0 24s.9 7.6 2.6 10.8l7.9-6.1z" /><path fill="#34A853" d="M24 48c6.5 0 11.9-2.1 15.9-5.8l-7.5-5.8c-2.1 1.4-4.9 2.3-8.4 2.3-6.3 0-11.6-4.1-13.5-9.8l-7.9 6.1C6.5 42.6 14.6 48 24 48z" /></svg>
        {busy ? "Abrindo o Google…" : "Continuar com Google"}
      </button>
      <p className="or" aria-hidden="true"><span>ou</span></p>
    </>
  );
}
