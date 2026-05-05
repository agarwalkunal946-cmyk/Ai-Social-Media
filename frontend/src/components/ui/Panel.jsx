import { motion } from "framer-motion";

export function Panel({ className = "", dark = false, hover = true, children, ...props }) {
  const base = dark ? "dark-panel" : "glass-panel";

  return (
    <motion.section
      initial={{ opacity: 0, y: 16 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.4, ease: "easeOut" }}
      whileHover={hover ? { y: -2, transition: { duration: 0.2 } } : undefined}
      className={`${base} neon-border ${className}`}
      {...props}
    >
      {children}
    </motion.section>
  );
}
