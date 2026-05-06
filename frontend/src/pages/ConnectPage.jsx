import { useMemo, useState } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { CheckCircle2, Link2, Loader2, Trash2 } from "lucide-react";
import { useSearchParams } from "react-router-dom";
import { motion } from "framer-motion";

import { AppShell } from "../components/layout/AppShell";
import { platformBrandIcons } from "../components/ui/PlatformIcon";
import { Button } from "../components/ui/Button";
import { GlowCard } from "../components/ui/GlowCard";
import { useToast } from "../hooks/useToast";
import { apiClient } from "../lib/apiClient";

const stagger = { hidden: { opacity: 0 }, show: { opacity: 1, transition: { staggerChildren: 0.1 } } };
const fadeUp = { hidden: { opacity: 0, y: 16 }, show: { opacity: 1, y: 0, transition: { duration: 0.4 } } };

const platformConfig = {
  instagram: { icon: platformBrandIcons.instagram, accent: "from-pink-500 to-purple-500", glow: "rgba(225,48,108,0.12)", label: "Instagram" },
  youtube: { icon: platformBrandIcons.youtube, accent: "from-red-500 to-orange-500", glow: "rgba(255,0,0,0.12)", label: "YouTube" },
  x: { icon: platformBrandIcons.x, accent: "from-slate-200 to-slate-500", glow: "rgba(255,255,255,0.1)", label: "X / Twitter" },
};

function ProviderSkeleton() {
  return (
    <GlowCard className="flex h-full min-h-[360px] flex-col p-5">
      <div className="h-12 w-12 animate-pulse rounded-2xl bg-white/10" />
      <div className="mt-3 h-5 w-32 animate-pulse rounded-full bg-white/10" />
      <div className="mt-3 h-4 w-full animate-pulse rounded-full bg-white/10" />
      <div className="mt-2 h-4 w-4/5 animate-pulse rounded-full bg-white/10" />
      <div className="mt-3 h-20 animate-pulse rounded-2xl bg-white/10" />
      <div className="mt-auto pt-4">
        <div className="h-11 animate-pulse rounded-xl bg-white/10" />
      </div>
    </GlowCard>
  );
}

