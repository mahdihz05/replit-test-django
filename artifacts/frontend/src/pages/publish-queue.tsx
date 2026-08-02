import { useEffect, useMemo, useState } from "react";
import { useAuth } from "@/lib/auth";
import { apiFetch } from "@/lib/api";
import { Card, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { useToast } from "@/hooks/use-toast";
import {
  CalendarClock,
  Clock,
  FileText,
  Image as ImageIcon,
  Loader2,
  Music2,
  RefreshCw,
  Send,
  Share2,
  Video,
  XCircle,
} from "lucide-react";

interface Attachment {
  id: string;
  media_type: "image" | "video" | "voice" | "document";
  original_filename: string;
  file_url?: string;
}

interface Job {
  id: string;
  content: string;
  content_title: string;
  channel: { name: string; platform: string };
  status: string;
  scheduled_at: string | null;
  next_retry_at: string | null;
  attachments: Attachment[];
  created_at: string;
}

function getPlatformIcon(platform: string) {
  if (platform === "telegram") return <Send className="h-4 w-4 text-blue-500" />;
  if (platform === "bale") return <Share2 className="h-4 w-4 text-green-500" />;
  return <Share2 className="h-4 w-4 text-muted-foreground" />;
}

function getMediaIcon(type: Attachment["media_type"]) {
  if (type === "image") return <ImageIcon className="h-3.5 w-3.5" />;
  if (type === "video") return <Video className="h-3.5 w-3.5" />;
  if (type === "voice") return <Music2 className="h-3.5 w-3.5" />;
  return <FileText className="h-3.5 w-3.5" />;
}

function Countdown({ date }: { date: string }) {
  const [now, setNow] = useState(Date.now());
  useEffect(() => {
    const timer = window.setInterval(() => setNow(Date.now()), 1000);
    return () => window.clearInterval(timer);
  }, []);

  const seconds = Math.floor((new Date(date).getTime() - now) / 1000);
  if (seconds <= 0) return <span className="font-medium text-blue-700">در انتظار پردازش</span>;
  const hours = Math.floor(seconds / 3600);
  const minutes = Math.floor((seconds % 3600) / 60);
  const remainingSeconds = seconds % 60;
  if (hours > 0) return <span>{hours.toLocaleString("fa-IR")} ساعت و {minutes.toLocaleString("fa-IR")} دقیقه دیگر</span>;
  if (minutes > 0) return <span>{minutes.toLocaleString("fa-IR")} دقیقه و {remainingSeconds.toLocaleString("fa-IR")} ثانیه دیگر</span>;
  return <span>{remainingSeconds.toLocaleString("fa-IR")} ثانیه دیگر</span>;
}

export default function PublishQueue() {
  const { selectedWorkspace } = useAuth();
  const { toast } = useToast();
  const [jobs, setJobs] = useState<Job[]>([]);
  const [loading, setLoading] = useState(false);
  const [cancelingId, setCancelingId] = useState<string | null>(null);

  const fetchJobs = async (quiet = false) => {
    if (!selectedWorkspace) return;
    if (!quiet) setLoading(true);
    try {
      const response = await apiFetch(`/workspaces/${selectedWorkspace.id}/publish/queue/`);
      setJobs(Array.isArray(response?.data) ? response.data : []);
    } catch (error: any) {
      if (!quiet) toast({ title: "خطا", description: error.message || "دریافت صف انتشار ناموفق بود.", variant: "destructive" });
    } finally {
      if (!quiet) setLoading(false);
    }
  };

  useEffect(() => {
    if (!selectedWorkspace) return;
    void fetchJobs();
    const timer = window.setInterval(() => void fetchJobs(true), 30_000);
    return () => window.clearInterval(timer);
  }, [selectedWorkspace]);

  const groupedCount = useMemo(() => new Set(jobs.map((job) => job.content)).size, [jobs]);

  const handleCancel = async (jobId: string) => {
    if (!selectedWorkspace) return;
    setCancelingId(jobId);
    try {
      await apiFetch(`/workspaces/${selectedWorkspace.id}/publish/jobs/${jobId}/cancel/`, { method: "POST" });
      setJobs((items) => items.filter((item) => item.id !== jobId));
      toast({ title: "زمان‌بندی لغو شد", description: "این مقصد از صف انتشار خارج شد." });
    } catch (error: any) {
      toast({ title: "لغو ناموفق", description: error.message || "امکان لغو این انتشار وجود ندارد.", variant: "destructive" });
    } finally {
      setCancelingId(null);
    }
  };

  return (
    <div className="space-y-6">
      <div className="flex items-start justify-between gap-4">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">صف انتشار</h1>
          <p className="mt-1 text-muted-foreground">زمان، مقصد و رسانه‌ی هر انتشار زمان‌بندی‌شده را اینجا دنبال کنید.</p>
        </div>
        <Button variant="outline" size="sm" className="gap-2" onClick={() => void fetchJobs()} disabled={loading}>
          <RefreshCw className={`h-4 w-4 ${loading ? "animate-spin" : ""}`} /> به‌روزرسانی
        </Button>
      </div>

      {!loading && jobs.length > 0 && (
        <div className="grid gap-3 sm:grid-cols-2">
          <Card><CardContent className="p-4"><p className="text-xs text-muted-foreground">محتوای زمان‌بندی‌شده</p><p className="mt-1 text-2xl font-bold">{groupedCount.toLocaleString("fa-IR")}</p></CardContent></Card>
          <Card><CardContent className="p-4"><p className="text-xs text-muted-foreground">مقصدهای در صف</p><p className="mt-1 text-2xl font-bold">{jobs.length.toLocaleString("fa-IR")}</p></CardContent></Card>
        </div>
      )}

      {loading ? (
        <div className="space-y-3">{[1, 2, 3].map((item) => <Card key={item} className="h-32 animate-pulse" />)}</div>
      ) : jobs.length === 0 ? (
        <Card>
          <CardContent className="flex flex-col items-center justify-center gap-4 py-16 text-center">
            <CalendarClock className="h-12 w-12 text-muted-foreground/30" />
            <div>
              <p className="font-medium">صف انتشار خالی است</p>
              <p className="mt-1 text-sm text-muted-foreground">پس از زمان‌بندی محتوا، زمان و مقصد آن در این صفحه دیده می‌شود.</p>
            </div>
          </CardContent>
        </Card>
      ) : (
        <div className="space-y-3">
          {jobs.map((job) => {
            const effectiveDate = job.next_retry_at || job.scheduled_at;
            return (
              <Card key={job.id} className="overflow-hidden">
                <CardContent className="p-0">
                  <div className="flex flex-col gap-4 p-5 sm:flex-row sm:items-center">
                    <div className="flex min-w-0 flex-1 items-start gap-3">
                      <div className="mt-0.5 flex h-10 w-10 shrink-0 items-center justify-center rounded-full bg-amber-100">
                        <Clock className="h-5 w-5 text-amber-700" />
                      </div>
                      <div className="min-w-0 flex-1">
                        <p className="truncate font-medium">{job.content_title || "محتوای بدون عنوان"}</p>
                        <div className="mt-1 flex flex-wrap items-center gap-2 text-sm text-muted-foreground">
                          {getPlatformIcon(job.channel.platform)}
                          <span>{job.channel.name}</span>
                          <span className="text-muted-foreground/40">·</span>
                          {effectiveDate && <Countdown date={effectiveDate} />}
                        </div>
                        {effectiveDate && (
                          <p className="mt-1.5 text-xs text-muted-foreground">
                            {job.next_retry_at ? "تلاش بعدی: " : "زمان ارسال: "}{new Date(effectiveDate).toLocaleString("fa-IR")}
                          </p>
                        )}
                        {job.attachments?.length > 0 && (
                          <div className="mt-2 flex flex-wrap gap-1.5">
                            {job.attachments.map((attachment) => (
                              <Badge key={attachment.id} variant="secondary" className="max-w-48 gap-1 font-normal">
                                {getMediaIcon(attachment.media_type)}
                                <span className="truncate">{attachment.original_filename || "رسانه"}</span>
                              </Badge>
                            ))}
                          </div>
                        )}
                      </div>
                    </div>
                    <div className="flex shrink-0 items-center gap-2">
                      <Badge variant="outline" className="gap-1 border-amber-200 bg-amber-50 text-amber-700"><Clock className="h-3 w-3" /> در صف</Badge>
                      <Button variant="outline" size="sm" className="gap-1.5 border-destructive/30 text-destructive hover:bg-destructive/10 hover:text-destructive" onClick={() => void handleCancel(job.id)} disabled={cancelingId === job.id}>
                        {cancelingId === job.id ? <Loader2 className="h-4 w-4 animate-spin" /> : <XCircle className="h-4 w-4" />} لغو
                      </Button>
                    </div>
                  </div>
                </CardContent>
              </Card>
            );
          })}
        </div>
      )}
    </div>
  );
}
