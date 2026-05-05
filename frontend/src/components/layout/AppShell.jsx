import { useEffect, useRef, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Camera, Bell, ChevronLeft, ChevronRight, LayoutDashboard, Link2, LogOut, Menu, Moon, Radar, ShieldCheck, Sun, X, Zap } from "lucide-react";
import { useTheme } from "../../hooks/useTheme";
import { Link, NavLink } from "react-router-dom";
import { motion, AnimatePresence } from "framer-motion";

import { Button } from "../ui/Button";
import { InstagramBrandIcon, XBrandIcon, YouTubeBrandIcon } from "../ui/PlatformIcon";
import { useAuth } from "../../hooks/useAuth";
import { useToast } from "../../hooks/useToast";
import { resolveAssetUrl } from "../../lib/assetUrl";
import { apiClient } from "../../lib/apiClient";

const navItems = [
  { to: "/dashboard", label: "Dashboard", icon: LayoutDashboard },
  { to: "/connect", label: "Connections", icon: Link2 },
  { to: "/reports", label: "Reports", icon: Radar },
];

const exploreItems = [
  { to: "/explore/instagram", label: "Instagram", icon: InstagramBrandIcon },
  { to: "/explore/youtube", label: "YouTube", icon: YouTubeBrandIcon },
  { to: "/explore/x", label: "X / Twitter", icon: XBrandIcon },
];

const adminNavItems = [
  { to: "/admin", label: "Control Center", icon: ShieldCheck },
];

