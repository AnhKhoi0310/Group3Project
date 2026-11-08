import { initializeApp } from "firebase/app";
import {
  createUserWithEmailAndPassword,
  getAuth,
  onAuthStateChanged,
  sendPasswordResetEmail,
  signInWithEmailAndPassword,
  signOut,
} from "firebase/auth";
import type { AppConfig } from "../config/env";

export interface AuthUser {
  uid: string;
  email: string | null;
}

/** Boundary around the identity provider, so tests can replace it. */
export interface AuthClient {
  subscribe(listener: (user: AuthUser | null) => void): () => void;
  signIn(email: string, password: string): Promise<void>;
  register(email: string, password: string): Promise<void>;
  resetPassword(email: string): Promise<void>;
  getToken(): Promise<string | null>;
  signOut(): Promise<void>;
}

export function createFirebaseAuthClient(
  config: AppConfig["firebase"],
): AuthClient {
  const auth = getAuth(initializeApp(config));

  return {
    subscribe: (listener) =>
      onAuthStateChanged(auth, (user) =>
        listener(user && { uid: user.uid, email: user.email }),
      ),
    signIn: async (email, password) => {
      await signInWithEmailAndPassword(auth, email, password);
    },
    register: async (email, password) => {
      await createUserWithEmailAndPassword(auth, email, password);
    },
    resetPassword: (email) => sendPasswordResetEmail(auth, email),
    getToken: async () => (await auth.currentUser?.getIdToken()) ?? null,
    signOut: () => signOut(auth),
  };
}

const MESSAGES: Record<string, string> = {
  "auth/invalid-credential": "That email or password is incorrect.",
  "auth/wrong-password": "That email or password is incorrect.",
  "auth/user-not-found": "That email or password is incorrect.",
  "auth/email-already-in-use":
    "An account with this email already exists. Try logging in instead.",
  "auth/invalid-email": "Enter a valid email address.",
  "auth/weak-password": "Choose a password with at least 6 characters.",
  "auth/too-many-requests":
    "Too many attempts. Please wait a few minutes and try again.",
  "auth/network-request-failed":
    "We couldn't reach the sign-in service. Check your connection and try again.",
};

export function authErrorMessage(error: unknown): string {
  const code = (error as { code?: string } | null)?.code;
  return (
    (code && MESSAGES[code]) ?? "We couldn't sign you in. Please try again."
  );
}
