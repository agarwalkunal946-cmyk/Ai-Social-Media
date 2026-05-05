import { useMemo, useState } from "react";
import { useMutation, useQuery } from "@tanstack/react-query";
import {
  Activity,
  Bot,
  BrainCircuit,
  FileText,
  Hash,
  MessageSquareText,
  ShieldAlert,
  Sparkles,
  TrendingUp,
  TriangleAlert,
  Users,
} from "lucide-react";
import { Area, AreaChart, CartesianGrid, Cell, Pie, PieChart, ResponsiveContainer, Tooltip, XAxis } from "recharts";
import { motion } from "framer-motion";
import { Link } from "react-router-dom";

import { AppShell } from "../components/layout/AppShell";
import { platformBrandIcons } from "../components/ui/PlatformIcon";
import { Button } from "../components/ui/Button";
import { DashboardAssistantWidget } from "../components/ui/DashboardAssistantWidget";
import { Panel } from "../components/ui/Panel";
import { StatCard } from "../components/ui/StatCard";
import { TopContentMediaCard } from "../components/ui/TopContentMediaCard";
import { useAuth } from "../hooks/useAuth";
import { apiClient } from "../lib/apiClient";
import { resolveAssetUrl } from "../lib/assetUrl";

const sentimentColors = ["#00e5ff", "#94a3b8", "#f43f5e"];
const apiRoot = (import.meta.env.VITE_API_BASE_URL || "http://localhost:8000/api").replace(/\/api$/, "");
const stagger = { hidden: { opacity: 0 }, show: { opacity: 1, transition: { staggerChildren: 0.08 } } };
const fadeUp = { hidden: { opacity: 0, y: 16 }, show: { opacity: 1, y: 0, transition: { duration: 0.4 } } };

const platformColors = {
  instagram: "from-pink-500 to-purple-500",
  youtube: "from-red-500 to-orange-500",
  x: "from-slate-200 to-slate-500",
};

const CustomTooltip = ({ active, payload, label }) => {
  if (!active || !payload?.length) return null;
  return (
    <div className="rounded-lg border border-white/10 bg-slate-900/95 px-3 py-2 text-xs shadow-lg backdrop-blur-xl">
      <p className="text-slate-400">{label}</p>
      <p className="font-mono font-semibold text-neon">{payload[0].value}</p>
    </div>
  );
};

function DashboardStatSkeleton() {
  return <div className="min-h-[8.75rem] animate-pulse rounded-3xl border border-white/[0.06] bg-white/[0.03]" />;
}

function ProviderCardSkeleton() {
  return (
    <div className="rounded-xl bg-white/[0.03] p-4">
      <div className="flex items-center gap-3">
        <div className="h-10 w-10 animate-pulse rounded-xl bg-white/10" />
        <div className="min-w-0 flex-1 space-y-2">
          <div className="h-4 w-28 animate-pulse rounded-full bg-white/10" />
          <div className="h-3 w-36 animate-pulse rounded-full bg-white/10" />
        </div>
        <div className="h-6 w-16 animate-pulse rounded-full bg-white/10" />
      </div>
    </div>
  );
}

function PanelSkeleton({ rows = 4, chart = false }) {
  return (
    <Panel className="p-5">
      <div className="space-y-3">
        <div className="h-4 w-28 animate-pulse rounded-full bg-white/10" />
        <div className="h-8 w-40 animate-pulse rounded-full bg-white/10" />
        {chart ? (
          <div className="mt-4 h-56 animate-pulse rounded-2xl bg-white/10" />
        ) : (
          Array.from({ length: rows }).map((_, index) => <div key={index} className="h-12 animate-pulse rounded-2xl bg-white/10" />)
        )}
      </div>
    </Panel>
  );
}

function ModuleCard({ title, value, detail, icon: Icon }) {
  return (
    <Panel className="p-5">
      <div className="flex items-start justify-between gap-4">
        <div>
          <p className="text-xs font-semibold uppercase tracking-[0.18em] text-slate-500">{title}</p>
          <h3 className="mt-3 font-display text-2xl font-bold text-white">{value}</h3>
          <p className="mt-2 text-xs leading-relaxed text-slate-400">{detail}</p>
        </div>
        <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl bg-neon/10">
          <Icon size={18} className="text-neon" />
        </div>
      </div>
    </Panel>
  );
}

