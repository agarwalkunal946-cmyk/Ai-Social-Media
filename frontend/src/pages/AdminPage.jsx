import { useEffect, useMemo, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { BarChart3, BellRing, FileText, Link2, Pencil, Search, Trash2, UserCheck, UserX, Users } from "lucide-react";
import { motion } from "framer-motion";

import { AppShell } from "../components/layout/AppShell";
import { Button } from "../components/ui/Button";
import { ConfirmModal } from "../components/ui/ConfirmModal";
import { Panel } from "../components/ui/Panel";
import { StatCard } from "../components/ui/StatCard";
import { TopContentMediaCard } from "../components/ui/TopContentMediaCard";
import { useToast } from "../hooks/useToast";
import { apiClient } from "../lib/apiClient";

const USERS_PER_PAGE = 8;

const stagger = { hidden: { opacity: 0 }, show: { opacity: 1, transition: { staggerChildren: 0.08 } } };
const fadeUp = { hidden: { opacity: 0, y: 16 }, show: { opacity: 1, y: 0, transition: { duration: 0.4 } } };

const healthColors = {
  healthy: "bg-emerald-500/10 text-emerald-400",
  warning: "bg-amber-500/10 text-amber-300",
  error: "bg-rose-500/10 text-rose-400",
};

const healthLabels = {
  healthy: "Connected",
  warning: "Needs check",
  error: "Error",
};

const severityStyles = {
  high: "bg-rose-500/10 text-rose-400",
  medium: "bg-amber-500/10 text-amber-300",
  low: "bg-emerald-500/10 text-emerald-300",
};

const userStatusStyles = {
  active: "bg-emerald-500/10 text-emerald-300",
  inactive: "bg-rose-500/10 text-rose-300",
};

const adminSelectClassName =
  "w-full appearance-none rounded-2xl border border-white/[0.08] bg-white/[0.03] px-4 py-3 text-sm text-white outline-none [color-scheme:dark]";

function formatDate(value) {
  if (!value) return "n/a";
  const parsed = new Date(value);
  if (Number.isNaN(parsed.getTime())) return "n/a";
  return parsed.toLocaleString();
}

function UserSkeleton() {
  return (
    <div className="space-y-3">
      {Array.from({ length: 5 }).map((_, index) => (
        <div key={`user-skeleton-${index}`} className="h-14 animate-pulse rounded-2xl bg-white/[0.04]" />
      ))}
    </div>
  );
}

export function AdminPage() {
  const queryClient = useQueryClient();
  const { showToast } = useToast();
  const [searchTerm, setSearchTerm] = useState("");
  const [sortKey, setSortKey] = useState("updated_at");
  const [sortDirection, setSortDirection] = useState("desc");
  const [currentPage, setCurrentPage] = useState(1);
  const [selectedUserId, setSelectedUserId] = useState("");
  const [editingUser, setEditingUser] = useState(null);
  const [confirmDialog, setConfirmDialog] = useState(null);
  const [alertForm, setAlertForm] = useState({
    platform: "system",
    severity: "medium",
    title: "",
    explanation: "",
    recommended_action: "",
  });

  const overviewQuery = useQuery({ queryKey: ["admin-overview"], queryFn: async () => (await apiClient.get("/admin/overview")).data });
  const usersQuery = useQuery({ queryKey: ["admin-users"], queryFn: async () => (await apiClient.get("/admin/users")).data });
  const connectionsQuery = useQuery({ queryKey: ["admin-connections"], queryFn: async () => (await apiClient.get("/admin/connections")).data });
  const reportsQuery = useQuery({ queryKey: ["admin-reports"], queryFn: async () => (await apiClient.get("/admin/reports")).data });
  const systemAlertsQuery = useQuery({ queryKey: ["admin-system-alerts"], queryFn: async () => (await apiClient.get("/alerts/admin/system")).data });
  const closeConfirmDialog = () => setConfirmDialog(null);

  const setCachedItems = (queryKey, updater) => {
    queryClient.setQueryData(queryKey, (current) => {
      if (!current) return current;
      return { ...current, items: updater([...(current.items || [])]) };
    });
  };

  const setCachedAnalysis = (userId, updater) => {
    queryClient.setQueryData(["admin-user-analysis", userId], (current) => (current ? updater(current) : current));
  };

  const users = usersQuery.data?.items || [];

  useEffect(() => {
    if (!users.length) {
      setSelectedUserId("");
      return;
    }
    if (!selectedUserId || !users.some((item) => item.id === selectedUserId)) {
      setSelectedUserId(users[0].id);
    }
  }, [users, selectedUserId]);

  const userAnalysisQuery = useQuery({
    queryKey: ["admin-user-analysis", selectedUserId],
    enabled: Boolean(selectedUserId),
    queryFn: async () => (await apiClient.get(`/admin/users/${selectedUserId}/analysis`)).data,
  });

  const createSystemAlert = useMutation({
    mutationFn: async (payload) => (await apiClient.post("/alerts/admin/system", payload)).data,
    onSuccess: (response) => {
      showToast(response.message || "System alert created.", "success");
      setAlertForm({
        platform: "system",
        severity: "medium",
        title: "",
        explanation: "",
        recommended_action: "",
      });
      queryClient.invalidateQueries({ queryKey: ["admin-system-alerts"] });
      queryClient.invalidateQueries({ queryKey: ["admin-overview"] });
    },
    onError: (error) => showToast(error, "error"),
  });

  const updateUser = useMutation({
    mutationFn: async ({ userId, payload }) => (await apiClient.patch(`/admin/users/${userId}`, payload)).data,
    onMutate: async ({ userId, payload }) => {
      await Promise.all([
        queryClient.cancelQueries({ queryKey: ["admin-users"] }),
        queryClient.cancelQueries({ queryKey: ["admin-user-analysis", userId] }),
      ]);

      const previousUsers = queryClient.getQueryData(["admin-users"]);
      const previousAnalysis = queryClient.getQueryData(["admin-user-analysis", userId]);

      setCachedItems(["admin-users"], (items) =>
        items.map((item) => (
          item.id === userId
            ? {
                ...item,
                ...(payload.display_name ? { display_name: payload.display_name } : {}),
                ...(payload.mode ? { mode: payload.mode } : {}),
                ...(payload.status ? { status: payload.status } : {}),
                updated_at: new Date().toISOString(),
              }
            : item
        ))
      );

      setCachedAnalysis(userId, (current) => ({
        ...current,
        user: {
          ...current.user,
          ...(payload.display_name ? { display_name: payload.display_name } : {}),
          ...(payload.mode ? { mode: payload.mode } : {}),
          ...(payload.status ? { status: payload.status } : {}),
        },
      }));

      return { previousUsers, previousAnalysis, userId };
    },
    onSuccess: (response) => {
      showToast(response.message || "User updated.", "success");
      setEditingUser(null);
    },
    onError: (error, _variables, context) => {
      if (context?.previousUsers) {
        queryClient.setQueryData(["admin-users"], context.previousUsers);
      }
      if (context?.previousAnalysis) {
        queryClient.setQueryData(["admin-user-analysis", context.userId], context.previousAnalysis);
      }
      showToast(error, "error");
    },
    onSettled: async (_response, _error, variables) => {
      await Promise.all([
        queryClient.invalidateQueries({ queryKey: ["admin-users"] }),
        queryClient.invalidateQueries({ queryKey: ["admin-overview"] }),
        queryClient.invalidateQueries({ queryKey: ["admin-connections"] }),
        queryClient.invalidateQueries({ queryKey: ["admin-user-analysis", variables.userId] }),
      ]);
    },
  });

  const deleteUser = useMutation({
    mutationFn: async (userId) => (await apiClient.delete(`/admin/users/${userId}`)).data,
    onMutate: async (userId) => {
      await Promise.all([
        queryClient.cancelQueries({ queryKey: ["admin-users"] }),
        queryClient.cancelQueries({ queryKey: ["admin-overview"] }),
        queryClient.cancelQueries({ queryKey: ["admin-connections"] }),
        queryClient.cancelQueries({ queryKey: ["admin-reports"] }),
        queryClient.cancelQueries({ queryKey: ["admin-user-analysis", userId] }),
      ]);

      const previousUsers = queryClient.getQueryData(["admin-users"]);
      const previousConnections = queryClient.getQueryData(["admin-connections"]);
      const previousReports = queryClient.getQueryData(["admin-reports"]);
      const previousAnalysis = queryClient.getQueryData(["admin-user-analysis", userId]);
      const previousSelectedUserId = selectedUserId;
      const remainingUsers = (previousUsers?.items || []).filter((item) => item.id !== userId);

      setConfirmDialog(null);
      setCachedItems(["admin-users"], (items) => items.filter((item) => item.id !== userId));
      setCachedItems(["admin-connections"], (items) => items.filter((item) => item.user_id !== userId));
      setCachedItems(["admin-reports"], (items) => items.filter((item) => item.user_id !== userId));
      queryClient.removeQueries({ queryKey: ["admin-user-analysis", userId], exact: true });

      if (selectedUserId === userId) {
        setSelectedUserId(remainingUsers[0]?.id || "");
      }

      return {
        previousUsers,
        previousConnections,
        previousReports,
        previousAnalysis,
        previousSelectedUserId,
        userId,
      };
    },
    onSuccess: (response, userId) => {
      showToast(response.message || "User deleted.", "success");
    },
    onError: (error, _userId, context) => {
      if (context?.previousUsers) {
        queryClient.setQueryData(["admin-users"], context.previousUsers);
      }
      if (context?.previousConnections) {
        queryClient.setQueryData(["admin-connections"], context.previousConnections);
      }
      if (context?.previousReports) {
        queryClient.setQueryData(["admin-reports"], context.previousReports);
      }
      if (context?.previousAnalysis) {
        queryClient.setQueryData(["admin-user-analysis", context.userId], context.previousAnalysis);
      }
      if (typeof context?.previousSelectedUserId === "string") {
        setSelectedUserId(context.previousSelectedUserId);
      }
      showToast(error, "error");
    },
    onSettled: async (_response, _error, userId) => {
      await Promise.all([
        queryClient.invalidateQueries({ queryKey: ["admin-users"] }),
        queryClient.invalidateQueries({ queryKey: ["admin-overview"] }),
        queryClient.invalidateQueries({ queryKey: ["admin-connections"] }),
        queryClient.invalidateQueries({ queryKey: ["admin-reports"] }),
        queryClient.invalidateQueries({ queryKey: ["admin-system-alerts"] }),
        queryClient.invalidateQueries({ queryKey: ["admin-user-analysis", userId] }),
      ]);
    },
  });

  const removeConnection = useMutation({
    mutationFn: async (connectionId) => (await apiClient.delete(`/admin/connections/${connectionId}`)).data,
    onSuccess: (response) => {
      showToast(response.message || "Connection removed.", "success");
      setConfirmDialog(null);
      queryClient.invalidateQueries({ queryKey: ["admin-connections"] });
      queryClient.invalidateQueries({ queryKey: ["admin-users"] });
      queryClient.invalidateQueries({ queryKey: ["admin-overview"] });
      if (selectedUserId) {
        queryClient.invalidateQueries({ queryKey: ["admin-user-analysis", selectedUserId] });
      }
    },
    onError: (error) => showToast(error, "error"),
  });

  const removeReport = useMutation({
    mutationFn: async (reportId) => (await apiClient.delete(`/admin/reports/${reportId}`)).data,
    onSuccess: (response) => {
      showToast(response.message || "Report removed.", "success");
      setConfirmDialog(null);
      queryClient.invalidateQueries({ queryKey: ["admin-reports"] });
      queryClient.invalidateQueries({ queryKey: ["admin-users"] });
      queryClient.invalidateQueries({ queryKey: ["admin-overview"] });
      if (selectedUserId) {
        queryClient.invalidateQueries({ queryKey: ["admin-user-analysis", selectedUserId] });
      }
    },
    onError: (error) => showToast(error, "error"),
  });

  const filteredUsers = useMemo(() => {
    const query = searchTerm.trim().toLowerCase();
    const items = query
      ? users.filter((user) =>
          [user.display_name, user.email, user.mode, user.status, user.connections]
            .filter(Boolean)
            .some((value) => String(value).toLowerCase().includes(query))
        )
      : users;

    const sorted = [...items].sort((left, right) => {
      const leftValue = left?.[sortKey];
      const rightValue = right?.[sortKey];

      if (sortKey === "report_count" || sortKey === "connection_count") {
        const delta = Number(leftValue || 0) - Number(rightValue || 0);
        return sortDirection === "asc" ? delta : -delta;
      }

      const leftText = String(leftValue || "").toLowerCase();
      const rightText = String(rightValue || "").toLowerCase();
      const delta = leftText.localeCompare(rightText);
      return sortDirection === "asc" ? delta : -delta;
    });

    return sorted;
  }, [users, searchTerm, sortKey, sortDirection]);

  useEffect(() => {
    setCurrentPage(1);
  }, [searchTerm, sortKey, sortDirection]);

  const totalPages = Math.max(1, Math.ceil(filteredUsers.length / USERS_PER_PAGE));
  const pagedUsers = filteredUsers.slice((currentPage - 1) * USERS_PER_PAGE, currentPage * USERS_PER_PAGE);

  const submitSystemAlert = () => {
    if (!alertForm.title.trim() || !alertForm.explanation.trim() || !alertForm.recommended_action.trim()) {
      showToast("Please complete the alert title, explanation, and recommended action.", "warning");
      return;
    }
    createSystemAlert.mutate(alertForm);
  };

  const handleToggleStatus = (user) => {
    const nextStatus = user.status === "inactive" ? "active" : "inactive";
    updateUser.mutate({ userId: user.id, payload: { status: nextStatus } });
  };

  const handleDeleteUser = (user) => {
    setConfirmDialog({
      kind: "delete-user",
      title: `Delete ${user.display_name}?`,
      description: "This removes the user record, saved reports, alerts, and connected accounts from the admin workspace.",
      confirmLabel: "Delete user",
      onConfirm: () => deleteUser.mutate(user.id),
    });
  };

  const handleRemoveConnection = (connection) => {
    setConfirmDialog({
      kind: "remove-connection",
      title: `Remove ${connection.platform} connection?`,
      description: `This disconnects ${connection.account_name} from the selected user in the admin workspace.`,
      confirmLabel: "Remove connection",
      onConfirm: () => removeConnection.mutate(connection.id),
    });
  };

  const handleRemoveReport = (report) => {
    setConfirmDialog({
      kind: "remove-report",
      title: "Remove saved report?",
      description: `This removes "${report.title}" from the managed user's saved reports.`,
      confirmLabel: "Remove report",
      onConfirm: () => removeReport.mutate(report.id),
    });
  };

  const openEditUser = (user) => {
    setEditingUser({
      id: user.id,
      display_name: user.display_name || "",
      mode: user.mode || "creator",
      status: user.status || "active",
    });
  };

  const saveEditUser = () => {
    if (!editingUser?.display_name?.trim()) {
      showToast("Display name is required.", "warning");
      return;
    }
    updateUser.mutate({
      userId: editingUser.id,
      payload: {
        display_name: editingUser.display_name,
        mode: editingUser.mode,
        status: editingUser.status,
      },
    });
  };

  const selectedAnalysis = userAnalysisQuery.data;
  const selectedOverview = selectedAnalysis?.snapshot?.overview || [];
  const selectedRollups = selectedAnalysis?.snapshot?.platform_rollups || [];
  const selectedTopContent = selectedAnalysis?.snapshot?.top_content || [];
  const selectedAlerts = selectedAnalysis?.alerts || [];
  const selectedConnections = selectedAnalysis?.connections || [];
  const recentConnections = useMemo(() => (connectionsQuery.data?.items || []).slice(0, 6), [connectionsQuery.data?.items]);
  const recentReports = useMemo(() => (reportsQuery.data?.items || []).slice(0, 6), [reportsQuery.data?.items]);
  const confirmPending =
    (confirmDialog?.kind === "delete-user" && deleteUser.isPending)
    || (confirmDialog?.kind === "remove-connection" && removeConnection.isPending)
    || (confirmDialog?.kind === "remove-report" && removeReport.isPending);

  const updateSort = (key) => {
    if (sortKey === key) {
      setSortDirection((current) => (current === "asc" ? "desc" : "asc"));
      return;
    }
    setSortKey(key);
    setSortDirection("asc");
  };

  return (
    <AppShell title="Operations Center" subtitle="Monitor and manage users, connections, reports, and alerts from one admin workspace.">
      <motion.section variants={stagger} initial="hidden" animate="show" className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
        {(overviewQuery.data?.overview || []).map((metric) => (
          <motion.div key={metric.label} variants={fadeUp}><StatCard {...metric} /></motion.div>
        ))}
      </motion.section>

      <motion.section variants={stagger} initial="hidden" animate="show" className="grid gap-4 xl:grid-cols-3">
        {(overviewQuery.data?.provider_status || []).map((item) => (
          <motion.div key={item.provider} variants={fadeUp}>
            <Panel className="p-4">
              <div className="flex items-center justify-between gap-3">
                <p className="font-medium text-white">{item.label || item.provider}</p>
                <span className={`rounded-full px-2.5 py-1 text-[10px] font-semibold ${healthColors[item.status] || healthColors.healthy}`}>
                  {healthLabels[item.status] || item.status}
                </span>
              </div>
              <p className="mt-2 text-xs leading-relaxed text-slate-500">{item.message}</p>
            </Panel>
          </motion.div>
        ))}
      </motion.section>

      <section className="grid items-start gap-4">
        <Panel className="p-5">
          <div className="flex flex-wrap items-center justify-between gap-3">
            <div className="flex items-center gap-3">
              <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-neon/10"><Users size={18} className="text-neon" /></div>
              <div>
                <h2 className="font-display text-xl font-bold text-white">Managed users</h2>
                <p className="text-xs text-slate-500">Search, sort, edit, activate, deactivate, or remove managed users from this table.</p>
              </div>
            </div>
            <div className="relative w-full max-w-sm">
              <Search size={14} className="pointer-events-none absolute left-3 top-1/2 -translate-y-1/2 text-slate-500" />
              <input
                value={searchTerm}
                onChange={(event) => setSearchTerm(event.target.value)}
                placeholder="Search by name, email, or connection..."
                className="w-full rounded-2xl border border-white/[0.08] bg-white/[0.03] py-2.5 pl-9 pr-3 text-sm text-white outline-none placeholder:text-slate-500"
              />
            </div>
          </div>

          <div className="mt-4 overflow-hidden rounded-2xl border border-white/[0.05]">
            <div className="overflow-x-auto">
              <table className="min-w-full text-left text-sm">
                <thead>
                  <tr className="border-b border-white/[0.05] bg-white/[0.02]">
                    {[
                      ["display_name", "User"],
                      ["email", "Email"],
                      ["status", "Status"],
                      ["mode", "Mode"],
                      ["connection_count", "Connections"],
                      ["report_count", "Reports"],
                    ].map(([key, label]) => (
                      <th key={key} className="px-4 py-3 text-[10px] font-semibold uppercase tracking-[0.18em] text-slate-500">
                        <button onClick={() => updateSort(key)} className="transition hover:text-white">
                          {label}
                        </button>
                      </th>
                    ))}
                    <th className="px-4 py-3 text-[10px] font-semibold uppercase tracking-[0.18em] text-slate-500">Actions</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-white/[0.04]">
                  {usersQuery.isLoading && (
                    <tr>
                      <td colSpan={7} className="px-4 py-4">
                        <UserSkeleton />
                      </td>
                    </tr>
                  )}

                  {!usersQuery.isLoading && pagedUsers.map((user) => (
                    <tr
                      key={user.id}
                      onClick={() => setSelectedUserId(user.id)}
                      className={`cursor-pointer transition hover:bg-white/[0.02] ${selectedUserId === user.id ? "bg-white/[0.03]" : ""}`}
                    >
                      <td className="px-4 py-3">
                        <div className="flex items-center gap-3">
                          <div className="flex h-9 w-9 items-center justify-center rounded-xl bg-gradient-to-br from-neon/20 to-blue-500/20 text-xs font-bold text-neon">
                            {(user.display_name || "U")[0].toUpperCase()}
                          </div>
                          <div className="min-w-0">
                            <p className="truncate font-medium text-white">{user.display_name}</p>
                            <p className="truncate text-[11px] text-slate-500">{user.provider}</p>
                          </div>
                        </div>
                      </td>
                      <td className="px-4 py-3 text-slate-400">{user.email}</td>
                      <td className="px-4 py-3">
                        <span className={`rounded-full px-2.5 py-1 text-[10px] font-semibold ${userStatusStyles[user.status] || userStatusStyles.active}`}>
                          {user.status}
                        </span>
                      </td>
                      <td className="px-4 py-3 text-slate-400">{user.mode}</td>
                      <td className="px-4 py-3 text-slate-400">{user.connection_count}</td>
                      <td className="px-4 py-3 text-slate-400">{user.report_count}</td>
                      <td className="px-4 py-3">
                        <div className="flex items-center gap-2">
                          <button
                            onClick={(event) => {
                              event.stopPropagation();
                              openEditUser(user);
                            }}
                            className="rounded-full border border-white/[0.08] bg-white/[0.03] p-2 text-slate-300 transition hover:bg-white/[0.06] hover:text-white"
                            title="Edit user"
                          >
                            <Pencil size={14} />
                          </button>
                          <button
                            onClick={(event) => {
                              event.stopPropagation();
                              handleToggleStatus(user);
                            }}
                            className={`rounded-full border p-2 transition ${user.status === "inactive" ? "border-emerald-500/20 bg-emerald-500/10 text-emerald-300 hover:bg-emerald-500/20" : "border-amber-500/20 bg-amber-500/10 text-amber-300 hover:bg-amber-500/20"}`}
                            title={user.status === "inactive" ? "Activate user" : "Deactivate user"}
                          >
                            {user.status === "inactive" ? <UserCheck size={14} /> : <UserX size={14} />}
                          </button>
                          <button
                            onClick={(event) => {
                              event.stopPropagation();
                              handleDeleteUser(user);
                            }}
                            className="rounded-full border border-rose-500/20 bg-rose-500/10 p-2 text-rose-300 transition hover:bg-rose-500/20"
                            title="Delete user"
                          >
                            <Trash2 size={14} />
                          </button>
                        </div>
                      </td>
                    </tr>
                  ))}

                  {!usersQuery.isLoading && pagedUsers.length === 0 && (
                    <tr>
                      <td colSpan={7} className="px-4 py-10 text-center text-sm text-slate-400">No user matched this filter.</td>
                    </tr>
                  )}
                </tbody>
              </table>
            </div>
          </div>

          <div className="mt-4 flex items-center justify-between gap-3 text-xs text-slate-500">
            <span>
              Showing {filteredUsers.length ? (currentPage - 1) * USERS_PER_PAGE + 1 : 0}-{Math.min(currentPage * USERS_PER_PAGE, filteredUsers.length)} of {filteredUsers.length}
            </span>
            <div className="flex items-center gap-2">
              <button
                onClick={() => setCurrentPage((page) => Math.max(1, page - 1))}
                disabled={currentPage === 1}
                className="rounded-full border border-white/[0.08] px-3 py-1.5 transition hover:bg-white/[0.06] hover:text-white disabled:cursor-not-allowed disabled:opacity-40"
              >
                Previous
              </button>
              <span>Page {currentPage} / {totalPages}</span>
              <button
                onClick={() => setCurrentPage((page) => Math.min(totalPages, page + 1))}
                disabled={currentPage === totalPages}
                className="rounded-full border border-white/[0.08] px-3 py-1.5 transition hover:bg-white/[0.06] hover:text-white disabled:cursor-not-allowed disabled:opacity-40"
              >
                Next
              </button>
            </div>
          </div>
        </Panel>

      </section>

      <section className="grid items-start gap-4 xl:grid-cols-[minmax(0,1.02fr)_minmax(340px,0.98fr)]">
        <div className="space-y-4">
          <Panel className="p-5">
            <div className="flex items-center gap-3">
              <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-purple-500/10"><BarChart3 size={18} className="text-purple-300" /></div>
              <div>
                <h2 className="font-display text-xl font-bold text-white">User analysis</h2>
                <p className="text-xs text-slate-500">Select any user to inspect their dashboard summary, content performance, and alerts.</p>
              </div>
            </div>

            {userAnalysisQuery.isLoading && <div className="mt-5 h-48 animate-pulse rounded-2xl bg-white/[0.04]" />}

            {!userAnalysisQuery.isLoading && selectedAnalysis && (
              <div className="mt-5 space-y-4">
                <div className="rounded-2xl border border-white/[0.05] bg-white/[0.03] p-4">
                  <div className="flex items-center justify-between gap-3">
                    <div>
                      <h3 className="font-display text-lg font-bold text-white">{selectedAnalysis.user.display_name}</h3>
                      <p className="text-xs text-slate-500">{selectedAnalysis.user.email}</p>
                    </div>
                    <span className={`rounded-full px-2.5 py-1 text-[10px] font-semibold ${userStatusStyles[selectedAnalysis.user.status] || userStatusStyles.active}`}>
                      {selectedAnalysis.user.status}
                    </span>
                  </div>
                  <div className="mt-4 grid gap-3 sm:grid-cols-2">
                    {selectedOverview.map((metric) => (
                      <div key={metric.label} className="rounded-xl bg-white/[0.03] p-3">
                        <p className="text-[10px] uppercase tracking-[0.18em] text-slate-500">{metric.label}</p>
                        <p className="mt-1 text-lg font-semibold text-white">{metric.value}</p>
                        <p className="text-[11px] text-slate-500">{metric.delta}</p>
                      </div>
                    ))}
                  </div>
                </div>

                <div className="grid gap-4">
                  <div className="rounded-2xl border border-white/[0.05] bg-white/[0.03] p-4">
                    <h4 className="text-sm font-semibold text-white">Platform rollups</h4>
                    <div className="mt-3 space-y-3">
                      {selectedRollups.length ? selectedRollups.map((item) => (
                        <div key={item.platform} className="rounded-xl bg-white/[0.03] p-3">
                          <div className="flex items-center justify-between gap-3">
                            <p className="font-medium text-white">{item.title}</p>
                            <span className="text-xs text-slate-400">{item.headline}</span>
                          </div>
                          <div className="mt-3 grid gap-2 sm:grid-cols-3">
                            {(item.metrics || []).map((metric) => (
                              <div key={metric.label} className="rounded-lg bg-slate-950/40 p-2.5">
                                <p className="text-[10px] uppercase tracking-[0.18em] text-slate-500">{metric.label}</p>
                                <p className="mt-1 text-sm text-white">{metric.value}</p>
                              </div>
                            ))}
                          </div>
                        </div>
                      )) : <p className="text-sm text-slate-400">Platform analytics are not available for this user yet.</p>}
                    </div>
                  </div>

                  <div className="rounded-2xl border border-white/[0.05] bg-white/[0.03] p-4">
                    <h4 className="text-sm font-semibold text-white">Top content</h4>
                    <div className="mt-3 grid gap-3 md:grid-cols-2">
                      {selectedTopContent.length ? selectedTopContent.slice(0, 4).map((item) => (
                        <TopContentMediaCard key={item.id} item={item} compact />
                      )) : <p className="text-sm text-slate-400">Top content has not loaded for this user yet.</p>}
                    </div>
                  </div>
                </div>
              </div>
            )}

            {!userAnalysisQuery.isLoading && !selectedAnalysis && (
              <div className="mt-5 rounded-2xl bg-white/[0.03] p-4 text-sm text-slate-400">Select a user to view detailed analysis.</div>
            )}
          </Panel>

        </div>

        <div className="space-y-4">
          <Panel className="p-5">
          <div className="flex items-center gap-3">
            <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-amber-500/10"><BellRing size={18} className="text-amber-300" /></div>
            <div>
              <h2 className="font-display text-xl font-bold text-white">System alerts</h2>
              <p className="text-xs text-slate-500">Weekly and monthly alerts are generated automatically, and admins can also create manual alerts here.</p>
            </div>
          </div>

          <div className="mt-4 grid items-start gap-4 2xl:grid-cols-[minmax(260px,0.9fr)_minmax(0,1.1fr)]">
            <div className="space-y-3">
              <select
                value={alertForm.platform}
                onChange={(event) => setAlertForm((current) => ({ ...current, platform: event.target.value }))}
                className={adminSelectClassName}
              >
                <option value="system" className="bg-slate-950 text-white">System</option>
                <option value="instagram" className="bg-slate-950 text-white">Instagram</option>
                <option value="youtube" className="bg-slate-950 text-white">YouTube</option>
                <option value="x" className="bg-slate-950 text-white">X / Twitter</option>
              </select>
              <select
                value={alertForm.severity}
                onChange={(event) => setAlertForm((current) => ({ ...current, severity: event.target.value }))}
                className={adminSelectClassName}
              >
                <option value="low" className="bg-slate-950 text-white">Low</option>
                <option value="medium" className="bg-slate-950 text-white">Medium</option>
                <option value="high" className="bg-slate-950 text-white">High</option>
              </select>
              <input
                value={alertForm.title}
                onChange={(event) => setAlertForm((current) => ({ ...current, title: event.target.value }))}
                placeholder="Short alert title"
                className="w-full rounded-2xl border border-white/[0.08] bg-white/[0.03] px-4 py-3 text-sm text-white outline-none placeholder:text-slate-500"
              />
              <textarea
                value={alertForm.explanation}
                onChange={(event) => setAlertForm((current) => ({ ...current, explanation: event.target.value }))}
                placeholder="Explain the issue or update in simple terms"
                rows={3}
                className="w-full rounded-2xl border border-white/[0.08] bg-white/[0.03] px-4 py-3 text-sm text-white outline-none placeholder:text-slate-500"
              />
              <textarea
                value={alertForm.recommended_action}
                onChange={(event) => setAlertForm((current) => ({ ...current, recommended_action: event.target.value }))}
                placeholder="Recommended next step"
                rows={2}
                className="w-full rounded-2xl border border-white/[0.08] bg-white/[0.03] px-4 py-3 text-sm text-white outline-none placeholder:text-slate-500"
              />
              <Button className="w-full justify-center" onClick={submitSystemAlert} disabled={createSystemAlert.isPending}>
                {createSystemAlert.isPending ? "Creating..." : "Create system alert"}
              </Button>
            </div>

            <div className="space-y-3 xl:max-h-[34rem] xl:overflow-y-auto xl:pr-1">
              {(systemAlertsQuery.data?.items || []).slice(0, 8).map((alert) => (
                <div key={alert.id} className="rounded-2xl border border-white/[0.05] bg-white/[0.03] p-4">
                  <div className="flex items-start justify-between gap-3">
                    <div>
                      <p className="text-[10px] font-semibold uppercase tracking-[0.18em] text-slate-500">{alert.platform}</p>
                      <h3 className="mt-1 text-sm font-semibold text-white">{alert.title}</h3>
                    </div>
                    <span className={`rounded-full px-2.5 py-1 text-[10px] font-semibold ${severityStyles[alert.severity] || "bg-white/[0.06] text-slate-300"}`}>
                      {alert.severity}
                    </span>
                  </div>
                  <p className="mt-2 text-xs leading-relaxed text-slate-400">{alert.explanation}</p>
                  <p className="mt-2 text-xs font-medium text-neon">{alert.recommended_action}</p>
                  <p className="mt-3 text-[11px] text-slate-500">{formatDate(alert.timestamp)}</p>
                </div>
              ))}
              {!(systemAlertsQuery.data?.items || []).length && (
                <div className="rounded-2xl bg-white/[0.03] p-4 text-sm text-slate-400">No system alert is available right now.</div>
              )}
            </div>
          </div>
          </Panel>

          <Panel className="p-5">
          <div className="flex items-center gap-3">
            <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-emerald-500/10"><Link2 size={18} className="text-emerald-300" /></div>
            <div>
              <h2 className="font-display text-xl font-bold text-white">Latest connections</h2>
              <p className="text-xs text-slate-500">Recent platform connections for managed users appear here.</p>
            </div>
          </div>
          <div className="mt-4 space-y-3">
            {recentConnections.map((item) => (
              <div key={item.id} className="rounded-2xl border border-white/[0.05] bg-white/[0.03] p-4">
                <div className="flex items-center justify-between gap-3">
                  <div>
                    <p className="font-medium text-white">{item.account_name}</p>
                    <p className="mt-1 text-xs text-slate-500">{item.user_name} - {item.user_email}</p>
                  </div>
                  <span className="text-[11px] text-slate-500">{item.platform}</span>
                </div>
              </div>
            ))}
            {!recentConnections.length && <div className="rounded-2xl bg-white/[0.03] p-4 text-sm text-slate-400">No recent connection is available right now.</div>}
          </div>
          </Panel>

          <Panel className="p-5">
          <div className="flex items-center gap-3">
            <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-rose-500/10"><FileText size={18} className="text-rose-300" /></div>
            <div>
              <h2 className="font-display text-xl font-bold text-white">Latest reports</h2>
              <p className="text-xs text-slate-500">Recently generated reports from the managed workspace appear here.</p>
            </div>
          </div>
          <div className="mt-4 space-y-3">
            {recentReports.map((item) => (
              <div key={item.id} className="rounded-2xl border border-white/[0.05] bg-white/[0.03] p-4">
                <div className="flex items-center justify-between gap-3">
                  <div>
                    <p className="font-medium text-white">{item.title}</p>
                    <p className="mt-1 text-xs text-slate-500">{item.owner_name} - {item.owner_email}</p>
                  </div>
                  <span className="rounded-full bg-white/[0.05] px-2.5 py-1 text-[10px] font-semibold text-slate-300">{item.period}</span>
                </div>
              </div>
            ))}
            {!recentReports.length && <div className="rounded-2xl bg-white/[0.03] p-4 text-sm text-slate-400">No report is available right now.</div>}
          </div>
          </Panel>
        </div>
      </section>

      <section className="grid items-start gap-4">
        <Panel className="p-5">
          <div className="flex items-center gap-3">
            <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-blue-500/10"><Link2 size={18} className="text-blue-300" /></div>
            <div>
              <h2 className="font-display text-xl font-bold text-white">Selected user activity</h2>
              <p className="text-xs text-slate-500">Review the selected user's connections, alerts, and saved reports here.</p>
            </div>
          </div>

          <div className="mt-3 grid items-start gap-3 md:grid-cols-2 xl:grid-cols-3">
            <div className="rounded-2xl border border-white/[0.05] bg-white/[0.03] p-4">
              <h3 className="text-sm font-semibold text-white">Connections</h3>
              <div className="mt-2.5 space-y-2.5">
                {selectedConnections.length ? selectedConnections.slice(0, 4).map((item) => (
                  <div key={item.id} className="rounded-xl bg-white/[0.03] p-3">
                    <div className="flex items-center justify-between gap-2">
                      <p className="font-medium text-white">{item.platform}</p>
                      <span className="text-[11px] text-slate-500">{item.status}</span>
                    </div>
                    <p className="mt-1 text-xs text-slate-500">{item.account_name}</p>
                    <button
                      onClick={() => handleRemoveConnection(item)}
                      disabled={removeConnection.isPending}
                      className="mt-3 rounded-full border border-rose-500/20 bg-rose-500/10 px-3 py-1.5 text-[11px] font-semibold text-rose-300 transition hover:bg-rose-500/20 disabled:cursor-not-allowed disabled:opacity-60"
                    >
                      Remove
                    </button>
                  </div>
                )) : <p className="text-sm text-slate-400">This user does not have a connected account yet.</p>}
              </div>
            </div>

            <div className="rounded-2xl border border-white/[0.05] bg-white/[0.03] p-4">
              <h3 className="text-sm font-semibold text-white">Alerts</h3>
              <div className="mt-2.5 max-h-[18rem] space-y-2.5 overflow-y-auto pr-1">
                {selectedAlerts.length ? selectedAlerts.slice(0, 6).map((item) => (
                  <div key={item.id} className="rounded-xl bg-white/[0.03] p-3">
                    <div className="flex items-center justify-between gap-2">
                      <p className="font-medium text-white">{item.title}</p>
                      <span className={`rounded-full px-2 py-1 text-[10px] font-semibold ${severityStyles[item.severity] || "bg-white/[0.06] text-slate-300"}`}>
                        {item.severity}
                      </span>
                    </div>
                    <p className="mt-2 text-xs text-slate-500">{item.explanation}</p>
                  </div>
                )) : <p className="text-sm text-slate-400">No alert is currently available for this user.</p>}
              </div>
            </div>

            <div className="rounded-2xl border border-white/[0.05] bg-white/[0.03] p-4">
              <h3 className="text-sm font-semibold text-white">Reports</h3>
              <div className="mt-2.5 space-y-2.5">
                {(selectedAnalysis?.reports || []).length ? selectedAnalysis.reports.slice(0, 4).map((item) => (
                  <div key={item.id} className="rounded-xl bg-white/[0.03] p-3">
                    <p className="font-medium text-white">{item.title}</p>
                    <p className="mt-1 text-xs text-slate-500">{item.period} - {formatDate(item.created_at)}</p>
                    <button
                      onClick={() => handleRemoveReport(item)}
                      disabled={removeReport.isPending}
                      className="mt-3 rounded-full border border-rose-500/20 bg-rose-500/10 px-3 py-1.5 text-[11px] font-semibold text-rose-300 transition hover:bg-rose-500/20 disabled:cursor-not-allowed disabled:opacity-60"
                    >
                      Remove
                    </button>
                  </div>
                )) : <p className="text-sm text-slate-400">This user does not have a saved report yet.</p>}
              </div>
            </div>
          </div>
        </Panel>
      </section>

      {editingUser && (
        <>
          <div className="fixed inset-0 z-[70] bg-black/70 backdrop-blur-sm" onClick={() => setEditingUser(null)} />
          <div className="fixed inset-0 z-[80] flex items-center justify-center p-4">
            <div className="w-full max-w-md rounded-3xl border border-white/[0.08] bg-slate-950/95 p-6 shadow-2xl backdrop-blur-2xl">
              <div className="flex items-center gap-3">
                <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-purple-500/10"><Pencil size={18} className="text-purple-300" /></div>
                <div>
                  <h2 className="font-display text-xl font-bold text-white">Edit managed user</h2>
                  <p className="text-xs text-slate-500">Update the user's profile details, mode, and account status from here.</p>
                </div>
              </div>

              <div className="mt-5 space-y-3">
                <input
                  value={editingUser.display_name}
                  onChange={(event) => setEditingUser((current) => ({ ...current, display_name: event.target.value }))}
                  className="w-full rounded-2xl border border-white/[0.08] bg-white/[0.03] px-4 py-3 text-sm text-white outline-none"
                  placeholder="Display name"
                />
                <select
                  value={editingUser.mode}
                  onChange={(event) => setEditingUser((current) => ({ ...current, mode: event.target.value }))}
                  className={adminSelectClassName}
                >
                  <option value="creator" className="bg-slate-950 text-white">Creator</option>
                  <option value="brand" className="bg-slate-950 text-white">Brand</option>
                </select>
                <select
                  value={editingUser.status}
                  onChange={(event) => setEditingUser((current) => ({ ...current, status: event.target.value }))}
                  className={adminSelectClassName}
                >
                  <option value="active" className="bg-slate-950 text-white">Active</option>
                  <option value="inactive" className="bg-slate-950 text-white">Inactive</option>
                </select>
              </div>

              <div className="mt-6 flex gap-3">
                <Button variant="secondary" className="flex-1" onClick={() => setEditingUser(null)}>
                  Cancel
                </Button>
                <Button className="flex-1" onClick={saveEditUser} disabled={updateUser.isPending}>
                  Save changes
                </Button>
              </div>
            </div>
          </div>
        </>
      )}

      <ConfirmModal
        open={Boolean(confirmDialog)}
        title={confirmDialog?.title}
        description={confirmDialog?.description}
        confirmLabel={confirmDialog?.confirmLabel}
        tone="danger"
        isPending={confirmPending}
        onConfirm={() => confirmDialog?.onConfirm?.()}
        onClose={closeConfirmDialog}
      />
    </AppShell>
  );
}
