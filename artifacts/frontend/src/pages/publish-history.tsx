import { useState, useEffect } from "react";
import { useAuth } from "@/lib/auth";
import { apiFetch } from "@/lib/api";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { useToast } from "@/hooks/use-toast";
import {
  Send, Share2, CheckCircle2, XCircle, Clock, RefreshCw,
  Loader2, ChevronDown, ChevronUp, History, AlertCircle
} from "lucide-react";

interface PublishLog {
  id: string;
  attempt_number: number;
  success: boolean;
  error_message: string;
  user_message: string;
  attempted_at: string;
}

interface Job {
  id: string;
  content: { id: string; title: string } | null;
  channel: { id: string; name: string; platform: string };
  status: string;
  scheduled_at: string | null;
  started_at: string | null;
  completed_at: string | null;
  attempt_count: number;
  created_at: string;
  logs: PublishLog[];
}

const STATUS_MAP: Record<string, { label: string; color: string; icon: JSX.Element }> = {
  success: { label: "موفق", color: "bg-green-50 text-green-700 border-green-200", icon: <CheckCircle2 className="w-3 h-3" /> },
  failed: { label: "ناموفق", color: "bg-red-50 text-red-700 border-red-200", icon: <XCircle className="w-3 h-3" /> },
  queued: { label: "در صف", color: "bg-amber-50 text-amber-700 border-amber-200", icon: <Clock className="w-3 h-3" /> },
  processing: { label: "در حال پردازش", color: "bg-blue-50 text-blue-700 border-blue-200", icon: <Loader2 className="w-3 h-3 animate-spin" /> },
};

function getPlatformIcon(platform: string) {
  if (platform === "telegram") return <Send className="w-4 h-4 text-blue-500" />;
  if (platform === "bale") return <Share2 className="w-4 h-4 text-green-500" />;
  return <Share2 className="w-4 h-4 text-muted-foreground" />;
}

function JobRow({ job, onRetry }: { job: Job; onRetry: (id: string) => void }) {
  const [expanded, setExpanded] = useState(false);
  const [retrying, setRetrying] = useState(false);
  const statusInfo = STATUS_MAP[job.status] || { label: job.status, color: "bg-muted text-muted-foreground", icon: <AlertCircle className="w-3 h-3" /> };

  const handleRetry = async () => {
    setRetrying(true);
    await onRetry(job.id);
    setRetrying(false);
  };

  return (
    <Card>
      <CardContent className="p-0">
        <button
          className="w-full flex flex-col sm:flex-row items-start sm:items-center justify-between p-5 gap-4 text-right hover:bg-muted/30 transition-colors"
          onClick={() => setExpanded(!expanded)}
        >
          <div className="flex items-start gap-3 flex-1 min-w-0">
            <div className="mt-0.5">{getPlatformIcon(job.channel.platform)}</div>
            <div className="min-w-0">
              <p className="font-medium truncate">
                {job.content?.title || "متن مستقیم"}
              </p>
              <p className="text-sm text-muted-foreground mt-0.5">
                {job.channel.name} · {new Date(job.created_at).toLocaleString("fa-IR")}
              </p>
            </div>
          </div>
          <div className="flex items-center gap-3 shrink-0">
            <Badge variant="outline" className={`gap-1 ${statusInfo.color}`}>
              {statusInfo.icon} {statusInfo.label}
            </Badge>
            {job.status === "failed" && (
              <Button
                size="sm"
                variant="outline"
                className="text-xs gap-1.5"
                onClick={e => { e.stopPropagation(); handleRetry(); }}
                disabled={retrying}
              >
                {retrying ? <Loader2 className="w-3 h-3 animate-spin" /> : <RefreshCw className="w-3 h-3" />}
                تلاش مجدد
              </Button>
            )}
            {expanded ? <ChevronUp className="w-4 h-4 text-muted-foreground" /> : <ChevronDown className="w-4 h-4 text-muted-foreground" />}
          </div>
        </button>

        {expanded && (
          <div className="border-t px-5 pb-4 pt-3 bg-muted/20">
            <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 mb-3 text-sm">
              <div>
                <p className="text-muted-foreground text-xs mb-0.5">شروع</p>
                <p>{job.started_at ? new Date(job.started_at).toLocaleString("fa-IR") : "—"}</p>
              </div>
              <div>
                <p className="text-muted-foreground text-xs mb-0.5">اتمام</p>
                <p>{job.completed_at ? new Date(job.completed_at).toLocaleString("fa-IR") : "—"}</p>
              </div>
              <div>
                <p className="text-muted-foreground text-xs mb-0.5">تلاش‌ها</p>
                <p>{job.attempt_count} از {3}</p>
              </div>
              <div>
                <p className="text-muted-foreground text-xs mb-0.5">زمان‌بندی</p>
                <p>{job.scheduled_at ? new Date(job.scheduled_at).toLocaleString("fa-IR") : "فوری"}</p>
              </div>
            </div>

            {job.logs && job.logs.length > 0 && (
              <div className="space-y-2">
                <p className="text-xs font-medium text-muted-foreground">لاگ‌های تلاش</p>
                {job.logs.map(log => (
                  <div
                    key={log.id}
                    className={`rounded-lg p-3 text-xs border ${log.success ? "bg-green-50 border-green-200" : "bg-red-50 border-red-200"}`}
                  >
                    <div className="flex items-center justify-between mb-1">
                      <span className="font-medium">تلاش {log.attempt_number}</span>
                      <span className="text-muted-foreground">{new Date(log.attempted_at).toLocaleString("fa-IR")}</span>
                    </div>
                    {!log.success && log.user_message && (
                      <p className="text-red-700">{log.user_message}</p>
                    )}
                    {log.success && <p className="text-green-700">انتشار موفق</p>}
                  </div>
                ))}
              </div>
            )}
          </div>
        )}
      </CardContent>
    </Card>
  );
}

