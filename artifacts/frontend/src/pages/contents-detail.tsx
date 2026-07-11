import { useEffect, useState } from "react";
import { useRoute, Link } from "wouter";
import { useAuth } from "@/lib/auth";
import { apiFetch } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { ArrowRight, History, Send, ImageIcon } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { useToast } from "@/hooks/use-toast";

export default function ContentDetail() {
  const [, params] = useRoute("/contents/:id");
  const { selectedWorkspace } = useAuth();
  const { toast } = useToast();
  const [content, setContent] = useState<any>(null);
  const [versions, setVersions] = useState<any[]>([]);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (!selectedWorkspace || !params?.id) return;
    setLoading(true);
    Promise.all([
      apiFetch(`/workspaces/${selectedWorkspace.id}/contents/${params.id}/`),
      apiFetch(`/workspaces/${selectedWorkspace.id}/contents/${params.id}/versions/`).catch(() => ({ data: [] }))
    ])
      .then(([contentRes, versionsRes]) => {
        setContent(contentRes?.data ?? contentRes);
        setVersions(versionsRes?.data ?? []);
      })
      .catch((err) => {
        toast({ title: "خطا", description: err.message || "خطا در بارگذاری محتوا", variant: "destructive" });
      })
      .finally(() => setLoading(false));
  }, [selectedWorkspace, params?.id]);

  if (loading) return <div className="animate-pulse p-8">در حال بارگذاری...</div>;
  if (!content) return <div>محتوا یافت نشد.</div>;

  const statusBadge = (status: string) => {
    switch (status) {
      case "draft": return <Badge variant="outline" className="bg-gray-100 text-gray-800">پیش‌نویس</Badge>;
      case "ready": return <Badge variant="outline" className="bg-blue-100 text-blue-800">آماده</Badge>;
      case "scheduled": return <Badge variant="outline" className="bg-amber-100 text-amber-800">زمان‌بندی شده</Badge>;
      case "published": return <Badge variant="outline" className="bg-green-100 text-green-800">منتشر شده</Badge>;
      case "failed": return <Badge variant="destructive">ناموفق</Badge>;
      default: return <Badge variant="outline">{status}</Badge>;
    }
  };

  return (
    <div className="space-y-6 max-w-6xl mx-auto">
      <div className="flex items-center gap-4">
        <Link href="/contents">
          <Button variant="ghost" size="icon" className="rounded-full">
            <ArrowRight className="w-5 h-5" />
          </Button>
        </Link>
        <div>
          <div className="flex items-center gap-3">
            <h1 className="text-2xl font-bold tracking-tight">{content.title}</h1>
            {statusBadge(content.status)}
          </div>
          <p className="text-sm text-muted-foreground mt-1">
            آخرین ویرایش: {new Date(content.updated_at || content.created_at).toLocaleDateString('fa-IR')}
          </p>
        </div>
        <div className="mr-auto flex gap-2">
          <Link href="/publish">
            <Button className="gap-2">
              <Send className="w-4 h-4" /> انتشار
            </Button>
          </Link>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-4 gap-6">
        <div className="lg:col-span-3 space-y-6">
          {content.image_url && (
            <Card>
              <CardContent className="p-4">
                <div className="flex items-center gap-2 text-sm text-muted-foreground mb-3">
                  <ImageIcon className="w-4 h-4" /> تصویر پیوست‌شده
                </div>
                <img
                  src={content.image_url}
                  alt="تصویر محتوا"
                  className="max-h-96 rounded-lg border shadow-sm object-contain"
                />
              </CardContent>
            </Card>
          )}
          <Card>
            <CardContent className="p-6">
              <div className="prose dark:prose-invert max-w-none font-sans text-base leading-loose whitespace-pre-wrap">
                {content.body}
              </div>
            </CardContent>
          </Card>
        </div>

        <div className="space-y-6">
          <Card>
            <CardHeader className="pb-3">
              <CardTitle className="text-base flex items-center gap-2">
                <History className="w-4 h-4" /> تاریخچه نسخه‌ها
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className="relative border-r border-muted pl-4 space-y-6 mt-2 mr-2">
                {versions.length === 0 ? (
                  <p className="text-sm text-muted-foreground">تاریخچه‌ای موجود نیست.</p>
                ) : (
                  versions.map((v: any) => (
                    <div key={v.id} className="relative">
                      <div className="absolute -right-[21px] w-3 h-3 rounded-full bg-primary ring-4 ring-background" />
                      <p className="font-medium text-sm">نسخه {v.version_number}</p>
                      <p className="text-xs text-muted-foreground mt-1 flex items-center gap-1">
                        {v.source === "ai" ? "تولید توسط AI" : "ویرایش دستی"} • {new Date(v.created_at).toLocaleTimeString('fa-IR')}
                      </p>
                    </div>
                  ))
                )}
              </div>
            </CardContent>
          </Card>
        </div>
      </div>
    </div>
  );
}
