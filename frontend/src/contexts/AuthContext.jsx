import { createContext, useEffect, useMemo, useState } from "react";
import {
  createUserWithEmailAndPassword,
  fetchSignInMethodsForEmail,
  onAuthStateChanged,
  sendPasswordResetEmail,
  signInWithEmailAndPassword,
  signInWithPopup,
  signOut,
  updateProfile as updateFirebaseProfile,
} from "firebase/auth";

import { apiClient } from "../lib/apiClient";
import { auth, facebookProvider, githubProvider, googleProvider } from "../lib/firebase";

export const AuthContext = createContext(null);

const SOCIAL_PROVIDER_LABELS = {
  "facebook.com": "Facebook",
  "github.com": "GitHub",
  "google.com": "Google",
};

function normalizeEmail(email) {
  const value = (email || "").trim();
  if (!value) {
    throw new Error("Enter your email first.");
  }
  return value;
}

export function AuthProvider({ children }) {
  const [firebaseUser, setFirebaseUser] = useState(null);
  const [backendUser, setBackendUser] = useState(null);
  const [loading, setLoading] = useState(true);

  const syncBackendUser = async () => {
    if (!auth.currentUser) {
      setBackendUser(null);
      return null;
    }
    const response = await apiClient.get("/auth/me");
    setBackendUser(response.data.user);
    return response.data.user;
  };

  useEffect(() => {
    const unsubscribe = onAuthStateChanged(auth, async (user) => {
      setFirebaseUser(user);
      if (user) {
        try {
          await syncBackendUser();
        } catch (error) {
          console.error("Backend sync failed", error);
        }
      } else {
        setBackendUser(null);
      }
      setLoading(false);
    });
    return unsubscribe;
  }, []);

  const loginWithGoogle = async () => {
    await signInWithPopup(auth, googleProvider);
    return syncBackendUser();
  };

  const loginWithGithub = async () => {
    await signInWithPopup(auth, githubProvider);
    return syncBackendUser();
  };

  const loginWithFacebook = async () => {
    await signInWithPopup(auth, facebookProvider);
    return syncBackendUser();
  };

  const loginWithEmail = async (email, password) => {
    await signInWithEmailAndPassword(auth, normalizeEmail(email), password);
    return syncBackendUser();
  };

  const registerWithEmail = async ({ name, email, password }) => {
    const credential = await createUserWithEmailAndPassword(auth, normalizeEmail(email), password);
    if (name) {
      await updateFirebaseProfile(credential.user, { displayName: name.trim() });
      await credential.user.getIdToken(true);
    }
    return syncBackendUser();
  };

  const logout = async () => {
    await signOut(auth);
  };

  const requestPasswordReset = async (email) => {
    const normalizedEmail = normalizeEmail(email);
    let signInMethods = null;
    let accountSnapshot = null;

    try {
      const response = await apiClient.get("/auth/password-reset-status", {
        params: { email: normalizedEmail },
      });
      accountSnapshot = response.data;
    } catch {
      accountSnapshot = null;
    }

    if (accountSnapshot && !accountSnapshot.exists) {
      throw new Error("No account found with this email.");
    }

    const socialProviderLabel = SOCIAL_PROVIDER_LABELS[accountSnapshot?.provider];
    if (socialProviderLabel) {
      throw new Error(`This account uses ${socialProviderLabel}. Sign in with ${socialProviderLabel} instead of password reset.`);
    }

    try {
      signInMethods = await fetchSignInMethodsForEmail(auth, normalizedEmail);
    } catch {
      signInMethods = null;
    }

    if (Array.isArray(signInMethods) && signInMethods.length > 0 && !signInMethods.includes("password")) {
      const providerLabel =
        signInMethods
          .map((method) => SOCIAL_PROVIDER_LABELS[method])
          .find(Boolean) || "social login";

      throw new Error(`This account uses ${providerLabel}. Sign in with ${providerLabel} instead of password reset.`);
    }

    await sendPasswordResetEmail(auth, normalizedEmail);

    if (Array.isArray(signInMethods)) {
      if (signInMethods.includes("password")) {
        return "Password reset link sent to your email.";
      }
    }

    return "Password reset link sent to your email.";
  };

  const updateMode = async (mode) => {
    const response = await apiClient.patch("/auth/mode", { mode });
    setBackendUser(response.data.user);
  };

  const updateProfile = async ({ display_name }) => {
    const response = await apiClient.patch("/auth/profile", { display_name });
    setBackendUser(response.data.user);
    return response.data.user;
  };

  const uploadAvatar = async (file) => {
    const formData = new FormData();
    formData.append("image", file);
    const response = await apiClient.post("/auth/avatar", formData);
    setBackendUser(response.data.user);
    return response.data;
  };

  const value = useMemo(
    () => ({
      firebaseUser,
      backendUser,
      loading,
      loginWithGoogle,
      loginWithGithub,
      loginWithFacebook,
      loginWithEmail,
      registerWithEmail,
      requestPasswordReset,
      updateMode,
      updateProfile,
      uploadAvatar,
      logout,
      syncBackendUser,
    }),
    [firebaseUser, backendUser, loading]
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}
