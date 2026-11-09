import { initializeApp } from "firebase/app";
import { connectAuthEmulator, getAuth } from "firebase/auth";
import { connectFirestoreEmulator, getFirestore } from "firebase/firestore";

const app = initializeApp({ apiKey: "fake-api-key", projectId: "demo-waitorbuy" });
export const auth = getAuth(app);
export const db = getFirestore(app);
connectAuthEmulator(auth, import.meta.env.VITE_AUTH_EMULATOR ?? "http://localhost:9099", { disableWarnings: true });
connectFirestoreEmulator(db, import.meta.env.VITE_FIRESTORE_EMULATOR_HOST ?? "localhost", Number(import.meta.env.VITE_FIRESTORE_EMULATOR_PORT ?? 8080));
