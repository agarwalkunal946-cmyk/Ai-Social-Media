import { motion } from "framer-motion";

const accentColors = {
  positive: { bar: "from-emerald-400 to-cyan-400", dot: "bg-emerald-400", text: "text-emerald-400" },
  warning: { bar: "from-amber-400 to-orange-400", dot: "bg-amber-400", text: "text-amber-400" },
  negative: { bar: "from-rose-400 to-red-400", dot: "bg-rose-400", text: "text-rose-400" },
  neutral: { bar: "from-neon to-purple-400", dot: "bg-neon", text: "text-slate-400" },
};

export function StatCard({ label, value, delta, tone = "neutral" }) {
  const accent = accentColors[tone] || accentColors.neutral;

  return (
    <motion.div
      initial={{ opacity: 0, scale: 0.95 }}
      animate={{ opacity: 1, scale: 1 }}
      transition={{ duration: 0.4, ease: "easeOut" }}
      whileHover={{ y: -3, transition: { duration: 0.2 } }}
      className="relative flex min-h-[8.75rem] flex-col overflow-hidden rounded-2xl border border-white/[0.06] bg-slate-900/50 p-5 backdrop-blur-xl"
    >
      {/* Accent bar */}
      <div className={`absolute top-0 left-0 right-0 h-[2px] bg-gradient-to-r ${accent.bar}`} />

      <p className="max-w-full break-words text-sm text-slate-400">{label}</p>
      <div className="mt-4 flex flex-1 flex-col justify-end gap-3">
        <h3 className="max-w-full break-words font-display text-[clamp(1.55rem,2.7vw,2rem)] font-bold leading-tight text-white">
          {value}
        </h3>
        {delta && (
          <span
            className={`inline-flex w-fit max-w-full items-center gap-2 self-start rounded-2xl bg-white/[0.04] px-3 py-2 text-[11px] font-semibold leading-snug ${accent.text}`}
          >
            <span className={`h-1.5 w-1.5 rounded-full ${accent.dot} animate-pulse`} />
            <span className="break-words">{delta}</span>
          </span>
        )}
      </div>
    </motion.div>
  );
}
