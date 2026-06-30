import { useState, useEffect } from "react";
import { useAuth } from "@/lib/auth";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip as RechartsTooltip, ResponsiveContainer, PieChart, Pie, Cell } from "recharts";

export default function Reports() {
  const { selectedWorkspace } = useAuth();
  const [loading, setLoading] = useState(false);

  const dataStatus = [
    { name: 'منتشر شده', value: 45, color: 'hsl(var(--chart-1))' },
    { name: 'آماده', value: 25, color: 'hsl(var(--chart-2))' },
    { name: 'پیش‌نویس', value: 20, color: 'hsl(var(--chart-3))' },
    { name: 'ناموفق', value: 10, color: 'hsl(var(--chart-5))' },
  ];

  const dataTimeline = [
    { name: 'فروردین', content: 12 },
    { name: 'اردیبهشت', content: 19 },
    { name: 'خرداد', content: 15 },
    { name: 'تیر', content: 22 },
    { name: 'مرداد', content: 30 },
    { name: 'شهریور', content: 28 },
  ];

  useEffect(() => {
    if (selectedWorkspace) {
      setTimeout(() => setLoading(false), 500);
    }
  }, [selectedWorkspace]);

  if (loading) return <div className="p-8">در حال بارگذاری گزارش‌ها...</div>;

  return (
    <div className="space-y-6">
      <h1 className="text-3xl font-bold tracking-tight">گزارش‌ها و آمار</h1>
      
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        <Card>
          <CardHeader>
            <CardTitle>وضعیت محتواها</CardTitle>
          </CardHeader>
          <CardContent className="h-80 flex items-center justify-center">
            <ResponsiveContainer width="100%" height="100%">
              <PieChart>
                <Pie
                  data={dataStatus}
                  cx="50%"
                  cy="50%"
                  innerRadius={60}
                  outerRadius={100}
                  paddingAngle={5}
                  dataKey="value"
                >
                  {dataStatus.map((entry, index) => (
                    <Cell key={`cell-${index}`} fill={entry.color} />
                  ))}
                </Pie>
                <RechartsTooltip formatter={(val: number) => [`${val} مورد`, "تعداد"]} />
              </PieChart>
            </ResponsiveContainer>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>تولید محتوا در ۶ ماه گذشته</CardTitle>
          </CardHeader>
          <CardContent className="h-80">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={dataTimeline} margin={{ top: 20, right: 0, left: -20, bottom: 0 }}>
                <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="hsl(var(--border))" />
                <XAxis dataKey="name" tick={{ fontSize: 12, fill: 'hsl(var(--muted-foreground))' }} tickLine={false} axisLine={false} />
                <YAxis tick={{ fontSize: 12, fill: 'hsl(var(--muted-foreground))' }} tickLine={false} axisLine={false} />
                <RechartsTooltip cursor={{fill: 'hsl(var(--muted)/0.5)'}} />
                <Bar dataKey="content" fill="hsl(var(--primary))" radius={[4, 4, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
