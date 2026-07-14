import { useEffect, useMemo, useState } from "react";
import { useLocation } from "wouter";
import { useAuth } from "@/lib/auth";
import { apiFetch } from "@/lib/api";
import { useToast } from "@/hooks/use-toast";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { Label } from "@/components/ui/label";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Badge } from "@/components/ui/badge";
import { Checkbox } from "@/components/ui/checkbox";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import {
  Activity,
  ContactRound,
  Bot,
  CheckCircle2,
  ChevronLeft,
  ChevronRight,
  CircleAlert,
  FileSpreadsheet,
  Gauge,
  Loader2,
  Mail,
  Megaphone,
  MessageSquareText,
  Play,
  Plus,
  RefreshCw,
  Send,
  ServerCog,
  Trash2,
  Users,
  Wand2,
  XCircle,
  Pencil,
  CalendarClock,
} from "lucide-react";

type Provider = {
  id: string;
  type: "sms" | "email";
  provider_key: string;
  name: string;
  settings: Record<string, any>;
  status: string;
  last_test_status: string;
  last_test_error?: string;
};
type Contact = {
  id: string;
  name: string;
  phone: string;
  email: string;
  company: string;
  city: string;
  status: string;
};
type Group = {
  id: string;
  name: string;
  description: string;
  contact_count: number;
};
type Template = {
  id: string;
  channel: "sms" | "email";
  title: string;
  category: string;
  subject: string;
  body: string;
  body_type: string;
  variables: string[];
};
type Campaign = {
  id: string;
  name: string;
  channel: "sms" | "email";
  provider_name: string;
  status: string;
  recipients_count: number;
  valid_recipients_count: number;
  sent_count: number;
  failed_count: number;
  success_rate: number;
  created_at: string;
  scheduled_at?: string;
};
type MessageLog = {
  id: string;
  recipient_name: string;
  recipient_phone: string;
  recipient_email: string;
  rendered_subject: string;
  rendered_body: string;
  status: string;
  error_message: string;
  sent_at?: string;
  retry_count: number;
  is_test: boolean;
};

const EMPTY_DASHBOARD = {
  total_campaigns: 0,
  sms_campaigns: 0,
  email_campaigns: 0,
  total_contacts: 0,
  sent_messages: 0,
  failed_messages: 0,
  running_campaigns: 0,
  ai_generated_messages: 0,
  recent_campaigns: [] as Campaign[],
};
const STATUS_LABELS: Record<string, string> = {
  draft: "پیش‌نویس",
  scheduled: "زمان‌بندی‌شده",
  queued: "در صف",
  sending: "در حال ارسال",
  sent: "ارسال‌شده",
  delivered: "تحویل‌شده",
  failed: "ناموفق",
  cancelled: "لغوشده",
  skipped: "ردشده",
  connected: "متصل",
  not_tested: "تست‌نشده",
  disabled: "غیرفعال",
  active: "فعال",
};

function StatusBadge({ value }: { value: string }) {
  const good = ["sent", "delivered", "connected", "active"].includes(value);
  const bad = ["failed", "cancelled"].includes(value);
  return (
    <Badge variant={bad ? "destructive" : good ? "default" : "secondary"}>
      {STATUS_LABELS[value] || value}
    </Badge>
  );
}

export default function Communication() {
  const [location, setLocation] = useLocation();
  const { selectedWorkspace } = useAuth();
  const { toast } = useToast();
  const wid = selectedWorkspace?.id;
  const routeSection = location.split("/")[2];
  const sidebarSections = ["campaigns", "contacts", "templates", "providers"];
  const [tab, setTab] = useState(
    sidebarSections.includes(routeSection) ? routeSection : "dashboard",
  );
  const [loading, setLoading] = useState(true);
  const [dashboard, setDashboard] = useState(EMPTY_DASHBOARD);
  const [providers, setProviders] = useState<Provider[]>([]);
  const [contacts, setContacts] = useState<Contact[]>([]);
  const [groups, setGroups] = useState<Group[]>([]);
  const [templates, setTemplates] = useState<Template[]>([]);
  const [campaigns, setCampaigns] = useState<Campaign[]>([]);

  const loadAll = async () => {
    if (!wid) return;
    setLoading(true);
    try {
      const [dash, prov, con, grp, tmpl, camp] = await Promise.all([
        apiFetch(`/workspaces/${wid}/communication/dashboard/`),
        apiFetch(`/workspaces/${wid}/communication/providers/`),
        apiFetch(`/workspaces/${wid}/communication/contacts/`),
        apiFetch(`/workspaces/${wid}/communication/contact-groups/`),
        apiFetch(`/workspaces/${wid}/communication/templates/`),
        apiFetch(`/workspaces/${wid}/communication/campaigns/`),
      ]);
      setDashboard(dash.data);
      setProviders(prov.data);
      setContacts(con.data);
      setGroups(grp.data);
      setTemplates(tmpl.data);
      setCampaigns(camp.data);
    } catch (error: any) {
      toast({
        title: "خطا",
        description: error.message,
        variant: "destructive",
      });
    } finally {
      setLoading(false);
    }
  };
  useEffect(() => {
    loadAll();
  }, [wid]);
  useEffect(() => {
    if (sidebarSections.includes(routeSection)) setTab(routeSection);
    else if (location === "/communication") setTab("dashboard");
  }, [location, routeSection]);

  const openSection = (section: string) => {
    setTab(section);
    if (sidebarSections.includes(section)) {
      setLocation(`/communication/${section}`);
    } else if (section === "dashboard") {
      setLocation("/communication");
    }
  };

  if (!wid)
    return (
      <div className="p-8 text-center text-muted-foreground">
        ابتدا یک فضای کاری انتخاب کنید.
      </div>
    );
  if (loading)
    return (
      <div className="flex h-80 items-center justify-center">
        <Loader2 className="h-8 w-8 animate-spin text-primary" />
      </div>
    );

  return (
    <div className="mx-auto max-w-7xl space-y-6">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h1 className="flex items-center gap-2 text-3xl font-bold">
            <Megaphone className="h-7 w-7 text-primary" />
            AI Campaign Center
          </h1>
          <p className="mt-1 text-muted-foreground">
            ارسال پیامک و ایمیل، ساده و مرحله‌به‌مرحله
          </p>
        </div>
        <Button variant="outline" onClick={loadAll}>
          <RefreshCw className="ml-2 h-4 w-4" />
          به‌روزرسانی
        </Button>
      </div>
      <Tabs value={tab} onValueChange={openSection} dir="rtl">
        <TabsList className="h-auto w-full flex-wrap justify-start gap-1 bg-muted/60 p-1">
          <TabsTrigger value="dashboard">
            <Gauge className="ml-1 h-4 w-4" />
            داشبورد
          </TabsTrigger>
          <TabsTrigger value="reports">
            <Activity className="ml-1 h-4 w-4" />
            گزارش‌ها
          </TabsTrigger>
        </TabsList>
        <TabsContent value="dashboard">
          <DashboardView
            data={dashboard}
            onCreate={() => openSection("campaigns")}
          />
        </TabsContent>
        <TabsContent value="contacts">
          <ContactsView wid={wid} contacts={contacts} reload={loadAll} />
          <div className="mt-6 border-t pt-6">
            <div className="mb-4">
              <h2 className="text-xl font-semibold">گروه‌های مخاطبین</h2>
              <p className="text-sm text-muted-foreground">
                گروه‌ها برای انتخاب سریع مخاطبین در کمپین استفاده می‌شوند.
              </p>
            </div>
            <GroupsView
              wid={wid}
              groups={groups}
              contacts={contacts}
              reload={loadAll}
            />
          </div>
        </TabsContent>
        <TabsContent value="templates">
          <TemplatesView wid={wid} templates={templates} reload={loadAll} />
        </TabsContent>
        <TabsContent value="campaigns">
          <CampaignsCenterView
            wid={wid}
            providers={providers}
            contacts={contacts}
            groups={groups}
            templates={templates}
            campaigns={campaigns}
            reload={loadAll}
            onOpenContacts={() => openSection("contacts")}
            onOpenProviders={() => openSection("providers")}
          />
        </TabsContent>
        <TabsContent value="providers">
          <ProvidersView wid={wid} providers={providers} reload={loadAll} />
        </TabsContent>
        <TabsContent value="reports">
          <ReportsView wid={wid} campaigns={campaigns} />
        </TabsContent>
      </Tabs>
    </div>
  );
}

function DashboardView({
  data,
  onCreate,
}: {
  data: typeof EMPTY_DASHBOARD;
  onCreate: () => void;
}) {
  const cards = [
    ["کل کمپین‌ها", data.total_campaigns, Megaphone],
    ["مخاطبین", data.total_contacts, Users],
    ["پیام‌های ارسال‌شده", data.sent_messages, CheckCircle2],
    ["در حال اجرا", data.running_campaigns, Activity],
  ] as const;
  return (
    <div className="space-y-6 pt-4">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h2 className="text-xl font-semibold">نمای کلی</h2>
          <p className="text-sm text-muted-foreground">
            مهم‌ترین وضعیت‌های ارسال در یک نگاه
          </p>
        </div>
        <Button onClick={onCreate}>
          <Plus className="ml-2 h-4 w-4" />
          ساخت کمپین
        </Button>
      </div>
      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        {cards.map(([title, value, Icon]) => (
          <Card key={title}>
            <CardContent className="flex items-center justify-between p-5">
              <div>
                <p className="text-sm text-muted-foreground">{title}</p>
                <p className="mt-1 text-2xl font-bold">
                  {value.toLocaleString("fa-IR")}
                </p>
              </div>
              <Icon className="h-8 w-8 text-primary/70" />
            </CardContent>
          </Card>
        ))}
      </div>
      <Card>
        <CardHeader>
          <CardTitle>آخرین کمپین‌ها</CardTitle>
        </CardHeader>
        <CardContent>
          <CampaignTable campaigns={data.recent_campaigns} />
        </CardContent>
      </Card>
    </div>
  );
}

