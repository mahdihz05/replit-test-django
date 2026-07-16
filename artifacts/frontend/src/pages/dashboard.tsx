import { useEffect, useState } from "react";
import { useAuth } from "@/lib/auth";
import { apiFetch } from "@/lib/api";
import {
  Card, CardContent, CardDescription, CardHeader, CardTitle
} from "@/components/ui/card";
import {
  FileText, Send, Coins, Share2, Activity, Plus, Bot, AlertCircle,
  TrendingUp, CheckCircle2, XCircle, Clock
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Link } from "wouter";
import { useToast } from "@/hooks/use-toast";
import {
  ResponsiveContainer,
  PieChart, Pie, Cell, Tooltip, Legend,
  BarChart, Bar, XAxis, YAxis, CartesianGrid,
  LineChart, Line, Area, AreaChart
} from "recharts";

interface DashboardData {
  contents: {
    total: number;
    by_status: Record<string, number>;
    current_month: number;
    previous_month: number;
    change_percent: number | null;
  };
  publishes: {
    total: number;
    by_status: Record<string, number>;
    by_day: { date: string; count: number }[];
    today: number;
  };
  channels: {
    total: number;
    verified: number;
    by_platform: Record<string, number>;
  };
  wallet: {
    balance: number;
    total_spent: number;
    total_charged: number;
  };
  recent_errors: {
    error_type: string;
    user_message: string;
    attempted_at: string;
  }[];
}

const STATUS_COLORS: Record<string, string> = {
  draft: "#94a3b8",
  ready: "#3b82f6",
  scheduled: "#f59e0b",
  publishing: "#8b5cf6",
  published: "#10b981",
  failed: "#ef4444",
};

const PLATFORM_COLORS: Record<string, string> = {
  telegram: "#3b82f6",
  bale: "#10b981",
  website: "#8b5cf6",
};

const STATUS_NAMES: Record<string, string> = {
  draft: "پیش‌نویس",
  ready: "آماده",
  scheduled: "زمان‌بندی شده",
  publishing: "در حال انتشار",
  published: "منتشر شده",
  failed: "ناموفق",
};

const PLATFORM_NAMES: Record<string, string> = {
  telegram: "تلگرام",
  bale: "بله",
  website: "وب‌سایت",
};

function formatNumber(n: number) {
  return n.toLocaleString("fa-IR");
}

function toPersianDate(iso: string) {
  try {
    return new Date(iso).toLocaleDateString("fa-IR", {
      month: "short",
      day: "numeric",
    });
  } catch {
    return iso;
  }
}

