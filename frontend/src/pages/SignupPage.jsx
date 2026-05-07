import { useEffect, useRef, useState } from "react";
import { ArrowRight, Camera, Eye, EyeOff, Github, KeyRound, Mail, Moon, Sun, User, Zap } from "lucide-react";
import { Link, useNavigate } from "react-router-dom";
import { motion } from "framer-motion";
import { useAuth } from "../hooks/useAuth";
import { useToast } from "../hooks/useToast";
import { useTheme } from "../hooks/useTheme";
import { Button } from "../components/ui/Button";
import { AnimatedBackground } from "../components/ui/AnimatedBackground";
import { isSilentAuthDismissError } from "../lib/errorMessage";

const SOCIAL_LOADING_LABELS = new Set(["google", "github"]);

export function SignupPage() {
  const { firebaseUser, backendUser, loginWithGoogle, loginWithGithub, registerWithEmail, uploadAvatar } = useAuth();
  const navigate = useNavigate();
  const { showToast } = useToast();
  const { theme, toggleTheme } = useTheme();
  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [avatarFile, setAvatarFile] = useState(null);
  const [avatarPreview, setAvatarPreview] = useState("");
  const [loading, setLoading] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const suppressDismissToastRef = useRef(false);
  const avatarInputRef = useRef(null);

  useEffect(() => {
    if (firebaseUser && backendUser && loading !== "register") {
      navigate(backendUser.role === "admin" ? "/admin" : "/dashboard", { replace: true });
    }
  }, [firebaseUser, backendUser, loading, navigate]);

  useEffect(() => {
    const handleFocus = () => {
      setLoading((current) => {
        if (SOCIAL_LOADING_LABELS.has(current)) {
          suppressDismissToastRef.current = true;
          return "";
        }
        return current;
      });
    };

    window.addEventListener("focus", handleFocus);
    return () => window.removeEventListener("focus", handleFocus);
  }, []);

  useEffect(() => {
    if (!avatarFile) {
      setAvatarPreview("");
      return undefined;
    }

    const objectUrl = URL.createObjectURL(avatarFile);
    setAvatarPreview(objectUrl);

    return () => URL.revokeObjectURL(objectUrl);
  }, [avatarFile]);

  const wrap = async (label, action, options = {}) => {
    setLoading(label);
    try {
      await action();
      if (options.successMessage) {
        showToast(options.successMessage, "success");
      }
    } catch (error) {
      if (options.silentDismiss && (isSilentAuthDismissError(error) || suppressDismissToastRef.current)) {
        suppressDismissToastRef.current = false;
        setLoading("");
        return;
      }
      if (options.releaseBeforeToast) {
        setLoading("");
        setTimeout(() => showToast(error, "error"), 0);
        return;
      }
      showToast(error, "error");
    } finally {
      suppressDismissToastRef.current = false;
      setLoading((current) => (current === label ? "" : current));
    }
  };

  const handleAvatarChange = (event) => {
    const file = event.target.files?.[0];
    if (!file) {
      return;
    }

    setAvatarFile(file);
  };

  const clearAvatar = () => {
    setAvatarFile(null);
    if (avatarInputRef.current) {
      avatarInputRef.current.value = "";
    }
  };

  const handleRegister = () =>
    wrap("register", async () => {
      await registerWithEmail({ name, email, password });
      if (avatarFile) {
        try {
          await uploadAvatar(avatarFile);
        } catch (error) {
          showToast("Account created, but profile photo could not be uploaded. You can add it later from the dashboard.", "warning");
        }
      }
    });

  return (
    <div className="relative flex min-h-screen items-center justify-center bg-void px-4 py-8">
      <AnimatedBackground />
      {/* Theme toggle */}
      <button
        onClick={toggleTheme}
        className="fixed top-5 right-5 z-50 flex h-10 w-10 items-center justify-center rounded-xl border border-white/[0.06] bg-white/[0.03] text-slate-400 transition hover:text-white backdrop-blur-xl cursor-pointer"
        title={theme === 'dark' ? 'Switch to light mode' : 'Switch to dark mode'}
      >
        {theme === 'dark' ? <Sun size={16} /> : <Moon size={16} />}
      </button>
      <div className="relative z-10 w-full max-w-[480px]">
        <motion.div initial={{ opacity: 0, y: 24 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.5 }}>
          <Link to="/" className="mb-8 flex items-center justify-center gap-3">
            <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-gradient-to-br from-neon/20 to-purple-500/20 border border-neon/20">
              <Zap size={18} className="text-neon" />
            </div>
            <span className="font-display text-xl font-bold text-white">Synapse</span>
          </Link>

          <div className="rounded-2xl border border-white/[0.06] bg-slate-900/60 p-8 shadow-ambient backdrop-blur-2xl">
            <div className="text-center">
              <h1 className="font-display text-2xl font-bold text-white">Create your account</h1>
              <p className="mt-2 text-sm text-slate-400">Start analyzing your social media in minutes</p>
            </div>

            <div className="mt-8 grid grid-cols-2 gap-3">
              <Button
                variant="secondary"
                onClick={() => wrap("google", loginWithGoogle, { releaseBeforeToast: true, silentDismiss: true })}
                disabled={loading === "google"}
                className="text-xs"
              >
                <svg className="h-4 w-4" viewBox="0 0 24 24"><path d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92a5.06 5.06 0 01-2.2 3.32v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.1z" fill="#4285F4"/><path d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z" fill="#34A853"/><path d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z" fill="#FBBC05"/><path d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z" fill="#EA4335"/></svg>
                Google
              </Button>
              <Button
                variant="secondary"
                onClick={() => wrap("github", loginWithGithub, { releaseBeforeToast: true, silentDismiss: true })}
                disabled={loading === "github"}
                className="text-xs"
              >
                <Github size={16} /> GitHub
              </Button>
            </div>

            <div className="my-6 flex items-center gap-4">
              <div className="h-px flex-1 bg-white/[0.06]" />
              <span className="text-xs text-slate-500">or register with email</span>
              <div className="h-px flex-1 bg-white/[0.06]" />
            </div>

            <div className="space-y-4">
              <div>
                <label className="mb-1.5 block text-xs font-medium text-slate-400">Profile photo</label>
                <div className="flex items-center gap-3">
                  <label className="flex flex-1 cursor-pointer items-center gap-3 rounded-2xl border border-white/[0.06] bg-white/[0.03] p-3 transition hover:bg-white/[0.05]">
                    <input
                      ref={avatarInputRef}
                      type="file"
                      accept="image/*"
                      className="hidden"
                      onChange={handleAvatarChange}
                    />
                    <div className="flex h-14 w-14 shrink-0 items-center justify-center overflow-hidden rounded-2xl border border-white/[0.08] bg-white/[0.04]">
                      {avatarPreview ? (
                        <img src={avatarPreview} alt="Avatar preview" className="h-full w-full object-cover" />
                      ) : (
                        <Camera size={18} className="text-slate-400" />
                      )}
                    </div>
                    <div className="min-w-0 flex-1">
                      <p className="truncate text-sm font-medium text-white">{avatarFile ? avatarFile.name : "Upload your photo"}</p>
                      <p className="text-xs text-slate-500">Optional. Saved locally in uploads.</p>
                    </div>
                  </label>
                  {avatarFile && (
                    <button
                      type="button"
                      onClick={clearAvatar}
                      className="rounded-xl border border-white/[0.08] px-3 py-2 text-xs text-slate-400 transition hover:text-white"
                    >
                      Remove
                    </button>
                  )}
                </div>
              </div>
              <div>
                <label className="mb-1.5 block text-xs font-medium text-slate-400">Full name</label>
                <div className="relative">
                  <User size={16} className="pointer-events-none absolute left-3.5 top-1/2 -translate-y-1/2 text-slate-500" />
                  <input type="text" className="input-field has-left-icon" placeholder="John Doe" value={name} onChange={(e) => setName(e.target.value)} />
                </div>
              </div>
              <div>
                <label className="mb-1.5 block text-xs font-medium text-slate-400">Email</label>
                <div className="relative">
                  <Mail size={16} className="pointer-events-none absolute left-3.5 top-1/2 -translate-y-1/2 text-slate-500" />
                  <input type="email" className="input-field has-left-icon" placeholder="you@example.com" value={email} onChange={(e) => setEmail(e.target.value)} />
                </div>
              </div>
              <div>
                <label className="mb-1.5 block text-xs font-medium text-slate-400">Password</label>
                <div className="relative">
                  <KeyRound size={16} className="pointer-events-none absolute left-3.5 top-1/2 -translate-y-1/2 text-slate-500" />
                  <input
                    type={showPassword ? "text" : "password"}
                    className="input-field has-left-icon has-right-icon"
                    placeholder="Min 6 characters"
                    value={password}
                    onChange={(e) => setPassword(e.target.value)}
                  />
                  <button
                    type="button"
                    onClick={() => setShowPassword((value) => !value)}
                    className="absolute right-3.5 top-1/2 -translate-y-1/2 text-slate-500 transition hover:text-white"
                    aria-label={showPassword ? "Hide password" : "Show password"}
                  >
                    {showPassword ? <Eye size={16} /> : <EyeOff size={16} />}
                  </button>
                </div>
              </div>
              <Button className="w-full gap-2" onClick={handleRegister} disabled={loading === "register"}>
                Create account <ArrowRight size={16} />
              </Button>
            </div>
          </div>

          <p className="mt-6 text-center text-sm text-slate-500">
            Already have an account?{" "}
            <Link to="/login" className="font-medium text-neon transition hover:text-cyan-300">Sign in</Link>
          </p>
        </motion.div>
      </div>
    </div>
  );
}