function ProvidersView({
  wid,
  providers,
  reload,
}: {
  wid: string;
  providers: Provider[];
  reload: () => void;
}) {
  const { toast } = useToast();
  const [key, setKey] = useState("gmail_smtp");
  const [name, setName] = useState("");
  const [apiKey, setApiKey] = useState("");
  const [host, setHost] = useState("smtp.gmail.com");
  const [port, setPort] = useState("587");
  const [encryption, setEncryption] = useState("tls");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [fromName, setFromName] = useState("");
  const [sender, setSender] = useState("");
  const [busy, setBusy] = useState(false);
  const [editingId, setEditingId] = useState("");
  const isSms = key === "kavenegar";
  const isGmail = key === "gmail_smtp";
  const save = async () => {
    setBusy(true);
    try {
      const credentials = isSms
        ? apiKey
          ? { api_key: apiKey }
          : undefined
        : password
          ? { username: email, password }
          : undefined;
      const response = await apiFetch(
        editingId
          ? `/workspaces/${wid}/communication/providers/${editingId}/`
          : `/workspaces/${wid}/communication/providers/`,
        {
          method: editingId ? "PATCH" : "POST",
          data: {
            type: isSms ? "sms" : "email",
            provider_key: key,
            name:
              name ||
              (isSms
                ? "کاوه‌نگار"
                : isGmail
                  ? `Gmail - ${email}`
                  : "SMTP اختصاصی"),
            ...(credentials ? { credentials } : {}),
            settings: isSms
              ? { sender }
              : {
                  host,
                  port: Number(port),
                  encryption,
                  email,
                  from_email: email,
                  from_name: fromName,
                },
          },
        },
      );
      if (isGmail) {
        try {
          await apiFetch(
            `/workspaces/${wid}/communication/providers/${response.data.id}/test/`,
            { method: "POST" },
          );
          toast({ title: "Gmail متصل شد و آماده ارسال است" });
        } catch (testError: any) {
          toast({
            title: "Gmail ذخیره شد ولی اتصال تأیید نشد",
            description: testError.message,
            variant: "destructive",
          });
        }
      } else {
        toast({ title: "سرویس ارسال ذخیره شد" });
      }
      setName("");
      setApiKey("");
      setPassword("");
      setEditingId("");
      reload();
    } catch (e: any) {
      toast({ title: "خطا", description: e.message, variant: "destructive" });
    } finally {
      setBusy(false);
    }
  };
  const test = async (id: string) => {
    try {
      await apiFetch(`/workspaces/${wid}/communication/providers/${id}/test/`, {
        method: "POST",
      });
      toast({ title: "اتصال موفق بود" });
      reload();
    } catch (e: any) {
      toast({
        title: "تست ناموفق",
        description: e.message,
        variant: "destructive",
      });
      reload();
    }
  };
  const remove = async (id: string) => {
    await apiFetch(`/workspaces/${wid}/communication/providers/${id}/`, {
      method: "DELETE",
    });
    reload();
  };
  const toggle = async (provider: Provider) => {
    try {
      await apiFetch(
        `/workspaces/${wid}/communication/providers/${provider.id}/`,
        {
          method: "PATCH",
          data: {
            status: provider.status === "active" ? "disabled" : "active",
          },
        },
      );
      toast({
        title:
          provider.status === "active" ? "سرویس غیرفعال شد" : "سرویس فعال شد",
      });
      reload();
    } catch (e: any) {
      toast({
        title: "تغییر وضعیت ناموفق بود",
        description: e.message,
        variant: "destructive",
      });
    }
  };
  const edit = (provider: Provider) => {
    setEditingId(provider.id);
    setKey(provider.provider_key);
    setName(provider.name);
    setHost(provider.settings?.host || "smtp.gmail.com");
    setPort(String(provider.settings?.port || 587));
    setEncryption(provider.settings?.encryption || "tls");
    setEmail(provider.settings?.email || provider.settings?.from_email || "");
    setFromName(provider.settings?.from_name || "");
    setSender(provider.settings?.sender || "");
    setApiKey("");
    setPassword("");
  };
  return (
    <div className="grid gap-6 pt-4 lg:grid-cols-[380px_1fr]">
      <Card>
        <CardHeader>
          <CardTitle>
            {editingId ? "ویرایش سرویس ارسال" : "اتصال سرویس جدید"}
          </CardTitle>
          <CardDescription>
            اطلاعات اتصال رمزنگاری می‌شوند و فقط در همین بخش مدیریت خواهند شد.
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <Field label="نوع سرویس">
            <Select
              value={key}
              onValueChange={(v) => {
                setKey(v);
                if (v === "gmail_smtp") setHost("smtp.gmail.com");
              }}
            >
              <SelectTrigger>
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="kavenegar">کاوه‌نگار SMS</SelectItem>
                <SelectItem value="gmail_smtp">اتصال ساده Gmail</SelectItem>
                <SelectItem value="custom_smtp">SMTP پیشرفته</SelectItem>
              </SelectContent>
            </Select>
          </Field>
          {!isGmail && (
            <Field label="نام نمایشی">
              <Input
                value={name}
                onChange={(e) => setName(e.target.value)}
                placeholder="مثلاً سرویس اصلی"
              />
            </Field>
          )}
          {isSms ? (
            <>
              <Field label="API Key">
                <Input
                  type="password"
                  value={apiKey}
                  onChange={(e) => setApiKey(e.target.value)}
                />
              </Field>
              <Field label="شماره خط ارسال‌کننده">
                <Input
                  value={sender}
                  onChange={(e) => setSender(e.target.value)}
                />
              </Field>
            </>
          ) : isGmail ? (
            <>
              <div className="rounded-xl border border-blue-200 bg-blue-50 p-4 text-sm text-blue-950">
                <p className="font-semibold">اتصال Gmail در سه قدم</p>
                <ol className="mt-2 list-inside list-decimal space-y-1 text-xs leading-6">
                  <li>تأیید دومرحله‌ای حساب Google را فعال کنید.</li>
                  <li>از صفحه App Passwords یک رمز برنامه بسازید.</li>
                  <li>ایمیل و رمز ۱۶ رقمی را اینجا وارد کنید.</li>
                </ol>
                <a
                  href="https://myaccount.google.com/apppasswords"
                  target="_blank"
                  rel="noreferrer"
                  className="mt-3 inline-block font-medium text-blue-700 underline"
                >
                  بازکردن صفحه ساخت App Password گوگل
                </a>
              </div>
              <Field label="آدرس Gmail شما">
                <Input
                  dir="ltr"
                  type="email"
                  placeholder="yourname@gmail.com"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                />
              </Field>
              <Field label="App Password شانزده‌رقمی">
                <Input
                  dir="ltr"
                  type="password"
                  placeholder="رمز معمولی Gmail را وارد نکنید"
                  value={password}
                  onChange={(e) =>
                    setPassword(e.target.value.replace(/\s/g, ""))
                  }
                />
              </Field>
              <Field label="نام فرستنده (اختیاری)">
                <Input
                  value={fromName}
                  onChange={(e) => setFromName(e.target.value)}
                  placeholder="مثلاً فروشگاه من"
                />
              </Field>
              <p className="text-xs text-muted-foreground">
                تنظیمات smtp.gmail.com، پورت ۵۸۷ و TLS به‌صورت خودکار انجام
                می‌شود.
              </p>
            </>
          ) : (
            <>
              <div className="grid grid-cols-2 gap-3">
                <Field label="SMTP Host">
                  <Input
                    dir="ltr"
                    value={host}
                    onChange={(e) => setHost(e.target.value)}
                  />
                </Field>
                <Field label="Port">
                  <Input
                    dir="ltr"
                    value={port}
                    onChange={(e) => setPort(e.target.value)}
                  />
                </Field>
              </div>
              <Field label="رمزنگاری">
                <Select value={encryption} onValueChange={setEncryption}>
                  <SelectTrigger>
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="tls">TLS</SelectItem>
                    <SelectItem value="ssl">SSL</SelectItem>
                    <SelectItem value="none">None</SelectItem>
                  </SelectContent>
                </Select>
              </Field>
              <Field label="آدرس ایمیل">
                <Input
                  dir="ltr"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                />
              </Field>
              <Field label="App Password / Password">
                <Input
                  type="password"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                />
              </Field>
              <Field label="نام فرستنده">
                <Input
                  value={fromName}
                  onChange={(e) => setFromName(e.target.value)}
                />
              </Field>
            </>
          )}
          <Button
            className="w-full"
            disabled={
              busy || (!editingId && (isSms ? !apiKey : !email || !password))
            }
            onClick={save}
          >
            {busy && <Loader2 className="ml-2 h-4 w-4 animate-spin" />}
            {editingId
              ? "ذخیره تنظیمات"
              : isGmail
                ? "اتصال و تست Gmail"
                : "ذخیره سرویس ارسال"}
          </Button>
          {editingId && (
            <Button
              className="w-full"
              variant="ghost"
              onClick={() => {
                setEditingId("");
                setName("");
                setApiKey("");
                setPassword("");
              }}
            >
              انصراف از ویرایش
            </Button>
          )}
        </CardContent>
      </Card>
      <div className="space-y-3">
        {providers.length === 0 && (
          <Empty text="هنوز Provider متصل نشده است." />
        )}
        {providers.map((p) => (
          <Card key={p.id}>
            <CardContent className="flex flex-wrap items-center justify-between gap-3 p-5">
              <div className="flex items-center gap-3">
                {p.type === "sms" ? (
                  <MessageSquareText className="h-6 w-6 text-primary" />
                ) : (
                  <Mail className="h-6 w-6 text-primary" />
                )}
                <div>
                  <p className="font-semibold">{p.name}</p>
                  <p className="text-xs text-muted-foreground">
                    {p.provider_key} ·{" "}
                    {p.settings?.email || p.settings?.sender || "تنظیم‌شده"}
                  </p>
                  {p.last_test_error && (
                    <p className="mt-1 max-w-md text-xs text-destructive">
                      {p.last_test_error}
                    </p>
                  )}
                </div>
              </div>
              <div className="flex items-center gap-2">
                <StatusBadge
                  value={
                    p.status === "disabled" ? "disabled" : p.last_test_status
                  }
                />
                <Button size="sm" variant="outline" onClick={() => test(p.id)}>
                  تست اتصال
                </Button>
                <Button size="sm" variant="ghost" onClick={() => toggle(p)}>
                  {p.status === "active" ? "غیرفعال‌کردن" : "فعال‌کردن"}
                </Button>
                <Button
                  size="icon"
                  variant="ghost"
                  aria-label="ویرایش سرویس"
                  onClick={() => edit(p)}
                >
                  <Pencil className="h-4 w-4" />
                </Button>
                <Button
                  size="icon"
                  variant="ghost"
                  onClick={() => remove(p.id)}
                >
                  <Trash2 className="h-4 w-4 text-destructive" />
                </Button>
              </div>
            </CardContent>
          </Card>
        ))}
      </div>
    </div>
  );
}

