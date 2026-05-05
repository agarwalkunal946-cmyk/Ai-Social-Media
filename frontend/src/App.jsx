import { Loader2 } from "lucide-react";
import { Navigate, Route, Routes } from "react-router-dom";

import { useAuth } from "./hooks/useAuth";
import { AdminPage } from "./pages/AdminPage";
import { ConnectPage } from "./pages/ConnectPage";
import { DashboardPage } from "./pages/DashboardPage";
import { LandingPage } from "./pages/LandingPage";
import { LoginPage } from "./pages/LoginPage";
import { SignupPage } from "./pages/SignupPage";
import { NotFoundPage } from "./pages/NotFoundPage";
import { PublicPlatformPage } from "./pages/PublicPlatformPage";
import { ReportsPage } from "./pages/ReportsPage";

function FullScreenLoader() {
  return (
    <div className="flex min-h-screen items-center justify-center bg-void">
      <div className="flex items-center gap-3 rounded-xl border border-white/[0.06] bg-slate-900/60 px-6 py-4 text-sm text-slate-300 backdrop-blur-2xl">
        <Loader2 className="animate-spin text-neon" size={18} />
        Loading your workspace...
      </div>
    </div>
  );
}

function ProtectedRoute({ children }) {
  const { firebaseUser, loading } = useAuth();
  if (loading) return <FullScreenLoader />;
  if (!firebaseUser) return <Navigate to="/login" replace />;
  return children;
}

function UserRoute({ children }) {
  const { firebaseUser, backendUser, loading } = useAuth();
  if (loading) return <FullScreenLoader />;
  if (!firebaseUser) return <Navigate to="/login" replace />;
  if (backendUser?.role === "admin") return <Navigate to="/admin" replace />;
  return children;
}

function AdminRoute({ children }) {
  const { firebaseUser, backendUser, loading } = useAuth();
  if (loading) return <FullScreenLoader />;
  if (!firebaseUser) return <Navigate to="/login" replace />;
  if (backendUser?.role !== "admin") return <Navigate to="/dashboard" replace />;
  return children;
}

export default function App() {
  return (
    <Routes>
      <Route path="/" element={<LandingPage />} />
      <Route path="/login" element={<LoginPage />} />
      <Route path="/signup" element={<SignupPage />} />
      <Route path="/explore/:platform" element={<PublicPlatformPage />} />
      <Route
        path="/dashboard"
        element={
          <UserRoute>
            <DashboardPage />
          </UserRoute>
        }
      />
      <Route
        path="/connect"
        element={
          <UserRoute>
            <ConnectPage />
          </UserRoute>
        }
      />
      <Route
        path="/reports"
        element={
          <UserRoute>
            <ReportsPage />
          </UserRoute>
        }
      />
      <Route
        path="/admin"
        element={
          <AdminRoute>
            <AdminPage />
          </AdminRoute>
        }
      />
      <Route path="*" element={<NotFoundPage />} />
    </Routes>
  );
}
