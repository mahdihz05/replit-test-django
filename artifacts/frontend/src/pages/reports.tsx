import { useEffect, useState } from "react";
import { useAuth } from "@/lib/auth";
import { apiFetch } from "@/lib/api";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import {
  FileText, Send, Coins, Share2, AlertCircle, Activity, CheckCircle2, XCircle,
  TrendingUp, Bot, Clock, BarChart3
} from "lucide-react";
import { useToast } from "@/hooks/use-toast";
import {
  ResponsiveContainer,
  PieChart, Pie, Cell, Tooltip, Legend,
  BarChart, Bar, XAxis, YAxis, CartesianGrid,
  Area, AreaChart, LineChart, Line
} from "recharts";

interface ReportsData {
  content: {
    total: number;
    by_status: Record<string, number>;
    by_month: { label: string; count: number }[];
    recent: { id: string; title: string; status: string; created_at: string }[];
  };
  publishing: {
    total: number;
    total_channels: number;
    by_status: Record<string, number>;
    by_channel: { channel__name: string; channel__platform: string; count: number }[];
    by_day: { date: string; count: number }[];
    by_platform: Record<string, number>;
  };
  ai: {
    total_spent: number;
    transaction_count: number;
    by_day: { date: string; amount: number }[];
  };
  errors: {
    total_errors: number;
    by_type: Record<string, number>;
    by_day: { date: string; count: number }[];
    recent: { error_type: string; user_message: string; attempted_at: string }[];
  };
}

const STATUS_COLORS: Record<string, string> = {
  draft: "#94a3b8",
  ready: "#3b82f6",
  scheduled: "#f59e0b",
  publishing: "#8b5cf6",
  published: "#10b981",
  failed: "#ef4444",
};

const PUBLISH_STATUS_COLORS: Record<string, string> = {
  queued: "#94a3b8",
  processing: "#3b82f6",
  success: "#10b981",
  failed: "#ef4444",
};

const PLATFORM_COLORS: Record<string, string> = {
  telegram: "#3b82f6",
  bale: "#10b981",
  website: "#8b5cf6",
  linkedin: "#0a66c2",
  wordpress: "#21759b",
};

const STATUS_NAMES: Record<string, string> = {
  draft: "پیش‌نویس",
  ready: "آماده",
  scheduled: "زمان‌بندی شده",
  publishing: "در حال انتشار",
  published: "منتشر شده",
  failed: "ناموفق",
};

const PUBLISH_STATUS_NAMES: Record<string, string> = {
  queued: "در صف",
  processing: "در حال پردازش",
  success: "موفق",
  failed: "ناموفق",
};

const PLATFORM_NAMES: Record<string, string> = {
  telegram: "تلگرام",
  bale: "بله",
  website: "وب‌سایت",
  linkedin: "LinkedIn",
  wordpress: "WordPress",
};

const ERROR_NAMES: Record<string, string> = {
  connection_error: "خطای اتصال",
  auth_error: "خطای احراز هویت",
  bot_removed: "ربات حذف شده",
  rate_limit: "محدودیت نرخ",
  unknown: "ناشناخته",
};

function ChartSkeleton({ height = "h-72" }: { height?: string }) {
  return (
    <div className={`w-full ${height} flex items-center justify-center`}>
      <div className="animate-pulse flex flex-col items-center gap-3">
        <div className="w-10 h-10 rounded-full bg-muted" />
        <div className="h-2 w-24 bg-muted rounded" />
      </div>
    </div>
  );
}

function formatNumber(n: number) {
  return n.toLocaleString("fa-IR");
}

