import { useEffect, useState } from "react";
import { useRoute, Link } from "wouter";
import { useAuth } from "@/lib/auth";
import { apiFetch } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { ArrowRight, History, Edit, Send } from "lucide-react";
import { Badge } from "@/components/ui/badge";

export default function ContentDetail() {
  const [, params] = useRoute("/contents/:id");
  const { selectedWorkspace } = useAuth();
  const [content, setContent] = useState<any>(null);
  const [versions, setVersions] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (selectedWorkspace && params?.id) {
      // Mock data for detail
      setTimeout(() => {
        setContent({
          id: params.id,
          title: "پست وبلاگ هوش مصنوعی",
          body: "این یک محتوای نمونه درباره کاربردهای هوش مصنوعی در کسب و کارهای نوین است. استفاده از AI می‌تواند فرآیندهای بازاریابی را تا ۵۰٪ تسریع کند.",
          status: "ready",
          created_at: new Date().toISOString()
        });
        setVersions([
          { id: 1, version_number: 2, created_at: new Date().toISOString(), source: "user" },
          { id: 2, version_number: 1, created_at: new Date(Date.now() - 3600000).toISOString(), source: "ai" }
        ]);
        setLoading(false);
      }, 500);
    }
  }, [selectedWorkspace, params?.id]);

  if (loading) return <div className="animate-pulse p-8">در حال بارگذاری...</div>;
  if (!content) return <div>محتوا یافت نشد.</div>;

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
            <Badge variant="outline" className="bg-blue-100 text-blue-800 border-blue-200">
              آماده انتشار
            </Badge>
          </div>
          <p className="text-sm text-muted-foreground mt-1">
            آخرین ویرایش: {new Date(content.created_at).toLocaleDateString('fa-IR')}
          </p>
        </div>
        <div className="mr-auto flex gap-2">
          <Link href={`/contents/${content.id}/edit`}>
            <Button variant="outline" className="gap-2">
              <Edit className="w-4 h-4" /> ویرایش
            </Button>
          </Link>
          <Button className="gap-2">
            <Send className="w-4 h-4" /> انتشار
          </Button>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-4 gap-6">
        <div className="lg:col-span-3 space-y-6">
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
                {versions.map(v => (
                  <div key={v.id} className="relative">
                    <div className="absolute -right-[21px] w-3 h-3 rounded-full bg-primary ring-4 ring-background" />
                    <p className="font-medium text-sm">نسخه {v.version_number}</p>
                    <p className="text-xs text-muted-foreground mt-1 flex items-center gap-1">
                      {v.source === "ai" ? "تولید توسط AI" : "ویرایش دستی"} • {new Date(v.created_at).toLocaleTimeString('fa-IR')}
                    </p>
                  </div>
                ))}
              </div>
            </CardContent>
          </Card>
        </div>
      </div>
    </div>
  );
}
