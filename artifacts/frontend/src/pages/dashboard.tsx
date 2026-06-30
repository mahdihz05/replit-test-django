import { useEffect, useState } from "react";
import { useAuth } from "@/lib/auth";
import { apiFetch } from "@/lib/api";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { FileText, Send, Coins, Share2, Activity, Plus, Bot } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Link } from "wouter";

export default function Dashboard() {
  const { selectedWorkspace } = useAuth();
  const [stats, setStats] = useState({
    totalContent: 0,
    publishedToday: 0,
    aiCredits: 0,
    activeChannels: 0,
  });
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (selectedWorkspace) {
      // Mock loading stats
      setLoading(true);
      setTimeout(() => {
        setStats({
          totalContent: 124,
          publishedToday: 5,
          aiCredits: 45000,
          activeChannels: 3
        });
        setLoading(false);
      }, 500);
    }
  }, [selectedWorkspace]);

  if (!selectedWorkspace) {
    return <div className="p-8 text-center text-muted-foreground">فضای کاری انتخاب نشده است</div>;
  }

  return (
    <div className="space-y-8 animate-in fade-in duration-500">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">سلام! 👋</h1>
          <p className="text-muted-foreground mt-1">نمای کلی فضای کاری {selectedWorkspace.name}</p>
        </div>
        <div className="flex items-center gap-2">
          <Link href="/ai">
            <Button variant="outline" className="gap-2 border-primary/20 text-primary hover:bg-primary/10">
              <Bot className="w-4 h-4" />
              دستیار هوشمند
            </Button>
          </Link>
          <Link href="/contents/new">
            <Button className="gap-2">
              <Plus className="w-4 h-4" />
              محتوای جدید
            </Button>
          </Link>
        </div>
      </div>

      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
        <Card>
          <CardHeader className="flex flex-row items-center justify-between pb-2 space-y-0">
            <CardTitle className="text-sm font-medium">کل محتوا</CardTitle>
            <FileText className="w-4 h-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{loading ? "..." : stats.totalContent}</div>
            <p className="text-xs text-muted-foreground mt-1">+۱۲٪ نسبت به ماه قبل</p>
          </CardContent>
        </Card>
        
        <Card>
          <CardHeader className="flex flex-row items-center justify-between pb-2 space-y-0">
            <CardTitle className="text-sm font-medium">منتشر شده امروز</CardTitle>
            <Send className="w-4 h-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{loading ? "..." : stats.publishedToday}</div>
            <p className="text-xs text-muted-foreground mt-1">۲ در صف انتشار</p>
          </CardContent>
        </Card>
        
        <Card>
          <CardHeader className="flex flex-row items-center justify-between pb-2 space-y-0">
            <CardTitle className="text-sm font-medium">موجودی هوش مصنوعی (کلمه)</CardTitle>
            <Coins className="w-4 h-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{loading ? "..." : stats.aiCredits.toLocaleString('fa-IR')}</div>
            <p className="text-xs text-muted-foreground mt-1">بسته پایه</p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between pb-2 space-y-0">
            <CardTitle className="text-sm font-medium">کانال‌های فعال</CardTitle>
            <Share2 className="w-4 h-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{loading ? "..." : stats.activeChannels}</div>
            <p className="text-xs text-muted-foreground mt-1">تلگرام، بله، وب‌سایت</p>
          </CardContent>
        </Card>
      </div>

      <div className="grid gap-4 md:grid-cols-2">
        <Card className="col-span-1">
          <CardHeader>
            <CardTitle>آخرین فعالیت‌ها</CardTitle>
            <CardDescription>اتفاقات اخیر در این فضای کاری</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="space-y-4">
              {[1, 2, 3, 4].map((i) => (
                <div key={i} className="flex items-start gap-4 pb-4 border-b last:border-0 last:pb-0">
                  <div className="w-8 h-8 rounded-full bg-primary/10 flex items-center justify-center shrink-0 mt-0.5">
                    <Activity className="w-4 h-4 text-primary" />
                  </div>
                  <div>
                    <p className="text-sm font-medium">محتوای "معرفی محصول جدید" منتشر شد</p>
                    <p className="text-xs text-muted-foreground mt-1">توسط ادمین • ۲ ساعت پیش</p>
                  </div>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>

        <Card className="col-span-1">
          <CardHeader>
            <CardTitle>در صف انتشار</CardTitle>
            <CardDescription>محتواهای زمان‌بندی شده برای آینده</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="space-y-4">
              <div className="flex items-center justify-between border-b pb-4">
                <div>
                  <p className="font-medium text-sm">راهنمای استفاده از خدمات</p>
                  <p className="text-xs text-muted-foreground">تلگرام • فردا ۱۰:۰۰ صبح</p>
                </div>
                <div className="px-2 py-1 bg-amber-100 text-amber-800 rounded text-xs font-medium dark:bg-amber-900/30 dark:text-amber-400">
                  زمان‌بندی شده
                </div>
              </div>
              <div className="flex items-center justify-between border-b pb-4">
                <div>
                  <p className="font-medium text-sm">اطلاعیه تخفیف نوروزی</p>
                  <p className="text-xs text-muted-foreground">بله، تلگرام • دوشنبه ۱۸:۰۰</p>
                </div>
                <div className="px-2 py-1 bg-amber-100 text-amber-800 rounded text-xs font-medium dark:bg-amber-900/30 dark:text-amber-400">
                  زمان‌بندی شده
                </div>
              </div>
            </div>
            <Button variant="outline" className="w-full mt-4" asChild>
              <Link href="/publish">مشاهده همه</Link>
            </Button>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