function formatCurrency(n: number) {
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

export default function Reports() {
  const { selectedWorkspace } = useAuth();
  const { toast } = useToast();
  const [data, setData] = useState<ReportsData | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!selectedWorkspace) return;
    setLoading(true);
    Promise.all([
      apiFetch(`/workspaces/${selectedWorkspace.id}/reports/content/`),
      apiFetch(`/workspaces/${selectedWorkspace.id}/reports/publishing/`),
      apiFetch(`/workspaces/${selectedWorkspace.id}/reports/ai-usage/`),
      apiFetch(`/workspaces/${selectedWorkspace.id}/reports/errors/`),
    ])
      .then(([contentRes, pubRes, aiRes, errRes]) => {
        setData({
          content: contentRes?.data,
          publishing: pubRes?.data,
          ai: aiRes?.data,
          errors: errRes?.data,
        });
      })
      .catch(() => {
        toast({ title: "خطا", description: "دریافت گزارش‌ها ناموفق بود", variant: "destructive" });
      })
      .finally(() => setLoading(false));
  }, [selectedWorkspace, toast]);

  if (!selectedWorkspace) {
    return <div className="p-8 text-center text-muted-foreground">فضای کاری انتخاب نشده است</div>;
  }

  const contentStatusData = data
    ? Object.entries(data.content.by_status).map(([status, count]) => ({
        name: STATUS_NAMES[status] || status,
        value: count,
        color: STATUS_COLORS[status] || "#94a3b8",
      }))
    : [];

  const publishingStatusData = data
    ? Object.entries(data.publishing.by_status).map(([status, count]) => ({
        name: PUBLISH_STATUS_NAMES[status] || status,
        value: count,
        color: PUBLISH_STATUS_COLORS[status] || "#94a3b8",
      }))
    : [];

  const channelChartData = data
    ? Object.entries(data.publishing.by_platform).map(([platform, count]) => ({
        name: PLATFORM_NAMES[platform] || platform,
        value: count,
        color: PLATFORM_COLORS[platform] || "#8b5cf6",
      }))
    : [];

  const errorTypeData = data
    ? Object.entries(data.errors.by_type).map(([type, count]) => ({
        name: ERROR_NAMES[type] || type,
        value: count,
      }))
    : [];

  const errorColors = ["#ef4444", "#f97316", "#f59e0b", "#8b5cf6", "#64748b"];

  const statCards = [
    {
      title: "کل محتوا",
      value: data?.content.total ?? 0,
      icon: FileText,
      color: "text-blue-500",
    },
    {
      title: "کل انتشارات",
      value: data?.publishing.total ?? 0,
      icon: Send,
      color: "text-emerald-500",
    },
    {
      title: "مصرف AI (تومان)",
      value: formatCurrency(data?.ai.total_spent ?? 0),
      icon: Coins,
      color: "text-amber-500",
    },
    {
      title: "خطاهای انتشار",
      value: data?.errors.total_errors ?? 0,
      icon: AlertCircle,
      color: "text-rose-500",
    },
  ];

  return (
    <div className="space-y-8 animate-in fade-in duration-500">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">گزارش‌ها و آمار</h1>
          <p className="text-muted-foreground mt-1">تحلیل جامع فضای کاری {selectedWorkspace.name}</p>
        </div>
      </div>

      {/* Stat Cards */}
      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
        {statCards.map((card) => (
          <Card key={card.title}>
            <CardHeader className="flex flex-row items-center justify-between pb-2 space-y-0">
              <CardTitle className="text-sm font-medium">{card.title}</CardTitle>
              <card.icon className={`w-4 h-4 ${card.color}`} />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">{loading ? "..." : card.value}</div>
            </CardContent>
          </Card>
        ))}
      </div>

      {/* Row 1: Content status + 6-month production */}
      <div className="grid gap-4 lg:grid-cols-3">
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <FileText className="w-5 h-5 text-primary" />
              وضعیت محتواها
            </CardTitle>
            <CardDescription>توزیع محتوا بر اساس وضعیت</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="h-72">
              {loading ? (
                <ChartSkeleton height="h-72" />
              ) : contentStatusData.length > 0 ? (
                <ResponsiveContainer width="100%" height="100%">
                  <PieChart>
                    <Pie
                      data={contentStatusData}
                      cx="50%"
                      cy="50%"
                      innerRadius={60}
                      outerRadius={90}
                      paddingAngle={3}
                      dataKey="value"
                    >
                      {contentStatusData.map((entry, index) => (
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

        <Card className="lg:col-span-2">
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <BarChart3 className="w-5 h-5 text-primary" />
              تولید محتوا در ۶ ماه گذشته
            </CardTitle>
            <CardDescription>تعداد محتواهای تولید شده در هر ماه</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="h-72">
              {loading ? (
                <ChartSkeleton height="h-72" />
              ) : data?.content.by_month && data.content.by_month.some(m => m.count > 0) ? (
                <ResponsiveContainer width="100%" height="100%">
                  <BarChart data={data.content.by_month} margin={{ top: 10, right: 10, left: 0, bottom: 0 }}>
                    <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#e2e8f0" />
                    <XAxis dataKey="label" tick={{ fontSize: 12 }} axisLine={false} tickLine={false} />
                    <YAxis tick={{ fontSize: 12 }} axisLine={false} tickLine={false} allowDecimals={false} />
                    <Tooltip
                      contentStyle={{ borderRadius: 8, border: "none", boxShadow: "0 4px 12px rgba(0,0,0,0.1)" }}
                      formatter={(value: number) => [formatNumber(value), "محتوا"]}
                    />
                    <Bar dataKey="count" fill="#3b82f6" radius={[8, 8, 0, 0]} />
                  </BarChart>
                </ResponsiveContainer>
              ) : (
                <div className="h-full flex flex-col items-center justify-center text-muted-foreground gap-2">
                  <BarChart3 className="w-10 h-10 opacity-30" />
                  <p className="text-sm">داده‌ای برای نمایش وجود ندارد</p>
                </div>
              )}
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Row 2: 30-day publish trend + publish status */}
      <div className="grid gap-4 lg:grid-cols-3">
        <Card className="lg:col-span-2">
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <TrendingUp className="w-5 h-5 text-primary" />
              روند انتشار ۳۰ روز اخیر
            </CardTitle>
            <CardDescription>تعداد انتشارهای موفق در ۳۰ روز گذشته</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="h-72">
              {loading ? (
                <ChartSkeleton height="h-72" />
              ) : data?.publishing.by_day && data.publishing.by_day.some(d => d.count > 0) ? (
                <ResponsiveContainer width="100%" height="100%">
                  <AreaChart data={data.publishing.by_day} margin={{ top: 10, right: 10, left: 0, bottom: 0 }}>
                    <defs>
                      <linearGradient id="colorPubTrend" x1="0" y1="0" x2="0" y2="1">
                        <stop offset="5%" stopColor="#10b981" stopOpacity={0.3} />
                        <stop offset="95%" stopColor="#10b981" stopOpacity={0} />
                      </linearGradient>
                    </defs>
                    <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#e2e8f0" />
                    <XAxis dataKey="date" tick={{ fontSize: 12 }} axisLine={false} tickLine={false} />
                    <YAxis tick={{ fontSize: 12 }} axisLine={false} tickLine={false} allowDecimals={false} />
                    <Tooltip
                      contentStyle={{ borderRadius: 8, border: "none", boxShadow: "0 4px 12px rgba(0,0,0,0.1)" }}
                      formatter={(value: number) => [formatNumber(value), "انتشار موفق"]}
                    />
                    <Area
                      type="monotone"
                      dataKey="count"
                      stroke="#10b981"
                      strokeWidth={3}
                      fillOpacity={1}
                      fill="url(#colorPubTrend)"
                    />
                  </AreaChart>
                </ResponsiveContainer>
              ) : (
                <div className="h-full flex flex-col items-center justify-center text-muted-foreground gap-2">
                  <TrendingUp className="w-10 h-10 opacity-30" />
                  <p className="text-sm">انتشاری در این بازه ثبت نشده است</p>
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
            <CardDescription>توزیع وضعیت‌های انتشار</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="h-72">
              {loading ? (
                <ChartSkeleton height="h-72" />
              ) : publishingStatusData.length > 0 ? (
                <ResponsiveContainer width="100%" height="100%">
                  <PieChart>
                    <Pie
                      data={publishingStatusData}
                      cx="50%"
                      cy="50%"
                      outerRadius={90}
                      paddingAngle={3}
                      dataKey="value"
                    >
                      {publishingStatusData.map((entry, index) => (
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
      </div>

      {/* Row 3: Channels by platform + AI usage + error types */}
      <div className="grid gap-4 lg:grid-cols-3">
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Share2 className="w-5 h-5 text-primary" />
              کانال‌ها بر اساس پلتفرم
            </CardTitle>
            <CardDescription>تعداد انتشار در هر پلتفرم</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="h-64">
              {loading ? (
                <ChartSkeleton height="h-64" />
              ) : channelChartData.length > 0 ? (
                <ResponsiveContainer width="100%" height="100%">
                  <BarChart data={channelChartData} margin={{ top: 10, right: 10, left: 0, bottom: 0 }}>
                    <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#e2e8f0" />
                    <XAxis dataKey="name" tick={{ fontSize: 12 }} axisLine={false} tickLine={false} />
                    <YAxis tick={{ fontSize: 12 }} axisLine={false} tickLine={false} allowDecimals={false} />
                    <Tooltip
                      contentStyle={{ borderRadius: 8, border: "none", boxShadow: "0 4px 12px rgba(0,0,0,0.1)" }}
                      formatter={(value: number) => [formatNumber(value), "انتشار"]}
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
              <Coins className="w-5 h-5 text-primary" />
              مصرف هوش مصنوعی
            </CardTitle>
            <CardDescription>تعداد تراکنش: {formatNumber(data?.ai.transaction_count ?? 0)}</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="h-64">
              {loading ? (
                <ChartSkeleton height="h-64" />
              ) : data?.ai.by_day && data.ai.by_day.some(d => d.amount > 0) ? (
                <ResponsiveContainer width="100%" height="100%">
                  <LineChart data={data.ai.by_day} margin={{ top: 10, right: 10, left: 0, bottom: 0 }}>
                    <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#e2e8f0" />
                    <XAxis dataKey="date" tick={{ fontSize: 12 }} axisLine={false} tickLine={false} />
                    <YAxis tick={{ fontSize: 12 }} axisLine={false} tickLine={false} />
                    <Tooltip
                      contentStyle={{ borderRadius: 8, border: "none", boxShadow: "0 4px 12px rgba(0,0,0,0.1)" }}
                      formatter={(value: number) => [formatCurrency(value), "تومان"]}
                    />
                    <Line type="monotone" dataKey="amount" stroke="#f59e0b" strokeWidth={3} dot={false} />
                  </LineChart>
                </ResponsiveContainer>
              ) : (
                <div className="h-full flex flex-col items-center justify-center text-muted-foreground gap-2">
                  <Coins className="w-10 h-10 opacity-30" />
                  <p className="text-sm">مصرفی ثبت نشده است</p>
                </div>
              )}
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <AlertCircle className="w-5 h-5 text-primary" />
              انواع خطا
            </CardTitle>
            <CardDescription>توزیع خطاها بر اساس نوع</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="h-64">
              {loading ? (
                <ChartSkeleton height="h-64" />
              ) : errorTypeData.length > 0 ? (
                <ResponsiveContainer width="100%" height="100%">
                  <PieChart>
                    <Pie
                      data={errorTypeData}
                      cx="50%"
                      cy="50%"
                      outerRadius={80}
                      paddingAngle={3}
                      dataKey="value"
                    >
                      {errorTypeData.map((entry, index) => (
                        <Cell key={`cell-${index}`} fill={errorColors[index % errorColors.length]} />
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
                  <CheckCircle2 className="w-10 h-10 text-emerald-500 opacity-60" />
                  <p className="text-sm">خطایی ثبت نشده است</p>
                </div>
              )}
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Row 4: Recent errors + recent content */}
      <div className="grid gap-4 md:grid-cols-2">
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <XCircle className="w-5 h-5 text-primary" />
              خطاهای اخیر
            </CardTitle>
            <CardDescription>۱۰ خطای آخر در انتشار</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="space-y-4">
              {data?.errors.recent && data.errors.recent.length > 0 ? (
                data.errors.recent.map((err, i) => (
                  <div key={i} className="flex items-start gap-3 pb-4 border-b last:border-0 last:pb-0">
                    <div className="w-8 h-8 rounded-full bg-destructive/10 flex items-center justify-center shrink-0 mt-0.5">
                      <XCircle className="w-4 h-4 text-destructive" />
                    </div>
                    <div className="min-w-0">
                      <p className="text-sm font-medium truncate">{err.user_message || ERROR_NAMES[err.error_type] || err.error_type}</p>
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

        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Activity className="w-5 h-5 text-primary" />
              آخرین محتواها
            </CardTitle>
            <CardDescription>۵ محتوای اخیر</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="space-y-4">
              {data?.content.recent && data.content.recent.length > 0 ? (
                data.content.recent.map((c) => (
                  <div key={c.id} className="flex items-start gap-3 pb-4 border-b last:border-0 last:pb-0">
                    <div className="w-8 h-8 rounded-full bg-primary/10 flex items-center justify-center shrink-0 mt-0.5">
                      <FileText className="w-4 h-4 text-primary" />
                    </div>
                    <div className="min-w-0 flex-1">
                      <p className="text-sm font-medium truncate">{c.title}</p>
                      <div className="flex items-center gap-2 mt-1">
                        <Badge variant="outline" className="text-xs">
                          {STATUS_NAMES[c.status] || c.status}
                        </Badge>
                        <span className="text-xs text-muted-foreground">{toPersianDate(c.created_at)}</span>
                      </div>
                    </div>
                  </div>
                ))
              ) : (
                <div className="h-48 flex flex-col items-center justify-center text-muted-foreground gap-2">
                  <FileText className="w-10 h-10 opacity-30" />
                  <p className="text-sm">محتوایی ثبت نشده است</p>
                </div>
              )}
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
