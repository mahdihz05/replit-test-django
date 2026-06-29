import { useState, useEffect } from "react";
import { useAuth } from "@/lib/auth";
import { apiFetch } from "@/lib/api";
import { Card, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { useToast } from "@/hooks/use-toast";
import { Send, Share2, Clock, RefreshCw, Loader2, XCircle, CalendarClock } from "lucide-react";

interface Job {
  id: string;
  content: { title: string } | null;
  channel: { name: string; platform: string };
  status: string;
  scheduled_at: string | null;
  created_at: string;
}

function getPlatformIcon(platform: string) {
  if (platform === "telegram") return <Send className="w-4 h-4 text-blue-500" />;
  if (platform === "bale") return <Share2 className="w-4 h-4 text-green-500" />;
  return <Share2 className="w-4 h-4 text-muted-foreground" />;
}

function Countdown({ scheduledAt }: { scheduledAt: string }) {
  const [label, setLabel] = useState("");
  useEffect(() => {
    const calc = () => {
      const diff = Math.max(0, Math.floor((new Date(scheduledAt).getTime() - Date.now()) / 1000));
      if (diff === 0) { setLabel("الان"); return; }
      const h = Math.floor(diff / 3600);
      const m = Math.floor((diff % 3600) / 60);
      const s = diff % 60;
      if (h > 0) setLabel(`${h}ساعت و ${m}دقیقه دیگر`);
      else if (m > 0) setLabel(`${m}دقیقه و ${s}ثانیه دیگر`);
      else setLabel(`${s}ثانیه دیگر`);
    };
    calc();
    const t = setInterval(calc, 1000);
    return () => clearInterval(t);
  }, [scheduledAt]);
  return <span className="text-amber-600 font-medium text-xs">{label}</span>;
}

export default function PublishQueue() {
  const { selectedWorkspace } = useAuth();
  const { toast } = useToast();
  const [jobs, setJobs] = useState<Job[]>([]);
  const [loading, setLoading] = useState(true);
  const [cancelingId, setCancelingId] = useState<string | null>(null);

  const fetchJobs = async () => {
    if (!selectedWorkspace) return;
    setLoading(true);
    try {
      const res = await apiFetch(`/workspaces/${selectedWorkspace.id}/publish/queue/`);
      setJobs(Array.isArray(res?.data) ? res.data : []);
    } catch {
      toast({ title: "خطا", description: "دریافت صف ناموفق بود", variant: "destructive" });
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { if (selectedWorkspace) fetchJobs(); }, [selectedWorkspace]);

  const handleCancel = async (jobId: string) => {
    if (!selectedWorkspace) return;
    setCancelingId(jobId);
    try {
      await apiFetch(`/workspaces/${selectedWorkspace.id}/publish/jobs/${jobId}/cancel/`, {
        method: "POST",
      });
      setJobs(prev => prev.filter(j => j.id !== jobId));
      toast({ title: "لغو شد", description: "کار از صف حذف شد" });
    } catch (e: any) {
      toast({ title: "خطا", description: e.message || "لغو ناموفق بود", variant: "destructive" });
    } finally {
      setCancelingId(null);
    }
  };

  return (
    <div className="space-y-6">
      <div className="flex justify-between items-center gap-4">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">صف انتشار</h1>
          <p className="text-muted-foreground mt-1">انتشارهای زمان‌بندی‌شده در انتظار اجرا</p>
        </div>
        <Button variant="outline" size="sm" onClick={fetchJobs}>
          <RefreshCw className="w-4 h-4" />
        </Button>
      </div>

      {loading ? (
        <div className="space-y-3">
          {[1, 2, 3].map(i => <Card key={i} className="animate-pulse h-24" />)}
        </div>
      ) : jobs.length === 0 ? (
        <Card>
          <CardContent className="flex flex-col items-center justify-center py-16 text-center gap-4">
            <CalendarClock className="w-12 h-12 text-muted-foreground/30" />
            <div>
              <p className="font-medium text-muted-foreground">صف خالی است</p>
              <p className="text-sm text-muted-foreground/70 mt-1">هیچ انتشار زمان‌بندی‌شده‌ای در انتظار نیست</p>
            </div>
          </CardContent>
        </Card>
      ) : (
        <div className="space-y-3">
          {jobs.map(job => (
            <Card key={job.id}>
              <CardContent className="flex flex-col sm:flex-row items-start sm:items-center justify-between p-5 gap-4">
                <div className="flex items-start gap-3 flex-1 min-w-0">
                  <div className="w-10 h-10 rounded-full bg-amber-100 flex items-center justify-center shrink-0 mt-0.5">
                    <Clock className="w-5 h-5 text-amber-600" />
                  </div>
                  <div className="min-w-0">
                    <p className="font-medium truncate">
                      {job.content?.title || "متن مستقیم"}
                    </p>
                    <div className="flex items-center gap-2 mt-1 flex-wrap">
                      {getPlatformIcon(job.channel.platform)}
                      <span className="text-sm text-muted-foreground">{job.channel.name}</span>
                      {job.scheduled_at && (
                        <>
                          <span className="text-muted-foreground/40">·</span>
                          <Countdown scheduledAt={job.scheduled_at} />
                        </>
                      )}
                    </div>
                    {job.scheduled_at && (
                      <p className="text-xs text-muted-foreground mt-1">
                        {new Date(job.scheduled_at).toLocaleString("fa-IR")}
                      </p>
                    )}
                  </div>
                </div>
                <div className="flex items-center gap-3 shrink-0">
                  <Badge variant="outline" className="bg-amber-50 text-amber-700 border-amber-200 gap-1">
                    <Clock className="w-3 h-3" /> در صف
                  </Badge>
                  <Button
                    variant="outline"
                    size="sm"
                    className="gap-1.5 text-destructive hover:bg-destructive/10 hover:text-destructive border-destructive/30"
                    onClick={() => handleCancel(job.id)}
                    disabled={cancelingId === job.id}
                  >
                    {cancelingId === job.id ? (
                      <Loader2 className="w-4 h-4 animate-spin" />
                    ) : (
                      <XCircle className="w-4 h-4" />
                    )}
                    لغو
                  </Button>
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
      )}
    </div>
  );
}
