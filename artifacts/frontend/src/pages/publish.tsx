import { useState, useEffect } from "react";
import { useAuth } from "@/lib/auth";
import { Card, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Send, RefreshCcw, AlertCircle, Clock, CheckCircle2 } from "lucide-react";

export default function Publish() {
  const { selectedWorkspace } = useAuth();
  const [jobs, setJobs] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (selectedWorkspace) {
      setLoading(true);
      setTimeout(() => {
        setJobs([
          { id: "1", content_title: "معرفی محصول جدید", channel: { name: "کانال اصلی تلگرام", platform: "telegram" }, status: "queued", scheduled_at: new Date(Date.now() + 3600000).toISOString() },
          { id: "2", content_title: "اطلاعیه تخفیف", channel: { name: "وبلاگ سایت", platform: "website" }, status: "processing", scheduled_at: new Date().toISOString() },
          { id: "3", content_title: "تبریک سال نو", channel: { name: "گروه مشتریان بله", platform: "bale" }, status: "success", scheduled_at: new Date(Date.now() - 7200000).toISOString() },
          { id: "4", content_title: "نکات امنیتی", channel: { name: "کانال اصلی تلگرام", platform: "telegram" }, status: "failed", scheduled_at: new Date(Date.now() - 86400000).toISOString() }
        ]);
        setLoading(false);
      }, 500);
    }
  }, [selectedWorkspace]);

  const getStatusDisplay = (status: string) => {
    switch(status) {
      case "queued": return { label: "در صف", color: "bg-blue-100 text-blue-800", icon: <Clock className="w-4 h-4" /> };
      case "processing": return { label: "در حال پردازش", color: "bg-amber-100 text-amber-800", icon: <RefreshCcw className="w-4 h-4 animate-spin" /> };
      case "success": return { label: "موفق", color: "bg-green-100 text-green-800", icon: <CheckCircle2 className="w-4 h-4" /> };
      case "failed": return { label: "ناموفق", color: "bg-destructive/10 text-destructive", icon: <AlertCircle className="w-4 h-4" /> };
      default: return { label: status, color: "bg-muted text-muted-foreground", icon: null };
    }
  };

  return (
    <div className="space-y-6">
      <div className="flex justify-between items-center gap-4">
        <h1 className="text-3xl font-bold tracking-tight">صف انتشار</h1>
        <Button variant="outline" className="gap-2">
          <RefreshCcw className="w-4 h-4" /> بروزرسانی
        </Button>
      </div>

      <div className="grid gap-4">
        {loading ? (
          [1, 2, 3].map(i => <Card key={i} className="animate-pulse h-24"></Card>)
        ) : jobs.map(job => {
          const status = getStatusDisplay(job.status);
          return (
            <Card key={job.id}>
              <CardContent className="flex flex-col sm:flex-row items-start sm:items-center justify-between p-6 gap-4">
                <div className="space-y-1">
                  <h3 className="font-medium text-lg">{job.content_title}</h3>
                  <p className="text-sm text-muted-foreground flex items-center gap-1">
                    مقصد: {job.channel.name} 
                    <span className="opacity-50 mx-1">•</span> 
                    زمان: {new Date(job.scheduled_at).toLocaleString('fa-IR')}
                  </p>
                </div>
                <div className="flex items-center gap-4 w-full sm:w-auto justify-between sm:justify-end">
                  <Badge variant="outline" className={`gap-1.5 py-1 ${status.color} border-transparent`}>
                    {status.icon} {status.label}
                  </Badge>
                  {job.status === "failed" && (
                    <Button size="sm" variant="outline" className="text-destructive hover:bg-destructive/10">
                      تلاش مجدد
                    </Button>
                  )}
                </div>
              </CardContent>
            </Card>
          );
        })}
      </div>
    </div>
  );
}
