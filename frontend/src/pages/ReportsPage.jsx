import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Download, FileText, Globe2, Printer, Sparkles, Trash2 } from "lucide-react";
import { motion } from "framer-motion";

import { AppShell } from "../components/layout/AppShell";
import { Button } from "../components/ui/Button";
import { ConfirmModal } from "../components/ui/ConfirmModal";
import { Panel } from "../components/ui/Panel";
import { apiClient } from "../lib/apiClient";
import { useToast } from "../hooks/useToast";

const apiRoot = (import.meta.env.VITE_API_BASE_URL || "http://localhost:8000/api").replace(/\/api$/, "");
const stagger = { hidden: { opacity: 0 }, show: { opacity: 1, transition: { staggerChildren: 0.1 } } };
const fadeUp = { hidden: { opacity: 0, y: 16 }, show: { opacity: 1, y: 0, transition: { duration: 0.4 } } };

export function ReportsPage() {
  const queryClient = useQueryClient();
  const { showToast } = useToast();
  const [reportToDelete, setReportToDelete] = useState(null);
  const { data } = useQuery({ queryKey: ["reports"], queryFn: async () => (await apiClient.get("/reports")).data });
  const generateMutation = useMutation({
    mutationFn: async (period) => (await apiClient.post(`/reports/generate?period=${period}`)).data,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["reports"] });
      queryClient.invalidateQueries({ queryKey: ["alerts"] });
      showToast("Detailed report generated successfully.", "success");
    },
    onError: (error) => {
      showToast(error, "error");
    },
  });
  const deleteMutation = useMutation({
    mutationFn: async (reportId) => (await apiClient.delete(`/reports/${reportId}`)).data,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["reports"] });
      setReportToDelete(null);
      showToast("Report deleted successfully.", "success");
    },
    onError: (error) => {
      showToast(error, "error");
    },
  });

  const generateReport = async (period) => {
    await generateMutation.mutateAsync(period);
  };

  const handleDeleteReport = (reportId) => {
    setReportToDelete(reportId);
  };

  const reports = data?.items || [];

  return (
    <AppShell title="Reports & public views" subtitle="Generate detailed shareable analytics reports and download them in a presentation-ready view.">
      <section className="grid gap-5 md:grid-cols-2">
        <Panel className="p-6">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-xs font-semibold uppercase tracking-[0.2em] text-slate-500">Generate</p>
              <h2 className="mt-2 font-display text-xl font-bold text-white">Fresh report</h2>
            </div>
            <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-neon/10">
              <FileText size={20} className="text-neon" />
            </div>
          </div>
          <p className="mt-4 text-sm text-slate-400">Create a new snapshot from your current analytics data with dashboard metrics, platform summaries, alerts, recommendations, and printable detail sections.</p>
          <div className="mt-6 flex flex-wrap gap-3">
            <Button onClick={() => generateReport("weekly")} disabled={generateMutation.isPending}>Generate weekly</Button>
            <Button variant="accent" onClick={() => generateReport("monthly")} disabled={generateMutation.isPending}>Generate monthly</Button>
          </div>
        </Panel>

        <Panel className="p-6">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-xs font-semibold uppercase tracking-[0.2em] text-slate-500">How it works</p>
              <h2 className="mt-2 font-display text-xl font-bold text-white">Public views</h2>
            </div>
            <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-purple-500/10">
              <Sparkles size={20} className="text-purple-400" />
            </div>
          </div>
          <p className="mt-4 text-sm text-slate-400">
            The backend now renders a detailed HTML report that mirrors the dashboard, stores a public token,
            and exposes a shareable URL you can open, print, or download as an HTML file.
          </p>
        </Panel>
      </section>

      {reports.length > 0 && (
        <motion.section variants={stagger} initial="hidden" animate="show">
          <h2 className="mb-4 text-xs font-semibold uppercase tracking-[0.2em] text-slate-500">Generated reports</h2>
          <div className="grid gap-4 lg:grid-cols-2">
            {reports.map((report) => {
              const overview = report.data?.overview || [];
              const quickStats = overview.slice(0, 4);
              const recommendationCount = report.data?.recommendations?.length || 0;
              const alertCount = report.data?.alerts?.length || 0;
              const connectionCount = report.data?.connections?.length || 0;
              return (
                <motion.div key={report.id} variants={fadeUp}>
                  <Panel className="p-5">
                    <div className="flex items-center justify-between gap-3">
                      <div>
                        <p className="text-[10px] font-semibold uppercase tracking-[0.2em] text-slate-500">{report.period}</p>
                        <h3 className="mt-1 font-display text-lg font-bold text-white">{report.title}</h3>
                      </div>
                      <Printer size={18} className="shrink-0 text-amber-400" />
                    </div>
                    <p className="mt-3 text-xs text-slate-400">Generated {new Date(report.created_at).toLocaleString()}</p>
                    <div className="mt-4 grid gap-2 sm:grid-cols-2">
                      {quickStats.map((metric) => (
                        <div key={`${report.id}-${metric.label}`} className="rounded-2xl border border-white/[0.06] bg-white/[0.03] px-4 py-3">
                          <p className="text-[10px] font-semibold uppercase tracking-[0.16em] text-slate-500">{metric.label}</p>
                          <p className="mt-2 font-display text-xl font-bold text-white">{metric.value}</p>
                          <p className="mt-1 text-xs text-neon">{metric.delta}</p>
                        </div>
                      ))}
                    </div>
                    <div className="mt-4 flex flex-wrap gap-2 text-[11px] text-slate-400">
                      <span className="rounded-full bg-white/[0.04] px-3 py-1.5">{connectionCount} connected account(s)</span>
                      <span className="rounded-full bg-white/[0.04] px-3 py-1.5">{recommendationCount} recommendation(s)</span>
                      <span className="rounded-full bg-white/[0.04] px-3 py-1.5">{alertCount} alert(s)</span>
                    </div>
                    <div className="mt-4 flex flex-wrap gap-3">
                      <Button className="gap-2 text-xs" onClick={() => window.open(`${apiRoot}/api/reports/public/${report.public_token}`, "_blank")}>
                        <Globe2 size={14} /> Open public view
                      </Button>
                      <Button variant="secondary" className="gap-2 text-xs" onClick={() => window.open(`${apiRoot}/api/reports/public/${report.public_token}/download`, "_blank")}>
                        <Download size={14} /> Download HTML
                      </Button>
                      <Button variant="danger" className="gap-2 text-xs" onClick={() => handleDeleteReport(report.id)} disabled={deleteMutation.isPending}>
                        <Trash2 size={14} /> Delete report
                      </Button>
                    </div>
                  </Panel>
                </motion.div>
              );
            })}
          </div>
        </motion.section>
      )}

      <ConfirmModal
        open={Boolean(reportToDelete)}
        title="Delete this report?"
        description="This removes the saved report card and its downloadable HTML file."
        confirmLabel="Delete report"
        tone="danger"
        isPending={deleteMutation.isPending}
        onConfirm={() => reportToDelete && deleteMutation.mutate(reportToDelete)}
        onClose={() => setReportToDelete(null)}
      />
    </AppShell>
  );
}
