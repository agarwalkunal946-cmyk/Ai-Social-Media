import { useEffect, useMemo, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import {
  ArrowUpRight,
  BarChart3,
  Bookmark,
  ChevronDown,
  ChevronRight,
  ChevronUp,
  Eye,
  Hash,
  Heart,
  Loader2,
  Maximize2,
  MessageCircle,
  Moon,
  Play,
  Repeat2,
  Search,
  Sparkles,
  Sun,
  X as XIcon,
  Zap,
} from "lucide-react";
import { Link, useParams } from "react-router-dom";
import { Area, AreaChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis } from "recharts";
import { AnimatePresence, motion } from "framer-motion";

import { apiClient } from "../lib/apiClient";
import { Button } from "../components/ui/Button";
import { Panel } from "../components/ui/Panel";
import { GlowCard } from "../components/ui/GlowCard";
import { AnimatedBackground } from "../components/ui/AnimatedBackground";
import { InstagramBrandIcon, XBrandIcon, YouTubeBrandIcon } from "../components/ui/PlatformIcon";
import { useAuth } from "../hooks/useAuth";
import { useTheme } from "../hooks/useTheme";
import { useDebouncedValue } from "../hooks/useDebouncedValue";
import { resolveAssetUrl } from "../lib/assetUrl";

const stagger = { hidden: { opacity: 0 }, show: { opacity: 1, transition: { staggerChildren: 0.08 } } };
const fadeUp = { hidden: { opacity: 0, y: 16 }, show: { opacity: 1, y: 0, transition: { duration: 0.4 } } };

const platformNames = { instagram: "Instagram", youtube: "YouTube", x: "X / Twitter" };
const platformIcons = { instagram: InstagramBrandIcon, youtube: YouTubeBrandIcon, x: XBrandIcon };
const platformColors = {
  instagram: { accent: "from-pink-500 to-purple-500", glow: "rgba(225,48,108,0.12)", badge: "bg-pink-500/10 text-pink-400" },
  youtube: { accent: "from-red-500 to-orange-500", glow: "rgba(255,0,0,0.12)", badge: "bg-red-500/10 text-red-400" },
  x: { accent: "from-slate-200 to-slate-500", glow: "rgba(255,255,255,0.12)", badge: "bg-white/10 text-slate-300" },
};

const modeOptions = [
  { key: "connected", label: "My data" },
  { key: "trending", label: "Trending" },
  { key: "search", label: "Public search" },
];
const ITEMS_PER_PAGE = 6;
const defaultSearchSeeds = {
  youtube: "MrBeast",
  instagram: "cristiano",
  x: "@AlwaysRamCharan",
};

const normalize = (value = "") =>
  value.toLowerCase().replace(/@/g, "").replace(/[^a-z0-9\s]/g, " ").replace(/\s+/g, " ").trim();

const CustomTooltip = ({ active, payload, label }) => {
  if (!active || !payload?.length) return null;
  return (
    <div className="rounded-lg border border-white/10 bg-slate-900/95 px-3 py-2 text-xs shadow-lg backdrop-blur-xl">
      <p className="text-slate-400">{label}</p>
      <p className="font-mono font-semibold text-neon">{payload[0].value}</p>
    </div>
  );
};

function CatalogLoader() {
  return (
    <div className="space-y-4">
      {Array.from({ length: 3 }).map((_, index) => (
        <GlowCard key={`catalog-loader-${index}`} className="overflow-hidden p-4">
          <div className="flex gap-4">
            <div className="h-24 w-36 shrink-0 animate-pulse rounded-xl bg-white/10" />
            <div className="flex-1 space-y-3">
              <div className="h-4 w-20 animate-pulse rounded-full bg-white/10" />
              <div className="h-5 w-4/5 animate-pulse rounded-full bg-white/10" />
              <div className="h-4 w-2/3 animate-pulse rounded-full bg-white/10" />
              <div className="flex gap-2">
                <div className="h-3 w-16 animate-pulse rounded-full bg-white/10" />
                <div className="h-3 w-16 animate-pulse rounded-full bg-white/10" />
                <div className="h-3 w-16 animate-pulse rounded-full bg-white/10" />
              </div>
            </div>
          </div>
        </GlowCard>
      ))}
    </div>
  );
}

function SideRailLoader() {
  return (
    <div className="space-y-6">
      {Array.from({ length: 3 }).map((_, index) => (
        <Panel key={`side-loader-${index}`} className="p-5">
          <div className="space-y-3">
            <div className="h-4 w-28 animate-pulse rounded-full bg-white/10" />
            <div className="h-10 w-full animate-pulse rounded-2xl bg-white/10" />
            <div className="h-10 w-full animate-pulse rounded-2xl bg-white/10" />
            <div className="h-10 w-4/5 animate-pulse rounded-2xl bg-white/10" />
          </div>
        </Panel>
      ))}
    </div>
  );
}

function MetricIcon({ label }) {
  const lower = (label || "").toLowerCase();
  if (lower.includes("view") || lower.includes("reach") || lower.includes("avg")) return Eye;
  if (lower.includes("like")) return Heart;
  if (lower.includes("comment") || lower.includes("reply")) return MessageCircle;
  if (lower.includes("share") || lower.includes("repost") || lower.includes("retweet")) return Repeat2;
  if (lower.includes("save")) return Bookmark;
  return BarChart3;
}

function MoodBadge({ value }) {
  if (!value) return null;
  const lower = (value || "").toLowerCase();
  let color = "bg-slate-500/10 text-slate-400";
  if (lower.includes("positive")) color = "bg-emerald-500/10 text-emerald-400";
  if (lower.includes("negative")) color = "bg-rose-500/10 text-rose-400";
  if (lower.includes("mixed")) color = "bg-amber-500/10 text-amber-400";
  if (lower.includes("neutral")) color = "bg-blue-500/10 text-blue-400";
  return <span className={`rounded-full px-2.5 py-1 text-[11px] font-medium ${color}`}>{value}</span>;
}

function getThumb(item, platform) {
  if (item.thumbnail) return item.thumbnail;
  if (platform === "youtube" && item.video_id) return `https://img.youtube.com/vi/${item.video_id}/hqdefault.jpg`;
  if (platform === "x" && item.media_url) return item.media_url;
  return null;
}

function isPlayableMedia(item, platform) {
  if (platform === "youtube") return Boolean(item.video_id);
  if (platform === "instagram") return Boolean(item.media_url) && /reel|video/i.test(item.type || "");
  if (platform === "x") return Boolean(item.media_url) && item.player_type === "x-video";
  return false;
}

function getYouTubeEmbedUrl(videoId, autoPlay = false) {
  if (!videoId) return "";
  return `https://www.youtube.com/embed/${videoId}?rel=0${autoPlay ? "&autoplay=1" : ""}`;
}

function MediaPlayer({ item, platform, autoPlay = false }) {
  const thumb = getThumb(item, platform);

  if (platform === "youtube" && item.video_id) {
    return (
      <div className="aspect-video overflow-hidden rounded-2xl bg-black">
        <iframe
          src={getYouTubeEmbedUrl(item.video_id, autoPlay)}
          title={item.title || "YouTube player"}
          className="h-full w-full"
          allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture; web-share"
          allowFullScreen
        />
      </div>
    );
  }

  if (platform === "instagram" && item.media_url) {
    return (
      <div className="overflow-hidden rounded-2xl bg-black">
        <video
          src={item.media_url}
          poster={thumb || undefined}
          controls
          playsInline
          autoPlay={autoPlay}
          className="aspect-video h-full w-full bg-black object-contain"
        />
      </div>
    );
  }

  if (platform === "x" && item.media_url && item.player_type === "x-video") {
    return (
      <div className="overflow-hidden rounded-2xl bg-black">
        <video
          src={item.media_url}
          poster={thumb || undefined}
          controls
          playsInline
          autoPlay={autoPlay}
          className="aspect-video h-full w-full bg-black object-contain"
        />
      </div>
    );
  }

  return null;
}

function PlayerModal({ item, platform, onClose }) {
  return (
    <AnimatePresence>
      {item && (
        <>
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            onClick={onClose}
            className="fixed inset-0 z-[70] bg-black/80 backdrop-blur-sm"
          />
          <div className="fixed inset-0 z-[80] flex items-center justify-center p-4 md:p-6">
            <motion.div
              initial={{ opacity: 0, y: 24, scale: 0.98 }}
              animate={{ opacity: 1, y: 0, scale: 1 }}
              exit={{ opacity: 0, y: 24, scale: 0.98 }}
              className="w-full max-w-5xl overflow-hidden rounded-3xl border border-white/[0.08] bg-slate-950/95 shadow-2xl backdrop-blur-2xl"
            >
              <div className="flex items-start justify-between gap-4 border-b border-white/[0.06] px-6 py-5">
                <div className="min-w-0">
                  <p className="text-xs font-semibold uppercase tracking-[0.25em] text-neon/70">Viewer</p>
                  <h2 className="mt-2 line-clamp-2 font-display text-2xl font-bold text-white">{item.title}</h2>
                  <p className="mt-2 text-sm text-slate-400">{item.creator}</p>
                </div>
                <button onClick={onClose} className="text-slate-500 transition hover:text-white">
                  <XIcon size={18} />
                </button>
              </div>
              <div className="p-6">
                <MediaPlayer item={item} platform={platform} autoPlay />
              </div>
            </motion.div>
          </div>
        </>
      )}
    </AnimatePresence>
  );
}

function ContentCard({ item, platform, onAnalytics, onOpenPlayer }) {
  const [expanded, setExpanded] = useState(false);
  const [showInlinePlayer, setShowInlinePlayer] = useState(false);
  const colors = platformColors[platform] || platformColors.youtube;
  const thumb = getThumb(item, platform);
  const isPlayable = isPlayableMedia(item, platform);
  const moodMetric = item.metrics?.find((metric) => metric.label.toLowerCase() === "mood");
  const statMetrics = item.metrics?.filter((metric) => metric.label.toLowerCase() !== "mood") || [];
  const platformLink = item.url;

  useEffect(() => {
    if (!expanded) {
      setShowInlinePlayer(false);
    }
  }, [expanded]);

  return (
    <GlowCard glowColor={colors.glow} className="overflow-hidden transition-all duration-300">
      <div className="flex cursor-pointer select-none gap-4 p-4" onClick={() => setExpanded((value) => !value)}>
        {thumb ? (
          <div
            className={`relative h-24 w-36 shrink-0 overflow-hidden rounded-xl bg-white/[0.04] ${isPlayable ? "cursor-pointer" : ""}`}
            onClick={(event) => {
              if (!isPlayable) return;
              event.stopPropagation();
              setExpanded(true);
              setShowInlinePlayer(true);
            }}
          >
            <img src={thumb} alt={item.title} className="h-full w-full object-cover" />
            {isPlayable && (
              <div className="absolute inset-0 flex items-center justify-center bg-black/30">
                <div
                  className="flex h-10 w-10 items-center justify-center rounded-full bg-slate-950/80 ring-1 ring-white/15"
                  style={{ color: "#ffffff" }}
                >
                  <Play size={16} className="ml-0.5" fill="currentColor" />
                </div>
              </div>
            )}
            {item.duration && (
              <span className="absolute bottom-1 right-1 rounded bg-black/80 px-1.5 py-0.5 text-[10px] font-mono text-white">
                {item.duration}
              </span>
            )}
          </div>
        ) : (
          <div className={`relative flex h-24 w-36 shrink-0 items-center justify-center rounded-xl bg-gradient-to-br ${colors.accent} opacity-20`}>
            {platformIcons[platform] &&
              (() => {
                const Icon = platformIcons[platform];
                return <Icon size={28} className="text-white opacity-60" />;
              })()}
          </div>
        )}

        <div className="min-w-0 flex-1">
          <div className="flex flex-wrap items-center gap-2">
            <span className={`rounded-full px-2 py-0.5 text-[10px] font-semibold uppercase tracking-wider ${colors.badge}`}>
              {item.type}
            </span>
            {moodMetric && <MoodBadge value={moodMetric.value} />}
          </div>

          <h3 className="mt-1.5 line-clamp-2 font-display text-base font-bold leading-snug text-white">{item.title}</h3>
          {item.creator && <p className="mt-1 truncate text-xs text-slate-400">{item.creator}</p>}

          <div className="mt-2 flex flex-wrap gap-2">
            {statMetrics.slice(0, 3).map((metric) => (
              <span key={`${item.id}-${metric.label}`} className="text-[11px] text-slate-500">
                {metric.value} {metric.label.toLowerCase()}
              </span>
            ))}
          </div>
        </div>

        <div className="flex shrink-0 flex-col items-center justify-center">
          {expanded ? <ChevronUp size={18} className="text-slate-500" /> : <ChevronDown size={18} className="text-slate-500" />}
        </div>
      </div>

      <AnimatePresence>
        {expanded && (
          <motion.div
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: "auto", opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            transition={{ duration: 0.25, ease: "easeInOut" }}
            className="overflow-hidden"
          >
            <div className="space-y-4 border-t border-white/[0.06] px-5 pb-5 pt-4">
              <p className="text-sm leading-relaxed text-slate-300">{item.description}</p>

              {showInlinePlayer && isPlayable && (
                <MediaPlayer item={item} platform={platform} autoPlay />
              )}

              {item.creator_url && (
                <a href={item.creator_url} target="_blank" rel="noreferrer" className="inline-flex items-center gap-1.5 text-xs font-medium text-neon transition hover:text-white">
                  {item.creator} <ArrowUpRight size={12} />
                </a>
              )}

              <div className="flex flex-wrap gap-2">
                {statMetrics.map((metric) => {
                  const Icon = MetricIcon({ label: metric.label });
                  return (
                    <div key={`${item.id}-detail-${metric.label}`} className="inline-flex items-center gap-1.5 rounded-lg bg-white/[0.04] px-3 py-2 text-xs">
                      <Icon size={13} className="text-neon" />
                      <span className="text-slate-400">{metric.label}</span>
                      <strong className="font-mono text-white">{metric.value}</strong>
                    </div>
                  );
                })}
              </div>

              {item.tags?.length > 0 && (
                <div className="flex flex-wrap gap-1.5">
                  {item.tags.map((tag) => (
                    <span key={`${item.id}-${tag}`} className="rounded-full bg-white/[0.04] px-2.5 py-1 text-[11px] text-slate-500">
                      #{tag}
                    </span>
                  ))}
                </div>
              )}

              {item.insight && (
                <div className="rounded-xl border border-neon/10 bg-neon/[0.04] px-4 py-3 text-sm text-slate-300">
                  {item.insight}
                </div>
              )}

              <div className="flex flex-wrap gap-2 pt-1">
                {isPlayable && !showInlinePlayer && (
                  <button
                    onClick={(event) => {
                      event.stopPropagation();
                      setShowInlinePlayer(true);
                    }}
                    className="inline-flex cursor-pointer items-center gap-2 rounded-xl border border-white/10 bg-white/[0.03] px-4 py-2.5 text-xs font-medium text-slate-200 transition hover:bg-white/[0.08] hover:text-white"
                  >
                    <Play size={14} />
                    Play here
                  </button>
                )}
                {isPlayable && (
                  <button
                    onClick={(event) => {
                      event.stopPropagation();
                      onOpenPlayer(item);
                    }}
                    className="inline-flex cursor-pointer items-center gap-2 rounded-xl border border-white/10 bg-white/[0.03] px-4 py-2.5 text-xs font-medium text-slate-200 transition hover:bg-white/[0.08] hover:text-white"
                  >
                    <Maximize2 size={14} />
                    Big view
                  </button>
                )}
                {platformLink && (
                  <a
                    href={platformLink}
                    target="_blank"
                    rel="noreferrer"
                    className={`inline-flex items-center gap-2 rounded-xl px-5 py-2.5 text-sm font-medium text-white transition ${
                      platform === "youtube"
                        ? "bg-red-600 hover:bg-red-700"
                        : platform === "instagram"
                        ? "bg-gradient-to-r from-pink-500 to-purple-600 hover:brightness-110"
                        : "bg-blue-600 hover:bg-blue-700"
                    }`}
                  >
                    <Play size={14} />
                    {item.url_label || `Open on ${platformNames[platform]}`}
                  </a>
                )}
                {item.creator_url && item.creator_url !== platformLink && (
                  <a
                    href={item.creator_url}
                    target="_blank"
                    rel="noreferrer"
                    className="inline-flex items-center gap-2 rounded-xl border border-white/10 bg-white/[0.03] px-4 py-2.5 text-xs font-medium text-slate-300 transition hover:bg-white/[0.08] hover:text-white"
                  >
                    {item.creator_label || "View profile"} <ArrowUpRight size={14} />
                  </a>
                )}
                <button
                  onClick={(event) => {
                    event.stopPropagation();
                    onAnalytics(item);
                  }}
                  className="inline-flex cursor-pointer items-center gap-2 rounded-xl border border-neon/20 bg-neon/10 px-4 py-2.5 text-xs font-medium text-neon transition hover:bg-neon/15 hover:text-white"
                >
                  <BarChart3 size={14} />
                  Analytics
                </button>
              </div>
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </GlowCard>
  );
}

function AnalyticsModal({ item, data, isLoading, onClose }) {
  return (
    <AnimatePresence>
      {item && (
        <>
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            onClick={onClose}
            className="fixed inset-0 z-[70] bg-black/70 backdrop-blur-sm"
          />
          <div className="fixed inset-0 z-[80] flex items-center justify-center p-4 md:p-6">
            <motion.div
              initial={{ opacity: 0, y: 24, scale: 0.98 }}
              animate={{ opacity: 1, y: 0, scale: 1 }}
              exit={{ opacity: 0, y: 24, scale: 0.98 }}
              className="w-full max-w-3xl overflow-hidden rounded-3xl border border-white/[0.08] bg-slate-950/95 shadow-2xl backdrop-blur-2xl"
            >
              <div className="flex items-start justify-between gap-4 border-b border-white/[0.06] px-6 py-5">
                <div>
                  <p className="text-xs font-semibold uppercase tracking-[0.25em] text-neon/70">Analytics</p>
                  <h2 className="mt-2 font-display text-2xl font-bold text-white">{data?.title || item.title}</h2>
                  <p className="mt-2 max-w-2xl text-sm text-slate-400">{data?.summary || item.description}</p>
                </div>
                <button onClick={onClose} className="text-slate-500 transition hover:text-white">
                  <XIcon size={18} />
                </button>
              </div>

              <div className="max-h-[78vh] overflow-auto px-6 py-5">
                {isLoading ? (
                  <div className="flex min-h-[300px] items-center justify-center gap-3 text-sm text-slate-400">
                    <Loader2 size={18} className="animate-spin text-neon" />
                    Fetching analytics...
                  </div>
                ) : (
                  <div className="space-y-6">
                    {(data?.cards || []).length > 0 && (
                      <section className="grid gap-3 md:grid-cols-2 xl:grid-cols-3">
                        {data.cards.map((card) => (
                          <div key={card.label} className="rounded-2xl border border-white/[0.06] bg-white/[0.03] p-4">
                            <p className="text-[11px] uppercase tracking-wider text-slate-500">{card.label}</p>
                            <p className="mt-2 font-display text-2xl font-bold text-white">{card.value}</p>
                          </div>
                        ))}
                      </section>
                    )}

                    {(data?.chart || []).length > 0 && (
                      <Panel className="p-5">
                        <h3 className="text-xs font-semibold uppercase tracking-[0.2em] text-slate-500">Trend</h3>
                        <div className="mt-4 h-56">
                          <ResponsiveContainer width="100%" height="100%">
                            <AreaChart data={data.chart}>
                              <defs>
                                <linearGradient id="analyticsArea" x1="0" x2="0" y1="0" y2="1">
                                  <stop offset="5%" stopColor="#00e5ff" stopOpacity={0.2} />
                                  <stop offset="95%" stopColor="#00e5ff" stopOpacity={0} />
                                </linearGradient>
                              </defs>
                              <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.04)" />
                              <XAxis dataKey="label" stroke="#475569" tick={{ fontSize: 11 }} />
                              <Tooltip content={<CustomTooltip />} />
                              <Area type="monotone" dataKey="value" stroke="#00e5ff" strokeWidth={2} fill="url(#analyticsArea)" />
                            </AreaChart>
                          </ResponsiveContainer>
                        </div>
                      </Panel>
                    )}

                    {(data?.insights || []).length > 0 && (
                      <div className="space-y-3">
                        {data.insights.map((insight) => (
                          <div key={insight} className="rounded-2xl border border-white/[0.06] bg-white/[0.03] p-4 text-sm leading-relaxed text-slate-300">
                            {insight}
                          </div>
                        ))}
                      </div>
                    )}

                    {data?.external_url && (
                      <a
                        href={data.external_url}
                        target="_blank"
                        rel="noreferrer"
                        className="inline-flex items-center gap-2 text-sm font-medium text-neon transition hover:text-white"
                      >
                        Open original post <ArrowUpRight size={14} />
                      </a>
                    )}
                  </div>
                )}
              </div>
            </motion.div>
          </div>
        </>
      )}
    </AnimatePresence>
  );
}

export function PublicPlatformPage() {
  const { platform } = useParams();
  const { backendUser, firebaseUser, loading: authLoading } = useAuth();
  const [query, setQuery] = useState("");
  const [mode, setMode] = useState("connected");
  const [selectedItem, setSelectedItem] = useState(null);
  const [playerItem, setPlayerItem] = useState(null);
  const [page, setPage] = useState(1);
  const debouncedQuery = useDebouncedValue(query, 280);
  const fetchMode = mode;
  const searchQuery = mode === "search" ? debouncedQuery.trim() : "";
  const { theme, toggleTheme } = useTheme();
  const providersQuery = useQuery({
    queryKey: ["providers", "public-platform-page"],
    retry: false,
    placeholderData: (previousData) => previousData,
    queryFn: async () => {
      try {
        return (await apiClient.get("/providers")).data;
      } catch {
        return { items: [] };
      }
    },
  });

  const platformQuery = useQuery({
    queryKey: ["public-platform", platform, fetchMode, searchQuery],
    placeholderData: (previousData) => previousData,
    queryFn: async () =>
      (
        await apiClient.get(`/public/platform/${platform}`, {
          params: {
            mode: fetchMode,
            q: searchQuery || undefined,
          },
        })
      ).data,
  });
  const { data } = platformQuery;

  const analyticsQuery = useQuery({
    queryKey: ["platform-item-analytics", platform, selectedItem?.id, selectedItem?.analytics_source],
    enabled: Boolean(selectedItem),
    placeholderData: (previousData) => previousData,
    queryFn: async () =>
      (
        await apiClient.post(`/public/platform/${platform}/analytics`, {
          item: selectedItem,
          mode: fetchMode,
        })
      ).data,
  });

  useEffect(() => {
    setPage(1);
  }, [platform, fetchMode, searchQuery, data?.headline]);

  const PlatformIcon = platformIcons[platform] || Zap;
  const colors = platformColors[platform] || platformColors.youtube;
  const providerConnection = useMemo(
    () => (providersQuery.data?.items || []).find((item) => item.platform === platform),
    [platform, providersQuery.data?.items]
  );
  const hasConnectedProvider = Boolean(providerConnection?.connected);
  const isLive = data?.data_source === "live";
  const isConnected = isLive || data?.data_source === "connected";
  const isTypingSearch = mode === "search" && query !== debouncedQuery;
  const isPageLoading = (platformQuery.isLoading && !platformQuery.data) || (isTypingSearch && !platformQuery.data);
  const viewData = data;
  const accountLabel =
    backendUser?.display_name
    || backendUser?.email?.split("@")[0]
    || firebaseUser?.displayName
    || firebaseUser?.email?.split("@")[0]
    || "My account";
  const accountAvatar =
    (backendUser?.avatar_url ? resolveAssetUrl(backendUser.avatar_url) : "")
    || firebaseUser?.photoURL
    || "";
  const accountHref = backendUser?.role === "admin" ? "/admin" : "/dashboard";

  const filteredCatalog = useMemo(() => {
    const catalog = viewData?.catalog || [];
    if (fetchMode === "search") return catalog;
    if (!debouncedQuery.trim()) return catalog;
    const normalized = normalize(debouncedQuery);
    return catalog.filter((item) =>
      normalize([item.title, item.creator, item.description, ...(item.tags || [])].join(" ")).includes(normalized)
    );
  }, [viewData?.catalog, debouncedQuery, fetchMode]);
  const trendingHashtags = useMemo(() => {
    const counts = new Map();
    (viewData?.catalog || []).forEach((item) => {
      (item.tags || []).forEach((tag) => {
        const normalizedTag = String(tag || "").trim().replace(/^#/, "").toLowerCase();
        if (!normalizedTag) return;
        counts.set(normalizedTag, (counts.get(normalizedTag) || 0) + 1);
      });
    });
    return [...counts.entries()]
      .sort((left, right) => right[1] - left[1])
      .slice(0, 8)
      .map(([tag, count]) => ({ tag: `#${tag}`, count }));
  }, [viewData?.catalog]);

  const totalPages = Math.max(1, Math.ceil(filteredCatalog.length / ITEMS_PER_PAGE));
  const currentPage = Math.min(page, totalPages);
  const paginatedCatalog = filteredCatalog.slice((currentPage - 1) * ITEMS_PER_PAGE, currentPage * ITEMS_PER_PAGE);
  const featuredTitle = isConnected
    ? "Highlights"
    : platform === "youtube"
    ? "Recommended creators"
    : platform === "instagram"
    ? "Featured profiles"
    : "Featured";

  const statusLabel = useMemo(() => {
    if (isPageLoading) return "Fetching live data";
    if (viewData?.data_source === "search-ready") return "Ready for profile search";
    if (viewData?.data_source === "limitation") return "Showing available access mode";
    if (isConnected) {
      if (isLive) return "Showing your live connected data";
      return "Showing your connected account snapshot";
    }
    if (fetchMode === "search") return "Showing live public search results";
    if (fetchMode === "trending") return "Showing live trending mode";
    return "Waiting for live access";
  }, [fetchMode, isConnected, isLive, isPageLoading, viewData?.data_source]);

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
            <div className="flex items-center gap-2">
              {["instagram", "youtube", "x"].map((item) => {
                const Icon = platformIcons[item];
                return (
                  <Link
                    key={item}
                    to={`/explore/${item}`}
                    className={`hidden h-9 w-9 items-center justify-center rounded-xl border transition sm:flex ${
                      item === platform
                        ? "border-neon/30 bg-neon/10 text-neon"
                        : "border-white/[0.06] bg-white/[0.03] text-slate-400 hover:text-white"
                    }`}
                    title={platformNames[item]}
                  >
                    <Icon size={16} />
                  </Link>
                );
              })}
              <button
                onClick={toggleTheme}
                className="flex h-9 w-9 cursor-pointer items-center justify-center rounded-xl border border-white/[0.06] bg-white/[0.03] text-slate-400 transition hover:text-white"
              >
                {theme === "dark" ? <Sun size={16} /> : <Moon size={16} />}
              </button>
              {(backendUser || firebaseUser) ? (
                <Link
                  to={accountHref}
                  className="flex items-center gap-3 rounded-xl border border-white/[0.06] bg-white/[0.03] px-3 py-2 text-left transition hover:bg-white/[0.06]"
                >
                  <div className="flex h-9 w-9 items-center justify-center overflow-hidden rounded-xl bg-white/[0.06] text-sm font-semibold text-white">
                    {accountAvatar ? (
                      <img src={accountAvatar} alt={accountLabel} className="h-full w-full object-cover" />
                    ) : (
                      accountLabel[0]?.toUpperCase() || "U"
                    )}
                  </div>
                  <div className="hidden sm:block">
                    <p className="max-w-[10rem] truncate text-sm font-medium text-white">{accountLabel}</p>
                    <p className="text-[11px] text-slate-500">{backendUser?.role === "admin" ? "Open admin panel" : "Open dashboard"}</p>
                  </div>
                </Link>
              ) : authLoading ? (
                <div className="h-9 w-28 animate-pulse rounded-xl border border-white/[0.06] bg-white/[0.03]" />
              ) : (
                <Link to="/login">
                  <Button className="text-xs">Sign in</Button>
                </Link>
              )}
            </div>
          </div>
        </nav>

        <div className="mx-auto max-w-7xl space-y-8 px-6 py-8">
          <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }}>
            <div className="flex items-start gap-4">
              <div className={`flex h-14 w-14 shrink-0 items-center justify-center rounded-2xl bg-gradient-to-br ${colors.accent}`}>
                <PlatformIcon size={26} className="text-white" />
              </div>
              <div>
                <h1 className="font-display text-3xl font-bold text-white lg:text-4xl">
                  {viewData?.headline || `Explore ${platformNames[platform]}`}
                </h1>
                <p className="mt-2 max-w-2xl text-sm text-slate-400">{viewData?.summary || `Browse ${platformNames[platform]} analytics and public insights.`}</p>
              </div>
            </div>

            <div className="mt-4 flex flex-wrap items-center gap-3">
              <div className="inline-flex items-center gap-2 rounded-full bg-white/[0.04] px-4 py-2 text-xs text-slate-300">
                {isPageLoading ? (
                  <Loader2 size={12} className="animate-spin text-neon" />
                ) : (
                  <span className="glow-dot" style={{ width: 6, height: 6 }} />
                )}
                {statusLabel}
              </div>
              {viewData?.external_url && (
                <a href={viewData.external_url} target="_blank" rel="noreferrer" className="inline-flex items-center gap-2 text-sm text-neon transition hover:text-white">
                  {viewData.external_label || "Open"} <ArrowUpRight size={14} />
                </a>
              )}
            </div>
          </motion.div>

          <div className="flex flex-wrap gap-2">
            {modeOptions.map((option) => (
              <button
                key={option.key}
                onClick={() => {
                  setMode(option.key);
                  if (option.key === "search" && !query.trim()) {
                    setQuery(defaultSearchSeeds[platform] || "");
                  }
                  if (option.key !== "search") {
                    setQuery("");
                  }
                }}
                className={`rounded-xl px-4 py-2 text-xs font-medium transition ${
                  mode === option.key
                    ? "bg-neon/15 text-neon"
                    : "bg-white/[0.03] text-slate-400 hover:bg-white/[0.06] hover:text-white"
                }`}
              >
                {option.label}
              </button>
            ))}
          </div>

          {!isPageLoading && (viewData?.trending_cards || []).length > 0 && (
            <section className="grid gap-4 sm:grid-cols-3">
              {viewData.trending_cards.map((card) => (
                <GlowCard key={card.name} glowColor={colors.glow} className="p-5">
                  <p className="text-xs text-slate-400">{card.name}</p>
                  <h3 className="mt-2 font-display text-3xl font-bold text-white">{card.value}</h3>
                </GlowCard>
              ))}
            </section>
          )}

          <section className="grid gap-8 xl:grid-cols-[1.2fr_0.8fr]">
            <div className="space-y-5">
              <div className="flex items-center gap-3 rounded-2xl border border-white/[0.06] bg-white/[0.03] px-5 py-4 backdrop-blur-xl">
                <Search className="shrink-0 text-slate-500" size={18} />
                <input
                  value={query}
                  onChange={(event) => {
                    setQuery(event.target.value);
                    if (mode !== "search") {
                      setMode("search");
                    }
                  }}
                  className="w-full bg-transparent text-sm text-white outline-none placeholder:text-slate-500"
                  placeholder={viewData?.search_placeholder || `Search ${platformNames[platform]} content...`}
                />
                {query && (
                  <button onClick={() => setQuery("")} className="cursor-pointer text-slate-500 transition hover:text-white">
                    <XIcon size={16} />
                  </button>
                )}
              </div>

              {debouncedQuery.trim() && !isPageLoading && (
                <p className="text-xs text-slate-500">
                  {filteredCatalog.length} result{filteredCatalog.length !== 1 ? "s" : ""} for "{debouncedQuery}"
                </p>
              )}

              {isPageLoading ? (
                <CatalogLoader />
              ) : (
                <motion.div variants={stagger} initial="hidden" animate="show" className="space-y-4">
                  {paginatedCatalog.map((item) => (
                    <motion.div key={item.id} variants={fadeUp}>
                      <ContentCard item={item} platform={platform} onAnalytics={setSelectedItem} onOpenPlayer={setPlayerItem} />
                    </motion.div>
                  ))}
                </motion.div>
              )}

              {!isPageLoading && filteredCatalog.length === 0 && (
                <Panel className="p-8 text-center">
                  <p className="text-slate-400">
                    {viewData?.data_source === "limitation" ? "This access mode does not expose more public content right now." : "No content to display yet."}
                  </p>
                  {!hasConnectedProvider && (
                    <Link to="/connect">
                      <Button className="mt-4 text-xs">Connect your account</Button>
                    </Link>
                  )}
                  {!hasConnectedProvider && (
                    <p className="mt-3 text-xs text-slate-500">
                      Connect {platformNames[platform]} to unlock richer results and item analytics.
                    </p>
                  )}
                  {viewData?.data_source === "limitation" && (
                    <p className="mt-3 text-xs text-slate-500">
                      Try public search or connect the platform for account-backed analytics.
                    </p>
                  )}
                </Panel>
              )}

              {!isPageLoading && filteredCatalog.length > ITEMS_PER_PAGE && (
                <div className="flex flex-wrap items-center justify-between gap-3 rounded-2xl border border-white/[0.06] bg-white/[0.03] px-4 py-3 text-xs text-slate-400">
                  <span>
                    Showing {(currentPage - 1) * ITEMS_PER_PAGE + 1}-{Math.min(currentPage * ITEMS_PER_PAGE, filteredCatalog.length)} of {filteredCatalog.length}
                  </span>
                  <div className="flex gap-2">
                    <button
                      onClick={() => setPage((value) => Math.max(1, value - 1))}
                      disabled={currentPage === 1}
                      className="rounded-lg border border-white/[0.08] px-3 py-1.5 transition disabled:cursor-not-allowed disabled:opacity-40 hover:bg-white/[0.06] hover:text-white"
                    >
                      Previous
                    </button>
                    <button
                      onClick={() => setPage((value) => Math.min(totalPages, value + 1))}
                      disabled={currentPage === totalPages}
                      className="rounded-lg border border-white/[0.08] px-3 py-1.5 transition disabled:cursor-not-allowed disabled:opacity-40 hover:bg-white/[0.06] hover:text-white"
                    >
                      Next
                    </button>
                  </div>
                </div>
              )}

              {!isPageLoading && (viewData?.preview_charts || []).length > 0 && (
                <Panel className="p-5">
                  <h3 className="text-xs font-semibold uppercase tracking-[0.2em] text-slate-500">
                    {isConnected ? "Your activity" : "Engagement trend"}
                  </h3>
                  <div className="mt-4 h-56">
                    <ResponsiveContainer width="100%" height="100%">
                      <AreaChart data={viewData.preview_charts}>
                        <defs>
                          <linearGradient id="pubArea" x1="0" x2="0" y1="0" y2="1">
                            <stop offset="5%" stopColor="#00e5ff" stopOpacity={0.2} />
                            <stop offset="95%" stopColor="#00e5ff" stopOpacity={0} />
                          </linearGradient>
                        </defs>
                        <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.04)" />
                        <XAxis dataKey="label" stroke="#475569" tick={{ fontSize: 11 }} />
                        <Tooltip content={<CustomTooltip />} />
                        <Area type="monotone" dataKey="value" stroke="#00e5ff" strokeWidth={2} fill="url(#pubArea)" />
                      </AreaChart>
                    </ResponsiveContainer>
                  </div>
                </Panel>
              )}
            </div>

            <div className="space-y-6">
              {isPageLoading ? (
                <SideRailLoader />
              ) : (
                <>
                  {(viewData?.hero_metrics || []).length > 0 && (
                    <Panel className="p-5">
                      <h2 className="font-display text-lg font-bold text-white">{isConnected ? "Your account" : "Quick insights"}</h2>
                      <div className="mt-4 space-y-3">
                        {viewData.hero_metrics.map((metric) => (
                          <div key={metric.label} className="rounded-xl bg-white/[0.03] p-4">
                            <p className="text-[11px] uppercase tracking-wider text-slate-500">{metric.label}</p>
                            <p className="mt-1 text-sm font-semibold text-white">{metric.value}</p>
                          </div>
                        ))}
                      </div>
                    </Panel>
                  )}

                  {(viewData?.suggested_searches || []).length > 0 && (
                    <Panel className="p-5">
                      <div className="flex items-center gap-2">
                        <Sparkles size={16} className="text-amber-400" />
                        <h2 className="font-display text-lg font-bold text-white">Try searching</h2>
                      </div>
                      <div className="mt-4 flex flex-wrap gap-2">
                        {viewData.suggested_searches.map((item) => (
                          <button
                            key={item}
                            onClick={() => {
                              setMode("search");
                              setQuery(item);
                            }}
                            className="cursor-pointer rounded-lg bg-white/5 px-3 py-1.5 text-xs text-slate-400 transition hover:bg-white/10 hover:text-white"
                          >
                            {item}
                          </button>
                        ))}
                      </div>
                    </Panel>
                  )}

                  {!!trendingHashtags.length && (
                    <Panel className="p-5">
                      <div className="flex items-center gap-2">
                        <Hash size={16} className="text-neon" />
                        <h2 className="font-display text-lg font-bold text-white">Trending hashtags</h2>
                      </div>
                      <div className="mt-4 flex flex-wrap gap-2">
                        {trendingHashtags.map((item) => (
                          <div key={item.tag} className="rounded-lg bg-white/5 px-3 py-1.5 text-xs text-slate-300">
                            {item.tag} <span className="text-slate-500">({item.count})</span>
                          </div>
                        ))}
                      </div>
                    </Panel>
                  )}

                  {(viewData?.featured_profiles || []).length > 0 && (
                    <Panel className="p-5">
                      <h2 className="font-display text-lg font-bold text-white">{featuredTitle}</h2>
                      <div className="mt-4 space-y-3">
                        {viewData.featured_profiles.map((card) => (
                          <div key={card.name} className="rounded-xl bg-white/[0.03] p-4 transition hover:bg-white/[0.05]">
                            <div className="flex items-center justify-between gap-2">
                              <h3 className="truncate font-display text-sm font-bold text-white">{card.name}</h3>
                              <span className={`shrink-0 rounded-lg px-2 py-0.5 text-[10px] font-medium ${colors.badge}`}>{card.type}</span>
                            </div>
                            <p className="mt-2 text-xs leading-relaxed text-slate-400">{card.insight}</p>
                          </div>
                        ))}
                      </div>
                    </Panel>
                  )}

                  {(viewData?.side_insights || []).length > 0 && (
                    <Panel className="p-5">
                      <h2 className="font-display text-lg font-bold text-white">Notes</h2>
                      <div className="mt-4 space-y-3">
                        {viewData.side_insights.map((item) => (
                          <div key={item.title} className="rounded-xl bg-white/[0.03] p-4">
                            <h3 className="text-sm font-semibold text-white">{item.title}</h3>
                            <p className="mt-2 text-xs leading-relaxed text-slate-400">{item.body}</p>
                          </div>
                        ))}
                      </div>
                    </Panel>
                  )}

                  {!hasConnectedProvider && (
                    <Panel className="p-6">
                      <div className="text-center">
                        <div className={`mx-auto flex h-14 w-14 items-center justify-center rounded-2xl bg-gradient-to-br ${colors.accent}`}>
                          <PlatformIcon size={24} className="text-white" />
                        </div>
                        <h3 className="mt-4 font-display text-lg font-bold text-white">Want your own data?</h3>
                        <p className="mt-2 text-xs text-slate-400">Connect your {platformNames[platform]} account to see personal analytics and richer item insights.</p>
                        <Link to="/connect">
                          <Button className="mt-4 w-full gap-2 text-xs">
                            <ChevronRight size={14} /> Connect {platformNames[platform]}
                          </Button>
                        </Link>
                      </div>
                    </Panel>
                  )}
                </>
              )}
            </div>
          </section>
        </div>
      </div>

      <AnalyticsModal
        item={selectedItem}
        data={analyticsQuery.data}
        isLoading={analyticsQuery.isLoading || analyticsQuery.isFetching}
        onClose={() => setSelectedItem(null)}
      />
      <PlayerModal item={playerItem} platform={platform} onClose={() => setPlayerItem(null)} />
    </div>
  );
}