export function ConnectPage() {
  const { showToast } = useToast();
  const queryClient = useQueryClient();
  const [searchParams] = useSearchParams();
  const [loadingPlatform, setLoadingPlatform] = useState("");
  const [disconnectingPlatform, setDisconnectingPlatform] = useState("");
  const [xHandle, setXHandle] = useState("");
  const providersQuery = useQuery({
    queryKey: ["providers"],
    queryFn: async () => (await apiClient.get("/providers")).data,
  });
  const { data } = providersQuery;
  const successPlatform = useMemo(() => searchParams.get("platform"), [searchParams]);
  const successLabel = useMemo(() => platformConfig[successPlatform]?.label || successPlatform, [successPlatform]);

  const connectedPlatforms = useMemo(() => {
    const map = {};
    (data?.items || []).forEach((provider) => {
      map[provider.platform] = provider;
    });
    return map;
  }, [data]);

  const startOAuth = async (platform) => {
    setLoadingPlatform(platform);
    try {
      const response = await apiClient.get(`/providers/${platform}/start`);
      window.location.href = response.data.url;
    } catch (error) {
      showToast(error, "error");
      setLoadingPlatform("");
    }
  };

  const connectXHandle = async () => {
    const handle = xHandle.trim();
    if (!handle) {
      showToast("Enter an X handle first.", "error");
      return;
    }
    setLoadingPlatform("x-handle");
    try {
      const response = await apiClient.post("/providers/x/connect", { handle }, { timeout: 25000 });
      await queryClient.invalidateQueries({ queryKey: ["providers"] });
      await queryClient.invalidateQueries({ queryKey: ["dashboard"] });
      await queryClient.invalidateQueries({ queryKey: ["alerts"] });
      showToast(response.data?.message || "X / Twitter connected successfully.", "success");
      setXHandle("");
    } catch (error) {
      if (error?.code === "ECONNABORTED") {
        showToast("X handle request took too long. The backend X session may be stale. Restart the backend and try again.", "error");
      } else {
        showToast(error, "error");
      }
    } finally {
      setLoadingPlatform("");
    }
  };

  const disconnectPlatform = async (platform) => {
    setDisconnectingPlatform(platform);
    try {
      const response = await apiClient.delete(`/providers/${platform}`);
      await queryClient.invalidateQueries({ queryKey: ["providers"] });
      await queryClient.invalidateQueries({ queryKey: ["dashboard"] });
      await queryClient.invalidateQueries({ queryKey: ["alerts"] });
      await queryClient.invalidateQueries({ queryKey: ["public-platform"] });
      showToast(response.data?.message || "Disconnected successfully.", "success");
    } catch (error) {
      showToast(error, "error");
    } finally {
      setDisconnectingPlatform("");
    }
  };

  const platforms = [
    {
      key: "instagram",
      name: "Instagram",
      desc: "Connect a professional Instagram account to load posts, reels, comments, and business insights.",
      action: () => startOAuth("instagram"),
      actionLabel: "Connect Instagram",
      helper: "Only Instagram Business or Creator accounts are supported here.",
    },
    {
      key: "youtube",
      name: "YouTube",
      desc: "Connect YouTube to track channel performance, views, subscriber growth, and analytics.",
      action: () => startOAuth("youtube"),
      actionLabel: "Connect YouTube",
    },
    {
      key: "x",
      name: "X / Twitter",
      desc: "Connect a public X / Twitter handle to load profile data, recent posts, search insights, and trends.",
      action: null,
      actionLabel: "Connect X / Twitter",
      helper: "Enter a public X handle to connect public profile and timeline analytics.",
    },
  ];

  return (
      <AppShell title="Connect your accounts" subtitle="Link your social accounts to unlock live analytics, audience insights, and personalized recommendations.">
      {successPlatform && (
        <motion.div initial={{ opacity: 0, y: -10 }} animate={{ opacity: 1, y: 0 }} className="flex items-center gap-3 rounded-xl border border-emerald-500/20 bg-emerald-500/10 p-4 text-sm text-emerald-300">
          <CheckCircle2 size={18} /> {successLabel} connected successfully.
        </motion.div>
      )}

      <motion.section variants={stagger} initial="hidden" animate="show" className="grid gap-5 xl:auto-rows-fr xl:grid-cols-3">
        {providersQuery.isLoading &&
          Array.from({ length: 3 }).map((_, index) => (
            <motion.div key={`provider-skeleton-${index}`} variants={fadeUp}>
              <ProviderSkeleton />
            </motion.div>
          ))}

        {!providersQuery.isLoading &&
          platforms.map((platform) => {
            const config = platformConfig[platform.key];
            const Icon = config.icon;
            const connection = connectedPlatforms[platform.key];
            const isConnected = connection?.connected;
            const isLoading = loadingPlatform === platform.key;
            const isXHandleLoading = loadingPlatform === "x-handle";
            const statusLabel = "Connected";

            return (
              <motion.div key={platform.key} variants={fadeUp}>
                <GlowCard glowColor={config.glow} className="flex h-full min-h-[360px] flex-col p-5">
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-3">
                      <div className={`flex h-12 w-12 items-center justify-center rounded-2xl bg-gradient-to-br ${config.accent}`}>
                        <Icon size={22} className="text-white" />
                      </div>
                      <div>
                        <h3 className="font-display text-lg font-bold text-white">{platform.name}</h3>
                      </div>
                    </div>
                    {isConnected && (
                      <span className="shrink-0 rounded-full bg-emerald-500/10 px-3 py-1 text-xs font-medium text-emerald-400">
                        {statusLabel}
                      </span>
                    )}
                  </div>

                  <div className="mt-4 flex flex-1 flex-col">
                    <div>
                      <p className="text-sm leading-6 text-slate-400">{platform.desc}</p>
                      {platform.helper && <p className="mt-2 text-xs leading-5 text-slate-500">{platform.helper}</p>}
                    </div>

                    {platform.key === "x" && !isConnected && (
                      <div className="mt-auto pt-4">
                        <div className="rounded-xl border border-white/10 bg-black/20 p-3">
                          <input
                            value={xHandle}
                            onChange={(event) => setXHandle(event.target.value)}
                            placeholder="@username"
                            className="w-full rounded-xl border border-white/10 bg-white/[0.04] px-3 py-2 text-sm text-white outline-none transition placeholder:text-slate-500 focus:border-cyan-400/50"
                          />
                          <Button className="mt-3 w-full gap-2" variant="secondary" onClick={connectXHandle} disabled={isXHandleLoading}>
                            {isXHandleLoading ? <Loader2 size={16} className="animate-spin" /> : <Link2 size={16} />}
                            {isXHandleLoading ? "Connecting handle..." : "Connect X handle"}
                          </Button>
                        </div>
                      </div>
                    )}

                    {isConnected && (
                      <div className="mt-auto pt-4">
                        <div className="rounded-xl bg-white/[0.03] p-3.5">
                          <div className="flex items-center gap-3">
                            <div className="min-w-0">
                              <p className="text-xs text-slate-500">Connected as</p>
                              <p className="mt-1 truncate font-display text-base font-bold text-white">{connection.account_name || connection.handle || "Connected"}</p>
                            </div>
                          </div>
                        </div>
                        <Button
                          className="mt-3 w-full gap-2"
                          variant="secondary"
                          onClick={() => disconnectPlatform(platform.key)}
                          disabled={disconnectingPlatform === platform.key}
                          style={{ borderColor: "rgba(239,68,68,0.3)", color: "#f87171" }}
                        >
                          {disconnectingPlatform === platform.key ? <Loader2 size={16} className="animate-spin" /> : <Trash2 size={16} />}
                          {disconnectingPlatform === platform.key ? "Removing..." : "Remove connection"}
                        </Button>
                      </div>
                    )}

                    {platform.key !== "x" && !isConnected && (
                      <div className="mt-auto pt-4">
                        <Button className="w-full gap-2" variant="primary" onClick={platform.action} disabled={isLoading}>
                          {isLoading ? <Loader2 size={16} className="animate-spin" /> : <Link2 size={16} />}
                          {isLoading ? "Connecting..." : platform.actionLabel}
                        </Button>
                      </div>
                    )}
                  </div>
                </GlowCard>
              </motion.div>
            );
          })}
      </motion.section>
    </AppShell>
  );
}
