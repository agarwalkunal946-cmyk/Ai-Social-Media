import { createContext, useCallback, useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { AlertCircle, CheckCircle2, Info, X, AlertTriangle } from "lucide-react";
import { getUserFacingError } from "../lib/errorMessage";

const ToastContext = createContext(null);

const config = {
  success: { Icon: CheckCircle2, border: "border-emerald-500/20", bg: "bg-emerald-500/10", icon: "text-emerald-400", bar: "bg-emerald-400" },
  error: { Icon: AlertCircle, border: "border-rose-500/20", bg: "bg-rose-500/10", icon: "text-rose-400", bar: "bg-rose-400" },
  warning: { Icon: AlertTriangle, border: "border-amber-500/20", bg: "bg-amber-500/10", icon: "text-amber-400", bar: "bg-amber-400" },
  info: { Icon: Info, border: "border-neon/20", bg: "bg-neon/10", icon: "text-neon", bar: "bg-neon" },
};

function Toast({ id, type, message, onClose }) {
  const s = config[type] || config.info;
  return (
    <motion.div
      layout
      initial={{ opacity: 0, x: 60, scale: 0.95 }}
      animate={{ opacity: 1, x: 0, scale: 1 }}
      exit={{ opacity: 0, x: 60, scale: 0.95, transition: { duration: 0.2 } }}
      className={`pointer-events-auto relative overflow-hidden rounded-xl border ${s.border} ${s.bg} backdrop-blur-2xl p-4 shadow-lg min-w-[300px] max-w-[400px]`}
    >
      <div className="flex items-start gap-3">
        <s.Icon size={18} className={`mt-0.5 shrink-0 ${s.icon}`} />
        <p className="flex-1 text-sm text-white/90">{message}</p>
        <button onClick={() => onClose(id)} className="shrink-0 text-white/40 hover:text-white/70 transition cursor-pointer">
          <X size={14} />
        </button>
      </div>
      <motion.div
        initial={{ scaleX: 1 }}
        animate={{ scaleX: 0 }}
        transition={{ duration: 4, ease: "linear" }}
        onAnimationComplete={() => onClose(id)}
        className={`absolute bottom-0 left-0 right-0 h-[2px] ${s.bar} origin-left`}
      />
    </motion.div>
  );
}

export function ToastProvider({ children }) {
  const [toasts, setToasts] = useState([]);

  const showToast = useCallback((message, type = "info") => {
    const resolvedMessage =
      type === "error"
        ? getUserFacingError(message)
        : String(message || "").trim();

    if (!resolvedMessage) {
      return;
    }

    const id = Date.now() + Math.random();
    setToasts((prev) => [...prev, { id, message: resolvedMessage, type }]);
  }, []);

  const removeToast = useCallback((id) => {
    setToasts((prev) => prev.filter((t) => t.id !== id));
  }, []);

  return (
    <ToastContext.Provider value={{ showToast }}>
      {children}
      <div className="fixed top-5 right-5 z-[100] flex flex-col gap-3 pointer-events-none">
        <AnimatePresence mode="popLayout">
          {toasts.map((t) => (
            <Toast key={t.id} {...t} onClose={removeToast} />
          ))}
        </AnimatePresence>
      </div>
    </ToastContext.Provider>
  );
}

export { ToastContext };