export function AppShell({ title, subtitle, children }) {
  const { backendUser, logout, updateProfile, uploadAvatar } = useAuth();
  const { theme, toggleTheme } = useTheme();
  const { showToast } = useToast();
  const queryClient = useQueryClient();
  const isAdmin = backendUser?.role === "admin";
  const shellNavItems = isAdmin ? adminNavItems : navItems;
  const shellExploreItems = isAdmin ? [] : exploreItems;
  const alertQueryKey = isAdmin ? ["admin-system-alerts"] : ["alerts"];
  const alertEndpoint = isAdmin ? "/alerts/admin/system" : "/alerts";
  const [collapsed, setCollapsed] = useState(false);
  const [mobileOpen, setMobileOpen] = useState(false);
  const [profileOpen, setProfileOpen] = useState(false);
  const [notificationsOpen, setNotificationsOpen] = useState(false);
  const [profileName, setProfileName] = useState("");
  const [savingProfile, setSavingProfile] = useState(false);
  const avatarInputRef = useRef(null);
  const notificationsRef = useRef(null);
  const notificationButtonRef = useRef(null);

  const sidebarWidth = collapsed ? "w-[72px]" : "w-[260px]";
  const initials = (backendUser?.display_name || "U")[0].toUpperCase();
  const alertsQuery = useQuery({
    queryKey: alertQueryKey,
    queryFn: async () => (await apiClient.get(alertEndpoint)).data,
    staleTime: 30_000,
  });
  const alerts = alertsQuery.data?.items || [];
  const unreadCount = alerts.filter((alert) => alert.status !== "acknowledged").length;
  const acknowledgeAlert = useMutation({
    mutationFn: async (alertId) => (await apiClient.post(`/alerts/${alertId}/ack`)).data,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: alertQueryKey });
    },
    onError: (error) => {
      showToast(error, "error");
    },
  });
  const acknowledgeAllAlerts = useMutation({
    mutationFn: async () => (await apiClient.post("/alerts/ack-all")).data,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: alertQueryKey });
    },
    onError: (error) => {
      showToast(error, "error");
    },
  });

  useEffect(() => {
    setProfileName(backendUser?.display_name || "");
  }, [backendUser?.display_name]);

  useEffect(() => {
    if (!notificationsOpen) {
      return undefined;
    }

    const handlePointerDown = (event) => {
      const target = event.target;
      if (notificationsRef.current?.contains(target) || notificationButtonRef.current?.contains(target)) {
        return;
      }
      setNotificationsOpen(false);
    };

    const handleEscape = (event) => {
      if (event.key === "Escape") {
        setNotificationsOpen(false);
      }
    };

    document.addEventListener("mousedown", handlePointerDown);
    document.addEventListener("keydown", handleEscape);
    return () => {
      document.removeEventListener("mousedown", handlePointerDown);
      document.removeEventListener("keydown", handleEscape);
    };
  }, [notificationsOpen]);

  const handleProfileSave = async () => {
    if (!profileName.trim()) {
      showToast("Display name cannot be empty.", "warning");
      return;
    }

    setSavingProfile(true);
    try {
      await updateProfile({ display_name: profileName });
      showToast("Profile updated successfully.", "success");
      setProfileOpen(false);
    } catch (error) {
      showToast(error, "error");
    } finally {
      setSavingProfile(false);
    }
  };

  const handleAvatarFile = async (file) => {
    if (!file) {
      return;
    }

    setSavingProfile(true);
    try {
      await uploadAvatar(file);
      showToast("Profile photo updated.", "success");
    } catch (error) {
      showToast(error, "error");
    } finally {
      setSavingProfile(false);
    }
  };

  const formatNotificationTime = (value) => {
    if (!value) {
      return "Just now";
    }
    const parsed = new Date(value);
    if (Number.isNaN(parsed.getTime())) {
      return "Just now";
    }
    return parsed.toLocaleString();
  };

  return (
    <div className="relative h-screen overflow-hidden bg-void">
      {/* Background mesh */}
      <div className="mesh-bg" aria-hidden="true" />

      <div className="relative z-10 flex h-screen overflow-hidden">
        {/* Mobile menu button */}
        <button
          onClick={() => setMobileOpen(true)}
          className="fixed top-4 left-4 z-50 flex h-10 w-10 items-center justify-center rounded-xl border border-white/10 bg-slate-900/80 text-white backdrop-blur-xl lg:hidden"
        >
          <Menu size={18} />
        </button>

        {/* Mobile overlay */}
        <AnimatePresence>
          {mobileOpen && (
            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              onClick={() => setMobileOpen(false)}
              className="fixed inset-0 z-40 bg-black/60 backdrop-blur-sm lg:hidden"
            />
          )}
        </AnimatePresence>

        {/* Sidebar */}
        <aside
          className={`fixed inset-y-0 left-0 z-50 flex h-screen flex-col border-r border-white/[0.04] ${isAdmin ? "bg-slate-950/95" : "bg-slate-950/90"} backdrop-blur-2xl transition-all duration-300 lg:relative lg:translate-x-0 ${sidebarWidth} ${mobileOpen ? "translate-x-0" : "-translate-x-full"}`}
        >
          {/* Close on mobile */}
          <button
            onClick={() => setMobileOpen(false)}
            className="absolute top-4 right-4 text-slate-400 lg:hidden"
          >
            <X size={18} />
          </button>

          {/* Logo */}
          <div className={`flex items-center gap-3 border-b border-white/[0.04] p-4 ${collapsed ? "justify-center" : ""}`}>
            <div className={`flex h-10 w-10 shrink-0 items-center justify-center rounded-xl border ${isAdmin ? "border-purple-400/20 bg-gradient-to-br from-purple-500/20 to-amber-400/20" : "border-neon/20 bg-gradient-to-br from-neon/20 to-purple-500/20"}`}>
              <Zap size={18} className={isAdmin ? "text-purple-300" : "text-neon"} />
            </div>
            {!collapsed && (
              <div className="overflow-hidden">
                <h1 className="font-display text-lg font-bold text-white">{isAdmin ? "Synapse Admin" : "Synapse"}</h1>
                <p className="text-[11px] text-slate-500">{isAdmin ? "Operations Console" : "AI Social Intelligence"}</p>
              </div>
            )}
          </div>

          {/* Nav */}
          <nav className="flex-1 space-y-1 overflow-y-auto p-3">
            {!collapsed && (
              <p className="mb-2 px-3 text-[10px] font-semibold uppercase tracking-[0.2em] text-slate-600">
                {isAdmin ? "Control" : "Menu"}
              </p>
            )}
            {shellNavItems.map(({ to, label, icon: Icon }) => (
              <NavLink
                key={to}
                to={to}
                onClick={() => setMobileOpen(false)}
                className={({ isActive }) =>
                  `group flex items-center gap-3 rounded-xl px-3 py-2.5 text-sm transition-all duration-200 ${
                    isActive
                      ? isAdmin
                        ? "bg-purple-500/10 text-purple-300"
                        : "bg-neon/10 text-neon"
                      : "text-slate-400 hover:bg-white/5 hover:text-white"
                  } ${collapsed ? "justify-center" : ""}`
                }
              >
                {({ isActive }) => (
                  <>
                    <div className="relative">
                      <Icon size={18} />
                      {isActive && (
                        <span className={`absolute -left-[18px] top-1/2 h-5 w-[3px] -translate-y-1/2 rounded-r-full ${isAdmin ? "bg-purple-400" : "bg-neon shadow-neon-sm"}`} />
                      )}
                    </div>
                    {!collapsed && <span>{label}</span>}
                  </>
                )}
              </NavLink>
            ))}

            {/* Explore Section */}
            {!isAdmin && !collapsed && (
              <p className="mb-2 mt-6 px-3 text-[10px] font-semibold uppercase tracking-[0.2em] text-slate-600">
                Explore
              </p>
            )}
            {!isAdmin && collapsed && <div className="my-4 h-px bg-white/[0.06]" />}
            {shellExploreItems.map(({ to, label, icon: Icon }) => (
              <NavLink
                key={to}
                to={to}
                onClick={() => setMobileOpen(false)}
                className={({ isActive }) =>
                  `group flex items-center gap-3 rounded-xl px-3 py-2.5 text-sm transition-all duration-200 ${
                    isActive
                      ? "bg-neon/10 text-neon"
                      : "text-slate-400 hover:bg-white/5 hover:text-white"
                  } ${collapsed ? "justify-center" : ""}`
                }
              >
                <Icon size={18} />
                {!collapsed && <span>{label}</span>}
              </NavLink>
            ))}
          </nav>

          <div className="border-t border-white/[0.04] p-3">
            <button
              onClick={logout}
              className={`flex w-full items-center gap-2 rounded-xl border border-white/[0.06] bg-white/[0.03] py-2.5 text-xs text-slate-400 transition hover:bg-white/5 hover:text-rose-400 ${collapsed ? "justify-center px-0" : "justify-center px-3"}`}
              title="Sign out"
            >
              <LogOut size={14} />
              {!collapsed && <span>Sign out</span>}
            </button>
            <button
              onClick={() => setCollapsed(!collapsed)}
              className="mt-3 hidden w-full items-center justify-center rounded-xl border border-white/[0.06] bg-white/[0.03] px-3 py-2.5 text-xs text-slate-500 transition hover:bg-white/5 hover:text-white lg:flex"
              title="Toggle sidebar"
              aria-label="Toggle sidebar"
            >
              {collapsed ? <ChevronRight size={14} /> : <ChevronLeft size={14} />}
            </button>
          </div>
        </aside>

        {/* Main */}
        <main className="flex h-screen min-w-0 flex-1 flex-col overflow-hidden">
          {/* Top bar */}
          <header className="sticky top-0 z-30 flex items-center justify-between border-b border-white/[0.04] bg-void/80 px-6 py-4 backdrop-blur-2xl lg:px-8">
            <div className="min-w-0 pl-12 lg:pl-0">
              <h1 className="truncate font-display text-xl font-bold text-white lg:text-2xl">
                {title}
              </h1>
              {subtitle && (
                <p className="mt-1 hidden max-w-2xl text-sm text-slate-500 lg:block">{subtitle}</p>
              )}
            </div>
            <div className="flex items-center gap-3">
              <button
                onClick={() => setProfileOpen(true)}
                className="hidden items-center gap-2 rounded-xl border border-white/[0.06] bg-white/[0.03] px-3 py-1.5 text-left text-slate-300 transition hover:bg-white/[0.06] md:flex"
              >
                <div className="flex h-8 w-8 shrink-0 items-center justify-center overflow-hidden rounded-lg bg-gradient-to-br from-neon/20 to-purple-500/20 text-[11px] font-bold text-neon">
                  {backendUser?.avatar_url ? (
                    <img
                      src={resolveAssetUrl(backendUser.avatar_url)}
                      alt={backendUser?.display_name || "User avatar"}
                      className="h-full w-full object-cover"
                    />
                  ) : (
                    initials
                  )}
                </div>
                <div className="min-w-0">
                  <p className="max-w-[140px] truncate text-xs font-semibold text-white">{backendUser?.display_name || "User"}</p>
                  <p className="text-[10px] text-slate-500">{isAdmin ? "System admin" : "Edit profile"}</p>
                </div>
              </button>
              <button
                onClick={toggleTheme}
                className="flex h-9 w-9 items-center justify-center rounded-xl border border-white/[0.06] bg-white/[0.03] text-slate-400 transition hover:text-white cursor-pointer"
                title={theme === 'dark' ? 'Switch to light mode' : 'Switch to dark mode'}
              >
                {theme === 'dark' ? <Sun size={16} /> : <Moon size={16} />}
              </button>
              <div className="relative" ref={notificationsRef}>
                <button
                  ref={notificationButtonRef}
                  onClick={() => setNotificationsOpen((current) => !current)}
                  className="relative flex h-9 w-9 items-center justify-center rounded-xl border border-white/[0.06] bg-white/[0.03] text-slate-400 transition hover:text-white"
                  title="Notifications"
                  aria-label="Notifications"
                >
                  <Bell size={16} />
                  {unreadCount > 0 && (
                    <span className="absolute -top-1.5 -right-1.5 min-w-[18px] rounded-full bg-neon px-1.5 py-[1px] text-[10px] font-bold text-slate-950 shadow-neon-sm">
                      {unreadCount > 9 ? "9+" : unreadCount}
                    </span>
                  )}
                </button>

                <AnimatePresence>
                  {notificationsOpen && (
                    <motion.div
                      initial={{ opacity: 0, y: 12, scale: 0.98 }}
                      animate={{ opacity: 1, y: 0, scale: 1 }}
                      exit={{ opacity: 0, y: 12, scale: 0.98 }}
                      className="absolute right-0 top-12 z-[60] w-[min(24rem,calc(100vw-2rem))] overflow-hidden rounded-3xl border border-white/[0.08] bg-slate-950/95 shadow-2xl backdrop-blur-2xl"
                    >
                      <div className="border-b border-white/[0.06] px-4 py-3">
                        <div className="flex items-center justify-between gap-3">
                          <div>
                            <p className="text-xs font-semibold uppercase tracking-[0.18em] text-slate-500">Notifications</p>
                            <h3 className="mt-1 font-display text-base font-bold text-white">{isAdmin ? "System alerts" : "Latest alerts"}</h3>
                          </div>
                          <div className="flex items-center gap-2">
                            <span className="rounded-full bg-white/[0.05] px-2.5 py-1 text-[10px] font-semibold text-slate-400">
                              {unreadCount > 0 ? `${unreadCount} unread` : "All caught up"}
                            </span>
                            {unreadCount > 0 && (
                              <button
                                onClick={() => acknowledgeAllAlerts.mutate()}
                                disabled={acknowledgeAllAlerts.isPending}
                                className="rounded-full border border-white/[0.08] bg-white/[0.03] px-2.5 py-1 text-[10px] font-semibold text-slate-300 transition hover:bg-white/[0.06] hover:text-white disabled:cursor-not-allowed disabled:opacity-60"
                              >
                                Mark all read
                              </button>
                            )}
                          </div>
                        </div>
                      </div>

                      <div className="max-h-[26rem] overflow-y-auto p-3">
                        {alertsQuery.isLoading && (
                          <div className="space-y-3">
                            {Array.from({ length: 3 }).map((_, index) => (
                              <div key={`notification-skeleton-${index}`} className="h-24 animate-pulse rounded-2xl bg-white/[0.04]" />
                            ))}
                          </div>
                        )}

                        {!alertsQuery.isLoading && alerts.length === 0 && (
                          <div className="rounded-2xl bg-white/[0.03] p-4 text-sm text-slate-400">
                            No notifications yet.
                          </div>
                        )}

                        {!alertsQuery.isLoading && alerts.length > 0 && (
                          <div className="space-y-3">
                            {alerts.slice(0, 6).map((alert) => {
                              const severityStyles = {
                                high: "bg-rose-500/10 text-rose-400",
                                medium: "bg-amber-500/10 text-amber-300",
                                low: "bg-emerald-500/10 text-emerald-300",
                              };
                              return (
                                <div key={alert.id} className="rounded-2xl border border-white/[0.05] bg-white/[0.03] p-4">
                                  <div className="flex flex-wrap items-start justify-between gap-2">
                                    <div className="min-w-0">
                                      <p className="text-[10px] font-semibold uppercase tracking-[0.18em] text-slate-500">
                                        {alert.platform}
                                      </p>
                                      <h4 className="mt-1 text-sm font-semibold text-white">{alert.title}</h4>
                                    </div>
                                    <span className={`rounded-full px-2.5 py-1 text-[10px] font-semibold ${severityStyles[alert.severity] || "bg-white/[0.06] text-slate-300"}`}>
                                      {alert.severity}
                                    </span>
                                  </div>
                                  <p className="mt-2 text-xs leading-relaxed text-slate-400">{alert.explanation}</p>
                                  <p className="mt-2 text-xs font-medium text-neon">{alert.recommended_action}</p>
                                  <div className="mt-3 flex items-center justify-between gap-3">
                                    <span className="text-[11px] text-slate-500">{formatNotificationTime(alert.timestamp)}</span>
                                    {alert.status !== "acknowledged" && (
                                      <button
                                        onClick={() => acknowledgeAlert.mutate(alert.id)}
                                        disabled={acknowledgeAlert.isPending}
                                        className="rounded-full border border-white/[0.08] bg-white/[0.03] px-3 py-1.5 text-[11px] font-semibold text-slate-300 transition hover:bg-white/[0.06] hover:text-white disabled:cursor-not-allowed disabled:opacity-60"
                                      >
                                        Mark read
                                      </button>
                                    )}
                                  </div>
                                </div>
                              );
                            })}
                          </div>
                        )}
                      </div>
                    </motion.div>
                  )}
                </AnimatePresence>
              </div>
            </div>
          </header>

          {/* Page content */}
          <div className="flex-1 overflow-y-auto">
            <div className="space-y-6 p-6 lg:p-8">{children}</div>
          </div>
        </main>
      </div>

      <AnimatePresence>
        {profileOpen && (
          <>
            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              onClick={() => setProfileOpen(false)}
              className="fixed inset-0 z-[70] bg-black/70 backdrop-blur-sm"
            />
            <div className="fixed inset-0 z-[80] flex items-center justify-center p-4 md:p-6">
              <motion.div
                initial={{ opacity: 0, y: 24, scale: 0.98 }}
                animate={{ opacity: 1, y: 0, scale: 1 }}
                exit={{ opacity: 0, y: 24, scale: 0.98 }}
                className="w-full max-w-md rounded-3xl border border-white/[0.08] bg-slate-950/95 p-6 shadow-2xl backdrop-blur-2xl"
              >
                <div className="flex items-start justify-between gap-4">
                  <div>
                    <h2 className="font-display text-xl font-bold text-white">Edit profile</h2>
                    <p className="mt-1 text-sm text-slate-400">Update your visible name and profile photo.</p>
                  </div>
                  <button onClick={() => setProfileOpen(false)} className="text-slate-500 transition hover:text-white">
                    <X size={18} />
                  </button>
                </div>

                <div className="mt-6 flex items-center gap-4">
                  <div className="flex h-20 w-20 shrink-0 items-center justify-center overflow-hidden rounded-3xl bg-gradient-to-br from-neon/20 to-purple-500/20 text-lg font-bold text-neon">
                    {backendUser?.avatar_url ? (
                      <img
                        src={resolveAssetUrl(backendUser.avatar_url)}
                        alt={backendUser?.display_name || "User avatar"}
                        className="h-full w-full object-cover"
                      />
                    ) : (
                      initials
                    )}
                  </div>
                  <div className="min-w-0 flex-1">
                    <input
                      ref={avatarInputRef}
                      type="file"
                      accept="image/*"
                      className="hidden"
                      onChange={(event) => handleAvatarFile(event.target.files?.[0])}
                    />
                    <Button variant="secondary" className="w-full justify-center text-xs" onClick={() => avatarInputRef.current?.click()}>
                      <Camera size={14} />
                      Change photo
                    </Button>
                    <p className="mt-2 text-xs text-slate-500">Local upload is used for custom profile photos.</p>
                  </div>
                </div>

                <div className="mt-5">
                  <label className="mb-2 block text-xs font-medium uppercase tracking-[0.18em] text-slate-500">Display name</label>
                  <input
                    value={profileName}
                    onChange={(event) => setProfileName(event.target.value)}
                    className="w-full rounded-2xl border border-white/[0.08] bg-white/[0.03] px-4 py-3 text-sm text-white outline-none transition placeholder:text-slate-500 focus:border-neon/40"
                    placeholder="Your name"
                  />
                </div>

                <div className="mt-6 flex gap-3">
                  <Button variant="secondary" className="flex-1" onClick={() => setProfileOpen(false)}>
                    Cancel
                  </Button>
                  <Button className="flex-1" onClick={handleProfileSave} disabled={savingProfile}>
                    Save changes
                  </Button>
                </div>
              </motion.div>
            </div>
          </>
        )}
      </AnimatePresence>
    </div>
  );
}