export default function PublishHistory() {
  const { selectedWorkspace } = useAuth();
  const { toast } = useToast();
  const [jobs, setJobs] = useState<Job[]>([]);
  const [loading, setLoading] = useState(true);
  const [statusFilter, setStatusFilter] = useState<string>("all");

  const fetchHistory = async () => {
    if (!selectedWorkspace) return;
    setLoading(true);
    try {
      const res = await apiFetch(`/workspaces/${selectedWorkspace.id}/publish/history/`);
      setJobs(Array.isArray(res?.data) ? res.data : []);
    } catch {
      toast({ title: "خطا", description: "دریافت تاریخچه ناموفق بود", variant: "destructive" });
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { if (selectedWorkspace) fetchHistory(); }, [selectedWorkspace]);

  const handleRetry = async (jobId: string) => {
    if (!selectedWorkspace) return;
    try {
      await apiFetch(`/workspaces/${selectedWorkspace.id}/publish/jobs/${jobId}/retry/`, {
        method: "POST",
      });
      toast({ title: "✅ در صف قرار گرفت", description: "مجدداً تلاش خواهد شد" });
      fetchHistory();
    } catch (e: any) {
      toast({ title: "خطا", description: e.message || "تلاش مجدد ناموفق بود", variant: "destructive" });
    }
  };

  const filteredJobs = statusFilter === "all" ? jobs : jobs.filter(j => j.status === statusFilter);

  const FILTERS = [
    { key: "all", label: "همه" },
    { key: "success", label: "موفق" },
    { key: "failed", label: "ناموفق" },
    { key: "queued", label: "در صف" },
  ];

  return (
    <div className="space-y-6">
      <div className="flex justify-between items-center gap-4">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">تاریخچه انتشار</h1>
          <p className="text-muted-foreground mt-1">سوابق انتشار محتوا در کانال‌ها</p>
        </div>
        <Button variant="outline" size="sm" onClick={fetchHistory}>
          <RefreshCw className="w-4 h-4" />
        </Button>
      </div>

      {/* Filters */}
      <div className="flex gap-2 flex-wrap">
        {FILTERS.map(f => (
          <button
            key={f.key}
            onClick={() => setStatusFilter(f.key)}
            className={`px-4 py-1.5 rounded-full text-sm font-medium border-2 transition-all ${statusFilter === f.key ? "border-primary bg-primary text-primary-foreground" : "border-border hover:border-muted-foreground"}`}
          >
            {f.label}
          </button>
        ))}
      </div>

      {loading ? (
        <div className="space-y-3">
          {[1, 2, 3, 4].map(i => <Card key={i} className="animate-pulse h-20" />)}
        </div>
      ) : filteredJobs.length === 0 ? (
        <Card>
          <CardContent className="flex flex-col items-center justify-center py-16 text-center gap-4">
            <History className="w-12 h-12 text-muted-foreground/30" />
            <div>
              <p className="font-medium text-muted-foreground">تاریخچه‌ای موجود نیست</p>
              <p className="text-sm text-muted-foreground/70 mt-1">پس از انتشار محتوا، سوابق اینجا نمایش داده می‌شوند</p>
            </div>
          </CardContent>
        </Card>
      ) : (
        <div className="space-y-3">
          {filteredJobs.map(job => (
            <JobRow key={job.id} job={job} onRetry={handleRetry} />
          ))}
        </div>
      )}
    </div>
  );
}
