import { initializeApp } from "firebase/app";
import { connectAuthEmulator, getAuth } from "firebase/auth";
import { connectFirestoreEmulator, getFirestore } from "firebase/firestore";

const env = import.meta.env, real = !!env.VITE_FIREBASE_API_KEY; // com chave real: sem emuladores
export const app = initializeApp({ apiKey: env.VITE_FIREBASE_API_KEY ?? "fake-api-key", projectId: env.VITE_FIREBASE_PROJECT_ID ?? "demo-waitorbuy", messagingSenderId: env.VITE_FIREBASE_MESSAGING_SENDER_ID, appId: env.VITE_FIREBASE_APP_ID });
export const auth = getAuth(app);
export const db = getFirestore(app);
if (!real) {
  connectAuthEmulator(auth, env.VITE_AUTH_EMULATOR ?? "http://localhost:9099", { disableWarnings: true });
  connectFirestoreEmulator(db, env.VITE_FIRESTORE_EMULATOR_HOST ?? "localhost", Number(env.VITE_FIRESTORE_EMULATOR_PORT ?? 8080));
}