function InsightMetric({ label, value, detail }) {
  return (
    <div className="rounded-2xl bg-white/[0.03] p-4">
      <p className="text-[10px] font-semibold uppercase tracking-[0.18em] text-slate-500">{label}</p>
      <h3 className="mt-2 font-display text-lg font-bold text-white">{value}</h3>
      <p className="mt-2 text-xs leading-relaxed text-slate-400">{detail}</p>
    </div>
  );
}

export function DashboardPage() {
  const { backendUser } = useAuth();
  const [assistantOpen, setAssistantOpen] = useState(false);
  const [chatInput, setChatInput] = useState("");
  const [chatHistory, setChatHistory] = useState([]);

  const dashboardQuery = useQuery({
    queryKey: ["dashboard"],
    placeholderData: (previousData) => previousData,
    queryFn: async () => (await apiClient.get("/dashboard")).data,
  });
  const alertsQuery = useQuery({
    queryKey: ["alerts"],
    placeholderData: (previousData) => previousData,
    queryFn: async () => (await apiClient.get("/alerts")).data,
  });
  const providersQuery = useQuery({
    queryKey: ["providers"],
    placeholderData: (previousData) => previousData,
    queryFn: async () => (await apiClient.get("/providers")).data,
  });
  const reportsQuery = useQuery({
    queryKey: ["reports"],
    placeholderData: (previousData) => previousData,
    queryFn: async () => (await apiClient.get("/reports")).data,
  });
  const data = dashboardQuery.data;

  const chatbotMutation = useMutation({
    mutationFn: async (message) => (await apiClient.post("/dashboard/chatbot", { message })).data,
    onSuccess: (response, message) => {
      setChatHistory((current) => [
        ...current,
        { role: "user", text: message },
        {
          role: "assistant",
          text: response.answer,
          bullets: response.bullets || [],
          followUp: response.follow_up || [],
          statCards: response.stat_cards || [],
          mediaItems: response.media_items || [],
        },
      ]);
    },
  });

  const firstName = (backendUser?.display_name || "").split(" ")[0] || "there";
  const providers = providersQuery.data?.items || [];
  const alerts = alertsQuery.data?.items || [];
  const reports = reportsQuery.data?.items || [];
  const connectedAccounts = data?.connected_accounts || [];
  const sentiment = data?.sentiment_breakdown || [];
  const emotions = data?.emotion_breakdown || [];
  const audienceInsightCards = data?.audience_insights?.cards || [];
  const explainabilityFactors = data?.explainable_ai?.factors || [];
  const moderationQueue = data?.moderation_queue || [];
  const crisisAlerts = data?.crisis_alerts || [];
  const trendingHashtags = data?.trending_hashtags || [];
  const sourceCards = connectedAccounts.length
    ? [
        ...connectedAccounts,
        ...providers
          .filter((provider) => !connectedAccounts.some((item) => item.platform === provider.platform))
          .map((provider) => ({
            platform: provider.platform,
            platform_label: provider.platform === "x" ? "X / Twitter" : provider.platform?.[0]?.toUpperCase() + provider.platform?.slice(1),
            account_name: provider.account_name || provider.handle || provider.platform,
            primary_metric: provider.connected ? "Connected and ready for live analytics" : "Not connected yet",
            status: provider.connected ? "connected" : "not_connected",
            avatar_url: provider.avatar_url,
          })),
      ]
    : providers.map((provider) => ({
        platform: provider.platform,
        platform_label: provider.platform === "x" ? "X / Twitter" : provider.platform?.[0]?.toUpperCase() + provider.platform?.slice(1),
        account_name: provider.account_name || provider.handle || provider.platform,
        primary_metric: provider.connected ? "Connected and ready for live analytics" : "Not connected yet",
        status: provider.connected ? "connected" : "not_connected",
        avatar_url: provider.avatar_url,
      }));

  const peakTrend = useMemo(() => {
    const trend = data?.engagement_trend || [];
    if (!trend.length) return null;
    return trend.reduce((best, current) => (current.value > best.value ? current : best), trend[0]);
  }, [data?.engagement_trend]);

  const audienceLeader = useMemo(() => {
    const comparison = data?.platform_comparison || [];
    if (!comparison.length) return null;
    return comparison.reduce((best, current) => ((current.reach || 0) > (best.reach || 0) ? current : best), comparison[0]);
  }, [data?.platform_comparison]);

  const dominantMood = data?.overview?.find((metric) => metric.label === "Overall Mood")?.value || "n/a";
  const interactionValue = data?.overview?.find((metric) => metric.label === "Interactions")?.value || "0";
  const connectedAccountsValue = data?.overview?.find((metric) => metric.label === "Connected Accounts")?.value || "0";
  const topEmotion = emotions[0]?.name || "n/a";
  const toxicityValue = data?.toxicity_summary?.label || "0%";
  const forecastDirection = data?.predictive_analysis?.trend_direction || "Stable";
  const predictedChange = data?.predictive_analysis?.predicted_change_pct ?? 0;

  const moduleCards = [
    {
      title: "Real-time analytics",
      value: interactionValue,
      detail: "Current interactions across indexed posts, videos, reels, and public conversations.",
      icon: Activity,
    },
    {
      title: "Multi-platform view",
      value: `${connectedAccountsValue}/3`,
      detail: "Instagram, YouTube, and X / Twitter are merged into one workspace.",
      icon: Users,
    },
    {
      title: "Sentiment and emotion",
      value: `${dominantMood}`,
      detail: `Primary detected emotion: ${topEmotion}.`,
      icon: MessageSquareText,
    },
    {
      title: "Toxicity detection",
      value: toxicityValue,
      detail: "Flagged moderation risk across the current indexed content sample.",
      icon: ShieldAlert,
    },
    {
      title: "Audience insights",
      value: audienceLeader?.platform || "n/a",
      detail: audienceLeader ? `${audienceLeader.platform} currently leads visible audience reach.` : "Connect a platform to compare audience reach.",
      icon: Users,
    },
    {
      title: "Predictive analysis",
      value: forecastDirection,
      detail: `Predicted engagement shift: ${predictedChange >= 0 ? "+" : ""}${predictedChange.toFixed(1)}%.`,
      icon: TrendingUp,
    },
    {
      title: "Recommendation system",
      value: `${data?.recommendations?.length || 0}`,
      detail: "Suggestions for timing, caption angles, hashtag mix, and trend response.",
      icon: Sparkles,
    },
    {
      title: "Explainable AI",
      value: `${explainabilityFactors.length}`,
      detail: "Transparent factors behind the platform, forecast, and risk outputs.",
      icon: BrainCircuit,
    },
    {
      title: "Trending hashtags",
      value: `${trendingHashtags.length}`,
      detail: "Recurring hashtag signals pulled from current high-performing content.",
      icon: Hash,
    },
    {
      title: "Crisis alerts",
      value: `${crisisAlerts.length}`,
      detail: crisisAlerts.length ? "Negative spikes or moderation issues currently need attention." : "No active crisis alert is dominating the workspace right now.",
      icon: TriangleAlert,
    },
    {
      title: "Chatbot assistant",
      value: `${data?.chatbot?.starter_questions?.length || 0}`,
      detail: "Interactive assistant for timing, audience, hashtag, and risk questions.",
      icon: Bot,
    },
    {
      title: "Automated reports",
      value: `${reports.length}`,
      detail: reports.length ? "Recent report snapshots are ready to open and share." : "Generate weekly or monthly reports from the reports workspace.",
      icon: FileText,
    },
  ];

  const sendMessage = async (message) => {
    const trimmed = (message || "").trim();
    if (!trimmed || chatbotMutation.isPending) return;
    setAssistantOpen(true);
    setChatInput("");
    await chatbotMutation.mutateAsync(trimmed);
  };

  return (
    <AppShell title={`Hello ${firstName}`} subtitle="Your connected social analytics workspace is ready with audience, trend, moderation, and recommendation insights.">
      <motion.section variants={stagger} initial="hidden" animate="show" className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
        {dashboardQuery.isLoading
          ? Array.from({ length: 4 }).map((_, index) => (
              <motion.div key={`stat-skeleton-${index}`} variants={fadeUp}>
                <DashboardStatSkeleton />
              </motion.div>
            ))
          : (data?.overview || []).map((metric) => (
              <motion.div key={metric.label} variants={fadeUp}>
                <StatCard {...metric} />
              </motion.div>
            ))}
      </motion.section>

      <section className="grid gap-4 xl:grid-cols-3">
        {dashboardQuery.isLoading
          ? Array.from({ length: 3 }).map((_, index) => <PanelSkeleton key={`rollup-skeleton-${index}`} />)
          : (data?.platform_rollups || []).map((rollup) => (
              <Panel key={rollup.platform} className="p-5">
                <p className="text-xs font-semibold uppercase tracking-[0.2em] text-slate-500">{rollup.title}</p>
                <h2 className="mt-3 font-display text-2xl font-bold text-white">{rollup.headline}</h2>
                <div className="mt-4 space-y-2.5">
                  {(rollup.metrics || []).map((metric) => (
                    <div key={`${rollup.platform}-${metric.label}`} className="flex items-center justify-between rounded-xl bg-white/[0.03] px-4 py-3 text-sm">
                      <span className="text-slate-400">{metric.label}</span>
                      <span className="font-mono font-semibold text-white">{metric.value}</span>
                    </div>
                  ))}
                </div>
              </Panel>
            ))}
      </section>

      <section>
        <div className="mb-4">
          <p className="text-xs font-semibold uppercase tracking-[0.2em] text-slate-500">Coverage</p>
          <h2 className="mt-2 font-display text-2xl font-bold text-white">Client-requested analytics modules</h2>
        </div>
        <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
          {dashboardQuery.isLoading
            ? Array.from({ length: 12 }).map((_, index) => <PanelSkeleton key={`module-skeleton-${index}`} rows={2} />)
            : moduleCards.map((card) => <ModuleCard key={card.title} {...card} />)}
        </div>
      </section>

      <section className="grid gap-6 xl:grid-cols-[1.15fr_0.85fr]">
        {dashboardQuery.isLoading ? (
          <>
            <PanelSkeleton chart />
            <PanelSkeleton chart />
          </>
        ) : (
          <>
            <Panel className="p-6">
              <div>
                <p className="text-xs font-semibold uppercase tracking-wider text-slate-500">Engagement trend</p>
                <h2 className="mt-2 font-display text-xl font-bold text-white">Weekly activity pattern</h2>
              </div>
              <div className="mt-6 h-72">
                <ResponsiveContainer width="100%" height="100%">
                  <AreaChart data={data?.engagement_trend || []}>
                    <defs>
                      <linearGradient id="engArea" x1="0" x2="0" y1="0" y2="1">
                        <stop offset="5%" stopColor="#00e5ff" stopOpacity={0.3} />
                        <stop offset="95%" stopColor="#00e5ff" stopOpacity={0} />
                      </linearGradient>
                    </defs>
                    <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.04)" />
                    <XAxis dataKey="day" stroke="#475569" tick={{ fontSize: 11 }} />
                    <Tooltip content={<CustomTooltip />} />
                    <Area type="monotone" dataKey="value" stroke="#00e5ff" strokeWidth={2} fill="url(#engArea)" />
                  </AreaChart>
                </ResponsiveContainer>
              </div>
              {peakTrend && <p className="mt-4 text-xs text-slate-400">{peakTrend.day} is the strongest engagement day in the current trend line.</p>}
            </Panel>

            <Panel className="p-6">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-xs font-semibold uppercase tracking-wider text-slate-500">Community mood</p>
                  <h2 className="mt-2 font-display text-xl font-bold text-white">Sentiment split</h2>
                </div>
                <Bot size={20} className="text-neon" />
              </div>
              <div className="mt-6 h-56">
                <ResponsiveContainer width="100%" height="100%">
                  <PieChart>
                    <Pie data={sentiment} dataKey="value" nameKey="name" innerRadius={65} outerRadius={90} strokeWidth={0}>
                      {sentiment.map((entry, index) => (
                        <Cell key={entry.name} fill={sentimentColors[index % sentimentColors.length]} />
                      ))}
                    </Pie>
                    <Tooltip content={<CustomTooltip />} />
                  </PieChart>
                </ResponsiveContainer>
              </div>
              <div className="mt-2 grid gap-2">
                {sentiment.map((entry, index) => (
                  <div key={entry.name} className="flex items-center justify-between rounded-xl bg-white/[0.03] px-4 py-2.5">
                    <div className="flex items-center gap-2.5">
                      <span className="h-2.5 w-2.5 rounded-full" style={{ backgroundColor: sentimentColors[index % sentimentColors.length] }} />
                      <span className="text-sm text-slate-300">{entry.name}</span>
                    </div>
                    <span className="font-mono text-sm font-semibold text-white">{entry.value}%</span>
                  </div>
                ))}
              </div>
            </Panel>
          </>
        )}
      </section>

      <section className="grid gap-6 xl:grid-cols-[1fr_1fr]">
        <Panel className="p-6">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-xs font-semibold uppercase tracking-wider text-slate-500">Audience insights</p>
              <h2 className="mt-2 font-display text-xl font-bold text-white">Who is responding and where</h2>
            </div>
            <Users size={20} className="text-neon" />
          </div>
          <div className="mt-5 grid gap-3 md:grid-cols-2">
            {dashboardQuery.isLoading
              ? Array.from({ length: 4 }).map((_, index) => <div key={`audience-skeleton-${index}`} className="h-28 animate-pulse rounded-2xl bg-white/[0.03]" />)
              : audienceInsightCards.map((item) => <InsightMetric key={item.label} {...item} />)}
          </div>
          {!!(data?.audience_insights?.notes || []).length && (
            <div className="mt-4 rounded-2xl bg-white/[0.03] p-4">
              <div className="space-y-2">
                {(data?.audience_insights?.notes || []).map((note) => (
                  <p key={note} className="text-xs leading-relaxed text-slate-400">{note}</p>
                ))}
              </div>
            </div>
          )}
        </Panel>

        <Panel className="p-6">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-xs font-semibold uppercase tracking-wider text-slate-500">Emotion and explainability</p>
              <h2 className="mt-2 font-display text-xl font-bold text-white">Why the dashboard is saying this</h2>
            </div>
            <BrainCircuit size={20} className="text-amber-400" />
          </div>
          <div className="mt-5 space-y-3">
            {!!emotions.length && (
              <div className="rounded-2xl bg-white/[0.03] p-4">
                <p className="text-[10px] font-semibold uppercase tracking-[0.18em] text-slate-500">Emotion distribution</p>
                <div className="mt-3 space-y-2.5">
                  {emotions.map((item) => {
                    const total = emotions.reduce((sum, row) => sum + (row.value || 0), 0) || 1;
                    const width = Math.max(8, Math.round(((item.value || 0) / total) * 100));
                    return (
                      <div key={item.name}>
                        <div className="flex items-center justify-between text-xs text-slate-300">
                          <span>{item.name}</span>
                          <span>{item.value}</span>
                        </div>
                        <div className="mt-1 h-2 overflow-hidden rounded-full bg-white/[0.05]">
                          <div className="h-full rounded-full bg-gradient-to-r from-neon to-cyan-300" style={{ width: `${width}%` }} />
                        </div>
                      </div>
                    );
                  })}
                </div>
              </div>
            )}

            <div className="rounded-2xl bg-white/[0.03] p-4">
              <p className="text-[10px] font-semibold uppercase tracking-[0.18em] text-slate-500">Explainable AI summary</p>
              <p className="mt-2 text-xs leading-relaxed text-slate-400">{data?.explainable_ai?.summary}</p>
            </div>

            {explainabilityFactors.map((factor) => (
              <div key={factor.label} className="rounded-2xl bg-white/[0.03] p-4">
                <div className="flex items-center justify-between gap-3">
                  <h3 className="text-sm font-semibold text-white">{factor.label}</h3>
                  <span className="rounded-full bg-white/[0.05] px-2.5 py-1 text-[10px] font-semibold text-slate-300">{factor.impact}</span>
                </div>
                <p className="mt-2 text-xs leading-relaxed text-slate-400">{factor.reason}</p>
              </div>
            ))}
          </div>
        </Panel>
      </section>

      <section className="grid items-start gap-6 lg:grid-cols-[0.85fr_1.15fr]">
        <Panel className="p-6">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-xs font-semibold uppercase tracking-wider text-slate-500">Connected sources</p>
              <h2 className="mt-2 font-display text-xl font-bold text-white">Accounts and hashtags</h2>
            </div>
          </div>
          <div className="mt-5 space-y-3">
            {providersQuery.isLoading &&
              Array.from({ length: 3 }).map((_, index) => <ProviderCardSkeleton key={`provider-loading-${index}`} />)}

            {!providersQuery.isLoading &&
              sourceCards.map((provider) => {
                const Icon = platformBrandIcons[provider.platform];
                const gradient = platformColors[provider.platform] || "from-slate-500 to-slate-600";
                const statusText = provider.status === "connected"
                  ? provider.secondary_metric || provider.primary_metric || "Connected. Open the explorer to view live data."
                  : "Not connected yet.";
                const avatarUrl = provider.avatar_url ? resolveAssetUrl(provider.avatar_url) : "";

                return (
                  <Link key={provider.platform} to={`/explore/${provider.platform}`} className="block rounded-xl bg-white/[0.03] p-4 transition hover:bg-white/[0.05]">
                    <div className="flex items-center gap-3">
                      <div className={`flex h-10 w-10 items-center justify-center overflow-hidden rounded-xl bg-gradient-to-br ${gradient}`}>
                        {avatarUrl ? (
                          <img src={avatarUrl} alt={provider.account_name} className="h-full w-full object-cover" />
                        ) : Icon ? (
                          <Icon size={18} className="text-white" />
                        ) : null}
                      </div>
                      <div className="min-w-0 flex-1">
                        <h3 className="truncate font-display text-base font-bold text-white">
                          {provider.account_name || provider.handle || provider.platform}
                        </h3>
                        <p className="text-xs text-slate-500">{statusText}</p>
                      </div>
                      <span className={`rounded-full px-2.5 py-1 text-[10px] font-medium ${
                        provider.status === "connected" ? "bg-emerald-500/10 text-emerald-400" : "bg-white/5 text-slate-500"
                      }`}>
                        {provider.status === "connected" ? "Active" : "Connect"}
                      </span>
                    </div>
                  </Link>
                );
              })}

            <Link to="/connect">
              <Button variant="secondary" className="mt-2 w-full text-xs">
                Manage connections
              </Button>
            </Link>
          </div>

          <div className="mt-6">
            <div className="flex items-center gap-2">
              <Hash size={16} className="text-neon" />
              <h3 className="font-display text-lg font-bold text-white">Trending hashtags</h3>
            </div>
            <div className="mt-4 flex flex-wrap gap-2">
              {trendingHashtags.length ? (
                trendingHashtags.map((item) => (
                  <div key={item.tag} className="rounded-xl bg-white/[0.03] px-3 py-2">
                    <p className="text-sm font-semibold text-white">{item.tag}</p>
                    <p className="text-[11px] text-slate-500">{item.count} mention(s)</p>
                  </div>
                ))
              ) : (
                <div className="rounded-xl bg-white/[0.03] p-4 text-sm text-slate-400">Trending hashtags will appear after recurring tags are detected in connected content.</div>
              )}
            </div>
          </div>
        </Panel>

        <div className="grid gap-6">
          <Panel className="p-6">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-xs font-semibold uppercase tracking-wider text-slate-500">Top content</p>
                <h2 className="mt-2 font-display text-xl font-bold text-white">What is working now</h2>
              </div>
              <Sparkles size={20} className="text-amber-400" />
            </div>
            <div className="mt-5 grid gap-3 md:grid-cols-2">
              {dashboardQuery.isLoading
                ? Array.from({ length: 4 }).map((_, index) => <div key={`top-content-skeleton-${index}`} className="aspect-video animate-pulse rounded-2xl bg-white/[0.03]" />)
                : (data?.top_content || []).length
                ? (data?.top_content || []).map((item) => <TopContentMediaCard key={item.id} item={item} />)
                : <div className="rounded-2xl bg-white/[0.03] p-4 text-sm text-slate-400">Top content will appear here once connected posts are indexed.</div>}
            </div>
          </Panel>

          <Panel className="p-6">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-xs font-semibold uppercase tracking-wider text-slate-500">Moderation and crisis</p>
                <h2 className="mt-2 font-display text-xl font-bold text-white">Toxicity and risk watchlist</h2>
              </div>
              <TriangleAlert size={20} className="text-rose-400" />
            </div>
            <div className="mt-5 space-y-3">
              {moderationQueue.length ? (
                moderationQueue.map((item) => (
                  <div key={item.id} className="rounded-xl bg-white/[0.03] p-4">
                    <div className="flex flex-wrap items-center justify-between gap-2">
                      <div>
                        <p className="text-[10px] font-semibold uppercase tracking-wider text-slate-500">{item.platform}</p>
                        <h3 className="mt-1 font-display text-base font-bold text-white">{item.title}</h3>
                      </div>
                      <span className={`rounded-lg px-2.5 py-1 text-[10px] font-medium ${
                        item.toxicity >= 40 ? "bg-rose-500/10 text-rose-400" : "bg-amber-500/10 text-amber-400"
                      }`}>
                        {item.toxicity}% toxicity
                      </span>
                    </div>
                    <p className="mt-2 text-xs text-slate-400">{item.snippet}</p>
                    <p className="mt-2 text-xs font-medium text-neon">{item.sentiment} sentiment | {item.emotion} emotion</p>
                  </div>
                ))
              ) : (
                <div className="rounded-xl bg-white/[0.03] p-4 text-sm text-slate-400">
                  No moderation item is currently above the review threshold.
                </div>
              )}
            </div>
          </Panel>
        </div>
      </section>

      <section className="grid gap-6 xl:grid-cols-2">
        <Panel className="p-6">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-xs font-semibold uppercase tracking-wider text-slate-500">Recommendations</p>
              <h2 className="mt-2 font-display text-xl font-bold text-white">AI guidance and crisis alerts</h2>
            </div>
            <Sparkles size={20} className="text-neon" />
          </div>
          <div className="mt-5 space-y-3">
            {(data?.recommendations || []).map((item) => (
              <div key={item.title} className="rounded-xl bg-white/[0.03] p-4">
                <h3 className="text-sm font-semibold text-white">{item.title}</h3>
                <p className="mt-2 text-xs leading-relaxed text-slate-400">{item.body}</p>
              </div>
            ))}
            {!!crisisAlerts.length && (
              <div className="rounded-2xl border border-rose-500/10 bg-rose-500/[0.03] p-4">
                <p className="text-[10px] font-semibold uppercase tracking-[0.18em] text-rose-300">Crisis alerts</p>
                <div className="mt-3 space-y-3">
                  {crisisAlerts.map((alert) => (
                    <div key={alert.title} className="rounded-xl bg-black/20 p-3">
                      <div className="flex items-center justify-between gap-2">
                        <h3 className="text-sm font-semibold text-white">{alert.title}</h3>
                        <span className={`rounded-full px-2.5 py-1 text-[10px] font-medium ${
                          alert.severity === "high" ? "bg-rose-500/10 text-rose-300" : "bg-amber-500/10 text-amber-300"
                        }`}>
                          {alert.severity}
                        </span>
                      </div>
                      <p className="mt-2 text-xs text-slate-400">{alert.explanation}</p>
                      <p className="mt-2 text-xs font-medium text-neon">{alert.recommended_action}</p>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
        </Panel>

        <Panel className="p-6">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-xs font-semibold uppercase tracking-wider text-slate-500">Reports</p>
              <h2 className="mt-2 font-display text-xl font-bold text-white">Automated reporting</h2>
            </div>
            <FileText size={20} className="text-amber-400" />
          </div>
          <div className="mt-5 space-y-3">
            {reportsQuery.isLoading &&
              Array.from({ length: 3 }).map((_, index) => <div key={`report-skeleton-${index}`} className="h-20 animate-pulse rounded-xl bg-white/[0.03]" />)}

            {!reportsQuery.isLoading &&
              reports.slice(0, 3).map((report) => (
                <div key={report.id} className="flex items-center justify-between gap-3 rounded-xl bg-white/[0.03] p-4">
                  <div className="min-w-0">
                    <p className="text-[10px] font-semibold uppercase tracking-wider text-slate-500">{report.period}</p>
                    <h3 className="truncate font-display text-sm font-bold text-white">{report.title}</h3>
                    <p className="mt-1 text-xs text-slate-400">{new Date(report.created_at).toLocaleString()}</p>
                  </div>
                  <Button className="shrink-0 text-xs" onClick={() => window.open(`${apiRoot}/api/reports/public/${report.public_token}`, "_blank")}>
                    Open
                  </Button>
                </div>
              ))}

            {!reportsQuery.isLoading && reports.length === 0 && (
              <div className="rounded-xl bg-white/[0.03] p-4 text-sm text-slate-400">
                No weekly or monthly report has been generated yet.
              </div>
            )}

            <Link to="/reports">
              <Button variant="secondary" className="mt-2 w-full text-xs">
                Open reports workspace
              </Button>
            </Link>
          </div>
        </Panel>
      </section>

      <section className="grid items-start gap-6 xl:grid-cols-[0.72fr_1.28fr]">
        <Panel className="p-5">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-xs font-semibold uppercase tracking-wider text-slate-500">Assistant status</p>
              <h2 className="mt-2 font-display text-xl font-bold text-white">Floating analytics assistant</h2>
            </div>
            <Bot size={20} className="text-neon" />
          </div>
          <p className="mt-3 text-sm leading-relaxed text-slate-400">
            The assistant now opens from the floating round icon in the bottom-right corner. It can answer connected analytics questions, pull public trend context, and surface playable media cards.
          </p>
          <div className="mt-4 flex flex-wrap gap-2">
            {(data?.chatbot?.starter_questions || []).slice(0, 4).map((question) => (
              <button
                key={question}
                onClick={() => sendMessage(question)}
                className="rounded-xl border border-white/[0.08] bg-white/[0.03] px-3 py-2 text-xs text-slate-300 transition hover:bg-white/[0.06] hover:text-white"
              >
                {question}
              </button>
            ))}
          </div>
        </Panel>

        <Panel className="p-6">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-xs font-semibold uppercase tracking-wider text-slate-500">Alert feed</p>
              <h2 className="mt-2 font-display text-xl font-bold text-white">Workspace notifications</h2>
            </div>
            <TriangleAlert size={20} className="text-rose-400" />
          </div>
          <div className="mt-5 space-y-3">
            {alertsQuery.isLoading &&
              Array.from({ length: 3 }).map((_, index) => <div key={`alert-skeleton-${index}`} className="h-24 animate-pulse rounded-xl bg-white/[0.03]" />)}

            {!alertsQuery.isLoading &&
              alerts.slice(0, 6).map((alert) => (
                <div key={alert.id} className="relative overflow-hidden rounded-xl bg-white/[0.03] p-4">
                  <div className="absolute bottom-0 left-0 top-0 w-[3px] bg-gradient-to-b from-rose-400 to-amber-400" />
                  <div className="pl-3">
                    <div className="flex flex-wrap items-center justify-between gap-2">
                      <div>
                        <p className="text-[10px] font-semibold uppercase tracking-wider text-slate-500">{alert.platform}</p>
                        <h3 className="mt-1 font-display text-base font-bold text-white">{alert.title}</h3>
                      </div>
                      <span className={`rounded-lg px-2.5 py-1 text-[10px] font-medium ${
                        alert.severity === "high" ? "bg-rose-500/10 text-rose-400" : alert.severity === "medium" ? "bg-amber-500/10 text-amber-400" : "bg-emerald-500/10 text-emerald-400"
                      }`}>
                        {alert.severity}
                      </span>
                    </div>
                    <p className="mt-2 text-xs text-slate-400">{alert.explanation}</p>
                    <p className="mt-2 text-xs font-medium text-neon">Action: {alert.recommended_action}</p>
                  </div>
                </div>
              ))}

            {!alertsQuery.isLoading && alerts.length === 0 && (
              <div className="rounded-xl bg-white/[0.03] p-4 text-sm text-slate-400">
                No active alerts are in the workspace right now.
              </div>
            )}
          </div>
        </Panel>
      </section>

      <DashboardAssistantWidget
        chatbotConfig={data?.chatbot}
        chatHistory={chatHistory}
        chatInput={chatInput}
        setChatInput={setChatInput}
        chatbotMutation={chatbotMutation}
        sendMessage={sendMessage}
        open={assistantOpen}
        setOpen={setAssistantOpen}
      />
    </AppShell>
  );
}