export default function Dashboard() {
  const { selectedWorkspace } = useAuth();
  const { toast } = useToast();
  const [data, setData] = useState<DashboardData | null>(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (!selectedWorkspace) return;
    setLoading(true);
    apiFetch(`/workspaces/${selectedWorkspace.id}/dashboard/`)
      .then((res) => {
        if (res?.data) setData(res.data);
      })
      .catch(() => {
        toast({ title: "خطا", description: "دریافت اطلاعات داشبورد ناموفق بود", variant: "destructive" });
      })
      .finally(() => setLoading(false));
  }, [selectedWorkspace, toast]);

  if (!selectedWorkspace) {
    return <div className="p-8 text-center text-muted-foreground">فضای کاری انتخاب نشده است</div>;
  }

  const contentChartData = data
    ? Object.entries(data.contents.by_status).map(([status, count]) => ({
        name: STATUS_NAMES[status] || status,
        value: count,
        color: STATUS_COLORS[status] || "#94a3b8",
      }))
    : [];

  const channelChartData = data
    ? Object.entries(data.channels.by_platform).map(([platform, count]) => ({
        name: PLATFORM_NAMES[platform] || platform,
        value: count,
        color: PLATFORM_COLORS[platform] || "#8b5cf6",
      }))
    : [];

  const publishStatusData = data
    ? Object.entries(data.publishes.by_status).map(([status, count]) => ({
        name: status === "success" ? "موفق" : status === "failed" ? "ناموفق" : status,
        value: count,
        color: status === "success" ? "#10b981" : status === "failed" ? "#ef4444" : "#f59e0b",
      }))
    : [];

  const publishDayData = data?.publishes.by_day || [];

  const contentTrend = (() => {
    if (!data) return "در حال دریافت اطلاعات";
    const { current_month, previous_month, change_percent } = data.contents;
    if (change_percent === null) {
      return previous_month === 0 && current_month > 0
        ? `${formatNumber(current_month)} محتوا در ماه جاری`
        : "بدون تغییر نسبت به ماه قبل";
    }
    const direction = change_percent > 0 ? "افزایش" : change_percent < 0 ? "کاهش" : "بدون تغییر";
    if (change_percent === 0) return `${direction} نسبت به ماه قبل`;
    return `${formatNumber(Math.abs(change_percent))}٪ ${direction} نسبت به ماه قبل`;
  })();

  const statCards = [
    {
      title: "کل محتوا",
      value: data?.contents.total ?? 0,
      icon: FileText,
      trend: contentTrend,
      color: "text-blue-500",
    },
    {
      title: "منتشر شده امروز",
      value: data?.publishes.today ?? 0,
      icon: Send,
      trend: `${data?.publishes.total ?? 0} انتشار کل`,
      color: "text-emerald-500",
    },
    {
      title: "موجودی اعتبار (تومان)",
      value: formatNumber(data?.wallet.balance ?? 0),
      icon: Coins,
      trend: `${formatNumber(data?.wallet.total_spent ?? 0)} مصرف شده`,
      color: "text-amber-500",
    },
    {
      title: "کانال‌های فعال",
      value: data?.channels.total ?? 0,
      icon: Share2,
      trend: `${data?.channels.verified ?? 0} تایید شده`,
      color: "text-violet-500",
    },
  ];

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
        {statCards.map((card) => (
          <Card key={card.title}>
            <CardHeader className="flex flex-row items-center justify-between pb-2 space-y-0">
              <CardTitle className="text-sm font-medium">{card.title}</CardTitle>
              <card.icon className={`w-4 h-4 ${card.color}`} />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">{loading ? "..." : card.value}</div>
              <p className="text-xs text-muted-foreground mt-1">{card.trend}</p>
            </CardContent>
          </Card>
        ))}
      </div>

      <div className="grid gap-4 lg:grid-cols-3">
        <Card className="lg:col-span-2">
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <TrendingUp className="w-5 h-5 text-primary" />
              روند انتشار ۷ روز اخیر
            </CardTitle>
            <CardDescription>تعداد انتشارهای موفق در هر روز</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="h-72">
              <ResponsiveContainer width="100%" height="100%">
                <AreaChart data={publishDayData} margin={{ top: 10, right: 10, left: 0, bottom: 0 }}>
                  <defs>
                    <linearGradient id="colorPublishes" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="5%" stopColor="#3b82f6" stopOpacity={0.3} />
                      <stop offset="95%" stopColor="#3b82f6" stopOpacity={0} />
                    </linearGradient>
                  </defs>
                  <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#e2e8f0" />
                  <XAxis dataKey="date" tick={{ fontSize: 12 }} axisLine={false} tickLine={false} />
                  <YAxis tick={{ fontSize: 12 }} axisLine={false} tickLine={false} allowDecimals={false} />
                  <Tooltip
                    contentStyle={{ borderRadius: 8, border: "none", boxShadow: "0 4px 12px rgba(0,0,0,0.1)" }}
                    formatter={(value: number) => [formatNumber(value), "انتشار موفق"]}
                    labelStyle={{ color: "#64748b" }}
                  />
                  <Area
                    type="monotone"
                    dataKey="count"
                    stroke="#3b82f6"
                    strokeWidth={3}
                    fillOpacity={1}
                    fill="url(#colorPublishes)"
                  />
                </AreaChart>
              </ResponsiveContainer>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <FileText className="w-5 h-5 text-primary" />
              وضعیت محتوا
            </CardTitle>
            <CardDescription>توزیع محتوا بر اساس وضعیت</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="h-72">
              {contentChartData.length > 0 ? (
                <ResponsiveContainer width="100%" height="100%">
                  <PieChart>
                    <Pie
                      data={contentChartData}
                      cx="50%"
                      cy="50%"
                      innerRadius={60}
                      outerRadius={90}
                      paddingAngle={3}
                      dataKey="value"
                    >
                      {contentChartData.map((entry, index) => (
                        <Cell key={`cell-${index}`} fill={entry.color} />
                      ))}
                    </Pie>
                    <Tooltip
                      contentStyle={{ borderRadius: 8, border: "none", boxShadow: "0 4px 12px rgba(0,0,0,0.1)" }}
                      formatter={(value: number, name: string) => [formatNumber(value), name]}
                    />
                    <Legend
                      verticalAlign="bottom"
                      height={36}
                      iconType="circle"
                      formatter={(value: string) => <span className="text-xs">{value}</span>}
                    />
                  </PieChart>
                </ResponsiveContainer>
              ) : (
                <div className="h-full flex flex-col items-center justify-center text-muted-foreground gap-2">
                  <FileText className="w-10 h-10 opacity-30" />
                  <p className="text-sm">محتوایی ثبت نشده است</p>
                </div>
              )}
            </div>
          </CardContent>
        </Card>
      </div>

      <div className="grid gap-4 lg:grid-cols-3">
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Share2 className="w-5 h-5 text-primary" />
              کانال‌ها بر اساس پلتفرم
            </CardTitle>
            <CardDescription>تعداد کانال‌های فعال در هر پلتفرم</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="h-64">
              {channelChartData.length > 0 ? (
                <ResponsiveContainer width="100%" height="100%">
                  <BarChart data={channelChartData} margin={{ top: 10, right: 10, left: 0, bottom: 0 }}>
                    <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#e2e8f0" />
                    <XAxis dataKey="name" tick={{ fontSize: 12 }} axisLine={false} tickLine={false} />
                    <YAxis tick={{ fontSize: 12 }} axisLine={false} tickLine={false} allowDecimals={false} />
                    <Tooltip
                      contentStyle={{ borderRadius: 8, border: "none", boxShadow: "0 4px 12px rgba(0,0,0,0.1)" }}
                      formatter={(value: number) => [formatNumber(value), "کانال"]}
                    />
                    <Bar dataKey="value" radius={[8, 8, 0, 0]}>
                      {channelChartData.map((entry, index) => (
                        <Cell key={`cell-${index}`} fill={entry.color} />
                      ))}
                    </Bar>
                  </BarChart>
                </ResponsiveContainer>
              ) : (
                <div className="h-full flex flex-col items-center justify-center text-muted-foreground gap-2">
                  <Share2 className="w-10 h-10 opacity-30" />
                  <p className="text-sm">کانالی ثبت نشده است</p>
                </div>
              )}
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Send className="w-5 h-5 text-primary" />
              وضعیت انتشار
            </CardTitle>
            <CardDescription>نسبت انتشارهای موفق و ناموفق</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="h-64">
              {publishStatusData.length > 0 ? (
                <ResponsiveContainer width="100%" height="100%">
                  <PieChart>
                    <Pie
                      data={publishStatusData}
                      cx="50%"
                      cy="50%"
                      outerRadius={90}
                      paddingAngle={3}
                      dataKey="value"
                    >
                      {publishStatusData.map((entry, index) => (
                        <Cell key={`cell-${index}`} fill={entry.color} />
                      ))}
                    </Pie>
                    <Tooltip
                      contentStyle={{ borderRadius: 8, border: "none", boxShadow: "0 4px 12px rgba(0,0,0,0.1)" }}
                      formatter={(value: number, name: string) => [formatNumber(value), name]}
                    />
                    <Legend
                      verticalAlign="bottom"
                      height={36}
                      iconType="circle"
                      formatter={(value: string) => <span className="text-xs">{value}</span>}
                    />
                  </PieChart>
                </ResponsiveContainer>
              ) : (
                <div className="h-full flex flex-col items-center justify-center text-muted-foreground gap-2">
                  <Send className="w-10 h-10 opacity-30" />
                  <p className="text-sm">انتشاری ثبت نشده است</p>
                </div>
              )}
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <AlertCircle className="w-5 h-5 text-primary" />
              خطاهای اخیر
            </CardTitle>
            <CardDescription>۵ خطای آخر در انتشار</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="space-y-4">
              {data?.recent_errors && data.recent_errors.length > 0 ? (
                data.recent_errors.map((err, i) => (
                  <div key={i} className="flex items-start gap-3 pb-4 border-b last:border-0 last:pb-0">
                    <div className="w-8 h-8 rounded-full bg-destructive/10 flex items-center justify-center shrink-0 mt-0.5">
                      <XCircle className="w-4 h-4 text-destructive" />
                    </div>
                    <div className="min-w-0">
                      <p className="text-sm font-medium truncate">{err.user_message || err.error_type}</p>
                      <p className="text-xs text-muted-foreground mt-1">{toPersianDate(err.attempted_at)}</p>
                    </div>
                  </div>
                ))
              ) : (
                <div className="h-48 flex flex-col items-center justify-center text-muted-foreground gap-2">
                  <CheckCircle2 className="w-10 h-10 text-emerald-500 opacity-60" />
                  <p className="text-sm">خطایی ثبت نشده است</p>
                </div>
              )}
            </div>
          </CardContent>
        </Card>
      </div>

      <div className="grid gap-4 md:grid-cols-2">
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Activity className="w-5 h-5 text-primary" />
              آخرین فعالیت‌ها
            </CardTitle>
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

        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Clock className="w-5 h-5 text-primary" />
              در صف انتشار
            </CardTitle>
            <CardDescription>محتواهای زمان‌بندی شده برای آینده</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="space-y-4">
              <div className="flex items-center justify-between border-b pb-4">
                <div>
                  <p className="font-medium text-sm">راهنمای استفاده از خدمات</p>
                  <p className="text-xs text-muted-foreground">تلگرام • فردا ۱۰:۰۰ صبح</p>
                </div>
                <Badge variant="secondary">زمان‌بندی شده</Badge>
              </div>
              <div className="flex items-center justify-between border-b pb-4">
                <div>
                  <p className="font-medium text-sm">اطلاعیه تخفیف نوروزی</p>
                  <p className="text-xs text-muted-foreground">بله، تلگرام • دوشنبه ۱۸:۰۰</p>
                </div>
                <Badge variant="secondary">زمان‌بندی شده</Badge>
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
