import { useQuery } from "@tanstack/react-query";
import { ArrowRight, BarChart3, Bot, ChevronRight, LineChart, Moon, Shield, Sparkles, Sun, Zap } from "lucide-react";
import { Link, Navigate } from "react-router-dom";
import { motion } from "framer-motion";

import { apiClient } from "../lib/apiClient";
import { Button } from "../components/ui/Button";
import { GlowCard } from "../components/ui/GlowCard";
import { AnimatedBackground } from "../components/ui/AnimatedBackground";
import { InstagramBrandIcon, XBrandIcon, YouTubeBrandIcon } from "../components/ui/PlatformIcon";
import { useAuth } from "../hooks/useAuth";
import { useTheme } from "../hooks/useTheme";

const stagger = {
  hidden: { opacity: 0 },
  show: { opacity: 1, transition: { staggerChildren: 0.1 } },
};

const fadeUp = {
  hidden: { opacity: 0, y: 24 },
  show: { opacity: 1, y: 0, transition: { duration: 0.5, ease: "easeOut" } },
};

const features = [
  {
    icon: LineChart,
    title: "Real-time analytics",
    desc: "Track followers, likes, comments, reach, and momentum across connected channels in one place.",
    color: "text-neon",
    glow: "rgba(0,229,255,0.1)",
  },
  {
    icon: Shield,
    title: "Toxicity and crisis alerts",
    desc: "Detect harmful conversations early and surface moderation risk before it becomes a brand problem.",
    color: "text-rose-400",
    glow: "rgba(244,63,94,0.1)",
  },
  {
    icon: Bot,
    title: "AI recommendations",
    desc: "Get best-time suggestions, caption direction, hashtag packs, and an assistant that explains the numbers.",
    color: "text-amber-400",
    glow: "rgba(245,158,11,0.1)",
  },
  {
    icon: BarChart3,
    title: "Presentation-ready reports",
    desc: "Generate clean weekly or monthly reports that can be opened, shared, printed, or downloaded.",
    color: "text-emerald-400",
    glow: "rgba(52,211,153,0.1)",
  },
];

const platformConfig = {
  instagram: { icon: InstagramBrandIcon, color: "from-pink-500 to-purple-500", glow: "rgba(225,48,108,0.1)" },
  youtube: { icon: YouTubeBrandIcon, color: "from-red-500 to-orange-500", glow: "rgba(255,0,0,0.1)" },
  x: { icon: XBrandIcon, color: "from-slate-200 to-slate-500", glow: "rgba(255,255,255,0.12)" },
};

