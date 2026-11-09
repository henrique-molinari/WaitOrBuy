// Fachada de autenticação e avisos: Firebase de verdade, ou mock (VITE_MOCK=1) sem tocar em rede.
import { mockSession, type MockUser } from "./mock";

export const MOCK = import.meta.env.VITE_MOCK === "1";
export type User = MockUser;
const fb = async () => ({ ...(await import("./firebase")), a: await import("firebase/auth"), f: await import("firebase/firestore") });

export function onAuth(cb: (u: User | null) => void): () => void {
  if (MOCK) return mockSession.onAuth(cb);
  let off = () => {}, dead = false;
  fb().then(({ auth, a }) => { if (!dead) off = a.onAuthStateChanged(auth, (u) => cb(u ? { uid: u.uid, email: u.email } : null)); });
  return () => { dead = true; off(); };
}
export async function signIn(email: string, pw: string, signup = false) {
  if (MOCK) return signup ? mockSession.signUp(email, pw) : mockSession.signIn(email, pw);
  const { auth, a } = await fb(); await (signup ? a.createUserWithEmailAndPassword : a.signInWithEmailAndPassword)(auth, email, pw);
}
export async function logOut() { if (MOCK) return mockSession.logOut(); const { auth, a } = await fb(); await a.signOut(auth); }
export async function getToken(): Promise<string | undefined> { if (MOCK) return mockSession.getToken(); return (await fb()).auth.currentUser?.getIdToken(); }
export function subscribeNotifs(user: User, cb: (items: any[]) => void): () => void { // tempo real (Firestore)
  if (MOCK) return mockSession.subscribeNotifs(cb);
  let off = () => {}, dead = false;
  fb().then(({ db, f }) => { if (!dead) off = f.onSnapshot(f.query(f.collection(db, "users", user.uid, "notifications"), f.orderBy("created_at", "desc")), (s) => cb(s.docs.map((d) => ({ id: d.id, ...d.data() }))), () => cb([])); });
  return () => { dead = true; off(); };
}
