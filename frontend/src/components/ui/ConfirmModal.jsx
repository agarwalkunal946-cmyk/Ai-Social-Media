import { AnimatePresence, motion } from "framer-motion";
import { AlertTriangle, Trash2, X } from "lucide-react";

import { Button } from "./Button";

const toneStyles = {
  danger: {
    iconWrap: "bg-rose-500/12",
    icon: "text-rose-300",
    confirm: "bg-rose-500 text-white hover:bg-rose-400",
  },
  warning: {
    iconWrap: "bg-amber-500/12",
    icon: "text-amber-300",
    confirm: "bg-amber-400 text-slate-950 hover:bg-amber-300",
  },
  neutral: {
    iconWrap: "bg-neon/12",
    icon: "text-neon",
    confirm: "bg-neon text-slate-950 hover:brightness-110",
  },
};

export function ConfirmModal({
  open,
  title,
  description,
  confirmLabel = "Confirm",
  cancelLabel = "Cancel",
  tone = "danger",
  isPending = false,
  onConfirm,
  onClose,
}) {
  const palette = toneStyles[tone] || toneStyles.danger;

  return (
    <AnimatePresence>
      {open && (
        <>
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            onClick={isPending ? undefined : onClose}
            className="fixed inset-0 z-[90] bg-black/75 backdrop-blur-sm"
          />
          <div className="fixed inset-0 z-[100] flex items-center justify-center p-4 md:p-6">
            <motion.div
              initial={{ opacity: 0, y: 20, scale: 0.98 }}
              animate={{ opacity: 1, y: 0, scale: 1 }}
              exit={{ opacity: 0, y: 20, scale: 0.98 }}
              className="w-full max-w-md rounded-3xl border border-white/[0.08] bg-slate-950/95 p-6 shadow-2xl backdrop-blur-2xl"
            >
              <div className="flex items-start justify-between gap-4">
                <div className="flex min-w-0 items-start gap-3">
                  <div className={`flex h-11 w-11 shrink-0 items-center justify-center rounded-2xl ${palette.iconWrap}`}>
                    {tone === "danger" ? <Trash2 size={18} className={palette.icon} /> : <AlertTriangle size={18} className={palette.icon} />}
                  </div>
                  <div className="min-w-0">
                    <h2 className="font-display text-xl font-bold text-white">{title}</h2>
                    {description && <p className="mt-2 text-sm leading-relaxed text-slate-400">{description}</p>}
                  </div>
                </div>
                <button
                  type="button"
                  onClick={onClose}
                  disabled={isPending}
                  className="text-slate-500 transition hover:text-white disabled:cursor-not-allowed disabled:opacity-50"
                  aria-label="Close dialog"
                >
                  <X size={18} />
                </button>
              </div>

              <div className="mt-6 flex gap-3">
                <Button variant="secondary" className="flex-1" onClick={onClose} disabled={isPending}>
                  {cancelLabel}
                </Button>
                <button
                  type="button"
                  onClick={onConfirm}
                  disabled={isPending}
                  className={`flex-1 rounded-2xl px-4 py-3 text-sm font-semibold transition disabled:cursor-not-allowed disabled:opacity-60 ${palette.confirm}`}
                >
                  {isPending ? "Please wait..." : confirmLabel}
                </button>
              </div>
            </motion.div>
          </div>
        </>
      )}
    </AnimatePresence>
  );
}