function ContactsView({
  wid,
  contacts,
  reload,
}: {
  wid: string;
  contacts: Contact[];
  reload: () => void;
}) {
  const { toast } = useToast();
  const [name, setName] = useState("");
  const [phone, setPhone] = useState("");
  const [email, setEmail] = useState("");
  const [company, setCompany] = useState("");
  const [city, setCity] = useState("");
  const [search, setSearch] = useState("");
  const [statusFilter, setStatusFilter] = useState("all");
  const [importResult, setImportResult] = useState<any>(null);
  const [editingId, setEditingId] = useState("");
  const filtered = contacts.filter(
    (c) =>
      (statusFilter === "all" || c.status === statusFilter) &&
      `${c.name} ${c.phone} ${c.email} ${c.company}`
        .toLowerCase()
        .includes(search.toLowerCase()),
  );
  const clearForm = () => {
    setEditingId("");
    setName("");
    setPhone("");
    setEmail("");
    setCompany("");
    setCity("");
  };
  const add = async () => {
    try {
      await apiFetch(
        editingId
          ? `/workspaces/${wid}/communication/contacts/${editingId}/`
          : `/workspaces/${wid}/communication/contacts/`,
        {
          method: editingId ? "PATCH" : "POST",
          data: { name, phone, email, company, city },
        },
      );
      clearForm();
      reload();
    } catch (e: any) {
      toast({ title: "خطا", description: e.message, variant: "destructive" });
    }
  };
  const upload = async (file?: File) => {
    if (!file) return;
    const form = new FormData();
    form.append("file", file);
    try {
      const response = await apiFetch(
        `/workspaces/${wid}/communication/contacts/import/preview/`,
        { method: "POST", data: form },
      );
      setImportResult(response.data);
    } catch (e: any) {
      toast({
        title: "خطای import",
        description: e.message,
        variant: "destructive",
      });
    }
  };
  const confirm = async () => {
    const response = await apiFetch(
      `/workspaces/${wid}/communication/contacts/import/${importResult.id}/confirm/`,
      { method: "POST", data: { mapping: importResult.mapping } },
    );
    toast({ title: `${response.data.created} مخاطب وارد شد` });
    setImportResult(null);
    reload();
  };
  const remap = async () => {
    const response = await apiFetch(
      `/workspaces/${wid}/communication/contacts/import/${importResult.id}/preview/`,
      { method: "POST", data: { mapping: importResult.mapping } },
    );
    setImportResult({ ...response.data, columns: importResult.columns });
  };
  const edit = (contact: Contact) => {
    setEditingId(contact.id);
    setName(contact.name);
    setPhone(contact.phone);
    setEmail(contact.email);
    setCompany(contact.company);
    setCity(contact.city);
    window.scrollTo({ top: 0, behavior: "smooth" });
  };
  const remove = async (id: string) => {
    await apiFetch(`/workspaces/${wid}/communication/contacts/${id}/`, {
      method: "DELETE",
    });
    reload();
  };
  return (
    <div className="space-y-6 pt-4">
      <div className="grid gap-6 lg:grid-cols-2">
        <Card>
          <CardHeader>
            <CardTitle>{editingId ? "ویرایش مخاطب" : "افزودن مخاطب"}</CardTitle>
          </CardHeader>
          <CardContent className="space-y-3">
            <div className="grid grid-cols-2 gap-3">
              <Input
                placeholder="نام"
                value={name}
                onChange={(e) => setName(e.target.value)}
              />
              <Input
                placeholder="شرکت"
                value={company}
                onChange={(e) => setCompany(e.target.value)}
              />
              <Input
                dir="ltr"
                placeholder="0912..."
                value={phone}
                onChange={(e) => setPhone(e.target.value)}
              />
              <Input
                dir="ltr"
                placeholder="email@example.com"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
              />
              <Input
                placeholder="شهر"
                value={city}
                onChange={(e) => setCity(e.target.value)}
              />
            </div>
            <div className="flex gap-2">
              <Button onClick={add} disabled={!phone && !email}>
                {editingId ? (
                  <Pencil className="ml-2 h-4 w-4" />
                ) : (
                  <Plus className="ml-2 h-4 w-4" />
                )}
                {editingId ? "ذخیره تغییرات" : "افزودن"}
              </Button>
              {editingId && (
                <Button variant="outline" onClick={clearForm}>
                  انصراف
                </Button>
              )}
            </div>
          </CardContent>
        </Card>
        <Card>
          <CardHeader>
            <CardTitle>ورود گروهی</CardTitle>
            <CardDescription>
              CSV یا XLSX را آپلود و ستون‌ها را به فیلدهای سیستم نگاشت کنید.
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-3">
            <Label className="flex cursor-pointer items-center justify-center gap-2 rounded-lg border-2 border-dashed p-6 hover:bg-muted">
              <FileSpreadsheet className="h-6 w-6" />
              انتخاب فایل
              <Input
                type="file"
                accept=".csv,.xlsx"
                className="hidden"
                onChange={(e) => upload(e.target.files?.[0])}
              />
            </Label>
            {importResult && (
              <div className="space-y-3 rounded-lg bg-muted p-3 text-sm">
                <div className="space-y-2">
                  {(
                    importResult.columns ||
                    Object.keys(importResult.mapping || {})
                  ).map((column: string) => (
                    <div
                      key={column}
                      className="grid grid-cols-2 items-center gap-2"
                    >
                      <span dir="ltr" className="truncate">
                        {column}
                      </span>
                      <Select
                        value={importResult.mapping?.[column] || "ignore"}
                        onValueChange={(value) =>
                          setImportResult({
                            ...importResult,
                            mapping: {
                              ...importResult.mapping,
                              [column]: value === "ignore" ? "" : value,
                            },
                          })
                        }
                      >
                        <SelectTrigger>
                          <SelectValue />
                        </SelectTrigger>
                        <SelectContent>
                          <SelectItem value="ignore">نادیده گرفتن</SelectItem>
                          <SelectItem value="name">نام</SelectItem>
                          <SelectItem value="phone">موبایل</SelectItem>
                          <SelectItem value="email">ایمیل</SelectItem>
                          <SelectItem value="company">شرکت</SelectItem>
                          <SelectItem value="city">شهر</SelectItem>
                          <SelectItem value={`custom_fields.${column}`}>
                            فیلد سفارشی
                          </SelectItem>
                        </SelectContent>
                      </Select>
                    </div>
                  ))}
                </div>
                <Button
                  size="sm"
                  variant="outline"
                  className="w-full"
                  onClick={remap}
                >
                  تحلیل مجدد Mapping
                </Button>
                <div className="grid grid-cols-4 gap-2 text-center">
                  <div>
                    کل
                    <br />
                    <b>{importResult.total_rows}</b>
                  </div>
                  <div className="text-green-600">
                    معتبر
                    <br />
                    <b>{importResult.valid_rows}</b>
                  </div>
                  <div className="text-destructive">
                    نامعتبر
                    <br />
                    <b>{importResult.invalid_rows}</b>
                  </div>
                  <div>
                    تکراری
                    <br />
                    <b>{importResult.duplicate_rows}</b>
                  </div>
                </div>
                {importResult.preview?.slice(0, 3).map((row: any) => (
                  <div
                    key={row.row}
                    className="rounded border bg-background p-2 text-xs"
                  >
                    ردیف {row.row}: {JSON.stringify(row.data)}{" "}
                    {row.errors?.length ? (
                      <span className="text-destructive">
                        · {row.errors.join("، ")}
                      </span>
                    ) : null}
                  </div>
                ))}
                <Button className="w-full" onClick={confirm}>
                  تأیید Import
                </Button>
              </div>
            )}
          </CardContent>
        </Card>
      </div>
      <Card>
        <CardHeader>
          <div className="flex items-center justify-between gap-4">
            <CardTitle>
              مخاطبین ({contacts.length.toLocaleString("fa-IR")})
            </CardTitle>
            <div className="flex gap-2">
              <Input
                className="max-w-xs"
                placeholder="جستجو..."
                value={search}
                onChange={(e) => setSearch(e.target.value)}
              />
              <Select value={statusFilter} onValueChange={setStatusFilter}>
                <SelectTrigger className="w-36">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="all">همه</SelectItem>
                  <SelectItem value="active">فعال</SelectItem>
                  <SelectItem value="inactive">غیرفعال</SelectItem>
                </SelectContent>
              </Select>
            </div>
          </div>
        </CardHeader>
        <CardContent>
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>نام</TableHead>
                <TableHead>موبایل</TableHead>
                <TableHead>ایمیل</TableHead>
                <TableHead>شرکت / شهر</TableHead>
                <TableHead></TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {filtered.map((c) => (
                <TableRow key={c.id}>
                  <TableCell className="font-medium">
                    {c.name || "بدون نام"}
                  </TableCell>
                  <TableCell dir="ltr">{c.phone || "—"}</TableCell>
                  <TableCell dir="ltr">{c.email || "—"}</TableCell>
                  <TableCell>
                    {[c.company, c.city].filter(Boolean).join(" · ") || "—"}
                  </TableCell>
                  <TableCell>
                    <div className="flex">
                      <Button
                        size="icon"
                        variant="ghost"
                        onClick={() => edit(c)}
                      >
                        <Pencil className="h-4 w-4" />
                      </Button>
                      <Button
                        size="icon"
                        variant="ghost"
                        onClick={() => remove(c.id)}
                      >
                        <Trash2 className="h-4 w-4 text-destructive" />
                      </Button>
                    </div>
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </CardContent>
      </Card>
    </div>
  );
}

function GroupsView({
  wid,
  groups,
  contacts,
  reload,
}: {
  wid: string;
  groups: Group[];
  contacts: Contact[];
  reload: () => void;
}) {
  const [name, setName] = useState("");
  const [description, setDescription] = useState("");
  const [selected, setSelected] = useState<string[]>([]);
  const create = async () => {
    await apiFetch(`/workspaces/${wid}/communication/contact-groups/`, {
      method: "POST",
      data: { name, description, contact_ids: selected },
    });
    setName("");
    setDescription("");
    setSelected([]);
    reload();
  };
  return (
    <div className="grid gap-6 pt-4 lg:grid-cols-[380px_1fr]">
      <Card>
        <CardHeader>
          <CardTitle>گروه جدید</CardTitle>
        </CardHeader>
        <CardContent className="space-y-3">
          <Input
            placeholder="نام گروه"
            value={name}
            onChange={(e) => setName(e.target.value)}
          />
          <Textarea
            placeholder="توضیحات"
            value={description}
            onChange={(e) => setDescription(e.target.value)}
          />
          <div className="max-h-52 space-y-2 overflow-auto rounded-lg border p-3">
            {contacts.map((c) => (
              <label key={c.id} className="flex items-center gap-2 text-sm">
                <Checkbox
                  checked={selected.includes(c.id)}
                  onCheckedChange={(v) =>
                    setSelected(
                      v
                        ? [...selected, c.id]
                        : selected.filter((id) => id !== c.id),
                    )
                  }
                />
                {c.name || c.phone || c.email}
              </label>
            ))}
          </div>
          <Button className="w-full" disabled={!name} onClick={create}>
            ساخت گروه
          </Button>
        </CardContent>
      </Card>
      <div className="grid gap-4 md:grid-cols-2">
        {groups.map((g) => (
          <Card key={g.id}>
            <CardHeader>
              <CardTitle className="flex items-center justify-between">
                <span>{g.name}</span>
                <Badge variant="secondary">
                  {g.contact_count.toLocaleString("fa-IR")} مخاطب
                </Badge>
              </CardTitle>
              <CardDescription>{g.description || "بدون توضیح"}</CardDescription>
            </CardHeader>
          </Card>
        ))}
        {groups.length === 0 && <Empty text="هنوز گروهی ساخته نشده است." />}
      </div>
    </div>
  );
}

function TemplatesView({
  wid,
  templates,
  reload,
}: {
  wid: string;
  templates: Template[];
  reload: () => void;
}) {
  const { toast } = useToast();
  const [channel, setChannel] = useState<"sms" | "email">("sms");
  const [title, setTitle] = useState("");
  const [subject, setSubject] = useState("");
  const [body, setBody] = useState("");
  const [bodyType, setBodyType] = useState("plain_text");
  const [prompt, setPrompt] = useState("");
  const [aiBusy, setAiBusy] = useState(false);
  const [editingId, setEditingId] = useState("");
  const [previewTemplate, setPreviewTemplate] = useState<Template | null>(null);
  const ai = async () => {
    setAiBusy(true);
    try {
      const action = channel === "sms" ? "sms-generate" : "email-generate";
      const response = await apiFetch(
        `/workspaces/${wid}/communication/ai/${action}/`,
        { method: "POST", data: { prompt } },
      );
      const result = response.data.result;
      if (channel === "sms")
        setBody(result.variants?.[0]?.body || result.text || "");
      else {
        setSubject(result.subjects?.[0] || "");
        setBody(result.bodies?.[0]?.body || result.text || "");
      }
      toast({
        title: "متن با AI تولید شد",
        description: `${response.data.cost.toLocaleString("fa-IR")} تومان از اعتبار AI کسر شد.`,
      });
    } catch (e: any) {
      toast({
        title: "خطای AI",
        description: e.message,
        variant: "destructive",
      });
    } finally {
      setAiBusy(false);
    }
  };
  const save = async () => {
    await apiFetch(
      editingId
        ? `/workspaces/${wid}/communication/templates/${editingId}/`
        : `/workspaces/${wid}/communication/templates/`,
      {
        method: editingId ? "PATCH" : "POST",
        data: {
          channel,
          title,
          subject,
          body,
          body_type: bodyType,
          category: "عمومی",
        },
      },
    );
    setTitle("");
    setSubject("");
    setBody("");
    setEditingId("");
    reload();
  };
  const edit = (template: Template) => {
    setEditingId(template.id);
    setChannel(template.channel);
    setTitle(template.title);
    setSubject(template.subject);
    setBody(template.body);
    setBodyType(template.body_type);
  };
  const remove = async (id: string) => {
    try {
      await apiFetch(`/workspaces/${wid}/communication/templates/${id}/`, {
        method: "DELETE",
      });
      toast({ title: "قالب حذف شد" });
      reload();
    } catch (e: any) {
      toast({
        title: "حذف قالب ناموفق بود",
        description: e.message,
        variant: "destructive",
      });
    }
  };
  return (
    <>
      <div className="grid gap-6 pt-4 lg:grid-cols-[440px_1fr]">
        <Card>
          <CardHeader>
            <CardTitle>{editingId ? "ویرایش قالب" : "قالب جدید"}</CardTitle>
            <CardDescription>
              متغیرهای قابل استفاده:{" "}
              {"{{name}}، {{phone}}، {{email}}، {{company}}، {{city}}"}
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-3">
            <Select
              value={channel}
              onValueChange={(v: "sms" | "email") => setChannel(v)}
            >
              <SelectTrigger>
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="sms">قالب پیامک</SelectItem>
                <SelectItem value="email">قالب ایمیل</SelectItem>
              </SelectContent>
            </Select>
            <Input
              placeholder="عنوان قالب"
              value={title}
              onChange={(e) => setTitle(e.target.value)}
            />
            {channel === "email" && (
              <>
                <Input
                  placeholder="Subject"
                  value={subject}
                  onChange={(e) => setSubject(e.target.value)}
                />
                <Select value={bodyType} onValueChange={setBodyType}>
                  <SelectTrigger>
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="plain_text">متن ساده</SelectItem>
                    <SelectItem value="html">HTML</SelectItem>
                  </SelectContent>
                </Select>
              </>
            )}
            <Textarea
              className="min-h-40"
              placeholder="متن پیام..."
              value={body}
              onChange={(e) => setBody(e.target.value)}
            />
            {channel === "sms" && (
              <p className="text-xs text-muted-foreground">
                {body.length.toLocaleString("fa-IR")} کاراکتر · حدود{" "}
                {Math.max(
                  1,
                  Math.ceil(body.length / (body.length > 70 ? 67 : 70)),
                ).toLocaleString("fa-IR")}{" "}
                بخش
              </p>
            )}
            <div className="rounded-lg border bg-muted/30 p-3">
              <Label>دستیار هوش مصنوعی</Label>
              <Textarea
                className="mt-2"
                placeholder="پیام مورد نظر را توضیح دهید..."
                value={prompt}
                onChange={(e) => setPrompt(e.target.value)}
              />
              <Button
                className="mt-2 w-full"
                variant="outline"
                disabled={!prompt || aiBusy}
                onClick={ai}
              >
                {aiBusy ? (
                  <Loader2 className="ml-2 h-4 w-4 animate-spin" />
                ) : (
                  <Wand2 className="ml-2 h-4 w-4" />
                )}
                پیشنهاد متن با AI
              </Button>
            </div>
            <Button
              className="w-full"
              disabled={!title || !body || (channel === "email" && !subject)}
              onClick={save}
            >
              {editingId ? "ذخیره تغییرات" : "ذخیره قالب"}
            </Button>
            {editingId && (
              <Button
                className="w-full"
                variant="ghost"
                onClick={() => {
                  setEditingId("");
                  setTitle("");
                  setSubject("");
                  setBody("");
                }}
              >
                انصراف از ویرایش
              </Button>
            )}
          </CardContent>
        </Card>
        <div className="space-y-3">
          {templates.map((t) => (
            <Card key={t.id}>
              <CardHeader>
                <div className="flex items-center justify-between">
                  <CardTitle className="text-base">{t.title}</CardTitle>
                  <div className="flex items-center gap-2">
                    <Badge>{t.channel === "sms" ? "SMS" : "Email"}</Badge>
                    <Button
                      size="icon"
                      variant="ghost"
                      aria-label="پیش‌نمایش قالب"
                      onClick={() => setPreviewTemplate(t)}
                    >
                      <MessageSquareText className="h-4 w-4" />
                    </Button>
                    <Button
                      size="icon"
                      variant="ghost"
                      aria-label="ویرایش قالب"
                      onClick={() => edit(t)}
                    >
                      <Pencil className="h-4 w-4" />
                    </Button>
                    <Button
                      size="icon"
                      variant="ghost"
                      aria-label="حذف قالب"
                      onClick={() => remove(t.id)}
                    >
                      <Trash2 className="h-4 w-4 text-destructive" />
                    </Button>
                  </div>
                </div>
                <CardDescription>{t.subject}</CardDescription>
              </CardHeader>
              <CardContent>
                <p className="line-clamp-3 whitespace-pre-wrap text-sm">
                  {t.body}
                </p>
                <div className="mt-3 flex flex-wrap gap-1">
                  {t.variables.map((v) => (
                    <Badge key={v} variant="outline">{`{{${v}}}`}</Badge>
                  ))}
                </div>
              </CardContent>
            </Card>
          ))}
          {templates.length === 0 && (
            <Empty text="هنوز قالبی ساخته نشده است." />
          )}
        </div>
      </div>
      <Dialog
        open={!!previewTemplate}
        onOpenChange={(open) => !open && setPreviewTemplate(null)}
      >
        <DialogContent>
          <DialogHeader>
            <DialogTitle>پیش‌نمایش {previewTemplate?.title}</DialogTitle>
          </DialogHeader>
          {previewTemplate?.subject && (
            <p className="font-semibold">
              {previewTemplate.subject.replaceAll("{{name}}", "سارا")}
            </p>
          )}
          <div className="rounded-lg border bg-muted/20 p-4">
            <p className="whitespace-pre-wrap text-sm">
              {previewTemplate?.body
                .replaceAll("{{name}}", "سارا")
                .replaceAll("{{company}}", "شرکت نمونه")
                .replaceAll("{{phone}}", "09120000000")
                .replaceAll("{{email}}", "sara@example.com")}
            </p>
          </div>
          <p className="text-xs text-muted-foreground">
            پیش‌نمایش با داده نمونه نمایش داده شده است.
          </p>
        </DialogContent>
      </Dialog>
    </>
  );
}

function CampaignsCenterView({
  wid,
  providers,
  contacts,
  groups,
  templates,
  campaigns,
  reload,
  onOpenContacts,
  onOpenProviders,
}: {
  wid: string;
  providers: Provider[];
  contacts: Contact[];
  groups: Group[];
  templates: Template[];
  campaigns: Campaign[];
  reload: () => void;
  onOpenContacts: () => void;
  onOpenProviders: () => void;
}) {
  const { toast } = useToast();
  const [creating, setCreating] = useState(false);
  const [step, setStep] = useState(1);
  const [name, setName] = useState("");
  const [channel, setChannel] = useState<"sms" | "email">("sms");
  const [contactIds, setContactIds] = useState<string[]>([]);
  const [groupIds, setGroupIds] = useState<string[]>([]);
  const [contentMode, setContentMode] = useState<"template" | "manual" | "ai">(
    "manual",
  );
  const [templateId, setTemplateId] = useState("");
  const [subject, setSubject] = useState("");
  const [body, setBody] = useState("");
  const [bodyType, setBodyType] = useState("plain_text");
  const [aiPrompt, setAiPrompt] = useState("");
  const [aiVariants, setAiVariants] = useState<
    { title?: string; body: string }[]
  >([]);
  const [ctaSuggestions, setCtaSuggestions] = useState<string[]>([]);
  const [aiBusy, setAiBusy] = useState(false);
  const [savedId, setSavedId] = useState("");
  const [samples, setSamples] = useState<any[]>([]);
  const [testRecipient, setTestRecipient] = useState("");
  const [scheduledAt, setScheduledAt] = useState("");
  const [busy, setBusy] = useState(false);

  const activeProvider =
    providers.find(
      (p) =>
        p.type === channel &&
        p.status === "active" &&
        p.last_test_status === "connected",
    ) || providers.find((p) => p.type === channel && p.status === "active");
  const availableTemplates = templates.filter((t) => t.channel === channel);
  const audienceEstimate =
    contactIds.length +
    groups
      .filter((g) => groupIds.includes(g.id))
      .reduce((sum, group) => sum + group.contact_count, 0);
  const missingDestinations = contacts.filter(
    (contact) =>
      contactIds.includes(contact.id) &&
      !(channel === "sms" ? contact.phone : contact.email),
  ).length;

  const reset = () => {
    setCreating(false);
    setStep(1);
    setName("");
    setChannel("sms");
    setContactIds([]);
    setGroupIds([]);
    setContentMode("manual");
    setTemplateId("");
    setSubject("");
    setBody("");
    setBodyType("plain_text");
    setAiPrompt("");
    setAiVariants([]);
    setCtaSuggestions([]);
    setSavedId("");
    setSamples([]);
    setTestRecipient("");
    setScheduledAt("");
  };

  const selectTemplate = (id: string) => {
    setTemplateId(id);
    const template = templates.find((item) => item.id === id);
    if (template) {
      setSubject(template.subject);
      setBody(template.body);
      setBodyType(template.body_type);
    }
  };

  const runAi = async (action?: "rewrite" | "shorten") => {
    setAiBusy(true);
    try {
      const endpoint =
        channel === "email"
          ? "email-generate"
          : action === "rewrite"
            ? "sms-rewrite"
            : action === "shorten"
              ? "sms-shorten"
              : "sms-generate";
      const prompt = action
        ? `${body}\n\nدرخواست: ${action === "shorten" ? "کوتاه‌سازی با حفظ CTA" : "بازنویسی حرفه‌ای"}`
        : aiPrompt;
      const response = await apiFetch(
        `/workspaces/${wid}/communication/ai/${endpoint}/`,
        {
          method: "POST",
          data: { prompt },
        },
      );
      const result = response.data.result;
      const variants =
        channel === "sms"
          ? (result.variants || []).map((item: any) => ({
              title: item.title,
              body: item.body,
            }))
          : (result.bodies || []).map((item: any) => ({
              title: item.title,
              body: item.body,
            }));
      setAiVariants(variants);
      setCtaSuggestions(result.cta_suggestions || []);
      if (channel === "email" && result.subjects?.[0])
        setSubject(result.subjects[0]);
      if (variants[0]) setBody(variants[0].body);
      toast({
        title: "پیشنهادهای AI آماده شد",
        description: `${response.data.cost.toLocaleString("fa-IR")} تومان هزینه AI`,
      });
    } catch (e: any) {
      toast({
        title: "خطای AI",
        description: e.message,
        variant: "destructive",
      });
    } finally {
      setAiBusy(false);
    }
  };

  const campaignPayload = () => ({
    name,
    channel,
    provider: activeProvider?.id,
    template: templateId || null,
    subject,
    body,
    body_type: bodyType,
    selected_contact_ids: contactIds,
    selected_group_ids: groupIds,
    settings: { ai_generated: contentMode === "ai" },
  });

  const saveDraftAndPreview = async () => {
    if (!activeProvider) return;
    setBusy(true);
    try {
      const response = await apiFetch(
        savedId
          ? `/workspaces/${wid}/communication/campaigns/${savedId}/`
          : `/workspaces/${wid}/communication/campaigns/`,
        { method: savedId ? "PATCH" : "POST", data: campaignPayload() },
      );
      const id = savedId || response.data.id;
      setSavedId(id);
      const preview = await apiFetch(
        `/workspaces/${wid}/communication/campaigns/${id}/preview/`,
        { method: "POST" },
      );
      setSamples(preview.data.samples || []);
      setStep(4);
      reload();
    } catch (e: any) {
      toast({
        title: "آماده‌سازی پیش‌نمایش ناموفق بود",
        description: e.message,
        variant: "destructive",
      });
    } finally {
      setBusy(false);
    }
  };

  const sendTest = async () => {
    try {
      await apiFetch(
        `/workspaces/${wid}/communication/campaigns/${savedId}/send-test/`,
        {
          method: "POST",
          data: { recipient: testRecipient },
        },
      );
      toast({ title: "پیام تست با موفقیت ارسال شد" });
    } catch (e: any) {
      toast({
        title: "ارسال تست ناموفق",
        description: e.message,
        variant: "destructive",
      });
    }
  };

  const sendNow = async () => {
    setBusy(true);
    try {
      const response = await apiFetch(
        `/workspaces/${wid}/communication/campaigns/${savedId}/start/`,
        { method: "POST" },
      );
      toast({
        title: "کمپین وارد صف ارسال شد",
        description: `${response.data.messages.toLocaleString("fa-IR")} پیام`,
      });
      reset();
      reload();
    } catch (e: any) {
      toast({
        title: "شروع کمپین ناموفق بود",
        description: e.message,
        variant: "destructive",
      });
    } finally {
      setBusy(false);
    }
  };

  const schedule = async () => {
    setBusy(true);
    try {
      await apiFetch(
        `/workspaces/${wid}/communication/campaigns/${savedId}/schedule/`,
        {
          method: "POST",
          data: { scheduled_at: new Date(scheduledAt).toISOString() },
        },
      );
      toast({ title: "کمپین زمان‌بندی شد" });
      reset();
      reload();
    } catch (e: any) {
      toast({
        title: "زمان‌بندی ناموفق بود",
        description: e.message,
        variant: "destructive",
      });
    } finally {
      setBusy(false);
    }
  };

  if (!creating)
    return (
      <div className="space-y-5 pt-4">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div>
            <h2 className="text-xl font-semibold">کمپین‌ها</h2>
            <p className="text-sm text-muted-foreground">
              ارسال‌های قبلی و وضعیت آن‌ها
            </p>
          </div>
          <Button onClick={() => setCreating(true)}>
            <Plus className="ml-2 h-4 w-4" />
            ساخت کمپین جدید
          </Button>
        </div>
        <Card>
          <CardContent className="p-5">
            <CampaignTable campaigns={campaigns} />
          </CardContent>
        </Card>
      </div>
    );

  const steps = ["نوع ارسال", "مخاطبین", "محتوا", "پیش‌نمایش", "ارسال"];
  return (
    <div className="space-y-5 pt-4">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-xl font-semibold">ساخت کمپین</h2>
          <p className="text-sm text-muted-foreground">پنج قدم ساده تا ارسال</p>
        </div>
        <Button variant="ghost" onClick={reset}>
          انصراف
        </Button>
      </div>
      <Card>
        <CardHeader>
          <div className="grid grid-cols-5 gap-2">
            {steps.map((label, index) => (
              <div key={label} className="text-center">
                <div
                  className={`mx-auto mb-2 flex h-8 w-8 items-center justify-center rounded-full text-sm ${index + 1 <= step ? "bg-primary text-primary-foreground" : "bg-muted text-muted-foreground"}`}
                >
                  {index + 1}
                </div>
                <span className="hidden text-xs sm:block">{label}</span>
              </div>
            ))}
          </div>
        </CardHeader>
        <CardContent className="min-h-[430px]">
          {step === 1 && (
            <div className="mx-auto max-w-2xl space-y-6">
              <Field label="نام کمپین">
                <Input
                  placeholder="مثلاً معرفی پیشنهاد تابستانی"
                  value={name}
                  onChange={(e) => setName(e.target.value)}
                />
              </Field>
              <div>
                <Label>نوع ارسال</Label>
                <div className="mt-3 grid grid-cols-2 gap-4">
                  {(["sms", "email"] as const).map((item) => (
                    <button
                      key={item}
                      onClick={() => {
                        setChannel(item);
                        setTemplateId("");
                        setSubject("");
                        setBody("");
                      }}
                      className={`rounded-2xl border-2 p-7 text-center transition ${channel === item ? "border-primary bg-primary/5 shadow-sm" : "hover:border-primary/40"}`}
                    >
                      {item === "sms" ? (
                        <MessageSquareText className="mx-auto mb-3 h-9 w-9 text-primary" />
                      ) : (
                        <Mail className="mx-auto mb-3 h-9 w-9 text-primary" />
                      )}
                      <p className="font-semibold">
                        {item === "sms" ? "پیامک" : "ایمیل"}
                      </p>
                    </button>
                  ))}
                </div>
              </div>
              {activeProvider ? (
                <div className="flex items-center justify-between rounded-lg bg-muted/50 p-3 text-sm">
                  <span>
                    سرویس ارسال به‌صورت خودکار انتخاب شد:{" "}
                    <b>{activeProvider.name}</b>
                  </span>
                  <StatusBadge value={activeProvider.last_test_status} />
                </div>
              ) : (
                <div className="rounded-lg border border-destructive/40 bg-destructive/5 p-4">
                  <p className="text-sm text-destructive">
                    برای {channel === "sms" ? "پیامک" : "ایمیل"} سرویس فعالی
                    وجود ندارد.
                  </p>
                  <Button
                    className="mt-2"
                    size="sm"
                    variant="outline"
                    onClick={onOpenProviders}
                  >
                    تنظیم سرویس ارسال
                  </Button>
                </div>
              )}
            </div>
          )}

          {step === 2 && (
            <div className="space-y-5">
              <div className="flex flex-wrap items-center justify-between gap-2">
                <div>
                  <h3 className="font-semibold">مخاطبین کمپین</h3>
                  <p className="text-sm text-muted-foreground">
                    گروه‌ها یا افراد مشخص را انتخاب کنید.
                  </p>
                </div>
                <Button variant="outline" onClick={onOpenContacts}>
                  <FileSpreadsheet className="ml-2 h-4 w-4" />
                  Import سریع CSV / Excel
                </Button>
              </div>
              <div className="grid gap-5 md:grid-cols-2">
                <div>
                  <Label>گروه‌های مخاطبین</Label>
                  <div className="mt-2 max-h-64 space-y-2 overflow-auto rounded-xl border p-3">
                    {groups.map((g) => (
                      <label
                        key={g.id}
                        className="flex items-center justify-between rounded-lg p-2 hover:bg-muted/50"
                      >
                        <span className="flex items-center gap-2">
                          <Checkbox
                            checked={groupIds.includes(g.id)}
                            onCheckedChange={(checked) =>
                              setGroupIds(
                                checked
                                  ? [...groupIds, g.id]
                                  : groupIds.filter((id) => id !== g.id),
                              )
                            }
                          />
                          {g.name}
                        </span>
                        <Badge variant="secondary">
                          {g.contact_count.toLocaleString("fa-IR")}
                        </Badge>
                      </label>
                    ))}
                    {!groups.length && <Empty text="گروهی وجود ندارد." />}
                  </div>
                </div>
                <div>
                  <Label>انتخاب مخاطبین مشخص</Label>
                  <div className="mt-2 max-h-64 space-y-2 overflow-auto rounded-xl border p-3">
                    {contacts.map((c) => (
                      <label
                        key={c.id}
                        className="flex items-center gap-2 rounded-lg p-2 hover:bg-muted/50"
                      >
                        <Checkbox
                          checked={contactIds.includes(c.id)}
                          onCheckedChange={(checked) =>
                            setContactIds(
                              checked
                                ? [...contactIds, c.id]
                                : contactIds.filter((id) => id !== c.id),
                            )
                          }
                        />
                        <span>
                          <span className="block text-sm">
                            {c.name || "بدون نام"}
                          </span>
                          <span
                            className="text-xs text-muted-foreground"
                            dir="ltr"
                          >
                            {channel === "sms" ? c.phone : c.email}
                          </span>
                        </span>
                      </label>
                    ))}
                    {!contacts.length && <Empty text="مخاطبی وجود ندارد." />}
                  </div>
                </div>
              </div>
              <div className="rounded-lg bg-primary/5 p-3 text-sm">
                حدود {audienceEstimate.toLocaleString("fa-IR")} مخاطب انتخاب شده
                است.
              </div>
            </div>
          )}

          {step === 3 && (
            <div className="mx-auto max-w-3xl space-y-5">
              <div className="grid grid-cols-3 gap-3">
                {(
                  [
                    {
                      id: "template",
                      label: "قالب آماده",
                      icon: MessageSquareText,
                    },
                    { id: "manual", label: "نوشتن دستی", icon: Pencil },
                    { id: "ai", label: "تولید با AI", icon: Wand2 },
                  ] as const
                ).map((mode) => (
                  <button
                    key={mode.id}
                    onClick={() => setContentMode(mode.id)}
                    className={`rounded-xl border-2 p-4 text-center ${contentMode === mode.id ? "border-primary bg-primary/5" : ""}`}
                  >
                    <mode.icon className="mx-auto mb-2 h-5 w-5" />
                    <span className="text-sm font-medium">{mode.label}</span>
                  </button>
                ))}
              </div>
              {contentMode === "template" && (
                <Field label="انتخاب قالب">
                  <Select value={templateId} onValueChange={selectTemplate}>
                    <SelectTrigger>
                      <SelectValue placeholder="یک قالب انتخاب کنید" />
                    </SelectTrigger>
                    <SelectContent>
                      {availableTemplates.map((t) => (
                        <SelectItem key={t.id} value={t.id}>
                          {t.title}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </Field>
              )}
              {contentMode === "ai" && (
                <div className="space-y-3 rounded-xl border bg-muted/20 p-4">
                  <Label>چه پیامی می‌خواهید؟</Label>
                  <Textarea
                    placeholder="هدف کمپین، لحن، پیشنهاد و مخاطب را توضیح دهید..."
                    value={aiPrompt}
                    onChange={(e) => setAiPrompt(e.target.value)}
                  />
                  <Button
                    disabled={!aiPrompt || aiBusy}
                    onClick={() => runAi()}
                  >
                    {aiBusy ? (
                      <Loader2 className="ml-2 h-4 w-4 animate-spin" />
                    ) : (
                      <Wand2 className="ml-2 h-4 w-4" />
                    )}
                    ساخت چند پیشنهاد
                  </Button>
                  {aiVariants.length > 0 && (
                    <div className="grid gap-2 md:grid-cols-2">
                      {aiVariants.map((variant, index) => (
                        <button
                          key={index}
                          onClick={() => setBody(variant.body)}
                          className={`rounded-lg border p-3 text-right text-sm ${body === variant.body ? "border-primary bg-primary/5" : ""}`}
                        >
                          <b>{variant.title || `پیشنهاد ${index + 1}`}</b>
                          <p className="mt-1 line-clamp-3 whitespace-pre-wrap text-muted-foreground">
                            {variant.body}
                          </p>
                        </button>
                      ))}
                    </div>
                  )}
                  {ctaSuggestions.length > 0 && (
                    <div>
                      <p className="mb-2 text-xs font-medium">
                        CTAهای پیشنهادی
                      </p>
                      <div className="flex flex-wrap gap-2">
                        {ctaSuggestions.map((cta) => (
                          <Button
                            key={cta}
                            size="sm"
                            variant="outline"
                            onClick={() => setBody(`${body}\n${cta}`)}
                          >
                            {cta}
                          </Button>
                        ))}
                      </div>
                    </div>
                  )}
                </div>
              )}
              {channel === "email" && (
                <div className="grid gap-3 sm:grid-cols-[1fr_160px]">
                  <Field label="موضوع ایمیل">
                    <Input
                      value={subject}
                      onChange={(e) => setSubject(e.target.value)}
                    />
                  </Field>
                  <Field label="نوع محتوا">
                    <Select value={bodyType} onValueChange={setBodyType}>
                      <SelectTrigger>
                        <SelectValue />
                      </SelectTrigger>
                      <SelectContent>
                        <SelectItem value="plain_text">متن ساده</SelectItem>
                        <SelectItem value="html">HTML</SelectItem>
                      </SelectContent>
                    </Select>
                  </Field>
                </div>
              )}
              <Field label="متن نهایی">
                <Textarea
                  className="min-h-44"
                  value={body}
                  onChange={(e) => setBody(e.target.value)}
                />
              </Field>
              <div className="flex flex-wrap items-center justify-between gap-2">
                <p className="text-xs text-muted-foreground">
                  متغیرها: {"{{name}}، {{phone}}، {{email}}، {{company}}"}
                </p>
                {channel === "sms" && (
                  <div className="flex gap-2">
                    <Button
                      size="sm"
                      variant="outline"
                      disabled={!body || aiBusy}
                      onClick={() => runAi("rewrite")}
                    >
                      بازنویسی
                    </Button>
                    <Button
                      size="sm"
                      variant="outline"
                      disabled={!body || aiBusy}
                      onClick={() => runAi("shorten")}
                    >
                      کوتاه‌کردن SMS
                    </Button>
                    <Badge variant="secondary">
                      {body.length.toLocaleString("fa-IR")} کاراکتر
                    </Badge>
                  </div>
                )}
              </div>
            </div>
          )}

          {step === 4 && (
            <div className="space-y-5">
              <div className="grid gap-3 sm:grid-cols-3">
                <Summary label="مخاطبین تقریبی" value={audienceEstimate} />
                <Summary label="نمونه‌های آماده" value={samples.length} />
                <Summary
                  label="خطاهای شناسایی‌شده"
                  value={missingDestinations}
                />
              </div>
              {missingDestinations > 0 && (
                <div className="flex gap-2 rounded-lg border border-amber-300 bg-amber-50 p-3 text-sm text-amber-900">
                  <CircleAlert className="h-5 w-5 shrink-0" />
                  {missingDestinations.toLocaleString("fa-IR")} مخاطب انتخابی
                  اطلاعات دریافت این کانال را ندارد و ارسال نخواهد شد.
                </div>
              )}
              <div>
                <h3 className="mb-3 font-semibold">
                  نمونه پیام با جایگذاری متغیرها
                </h3>
                <div className="grid gap-3 md:grid-cols-2">
                  {samples.map((sample, index) => (
                    <Card key={sample.contact_id || index}>
                      <CardHeader className="pb-2">
                        <CardTitle className="text-sm">
                          {sample.name || "مخاطب بدون نام"}
                        </CardTitle>
                        <CardDescription dir="ltr">
                          {sample.recipient || "گیرنده نامعتبر"}
                        </CardDescription>
                      </CardHeader>
                      <CardContent>
                        {sample.subject && (
                          <p className="mb-2 font-medium">{sample.subject}</p>
                        )}
                        <p className="whitespace-pre-wrap text-sm">
                          {sample.body}
                        </p>
                      </CardContent>
                    </Card>
                  ))}
                  {!samples.length && (
                    <Empty text="نمونه‌ای برای پیش‌نمایش وجود ندارد." />
                  )}
                </div>
              </div>
            </div>
          )}

          {step === 5 && (
            <div className="mx-auto max-w-2xl space-y-5">
              <div className="rounded-xl border bg-muted/20 p-4">
                <div className="flex items-center justify-between">
                  <div>
                    <p className="font-semibold">آماده ارسال</p>
                    <p className="text-sm text-muted-foreground">
                      {name} · {channel === "sms" ? "پیامک" : "ایمیل"} · حدود{" "}
                      {audienceEstimate.toLocaleString("fa-IR")} مخاطب
                    </p>
                  </div>
                  <CheckCircle2 className="h-7 w-7 text-emerald-600" />
                </div>
              </div>
              <div className="rounded-xl border p-4">
                <Label>ارسال تستی</Label>
                <div className="mt-2 flex gap-2">
                  <Input
                    dir="ltr"
                    placeholder={
                      channel === "sms" ? "شماره موبایل تست" : "ایمیل تست"
                    }
                    value={testRecipient}
                    onChange={(e) => setTestRecipient(e.target.value)}
                  />
                  <Button
                    variant="outline"
                    disabled={!testRecipient}
                    onClick={sendTest}
                  >
                    ارسال تست
                  </Button>
                </div>
              </div>
              <Button
                size="lg"
                className="w-full"
                disabled={busy}
                onClick={sendNow}
              >
                <Send className="ml-2 h-5 w-5" />
                ارسال فوری
              </Button>
              <div className="rounded-xl border p-4">
                <Label>یا زمان‌بندی ارسال</Label>
                <div className="mt-2 flex gap-2">
                  <Input
                    type="datetime-local"
                    value={scheduledAt}
                    onChange={(e) => setScheduledAt(e.target.value)}
                  />
                  <Button
                    variant="outline"
                    disabled={!scheduledAt || busy}
                    onClick={schedule}
                  >
                    <CalendarClock className="ml-2 h-4 w-4" />
                    زمان‌بندی
                  </Button>
                </div>
              </div>
            </div>
          )}

          <div className="mt-8 flex justify-between border-t pt-4">
            <Button
              variant="outline"
              disabled={step === 1 || busy}
              onClick={() => setStep(step - 1)}
            >
              <ChevronRight className="ml-1 h-4 w-4" />
              قبلی
            </Button>
            {step < 5 && (
              <Button
                disabled={
                  busy ||
                  (step === 1 && (!name || !activeProvider)) ||
                  (step === 2 && !contactIds.length && !groupIds.length) ||
                  (step === 3 && (!body || (channel === "email" && !subject)))
                }
                onClick={() =>
                  step === 3 ? saveDraftAndPreview() : setStep(step + 1)
                }
              >
                {busy && <Loader2 className="ml-2 h-4 w-4 animate-spin" />}بعدی
                <ChevronLeft className="mr-1 h-4 w-4" />
              </Button>
            )}
          </div>
        </CardContent>
      </Card>
    </div>
  );
}

function CampaignsView({
  wid,
  providers,
  contacts,
  groups,
  templates,
  campaigns,
  reload,
}: {
  wid: string;
  providers: Provider[];
  contacts: Contact[];
  groups: Group[];
  templates: Template[];
  campaigns: Campaign[];
  reload: () => void;
}) {
  const { toast } = useToast();
  const [step, setStep] = useState(1);
  const [channel, setChannel] = useState<"sms" | "email">("sms");
  const [name, setName] = useState("");
  const [providerId, setProviderId] = useState("");
  const [contactIds, setContactIds] = useState<string[]>([]);
  const [groupIds, setGroupIds] = useState<string[]>([]);
  const [templateId, setTemplateId] = useState("");
  const [subject, setSubject] = useState("");
  const [body, setBody] = useState("");
  const [bodyType, setBodyType] = useState("plain_text");
  const [savedId, setSavedId] = useState("");
  const [testRecipient, setTestRecipient] = useState("");
  const [busy, setBusy] = useState(false);
  const [aiPrompt, setAiPrompt] = useState("");
  const [aiBusy, setAiBusy] = useState(false);
  const [aiUsed, setAiUsed] = useState(false);
  const availableProviders = providers.filter(
    (p) => p.type === channel && p.status === "active",
  );
  const availableTemplates = templates.filter((t) => t.channel === channel);
  const chooseTemplate = (id: string) => {
    setTemplateId(id);
    const item = templates.find((t) => t.id === id);
    if (item) {
      setSubject(item.subject);
      setBody(item.body);
      setBodyType(item.body_type);
    }
  };
  const generateAi = async () => {
    setAiBusy(true);
    try {
      const action = channel === "sms" ? "sms-generate" : "email-generate";
      const response = await apiFetch(
        `/workspaces/${wid}/communication/ai/${action}/`,
        { method: "POST", data: { prompt: aiPrompt } },
      );
      const result = response.data.result;
      if (channel === "sms") {
        setBody(result.variants?.[0]?.body || result.text || "");
      } else {
        setSubject(result.subjects?.[0] || "");
        setBody(result.bodies?.[0]?.body || result.text || "");
      }
      setAiUsed(true);
      toast({
        title: "متن کمپین با AI تولید شد",
        description: `${response.data.cost.toLocaleString("fa-IR")} تومان از اعتبار AI کسر شد.`,
      });
    } catch (e: any) {
      toast({
        title: "خطای AI",
        description: e.message,
        variant: "destructive",
      });
    } finally {
      setAiBusy(false);
    }
  };
  const save = async () => {
    setBusy(true);
    try {
      const response = await apiFetch(
        `/workspaces/${wid}/communication/campaigns/`,
        {
          method: "POST",
          data: {
            name,
            channel,
            provider: providerId,
            template: templateId || null,
            subject,
            body,
            body_type: bodyType,
            selected_contact_ids: contactIds,
            selected_group_ids: groupIds,
            settings: { ai_generated: aiUsed },
          },
        },
      );
      setSavedId(response.data.id);
      toast({ title: "پیش‌نویس کمپین ذخیره شد" });
      reload();
    } catch (e: any) {
      toast({ title: "خطا", description: e.message, variant: "destructive" });
    } finally {
      setBusy(false);
    }
  };
  const sendTest = async () => {
    try {
      await apiFetch(
        `/workspaces/${wid}/communication/campaigns/${savedId}/send-test/`,
        { method: "POST", data: { recipient: testRecipient } },
      );
      toast({ title: "پیام تست ارسال شد" });
    } catch (e: any) {
      toast({
        title: "ارسال تست ناموفق",
        description: e.message,
        variant: "destructive",
      });
    }
  };
  const start = async (id = savedId) => {
    try {
      const response = await apiFetch(
        `/workspaces/${wid}/communication/campaigns/${id}/start/`,
        { method: "POST" },
      );
      toast({
        title: "کمپین وارد صف شد",
        description: `${response.data.messages} پیام آماده ارسال است.`,
      });
      setStep(1);
      setSavedId("");
      setName("");
      setBody("");
      setSubject("");
      setContactIds([]);
      setGroupIds([]);
      setAiPrompt("");
      setAiUsed(false);
      reload();
    } catch (e: any) {
      toast({ title: "خطا", description: e.message, variant: "destructive" });
    }
  };
  return (
    <div className="space-y-6 pt-4">
      <Card>
        <CardHeader>
          <CardTitle>ساخت کمپین جدید</CardTitle>
          <div className="flex gap-2">
            {[1, 2, 3, 4, 5].map((n) => (
              <div
                key={n}
                className={`h-1 flex-1 rounded ${n <= step ? "bg-primary" : "bg-muted"}`}
              />
            ))}
          </div>
        </CardHeader>
        <CardContent className="min-h-80">
          {step === 1 && (
            <div className="mx-auto max-w-xl space-y-5">
              <Field label="نام کمپین">
                <Input value={name} onChange={(e) => setName(e.target.value)} />
              </Field>
              <div className="grid grid-cols-2 gap-4">
                {(["sms", "email"] as const).map((c) => (
                  <button
                    key={c}
                    onClick={() => {
                      setChannel(c);
                      setProviderId("");
                      setTemplateId("");
                    }}
                    className={`rounded-xl border-2 p-6 text-center ${channel === c ? "border-primary bg-primary/5" : "border-border"}`}
                  >
                    {c === "sms" ? (
                      <MessageSquareText className="mx-auto mb-2 h-8 w-8" />
                    ) : (
                      <Mail className="mx-auto mb-2 h-8 w-8" />
                    )}
                    کمپین {c === "sms" ? "پیامکی" : "ایمیلی"}
                  </button>
                ))}
              </div>
            </div>
          )}
          {step === 2 && (
            <div className="mx-auto max-w-xl">
              <Label>Provider ارسال</Label>
              <div className="mt-3 space-y-2">
                {availableProviders.map((p) => (
                  <button
                    key={p.id}
                    onClick={() => setProviderId(p.id)}
                    className={`flex w-full items-center justify-between rounded-lg border-2 p-4 ${providerId === p.id ? "border-primary bg-primary/5" : ""}`}
                  >
                    <span>{p.name}</span>
                    <StatusBadge value={p.last_test_status} />
                  </button>
                ))}
                {availableProviders.length === 0 && (
                  <Empty text="ابتدا یک Provider فعال برای این کانال بسازید." />
                )}
              </div>
            </div>
          )}
          {step === 3 && (
            <div className="grid gap-6 md:grid-cols-2">
              <div>
                <Label>انتخاب گروه‌ها</Label>
                <div className="mt-2 max-h-60 space-y-2 overflow-auto rounded-lg border p-3">
                  {groups.map((g) => (
                    <label
                      key={g.id}
                      className="flex items-center justify-between text-sm"
                    >
                      <span className="flex items-center gap-2">
                        <Checkbox
                          checked={groupIds.includes(g.id)}
                          onCheckedChange={(v) =>
                            setGroupIds(
                              v
                                ? [...groupIds, g.id]
                                : groupIds.filter((x) => x !== g.id),
                            )
                          }
                        />
                        {g.name}
                      </span>
                      <Badge variant="secondary">{g.contact_count}</Badge>
                    </label>
                  ))}
                </div>
              </div>
              <div>
                <Label>انتخاب دستی مخاطبین</Label>
                <div className="mt-2 max-h-60 space-y-2 overflow-auto rounded-lg border p-3">
                  {contacts.map((c) => (
                    <label
                      key={c.id}
                      className="flex items-center gap-2 text-sm"
                    >
                      <Checkbox
                        checked={contactIds.includes(c.id)}
                        onCheckedChange={(v) =>
                          setContactIds(
                            v
                              ? [...contactIds, c.id]
                              : contactIds.filter((x) => x !== c.id),
                          )
                        }
                      />
                      {c.name || c.phone || c.email}
                    </label>
                  ))}
                </div>
              </div>
            </div>
          )}
          {step === 4 && (
            <div className="mx-auto max-w-2xl space-y-4">
              <Field label="قالب آماده">
                <Select value={templateId} onValueChange={chooseTemplate}>
                  <SelectTrigger>
                    <SelectValue placeholder="اختیاری" />
                  </SelectTrigger>
                  <SelectContent>
                    {availableTemplates.map((t) => (
                      <SelectItem key={t.id} value={t.id}>
                        {t.title}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </Field>
              {channel === "email" && (
                <>
                  <Field label="Subject">
                    <Input
                      value={subject}
                      onChange={(e) => setSubject(e.target.value)}
                    />
                  </Field>
                  <Select value={bodyType} onValueChange={setBodyType}>
                    <SelectTrigger>
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="plain_text">متن ساده</SelectItem>
                      <SelectItem value="html">HTML</SelectItem>
                    </SelectContent>
                  </Select>
                </>
              )}
              <Field label="متن پیام">
                <Textarea
                  className="min-h-44"
                  value={body}
                  onChange={(e) => setBody(e.target.value)}
                />
              </Field>
              {channel === "sms" && (
                <p className="text-xs text-muted-foreground">
                  {body.length} کاراکتر ·{" "}
                  {Math.max(
                    1,
                    Math.ceil(body.length / (body.length > 70 ? 67 : 70)),
                  )}{" "}
                  segment
                </p>
              )}
              <div className="rounded-lg border bg-muted/30 p-3">
                <Label>دستیار هوش مصنوعی کمپین</Label>
                <Textarea
                  className="mt-2"
                  placeholder="هدف، لحن و پیشنهاد کمپین را توضیح دهید..."
                  value={aiPrompt}
                  onChange={(e) => setAiPrompt(e.target.value)}
                />
                <Button
                  className="mt-2 w-full"
                  variant="outline"
                  disabled={!aiPrompt || aiBusy}
                  onClick={generateAi}
                >
                  {aiBusy ? (
                    <Loader2 className="ml-2 h-4 w-4 animate-spin" />
                  ) : (
                    <Wand2 className="ml-2 h-4 w-4" />
                  )}
                  تولید متن کمپین با AI
                </Button>
              </div>
            </div>
          )}
          {step === 5 && (
            <div className="mx-auto max-w-2xl space-y-4">
              <div className="grid grid-cols-2 gap-3">
                <Summary label="نام" value={name} />
                <Summary label="کانال" value={channel.toUpperCase()} />
                <Summary
                  label="Provider"
                  value={
                    providers.find((p) => p.id === providerId)?.name || "—"
                  }
                />
                <Summary
                  label="انتخاب مخاطب"
                  value={`${contactIds.length} مخاطب + ${groupIds.length} گروه`}
                />
              </div>
              <div className="rounded-lg border p-4">
                <p className="mb-2 font-medium">پیش‌نمایش متن</p>
                {subject && <p className="mb-2 font-semibold">{subject}</p>}
                <p className="whitespace-pre-wrap text-sm">{body}</p>
              </div>
              {!savedId ? (
                <Button className="w-full" onClick={save} disabled={busy}>
                  {busy && <Loader2 className="ml-2 h-4 w-4 animate-spin" />}
                  ذخیره پیش‌نویس و آماده‌سازی تست
                </Button>
              ) : (
                <div className="space-y-3 rounded-lg border bg-muted/30 p-4">
                  <Field label={channel === "sms" ? "شماره تست" : "ایمیل تست"}>
                    <Input
                      dir="ltr"
                      value={testRecipient}
                      onChange={(e) => setTestRecipient(e.target.value)}
                    />
                  </Field>
                  <div className="flex gap-2">
                    <Button
                      variant="outline"
                      className="flex-1"
                      disabled={!testRecipient}
                      onClick={sendTest}
                    >
                      ارسال تست
                    </Button>
                    <Button className="flex-1" onClick={() => start()}>
                      شروع کمپین
                    </Button>
                  </div>
                </div>
              )}
            </div>
          )}
          <div className="mt-6 flex justify-between">
            <Button
              variant="outline"
              disabled={step === 1 || !!savedId}
              onClick={() => setStep(step - 1)}
            >
              <ChevronRight className="ml-1 h-4 w-4" />
              قبلی
            </Button>
            {step < 5 && (
              <Button
                disabled={
                  (step === 1 && !name) ||
                  (step === 2 && !providerId) ||
                  (step === 3 && !contactIds.length && !groupIds.length) ||
                  (step === 4 && (!body || (channel === "email" && !subject)))
                }
                onClick={() => setStep(step + 1)}
              >
                بعدی
                <ChevronLeft className="mr-1 h-4 w-4" />
              </Button>
            )}
          </div>
        </CardContent>
      </Card>
      <Card>
        <CardHeader>
          <CardTitle>کمپین‌های ذخیره‌شده</CardTitle>
        </CardHeader>
        <CardContent>
          <CampaignTable
            campaigns={campaigns}
            action={(c) =>
              c.status === "draft" ? (
                <Button size="sm" onClick={() => start(c.id)}>
                  <Play className="ml-1 h-3 w-3" />
                  شروع
                </Button>
              ) : undefined
            }
          />
        </CardContent>
      </Card>
    </div>
  );
}

function ReportsView({
  wid,
  campaigns,
}: {
  wid: string;
  campaigns: Campaign[];
}) {
  const [selected, setSelected] = useState<Campaign | null>(null);
  const [messages, setMessages] = useState<MessageLog[]>([]);
  const [loading, setLoading] = useState(false);
  const [statusFilter, setStatusFilter] = useState("all");
  const [messageSearch, setMessageSearch] = useState("");
  const filteredMessages = messages.filter((message) => {
    const recipient =
      `${message.recipient_name} ${message.recipient_phone} ${message.recipient_email}`.toLowerCase();
    return (
      (statusFilter === "all" || message.status === statusFilter) &&
      recipient.includes(messageSearch.trim().toLowerCase())
    );
  });
  const open = async (campaign: Campaign) => {
    setSelected(campaign);
    setLoading(true);
    const response = await apiFetch(
      `/workspaces/${wid}/communication/campaigns/${campaign.id}/messages/`,
    );
    setMessages(response.data);
    setStatusFilter("all");
    setMessageSearch("");
    setLoading(false);
  };
  return (
    <div className="pt-4">
      <Card>
        <CardHeader>
          <CardTitle>گزارش کمپین‌ها</CardTitle>
        </CardHeader>
        <CardContent>
          <CampaignTable
            campaigns={campaigns}
            action={(c) => (
              <Button size="sm" variant="outline" onClick={() => open(c)}>
                مشاهده گزارش
              </Button>
            )}
          />
        </CardContent>
      </Card>
      <Dialog open={!!selected} onOpenChange={(v) => !v && setSelected(null)}>
        <DialogContent className="max-h-[90vh] max-w-5xl overflow-auto">
          <DialogHeader>
            <DialogTitle>گزارش {selected?.name}</DialogTitle>
          </DialogHeader>
          {selected && (
            <>
              <div className="grid grid-cols-4 gap-3">
                <Summary
                  label="گیرندگان"
                  value={selected.valid_recipients_count}
                />
                <Summary label="موفق" value={selected.sent_count} />
                <Summary label="ناموفق" value={selected.failed_count} />
                <Summary
                  label="نرخ موفقیت"
                  value={`${selected.success_rate}%`}
                />
              </div>
              {loading ? (
                <Loader2 className="mx-auto my-10 h-7 w-7 animate-spin" />
              ) : (
                <div className="space-y-3">
                  <div className="grid gap-3 md:grid-cols-[1fr_220px]">
                    <Input
                      placeholder="جست‌وجوی نام، شماره یا ایمیل گیرنده"
                      value={messageSearch}
                      onChange={(e) => setMessageSearch(e.target.value)}
                    />
                    <Select
                      value={statusFilter}
                      onValueChange={setStatusFilter}
                    >
                      <SelectTrigger>
                        <SelectValue />
                      </SelectTrigger>
                      <SelectContent>
                        <SelectItem value="all">همه وضعیت‌ها</SelectItem>
                        <SelectItem value="queued">در صف</SelectItem>
                        <SelectItem value="processing">در حال ارسال</SelectItem>
                        <SelectItem value="sent">موفق</SelectItem>
                        <SelectItem value="failed">ناموفق</SelectItem>
                        <SelectItem value="invalid">نامعتبر</SelectItem>
                      </SelectContent>
                    </Select>
                  </div>
                  <Table>
                    <TableHeader>
                      <TableRow>
                        <TableHead>گیرنده</TableHead>
                        <TableHead>پیام</TableHead>
                        <TableHead>وضعیت</TableHead>
                        <TableHead>خطا</TableHead>
                      </TableRow>
                    </TableHeader>
                    <TableBody>
                      {filteredMessages.map((m) => (
                        <TableRow key={m.id}>
                          <TableCell>
                            <p>{m.recipient_name || "—"}</p>
                            <p
                              className="text-xs text-muted-foreground"
                              dir="ltr"
                            >
                              {m.recipient_phone || m.recipient_email}
                            </p>
                            {m.is_test && <Badge variant="outline">تست</Badge>}
                          </TableCell>
                          <TableCell className="max-w-sm">
                            <p className="line-clamp-2 text-xs">
                              {m.rendered_body}
                            </p>
                          </TableCell>
                          <TableCell>
                            <StatusBadge value={m.status} />
                          </TableCell>
                          <TableCell className="max-w-xs text-xs text-destructive">
                            {m.error_message || "—"}
                          </TableCell>
                        </TableRow>
                      ))}
                    </TableBody>
                  </Table>
                  {filteredMessages.length === 0 && (
                    <Empty text="پیامی با این فیلتر پیدا نشد." />
                  )}
                </div>
              )}
            </>
          )}
        </DialogContent>
      </Dialog>
    </div>
  );
}

function CampaignTable({
  campaigns,
  action,
}: {
  campaigns: Campaign[];
  action?: (campaign: Campaign) => React.ReactNode;
}) {
  if (!campaigns.length) return <Empty text="هنوز کمپینی ساخته نشده است." />;
  return (
    <Table>
      <TableHeader>
        <TableRow>
          <TableHead>کمپین</TableHead>
          <TableHead>کانال</TableHead>
          <TableHead>وضعیت</TableHead>
          <TableHead>گیرندگان</TableHead>
          <TableHead>موفقیت</TableHead>
          <TableHead>تاریخ</TableHead>
          {action && <TableHead />}
        </TableRow>
      </TableHeader>
      <TableBody>
        {campaigns.map((c) => (
          <TableRow key={c.id}>
            <TableCell>
              <p className="font-medium">{c.name}</p>
              <p className="text-xs text-muted-foreground">{c.provider_name}</p>
            </TableCell>
            <TableCell>{c.channel === "sms" ? "SMS" : "Email"}</TableCell>
            <TableCell>
              <StatusBadge value={c.status} />
            </TableCell>
            <TableCell>{c.recipients_count.toLocaleString("fa-IR")}</TableCell>
            <TableCell>{c.success_rate}%</TableCell>
            <TableCell>
              {new Date(c.created_at).toLocaleDateString("fa-IR")}
            </TableCell>
            {action && <TableCell>{action(c)}</TableCell>}
          </TableRow>
        ))}
      </TableBody>
    </Table>
  );
}
function Field({
  label,
  children,
}: {
  label: string;
  children: React.ReactNode;
}) {
  return (
    <div className="space-y-1.5">
      <Label>{label}</Label>
      {children}
    </div>
  );
}
function Summary({ label, value }: { label: string; value: React.ReactNode }) {
  return (
    <div className="rounded-lg border bg-card p-3">
      <p className="text-xs text-muted-foreground">{label}</p>
      <p className="mt-1 font-semibold">{value}</p>
    </div>
  );
}
function Empty({ text }: { text: string }) {
  return (
    <div className="col-span-full flex min-h-28 items-center justify-center rounded-lg border-2 border-dashed text-sm text-muted-foreground">
      <CircleAlert className="ml-2 h-5 w-5" />
      {text}
    </div>
  );
}