export function LandingPage() {
  const { firebaseUser, backendUser, loading } = useAuth();
  const { data } = useQuery({
    queryKey: ["public-overview"],
    queryFn: async () => (await apiClient.get("/public/overview")).data,
  });
  const { theme, toggleTheme } = useTheme();

  if (loading) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-void">
        <div className="rounded-xl border border-white/[0.06] bg-slate-900/60 px-5 py-4 text-sm text-slate-300 backdrop-blur-2xl">
          Restoring your session...
        </div>
      </div>
    );
  }

  if (firebaseUser && backendUser) {
    return <Navigate to={backendUser.role === "admin" ? "/admin" : "/dashboard"} replace />;
  }

  return (
    <div className="relative min-h-screen bg-void">
      <AnimatedBackground />

      <div className="relative z-10">
        <nav className="sticky top-0 z-50 border-b border-white/[0.04] bg-void/70 backdrop-blur-2xl">
          <div className="mx-auto flex max-w-7xl items-center justify-between px-6 py-4">
            <Link to="/" className="flex items-center gap-3">
              <div className="flex h-9 w-9 items-center justify-center rounded-xl border border-neon/20 bg-gradient-to-br from-neon/20 to-purple-500/20">
                <Zap size={16} className="text-neon" />
              </div>
              <span className="font-display text-lg font-bold text-white">Synapse</span>
            </Link>

            <div className="hidden items-center gap-8 md:flex">
              <a href="#features" className="text-sm text-slate-400 transition hover:text-white">Features</a>
              <a href="#platforms" className="text-sm text-slate-400 transition hover:text-white">Platforms</a>
              <Link to="/explore/youtube" className="text-sm text-slate-400 transition hover:text-white">Explore</Link>
            </div>

            <div className="flex items-center gap-3">
              <button
                onClick={toggleTheme}
                className="flex h-9 w-9 cursor-pointer items-center justify-center rounded-xl border border-white/[0.06] bg-white/[0.03] text-slate-400 transition hover:text-white"
                title={theme === "dark" ? "Switch to light mode" : "Switch to dark mode"}
              >
                {theme === "dark" ? <Sun size={16} /> : <Moon size={16} />}
              </button>
              <Link to="/login">
                <Button variant="ghost" className="text-sm">Sign in</Button>
              </Link>
              <Link to="/signup">
                <Button className="text-sm">Get started</Button>
              </Link>
            </div>
          </div>
        </nav>

        <section className="relative overflow-hidden px-6 pb-24 pt-20 lg:pb-36 lg:pt-32">
          <div className="mx-auto max-w-7xl text-center">
            <motion.div variants={stagger} initial="hidden" animate="show">
              <motion.div variants={fadeUp} className="inline-flex items-center gap-2 rounded-full border border-neon/20 bg-neon/5 px-4 py-1.5 text-xs font-medium text-neon">
                <Sparkles size={12} />
                AI-powered social media analytics
              </motion.div>

              <motion.h1
                variants={fadeUp}
                className="mx-auto mt-8 max-w-5xl font-display text-4xl font-bold leading-tight text-white sm:text-5xl lg:text-7xl"
              >
                Read your audience, predict the next move, and protect your brand
              </motion.h1>

              <motion.p variants={fadeUp} className="mx-auto mt-6 max-w-3xl text-lg text-slate-400">
                Connect Instagram, YouTube, and X / Twitter to see real-time analytics, sentiment, emotion, toxicity, recommendations,
                chatbot insights, and shareable reports in one dashboard.
              </motion.p>

              <motion.div variants={fadeUp} className="mt-10 flex flex-wrap items-center justify-center gap-4">
                <Link to="/signup">
                  <Button className="gap-2 px-7 py-3.5 text-base">
                    Start the workspace
                    <ArrowRight size={16} />
                  </Button>
                </Link>
                <Link to="/explore/youtube">
                  <Button variant="secondary" className="gap-2 px-7 py-3.5 text-base">
                    Explore live trends
                    <ChevronRight size={16} />
                  </Button>
                </Link>
              </motion.div>

              <motion.div variants={fadeUp} className="mx-auto mt-16 flex max-w-2xl flex-wrap items-center justify-center gap-8 sm:gap-12">
                <div>
                  <p className="font-mono text-2xl font-bold text-white">3</p>
                  <p className="text-xs text-slate-500">Platforms</p>
                </div>
                <div className="h-8 w-px bg-white/10" />
                <div>
                  <p className="font-mono text-2xl font-bold text-white">AI</p>
                  <p className="text-xs text-slate-500">Insights and assistant</p>
                </div>
                <div className="h-8 w-px bg-white/10" />
                <div>
                  <p className="font-mono text-2xl font-bold text-white">Live</p>
                  <p className="text-xs text-slate-500">Dashboard signals</p>
                </div>
              </motion.div>
            </motion.div>
          </div>
        </section>

        <section id="features" className="px-6 py-24">
          <div className="mx-auto max-w-7xl">
            <motion.div
              initial={{ opacity: 0, y: 20 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true }}
              transition={{ duration: 0.5 }}
              className="text-center"
            >
              <p className="text-xs font-semibold uppercase tracking-[0.25em] text-neon/70">Why Synapse</p>
              <h2 className="mt-3 font-display text-3xl font-bold text-white sm:text-4xl">
                Everything needed for an AI analytics project
              </h2>
            </motion.div>

            <motion.div
              variants={stagger}
              initial="hidden"
              whileInView="show"
              viewport={{ once: true }}
              className="mt-14 grid gap-5 sm:grid-cols-2 lg:grid-cols-4"
            >
              {features.map((feature) => (
                <motion.div key={feature.title} variants={fadeUp}>
                  <GlowCard glowColor={feature.glow} className="h-full p-6">
                    <feature.icon size={24} className={feature.color} />
                    <h3 className="mt-5 font-display text-lg font-bold text-white">{feature.title}</h3>
                    <p className="mt-3 text-sm leading-relaxed text-slate-400">{feature.desc}</p>
                  </GlowCard>
                </motion.div>
              ))}
            </motion.div>
          </div>
        </section>

        <section id="platforms" className="px-6 py-24">
          <div className="mx-auto max-w-7xl">
            <motion.div
              initial={{ opacity: 0, y: 20 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true }}
              transition={{ duration: 0.5 }}
              className="text-center"
            >
              <p className="text-xs font-semibold uppercase tracking-[0.25em] text-purple-400/70">Platforms</p>
              <h2 className="mt-3 font-display text-3xl font-bold text-white sm:text-4xl">
                Explore Instagram, YouTube, and X / Twitter
              </h2>
            </motion.div>

            <motion.div
              variants={stagger}
              initial="hidden"
              whileInView="show"
              viewport={{ once: true }}
              className="mt-14 grid gap-5 md:grid-cols-3"
            >
              {(data?.cards || []).map((card) => {
                const config = platformConfig[card.platform] || platformConfig.x;
                const PlatformIcon = config.icon;
                return (
                  <motion.div key={card.platform} variants={fadeUp}>
                    <GlowCard glowColor={config.glow} className="flex h-full flex-col p-6">
                      <div className="flex items-center gap-3">
                        <div className={`flex h-12 w-12 items-center justify-center rounded-2xl bg-gradient-to-br ${config.color}`}>
                          <PlatformIcon size={22} className="text-white" />
                        </div>
                        <div>
                          <h3 className="font-display text-xl font-bold text-white">{card.title}</h3>
                        </div>
                      </div>
                      <p className="mt-4 text-sm text-slate-400">{card.subtitle}</p>
                      <div className="mt-5 flex flex-wrap gap-2">
                        {card.stats.map((item) => (
                          <span key={item} className="rounded-lg bg-white/5 px-2.5 py-1.5 text-[11px] text-slate-400">
                            {item}
                          </span>
                        ))}
                      </div>
                      <div className="mt-auto flex items-center justify-between pt-6">
                        <Link to={`/explore/${card.platform}`}>
                          <Button variant="secondary" className="gap-2 text-xs">
                            {card.cta}
                            <ChevronRight size={14} />
                          </Button>
                        </Link>
                      </div>
                    </GlowCard>
                  </motion.div>
                );
              })}
            </motion.div>
          </div>
        </section>

        <section className="px-6 py-24">
          <div className="mx-auto max-w-4xl">
            <motion.div
              initial={{ opacity: 0, scale: 0.96 }}
              whileInView={{ opacity: 1, scale: 1 }}
              viewport={{ once: true }}
              transition={{ duration: 0.5 }}
              className={`relative overflow-hidden rounded-3xl border p-12 text-center backdrop-blur-xl ${
                theme === "light"
                  ? "border-black/[0.08] bg-white shadow-[0_8px_32px_rgba(0,0,0,0.06)]"
                  : "border-white/[0.06] bg-gradient-to-br from-neon/5 via-slate-900/80 to-purple-500/5"
              }`}
            >
              <h2 className="font-display text-3xl font-bold text-white sm:text-4xl">
                Ready to turn social data into project-ready insights?
              </h2>
              <p className="mx-auto mt-4 max-w-2xl text-slate-400">
                Build with live platform connections, explainable analytics, automated reports, and a clean interface that is ready for demos.
              </p>
              <div className="mt-8 flex flex-wrap items-center justify-center gap-4">
                <Link to="/signup">
                  <Button className="gap-2 px-8 py-3.5">
                    Create free account
                    <ArrowRight size={16} />
                  </Button>
                </Link>
              </div>
            </motion.div>
          </div>
        </section>

        <footer className="border-t border-white/[0.04] px-6 py-8">
          <div className="mx-auto flex max-w-7xl flex-col items-center justify-between gap-4 md:flex-row">
            <div className="flex items-center gap-2">
              <Zap size={16} className="text-neon" />
              <span className="font-display text-sm font-bold text-white">Synapse</span>
              <span className="text-xs text-slate-600">(c) {new Date().getFullYear()}</span>
            </div>
            <div className="flex gap-6 text-xs text-slate-500">
              <Link to="/explore/instagram" className="transition hover:text-white">Instagram</Link>
              <Link to="/explore/youtube" className="transition hover:text-white">YouTube</Link>
              <Link to="/explore/x" className="transition hover:text-white">X / Twitter</Link>
              <Link to="/login" className="transition hover:text-white">Sign in</Link>
            </div>
          </div>
        </footer>
      </div>
    </div>
  );
}
