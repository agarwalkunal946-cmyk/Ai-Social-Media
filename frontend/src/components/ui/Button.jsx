import { motion } from "framer-motion";
import { useTheme } from "../../hooks/useTheme";

const darkVariants = {
  primary:
    "bg-gradient-to-r from-neon/90 to-cyan-400/90 text-slate-950 font-semibold shadow-neon-sm hover:shadow-neon hover:brightness-110",
  secondary:
    "bg-white/5 text-slate-200 border border-white/10 hover:bg-white/10 hover:border-white/20",
  ghost:
    "bg-transparent text-slate-300 hover:bg-white/5 hover:text-white",
  accent:
    "bg-gradient-to-r from-purple-500 to-violet-600 text-white font-semibold shadow-neon-violet hover:brightness-110",
  danger:
    "bg-gradient-to-r from-rose-500 to-red-600 text-white font-semibold hover:brightness-110",
};

const lightVariants = {
  primary:
    "bg-gradient-to-r from-cyan-500 to-teal-500 text-white font-semibold shadow-[0_2px_12px_rgba(8,145,178,0.25)] hover:shadow-[0_4px_20px_rgba(8,145,178,0.3)] hover:brightness-105",
  secondary:
    "bg-black/[0.04] text-slate-700 border border-black/[0.08] hover:bg-black/[0.07] hover:border-black/[0.15]",
  ghost:
    "bg-transparent text-slate-600 hover:bg-black/[0.04] hover:text-slate-900",
  accent:
    "bg-gradient-to-r from-purple-500 to-violet-600 text-white font-semibold shadow-[0_2px_12px_rgba(124,58,237,0.25)] hover:brightness-105",
  danger:
    "bg-gradient-to-r from-rose-500 to-red-600 text-white font-semibold hover:brightness-105",
};

export function Button({ className = "", variant = "primary", children, ...props }) {
  const { theme } = useTheme();
  const styles = theme === "light" ? lightVariants : darkVariants;

  return (
    <motion.button
      whileHover={{ scale: 1.02, y: -1 }}
      whileTap={{ scale: 0.98 }}
      transition={{ type: "spring", stiffness: 400, damping: 20 }}
      className={`inline-flex items-center justify-center gap-2 rounded-xl px-5 py-3 text-sm transition-all duration-300 cursor-pointer disabled:opacity-50 disabled:pointer-events-none ${styles[variant] || styles.primary} ${className}`}
      {...props}
    >
      {children}
    </motion.button>
  );
}
