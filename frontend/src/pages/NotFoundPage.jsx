import { Link } from "react-router-dom";
import { motion } from "framer-motion";
import { ArrowLeft, Moon, Sun, Zap } from "lucide-react";
import { Button } from "../components/ui/Button";
import { AnimatedBackground } from "../components/ui/AnimatedBackground";
import { useTheme } from "../hooks/useTheme";

export function NotFoundPage() {
  const { theme, toggleTheme } = useTheme();

  return (
    <div className="relative flex min-h-screen items-center justify-center bg-void px-4">
      <AnimatedBackground />
      {/* Theme toggle */}
      <button
        onClick={toggleTheme}
        className="fixed top-5 right-5 z-50 flex h-10 w-10 items-center justify-center rounded-xl border border-white/[0.06] bg-white/[0.03] text-slate-400 transition hover:text-white backdrop-blur-xl cursor-pointer"
      >
        {theme === 'dark' ? <Sun size={16} /> : <Moon size={16} />}
      </button>
      <div className="relative z-10 text-center">
        <motion.div
          initial={{ opacity: 0, scale: 0.9 }}
          animate={{ opacity: 1, scale: 1 }}
          transition={{ duration: 0.5 }}
        >
          <div className="mb-6 flex justify-center">
            <div className="flex h-16 w-16 items-center justify-center rounded-2xl bg-gradient-to-br from-neon/20 to-purple-500/20 border border-neon/20">
              <Zap size={28} className="text-neon" />
            </div>
          </div>
          <h1 className="font-mono text-8xl font-bold text-gradient">404</h1>
          <h2 className="mt-4 font-display text-2xl font-bold text-white">Page not found</h2>
          <p className="mt-3 max-w-md text-sm text-slate-400">
            The page you're looking for doesn't exist or has been moved.
          </p>
          <Link to="/" className="mt-8 inline-block">
            <Button className="gap-2">
              <ArrowLeft size={16} />
              Back to home
            </Button>
          </Link>
        </motion.div>
      </div>
    </div>
  );
}
