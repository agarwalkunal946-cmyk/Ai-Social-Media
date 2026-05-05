import axios from "axios";
import { auth } from "./firebase";

const apiBaseURL = import.meta.env.VITE_API_BASE_URL || "http://localhost:8000/api";

export const apiClient = axios.create({
  baseURL: apiBaseURL,
});

apiClient.interceptors.request.use(async (config) => {
  const currentUser = auth.currentUser;
  if (currentUser) {
    const token = await currentUser.getIdToken();
    config.headers.Authorization = `Bearer ${token}`;
    config.headers["X-Dev-User-Email"] = currentUser.email || "";
    config.headers["X-Dev-User-Name"] = currentUser.displayName || "";
  }
  return config;
});

