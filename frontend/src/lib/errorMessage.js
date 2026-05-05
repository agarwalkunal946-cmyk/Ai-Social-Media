const FIREBASE_AUTH_MESSAGES = {
  "auth/account-exists-with-different-credential": "This email is already linked to a different sign-in method.",
  "auth/cancelled-popup-request": "Sign-in popup request was cancelled. Please try again.",
  "auth/configuration-not-found": "This login method is not configured yet.",
  "auth/email-already-in-use": "This email is already registered.",
  "auth/invalid-credential": "Email or password is incorrect.",
  "auth/invalid-email": "Enter a valid email address.",
  "auth/invalid-login-credentials": "Email or password is incorrect.",
  "auth/missing-email": "Enter your email first.",
  "auth/missing-password": "Enter your password.",
  "auth/network-request-failed": "Network error. Check your internet connection and try again.",
  "auth/operation-not-allowed": "This sign-in method is not enabled yet.",
  "auth/popup-blocked": "Popup was blocked. Allow popups and try again.",
  "auth/popup-closed-by-user": "Sign-in popup was closed before completion.",
  "auth/too-many-requests": "Too many attempts. Please wait a bit and try again.",
  "auth/unauthorized-domain": "This domain is not authorized for login yet.",
  "auth/user-disabled": "This account has been disabled.",
  "auth/user-not-found": "No account found with this email.",
  "auth/weak-password": "Password must be at least 6 characters.",
  "auth/wrong-password": "Email or password is incorrect.",
};

const SILENT_AUTH_DISMISS_CODES = new Set([
  "auth/popup-closed-by-user",
  "auth/cancelled-popup-request",
]);

function cleanMessage(message) {
  if (!message) {
    return "";
  }

  return String(message)
    .trim()
    .replace(/^Firebase:\s*/i, "")
    .replace(/^Error:\s*/i, "")
    .replace(/\s*\(auth\/[^)]+\)\.?$/i, "")
    .trim();
}

function extractApiMessage(payload) {
  if (!payload) {
    return "";
  }

  if (typeof payload === "string") {
    return payload;
  }

  if (typeof payload.detail === "string") {
    return payload.detail;
  }

  if (typeof payload.message === "string") {
    return payload.message;
  }

  if (typeof payload.error === "string") {
    return payload.error;
  }

  if (Array.isArray(payload.detail)) {
    return payload.detail
      .map((item) => {
        if (typeof item === "string") {
          return item;
        }
        if (typeof item?.msg === "string") {
          return item.msg;
        }
        if (typeof item?.message === "string") {
          return item.message;
        }
        return "";
      })
      .filter(Boolean)
      .join(". ");
  }

  return "";
}

export function getUserFacingError(error, fallback = "Something went wrong.") {
  if (!error) {
    return fallback;
  }

  if (typeof error === "string") {
    return cleanMessage(error) || fallback;
  }

  const apiMessage = cleanMessage(extractApiMessage(error.response?.data));
  if (apiMessage) {
    return apiMessage;
  }

  const firebaseMessage = FIREBASE_AUTH_MESSAGES[error.code];
  if (firebaseMessage) {
    return firebaseMessage;
  }

  const directMessage = cleanMessage(error.message);
  if (directMessage && !/^Request failed with status code \d+$/i.test(directMessage)) {
    return directMessage;
  }

  if (error.response?.status === 401) {
    return "Please sign in again.";
  }

  if (error.response?.status === 403) {
    return "You do not have permission to do this.";
  }

  if (error.response?.status === 404) {
    return "Requested resource was not found.";
  }

  return fallback;
}

export function isSilentAuthDismissError(error) {
  return SILENT_AUTH_DISMISS_CODES.has(error?.code);
}
