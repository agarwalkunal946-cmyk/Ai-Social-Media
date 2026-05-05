import { useRef, useState } from "react";
import { motion } from "framer-motion";
import { useTheme } from "../../hooks/useTheme";

export function GlowCard({ children, className = "", glowColor = "rgba(0,229,255,0.12)", ...props }) {
  const ref = useRef(null);
  const { theme } = useTheme();
  const [glow, setGlow] = useState({ x: 50, y: 50 });

  const handleMouseMove = (e) => {
    const rect = ref.current?.getBoundingClientRect();
    if (!rect) return;
    const x = ((e.clientX - rect.left) / rect.width) * 100;
    const y = ((e.clientY - rect.top) / rect.height) * 100;
    setGlow({ x, y });
  };

  const baseBg = theme === "light" ? "rgba(255,255,255,0.92)" : "rgba(15,23,42,0.5)";
  const borderClass = theme === "light"
    ? "border-black/[0.06] hover:border-black/[0.12] shadow-[0_2px_20px_rgba(0,0,0,0.06)]"
    : "border-white/[0.06] hover:border-white/[0.12]";

  return (
    <motion.div
      ref={ref}
      onMouseMove={handleMouseMove}
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.5, ease: "easeOut" }}
      whileHover={{ y: -4, transition: { duration: 0.25 } }}
      className={`relative overflow-hidden rounded-2xl border backdrop-blur-xl transition-all duration-300 ${borderClass} ${className}`}
      style={{
        background: `radial-gradient(600px circle at ${glow.x}% ${glow.y}%, ${glowColor}, transparent 40%), ${baseBg}`,
      }}
      {...props}
    >
      {children}
    </motion.div>
  );
}
