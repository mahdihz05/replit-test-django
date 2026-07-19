import { useState, useEffect, useRef } from "react";
import { useAuth } from "@/lib/auth";
import { apiFetch } from "@/lib/api";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle
} from "@/components/ui/dialog";
import {
  AlertDialog, AlertDialogAction, AlertDialogCancel, AlertDialogContent,
  AlertDialogDescription, AlertDialogFooter, AlertDialogHeader, AlertDialogTitle
} from "@/components/ui/alert-dialog";
import { useToast } from "@/hooks/use-toast";
import {
  Plus, Send, Share2, CheckCircle2, XCircle, Clock, Copy, RefreshCw,
  Trash2, Zap, AlertCircle, Loader2, Globe, Linkedin, ShieldCheck,
  BookOpen, ArrowLeft
} from "lucide-react";

interface Channel {
  id: string;
  platform: string;
  channel_type: string;
  name: string;
  external_id: string;
  username: string;
  is_verified: boolean;
  is_active: boolean;
  created_at: string;
  extra_data?: Record<string, any>;
  wordpress?: {
    status: "active" | "invalid" | "disconnected";
    site_name?: string;
    synced_at?: string | null;
    capabilities?: { post_types?: { slug: string; name: string }[] };
  } | null;
}

interface VerificationData {
  id: string;
  platform: string;
  token: string;
  status: string;
  expires_at: string;
  name?: string;
  channel_type?: string;
  instructions?: string;
  channel?: Channel;
}

const PLATFORM_NAMES: Record<string, string> = {
  telegram: "تلگرام",
  bale: "بله",
  linkedin: "LinkedIn",
  wordpress: "WordPress",
  website: "وب‌سایت",
};

const TYPE_NAMES: Record<string, string> = {
  channel: "کانال",
  group: "گروه",
  personal: "پروفایل شخصی",
  organization: "صفحه سازمانی",
  site: "سایت",
};

function getPlatformIcon(platform: string, size = "w-5 h-5") {
  if (platform === "telegram") return <Send className={`${size} text-blue-500`} />;
  if (platform === "bale") return <Share2 className={`${size} text-green-500`} />;
  if (platform === "linkedin") return <Linkedin className={`${size} text-blue-700`} />;
  if (platform === "wordpress") return <Globe className={`${size} text-blue-600`} />;
  return <Share2 className={`${size} text-muted-foreground`} />;
}

interface LinkedInConfig {
  configured: boolean;
  credentials_configured: boolean;
  redirect_uri: string;
  redirect_is_https: boolean;
  api_version: string;
  missing: string[];
  required_products: string[];
  required_scopes: string[];
}

const CONNECTION_GUIDES: Record<string, { title: string; note: string; steps: string[] }> = {
  telegram: {
    title: "اتصال کانال یا گروه تلگرام",
    note: "رمز یا کد ورود تلگرام شما در هیچ مرحله‌ای از شما خواسته نمی‌شود.",
    steps: [
      "در تلگرام ربات @abrit_cloud_bot را باز کنید و آن را به کانال یا گروه موردنظر اضافه کنید.",
      "ربات @abrit_cloud_bot را Administrator کنید و حتماً مجوز Post Messages (ارسال پیام) را فعال نگه دارید.",
      "به محتوایار برگردید و نام نمایشی کانال و یکی از دو مقدار @username عمومی یا chat_id عددی کانال را وارد کنید.",
      "روی «ادامه» بزنید؛ سامانه ادمین‌بودن ربات و مجوز ارسال پیام را مستقیماً از تلگرام بررسی می‌کند.",
      "پس از تأیید موفق، کانال به فهرست کانال‌های انتشار اضافه و برای ارسال محتوا آماده می‌شود.",
    ],
  },
  bale: {
    title: "اتصال کانال یا گروه بله",
    note: "فقط ربات محتوایار به کانال دسترسی می‌گیرد؛ اطلاعات حساب شخصی شما دریافت نمی‌شود.",
    steps: [
      "ربات محتوایار را به کانال یا گروه بله اضافه کنید.",
      "ربات را مدیر کنید تا اجازه انتشار داشته باشد.",
      "کد تأییدی را که سامانه می‌سازد داخل کانال ارسال کنید.",
      "پس از شناسایی کد، کانال خودکار به لیست انتشار اضافه می‌شود.",
    ],
  },
  linkedin: {
    title: "اتصال امن حساب LinkedIn",
    note: "Client ID و Client Secret فقط یک‌بار توسط مدیر سامانه تنظیم می‌شوند و هرگز از کاربران دریافت نمی‌شوند. ورود شما فقط در صفحه رسمی linkedin.com انجام می‌شود.",
    steps: [
      "مدیر محتوایار یک LinkedIn App مرکزی را یک‌بار برای کل سامانه فعال می‌کند؛ کاربران نیازی به ساخت Developer App ندارند.",
      "پروفایل شخصی را انتخاب کنید و روی «اتصال به LinkedIn» بزنید.",
      "در صفحه رسمی linkedin.com وارد حساب خود شوید و مجوز پروفایل و انتشار را تأیید کنید.",
      "LinkedIn شما را به محتوایار برمی‌گرداند و حساب به‌صورت رمزنگاری‌شده به همین فضای کاری متصل می‌شود.",
    ],
  },
  wordpress: {
    title: "اتصال سایت WordPress",
    note: "برای امنیت بیشتر از Application Password استفاده می‌شود و رمز اصلی وردپرس لازم نیست.",
    steps: [
      "آدرس کامل و HTTPS سایت وردپرسی را وارد کنید.",
      "روی «دریافت مجوز» بزنید تا صفحه امن wp-admin همان سایت باز شود.",
      "در وردپرس وارد شوید و ساخت Application Password مخصوص محتوایار را تأیید کنید؛ رمز اصلی شما دریافت نمی‌شود.",
      "پس از بازگشت خودکار، نوع‌های محتوا و دسته‌بندی‌های سایت دریافت و انتشار آماده می‌شود.",
    ],
  },
};

function VerificationCountdown({ expiresAt }: { expiresAt: string }) {
  const [remaining, setRemaining] = useState(0);
  useEffect(() => {
    const calc = () => {
      const diff = Math.max(0, Math.floor((new Date(expiresAt).getTime() - Date.now()) / 1000));
      setRemaining(diff);
    };
    calc();
    const t = setInterval(calc, 1000);
    return () => clearInterval(t);
  }, [expiresAt]);

  const m = Math.floor(remaining / 60);
  const s = remaining % 60;
  const pct = (remaining / 600) * 100;
  const color = remaining < 60 ? "text-destructive" : remaining < 180 ? "text-amber-600" : "text-green-600";

  return (
    <div className="text-center">
      <div className={`text-3xl font-mono font-bold tabular-nums ${color}`}>
        {String(m).padStart(2, "0")}:{String(s).padStart(2, "0")}
      </div>
      <div className="text-xs text-muted-foreground mt-1">زمان باقی‌مانده</div>
      <div className="h-1.5 rounded-full bg-muted mt-2 overflow-hidden">
        <div
          className={`h-full rounded-full transition-all duration-1000 ${remaining < 60 ? "bg-destructive" : "bg-primary"}`}
          style={{ width: `${pct}%` }}
        />
      </div>
    </div>
  );
}

export default function Channels() {
  const { selectedWorkspace } = useAuth();
  const { toast } = useToast();
  const [channels, setChannels] = useState<Channel[]>([]);
  const [loading, setLoading] = useState(false);
  const [testingId, setTestingId] = useState<string | null>(null);
  const [syncingId, setSyncingId] = useState<string | null>(null);
  const [deletingId, setDeletingId] = useState<string | null>(null);
  const [deleteTarget, setDeleteTarget] = useState<Channel | null>(null);

  // Modal state
  const [showModal, setShowModal] = useState(false);
  const [showGuide, setShowGuide] = useState(false);
  const [step, setStep] = useState<1 | 2 | 3 | 4>(1);
  const [platform, setPlatform] = useState<"telegram" | "bale" | "linkedin" | "wordpress" | "">("");
  const [channelType, setChannelType] = useState<"channel" | "group">("channel");
  const [channelName, setChannelName] = useState("");
  const [verification, setVerification] = useState<VerificationData | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const pollRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const popupRef = useRef<Window | null>(null);

  // LinkedIn / WordPress
  const [linkedinTarget, setLinkedinTarget] = useState<"personal" | "organization">("personal");
  const [linkedinConfig, setLinkedinConfig] = useState<LinkedInConfig | null>(null);
  const [linkedinConfigLoading, setLinkedinConfigLoading] = useState(false);
  const [wpSiteUrl, setWpSiteUrl] = useState("");
  const [oauthUrl, setOauthUrl] = useState<string | null>(null);
  const [checkingConnection, setCheckingConnection] = useState(false);
  const [botStatus, setBotStatus] = useState<{ loading: boolean; ok?: boolean; bot?: any; error?: string } | null>(null);
  const [manualChatId, setManualChatId] = useState("");
  const [manualUsername, setManualUsername] = useState("");
  const [manualVerifying, setManualVerifying] = useState(false);

  const fetchChannels = async () => {
    if (!selectedWorkspace) return;
    try {
      const res = await apiFetch(`/workspaces/${selectedWorkspace.id}/channels/`);
      setChannels(Array.isArray(res?.data) ? res.data : []);
    } catch {
      toast({ title: "خطا", description: "دریافت کانال‌ها ناموفق بود", variant: "destructive" });
    } finally {
      setLoading(false);
    }
  };

  const fetchLinkedinConfig = async () => {
    if (!selectedWorkspace) return;
    setLinkedinConfigLoading(true);
    try {
      const res = await apiFetch(`/workspaces/${selectedWorkspace.id}/linkedin/config/`);
      setLinkedinConfig(res?.data || null);
    } catch (e: any) {
      setLinkedinConfig(null);
      toast({ title: "خطا", description: e.message || "بررسی تنظیمات LinkedIn ناموفق بود", variant: "destructive" });
    } finally {
      setLinkedinConfigLoading(false);
    }
  };

  useEffect(() => {
    if (selectedWorkspace) {
      setLoading(true);
      fetchChannels();
    }
  }, [selectedWorkspace]);

  useEffect(() => {
    if (showModal && platform === "linkedin" && selectedWorkspace) {
      fetchLinkedinConfig();
    }
  }, [showModal, platform, selectedWorkspace?.id]);

  useEffect(() => {
    if (showModal && platform === "telegram" && selectedWorkspace) {
      checkBotStatus();
    }
  }, [showModal, platform, selectedWorkspace?.id]);

  // Listen for OAuth popup messages (LinkedIn & WordPress)
  useEffect(() => {
    const handler = (event: MessageEvent) => {
      if (!event.data || typeof event.data !== "object") return;
      const { platform, success, message } = event.data;
      if (!platform || (platform !== "linkedin" && platform !== "wordpress")) return;
      const allowedOrigins = new Set([window.location.origin]);
      if (platform === "linkedin" && linkedinConfig?.redirect_uri) {
        try {
          allowedOrigins.add(new URL(linkedinConfig.redirect_uri).origin);
        } catch {}
      }
      if (!allowedOrigins.has(event.origin)) return;
      if (popupRef.current && !popupRef.current.closed) {
        popupRef.current.close();
      }
      if (success) {
        setStep(4);
        fetchChannels();
      } else {
        toast({ title: "خطا در اتصال", description: message || "اتصال ناموفق بود", variant: "destructive" });
      }
    };
    window.addEventListener("message", handler);
    return () => window.removeEventListener("message", handler);
  }, [selectedWorkspace, toast, linkedinConfig?.redirect_uri]);

  const stopPolling = () => {
    if (pollRef.current) {
      clearInterval(pollRef.current);
      pollRef.current = null;
    }
  };

  const startPolling = (token: string) => {
    stopPolling();
    pollRef.current = setInterval(async () => {
      if (!selectedWorkspace) return;
      try {
        const res = await apiFetch(`/workspaces/${selectedWorkspace.id}/channels/verify/${token}/status/`);
        const data: VerificationData = res?.data;
        setVerification(data);
        if (data?.status === "verified") {
          stopPolling();
          setStep(4);
          fetchChannels();
        } else if (data?.status === "expired") {
          stopPolling();
          toast({ title: "کد منقضی شد", description: "کد تأیید منقضی شد. مجدد تلاش کنید.", variant: "destructive" });
        }
      } catch {}
    }, 1000);
  };

  useEffect(() => () => stopPolling(), []);

  useEffect(() => {
    if (step === 3 && platform === "telegram" && verification) {
      checkBotStatus();
    }
  }, [step, platform, verification]);

  const closeModal = () => {
    stopPolling();
    if (popupRef.current && !popupRef.current.closed) popupRef.current.close();
    setShowModal(false);
    setShowGuide(false);
    setStep(1);
    setPlatform("");
    setChannelType("channel");
    setChannelName("");
    setVerification(null);
    setSubmitting(false);
    setLinkedinTarget("personal");
    setLinkedinConfig(null);
    setLinkedinConfigLoading(false);
    setWpSiteUrl("");
    setOauthUrl(null);
    setCheckingConnection(false);
    setBotStatus(null);
    setManualChatId("");
    setManualUsername("");
    setManualVerifying(false);
  };

  const handleStartVerification = async () => {
    if (!selectedWorkspace || !channelName.trim()) return;
    setSubmitting(true);
    try {
      const res = await apiFetch(`/workspaces/${selectedWorkspace.id}/channels/verify/start/`, {
        method: "POST",
        data: { platform, channel_type: channelType, name: channelName.trim() },
      });
      const data: VerificationData = res?.data;
      data.name = channelName.trim();
      data.channel_type = channelType;
      setVerification(data);

      if (platform === "telegram" && (manualChatId.trim() || manualUsername.trim())) {
        const confirmed = await apiFetch(
          `/workspaces/${selectedWorkspace.id}/channels/verify/${data.token}/confirm/`,
          {
            method: "POST",
            data: {
              chat_id: manualChatId.trim(),
              username: manualUsername.trim(),
            },
          }
        );
        if (!confirmed?.success) {
          throw new Error(confirmed?.error || "تأیید کانال ناموفق بود");
        }
        setVerification({ ...data, status: "verified" });
        setStep(4);
        fetchChannels();
        return;
      }

      setStep(3);
      startPolling(data.token);
    } catch (e: any) {
      toast({ title: "خطا", description: e.message || "شروع تأیید ناموفق بود", variant: "destructive" });
    } finally {
      setSubmitting(false);
    }
  };

  const handleRetryVerification = async () => {
    if (!selectedWorkspace || !verification) return;
    setSubmitting(true);
    try {
      const res = await apiFetch(
        `/workspaces/${selectedWorkspace.id}/channels/verify/${verification.token}/retry/`,
        { method: "POST" }
      );
      const data: VerificationData = res?.data;
      data.name = verification.name;
      data.channel_type = verification.channel_type;
      setVerification(data);
      startPolling(data.token);
    } catch (e: any) {
      toast({ title: "خطا", description: e.message || "تجدید کد ناموفق بود", variant: "destructive" });
    } finally {
      setSubmitting(false);
    }
  };

  const openOAuthPopup = (url: string) => {
    const width = 600;
    const height = 700;
    const left = window.screenX + (window.outerWidth - width) / 2;
    const top = window.screenY + (window.outerHeight - height) / 2;
    popupRef.current = window.open(
      url,
      "oauth",
      `width=${width},height=${height},left=${left},top=${top},resizable=yes,scrollbars=yes`
    );
  };

  const handleLinkedinStart = async () => {
    if (!selectedWorkspace) return;
    setSubmitting(true);
    try {
      const res = await apiFetch(`/workspaces/${selectedWorkspace.id}/linkedin/connect/start/`, {
        method: "POST",
        data: { platform_target: linkedinTarget, origin: window.location.origin },
      });
      const url = res?.data?.authorization_url;
      if (url) {
        setOauthUrl(url);
        openOAuthPopup(url);
        setStep(3);
      } else {
        throw new Error(res?.error || "آدرس OAuth دریافت نشد");
      }
    } catch (e: any) {
      toast({ title: "خطا", description: e.message || "شروع اتصال LinkedIn ناموفق بود", variant: "destructive" });
    } finally {
      setSubmitting(false);
    }
  };

  const checkForConnection = async () => {
    if (!selectedWorkspace) return;
    setCheckingConnection(true);
    try {
      const res = await apiFetch(`/workspaces/${selectedWorkspace.id}/channels/?platform=${platform}`);
      const list = Array.isArray(res?.data) ? res.data : [];
      if (list.length > 0) {
        stopPolling();
        setStep(4);
        fetchChannels();
      } else {
        toast({ title: "هنوز متصل نشده", description: "هنوز اتصال تأیید نشده است. دوباره بررسی کنید." });
      }
    } catch (e: any) {
      toast({ title: "خطا", description: e.message || "بررسی اتصال ناموفق بود", variant: "destructive" });
    } finally {
      setCheckingConnection(false);
    }
  };

  const checkBotStatus = async () => {
    if (!selectedWorkspace || platform !== "telegram") return;
    setBotStatus({ loading: true });
    try {
      const res = await apiFetch(`/workspaces/${selectedWorkspace.id}/telegram-bot-status/`);
      if (res?.success && res?.data?.bot) {
        setBotStatus({ loading: false, ok: true, bot: res.data.bot });
      } else {
        setBotStatus({ loading: false, ok: false, error: res?.error || "وضعیت ربات نامشخص است" });
      }
    } catch (e: any) {
      setBotStatus({ loading: false, ok: false, error: e.message || "خطا در بررسی وضعیت ربات" });
    }
  };

  const handleManualVerify = async () => {
    if (!selectedWorkspace || !verification) return;
    if (!manualChatId.trim() && !manualUsername.trim()) {
      toast({ title: "ورودی خالی", description: "chat_id یا username کانال را وارد کنید", variant: "destructive" });
      return;
    }
    setManualVerifying(true);
    try {
      const res = await apiFetch(
        `/workspaces/${selectedWorkspace.id}/channels/verify/${verification.token}/confirm/`,
        {
          method: "POST",
          data: {
            chat_id: manualChatId.trim(),
            username: manualUsername.trim(),
          },
        }
      );
      if (res?.success) {
        toast({ title: "✅ تأیید شد", description: res?.data?.message || "کانال تأیید شد" });
        stopPolling();
        setStep(4);
        fetchChannels();
      } else {
        throw new Error(res?.error || "تأیید دستی ناموفق بود");
      }
    } catch (e: any) {
      toast({ title: "خطا در تأیید دستی", description: e.message || "خطا", variant: "destructive" });
    } finally {
      setManualVerifying(false);
    }
  };

  const handleWordpressStart = async () => {
    if (!selectedWorkspace || !wpSiteUrl.trim()) return;
    setSubmitting(true);
    try {
      const res = await apiFetch(`/workspaces/${selectedWorkspace.id}/wordpress/connect/start/`, {
        method: "POST",
        data: { site_url: wpSiteUrl.trim(), origin: window.location.origin },
      });
      const url = res?.data?.authorization_url;
      if (url) {
        setOauthUrl(url);
        openOAuthPopup(url);
        setStep(3);
      } else {
        throw new Error(res?.error || "آدرس WordPress دریافت نشد");
      }
    } catch (e: any) {
      toast({ title: "خطا", description: e.message || "شروع اتصال WordPress ناموفق بود", variant: "destructive" });
    } finally {
      setSubmitting(false);
    }
  };

  const handleTestChannel = async (channel: Channel) => {
    if (!selectedWorkspace) return;
    setTestingId(channel.id);
    try {
      await apiFetch(`/workspaces/${selectedWorkspace.id}/channels/${channel.id}/test/`, {
        method: "POST",
      });
      toast({ title: "✅ موفق", description: "پیام آزمایشی با موفقیت ارسال شد" });
    } catch (e: any) {
      toast({ title: "ارسال ناموفق", description: e.message || "خطا در ارسال پیام آزمایشی", variant: "destructive" });
    } finally {
      setTestingId(null);
    }
  };

  const handleDeleteChannel = async () => {
    if (!selectedWorkspace || !deleteTarget) return;
    setDeletingId(deleteTarget.id);
    try {
      await apiFetch(`/workspaces/${selectedWorkspace.id}/channels/${deleteTarget.id}/`, {
        method: "DELETE",
      });
      setChannels(prev => prev.filter(c => c.id !== deleteTarget.id));
      toast({ title: "کانال حذف شد" });
    } catch (e: any) {
      toast({ title: "خطا", description: e.message || "حذف ناموفق بود", variant: "destructive" });
    } finally {
      setDeletingId(null);
      setDeleteTarget(null);
    }
  };

  const copyToken = (token: string) => {
    navigator.clipboard.writeText(token);
    toast({ title: "کپی شد", description: "کد تأیید کپی شد" });
  };

  const handleWordpressSync = async (channel: Channel) => {
    if (!selectedWorkspace) return;
    setSyncingId(channel.id);
    try {
      const res = await apiFetch(`/workspaces/${selectedWorkspace.id}/channels/${channel.id}/wordpress/capabilities/`, {
        method: "POST",
      });
      setChannels(prev => prev.map(item => item.id === channel.id
        ? { ...item, name: res.data.site_name || item.name, wordpress: { ...(item.wordpress || { status: "active" }), ...res.data } }
        : item));
      toast({ title: "اطلاعات وردپرس به‌روز شد", description: "نوع‌های محتوا و طبقه‌بندی‌ها دوباره دریافت شدند" });
    } catch (e: any) {
      toast({ title: "به‌روزرسانی ناموفق", description: e.message || "اتصال سایت را بررسی کنید", variant: "destructive" });
    } finally {
      setSyncingId(null);
    }
  };

  const copyLinkedinCallback = () => {
    if (!linkedinConfig?.redirect_uri) return;
    navigator.clipboard.writeText(linkedinConfig.redirect_uri);
    toast({ title: "کپی شد", description: "آدرس Callback لینکدین کپی شد" });
  };

  const telegramBotUsername = botStatus?.ok && botStatus.bot?.username
    ? `@${botStatus.bot.username}`
    : "@abrit_cloud_bot";
  const telegramBotUrl = `https://t.me/${telegramBotUsername.replace("@", "")}`;
  const formatTelegramGuideText = (text: string) => text.replaceAll("@abrit_cloud_bot", telegramBotUsername);

  const copyTelegramBotUsername = () => {
    navigator.clipboard.writeText(telegramBotUsername);
    toast({ title: "کپی شد", description: "شناسه ربات تلگرام کپی شد" });
  };

  const isBotPlatform = platform === "telegram" || platform === "bale";
  const isLinkedIn = platform === "linkedin";
  const isWordPress = platform === "wordpress";

  return (
    <div className="space-y-6">
      <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">کانال‌ها</h1>
          <p className="text-muted-foreground mt-1">مدیریت کانال‌های انتشار محتوا</p>
        </div>
        <div className="flex items-center gap-2">
          <Button variant="outline" size="sm" onClick={fetchChannels}>
            <RefreshCw className="w-4 h-4" />
          </Button>
          <Button className="gap-2" onClick={() => setShowModal(true)}>
            <Plus className="w-4 h-4" />
            افزودن کانال
          </Button>
        </div>
      </div>

      {loading ? (
        <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
          {[1, 2, 3].map(i => (
            <Card key={i} className="animate-pulse h-40" />
          ))}
        </div>
      ) : channels.length === 0 ? (
        <Card>
          <CardContent className="flex flex-col items-center justify-center py-16 text-center gap-4">
            <Share2 className="w-12 h-12 text-muted-foreground/30" />
            <div>
              <p className="font-medium text-muted-foreground">هنوز کانالی اضافه نشده</p>
              <p className="text-sm text-muted-foreground/70 mt-1">برای انتشار محتوا ابتدا یک کانال اضافه کنید</p>
            </div>
            <Button className="gap-2" onClick={() => setShowModal(true)}>
              <Plus className="w-4 h-4" />
              افزودن اولین کانال
            </Button>
          </CardContent>
        </Card>
      ) : (
        <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
          {channels.map(channel => (
            <Card key={channel.id} className="relative">
              <CardHeader className="pb-3">
                <div className="flex items-start justify-between gap-2">
                  <CardTitle className="text-base font-medium flex items-center gap-2 leading-snug">
                    {getPlatformIcon(channel.platform)}
                    <span>{channel.name}</span>
                  </CardTitle>
                  {channel.is_verified ? (
                    <CheckCircle2 className="w-5 h-5 text-green-500 shrink-0 mt-0.5" />
                  ) : (
                    <XCircle className="w-5 h-5 text-destructive shrink-0 mt-0.5" />
                  )}
                </div>
                <div className="flex items-center gap-2 mt-2 flex-wrap">
                  <Badge variant="outline" className="text-xs">
                    {PLATFORM_NAMES[channel.platform] || channel.platform}
                  </Badge>
                  {channel.channel_type && channel.channel_type !== "site" && (
                    <Badge variant="secondary" className="text-xs">
                      {TYPE_NAMES[channel.channel_type] || channel.channel_type}
                    </Badge>
                  )}
                  <Badge
                    variant="outline"
                    className={`text-xs ${channel.is_verified ? "text-green-700 border-green-300 bg-green-50" : "text-amber-700 border-amber-300 bg-amber-50"}`}
                  >
                    {channel.is_verified ? "تأیید شده" : "در انتظار تأیید"}
                  </Badge>
                  {channel.platform === "wordpress" && channel.wordpress?.status === "invalid" && (
                    <Badge variant="destructive" className="text-xs">نیازمند اتصال مجدد</Badge>
                  )}
                </div>
              </CardHeader>
              <CardContent>
                {channel.username && (
                  <p className="text-xs text-muted-foreground mb-3 dir-ltr text-right">@{channel.username}</p>
                )}
                {channel.external_id && channel.platform === "wordpress" && (
                  <p className="text-xs text-muted-foreground mb-3 dir-ltr text-right">{channel.external_id}</p>
                )}
                {channel.platform === "wordpress" && channel.wordpress?.synced_at && (
                  <p className="text-xs text-muted-foreground mb-3">
                    آخرین به‌روزرسانی: {new Date(channel.wordpress.synced_at).toLocaleString("fa-IR")}
                  </p>
                )}
                <div className="flex items-center gap-2 flex-wrap">
                  {channel.is_verified && (channel.platform === "telegram" || channel.platform === "bale" || channel.platform === "wordpress") && (
                    <Button
                      variant="outline"
                      size="sm"
                      className="gap-1.5 text-xs"
                      onClick={() => handleTestChannel(channel)}
                      disabled={testingId === channel.id}
                    >
                      {testingId === channel.id ? (
                        <Loader2 className="w-3 h-3 animate-spin" />
                      ) : (
                        <Zap className="w-3 h-3" />
                      )}
                      {channel.platform === "wordpress" ? "بررسی اتصال" : "تست اتصال"}
                    </Button>
                  )}
                  {channel.platform === "wordpress" && channel.is_verified && (
                    <Button variant="outline" size="sm" className="gap-1.5 text-xs"
                      onClick={() => handleWordpressSync(channel)} disabled={syncingId === channel.id}>
                      <RefreshCw className={`w-3 h-3 ${syncingId === channel.id ? "animate-spin" : ""}`} />
                      به‌روزرسانی اطلاعات
                    </Button>
                  )}
                  <Button
                    variant="ghost"
                    size="sm"
                    className="gap-1.5 text-xs text-destructive hover:bg-destructive/10 hover:text-destructive"
                    onClick={() => setDeleteTarget(channel)}
                    disabled={!!deletingId}
                  >
                    <Trash2 className="w-3 h-3" />
                    حذف
                  </Button>
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
      )}

      {/* Add Channel Modal */}
      <Dialog open={showModal} onOpenChange={open => !open && closeModal()}>
        <DialogContent className="max-h-[90vh] overflow-y-auto sm:max-w-md">
          <DialogHeader>
            <DialogTitle>افزودن کانال جدید</DialogTitle>
            <DialogDescription>
              {step === 1 && "پلتفرم مورد نظر خود را انتخاب کنید"}
              {step === 2 && "اطلاعات اتصال را وارد کنید"}
              {step === 3 && (isLinkedIn || isWordPress) && "تأیید را در پنجره بازشو کامل کنید"}
              {step === 3 && isBotPlatform && "کد زیر را در کانال خود ارسال کنید"}
              {step === 4 && "کانال با موفقیت تأیید شد!"}
            </DialogDescription>
          </DialogHeader>

          {step === 1 && (
            <div className="space-y-4">
              <div className="grid grid-cols-2 gap-4">
                {([
                  ["telegram", "تلگرام"],
                  ["bale", "بله"],
                  ["linkedin", "LinkedIn"],
                  ["wordpress", "WordPress"],
                ] as const).map(([p, label]) => (
                  <button
                    key={p}
                    onClick={() => { setPlatform(p); setShowGuide(true); setStep(2); }}
                    className={`flex flex-col items-center gap-3 p-6 rounded-lg border-2 transition-all hover:border-primary hover:bg-primary/5 ${platform === p ? "border-primary bg-primary/5" : "border-border"}`}
                  >
                    {getPlatformIcon(p, "w-10 h-10")}
                    <span className="font-medium">{label}</span>
                  </button>
                ))}
              </div>
            </div>
          )}

          {step === 2 && showGuide && platform && (
            <div className="space-y-5">
              <div className="flex items-center gap-3 rounded-xl border bg-muted/40 p-4">
                <div className="flex h-12 w-12 shrink-0 items-center justify-center rounded-xl bg-background shadow-sm">
                  {getPlatformIcon(platform, "w-7 h-7")}
                </div>
                <div>
                  <div className="flex items-center gap-2 text-xs text-primary">
                    <BookOpen className="h-3.5 w-3.5" />
                    راهنمای اتصال
                  </div>
                  <h3 className="mt-1 font-semibold">{CONNECTION_GUIDES[platform].title}</h3>
                </div>
              </div>

              <div className="space-y-3">
                {CONNECTION_GUIDES[platform].steps.map((item, index) => (
                  <div key={item} className="flex gap-3 rounded-lg border p-3">
                    <span className="flex h-7 w-7 shrink-0 items-center justify-center rounded-full bg-primary text-xs font-bold text-primary-foreground">
                      {index + 1}
                    </span>
                    <p className="pt-0.5 text-sm leading-6">{platform === "telegram" ? formatTelegramGuideText(item) : item}</p>
                  </div>
                ))}
              </div>

              {platform === "telegram" && (
                <div className="space-y-3 rounded-xl border border-blue-200 bg-blue-50 p-4">
                  <div className="flex items-start gap-3">
                    <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-full bg-blue-600 text-white">
                      <Send className="h-5 w-5" />
                    </div>
                    <div className="min-w-0 flex-1">
                      <p className="text-sm font-semibold text-blue-950">ربات رسمی محتوایار در تلگرام</p>
                      <p className="mt-1 text-xs leading-5 text-blue-800">
                        فقط همین ربات را به کانال اضافه و Administrator کنید.
                      </p>
                    </div>
                  </div>

                  <div className="flex gap-2" dir="ltr">
                    <Input value={telegramBotUsername} readOnly className="bg-white font-mono font-semibold text-blue-900" />
                    <Button type="button" variant="outline" size="icon" onClick={copyTelegramBotUsername} aria-label="کپی شناسه ربات">
                      <Copy className="h-4 w-4" />
                    </Button>
                  </div>

                  <Button asChild type="button" variant="outline" className="w-full gap-2 border-blue-300 bg-white text-blue-800 hover:bg-blue-100">
                    <a href={telegramBotUrl} target="_blank" rel="noreferrer">
                      <Send className="h-4 w-4" />
                      باز کردن ربات در تلگرام
                    </a>
                  </Button>

                  <div className="rounded-lg bg-white p-3 text-xs leading-6 text-blue-900">
                    <p><strong>مجوز ضروری:</strong> پس از افزودن ربات، در تنظیمات Administrators کانال گزینه ارسال پیام یا <span dir="ltr">Post Messages</span> را فعال کنید؛ بدون این مجوز تأیید انجام نمی‌شود.</p>
                  </div>
                </div>
              )}

              {platform === "linkedin" && (
                <div className="space-y-3 rounded-xl border border-blue-200 bg-blue-50 p-4">
                  <div className="flex items-center justify-between gap-3">
                    <div>
                      <p className="text-sm font-semibold text-blue-950">وضعیت تنظیمات این سرور</p>
                      <p className="mt-1 text-xs text-blue-800">
                        هیچ Client Secret یا توکنی در این صفحه نمایش داده نمی‌شود.
                      </p>
                    </div>
                    {linkedinConfigLoading ? (
                      <Loader2 className="h-5 w-5 animate-spin text-blue-700" />
                    ) : linkedinConfig?.configured ? (
                      <Badge className="bg-green-600">آماده اتصال</Badge>
                    ) : (
                      <Badge variant="destructive">نیازمند تنظیم</Badge>
                    )}
                  </div>

                  {linkedinConfig?.redirect_uri ? (
                    <div className="space-y-2">
                      <Label className="text-xs text-blue-950">Authorized redirect URL (عیناً ثبت شود)</Label>
                      <div className="flex gap-2" dir="ltr">
                        <Input value={linkedinConfig.redirect_uri} readOnly className="bg-white font-mono text-xs" />
                        <Button type="button" variant="outline" size="icon" onClick={copyLinkedinCallback} aria-label="کپی Callback">
                          <Copy className="h-4 w-4" />
                        </Button>
                      </div>
                    </div>
                  ) : (
                    !linkedinConfigLoading && (
                      <p className="rounded-lg bg-white p-3 text-xs text-destructive">
                        متغیر LINKEDIN_REDIRECT_URI هنوز روی سرور تنظیم نشده است.
                      </p>
                    )
                  )}

                  {linkedinConfig && !linkedinConfig.configured && (
                    <div className="space-y-1 text-xs text-destructive">
                      {!linkedinConfig.credentials_configured && (
                        <p>اتصال LinkedIn هنوز توسط مدیر سامانه فعال نشده است؛ کاربران نباید Client Secret شخصی وارد کنند.</p>
                      )}
                      {!linkedinConfig.redirect_is_https && linkedinConfig.redirect_uri && (
                        <p>Callback باید HTTPS باشد؛ برای لوکال اسکریپت start-linkedin-local.ps1 را اجرا کنید.</p>
                      )}
                    </div>
                  )}

                  <div className="rounded-lg bg-white p-3 text-xs leading-6 text-blue-900">
                    <p className="font-medium">تست لوکال با HTTPS توسعه</p>
                    <p>۱) اسکریپت start-linkedin-local.ps1 را اجرا کنید. ۲) هشدار گواهی localhost را یک‌بار در مرورگر تأیید کنید. ۳) Callback نمایش‌داده‌شده را عیناً در تب Auth لینکدین ثبت کنید.</p>
                    <p className="mt-1">نسخه API فعال: <span dir="ltr" className="font-mono">{linkedinConfig?.api_version || "—"}</span></p>
                  </div>
                </div>
              )}

              <div className="flex gap-2 rounded-lg border border-green-200 bg-green-50 p-3 text-xs leading-5 text-green-800">
                <ShieldCheck className="mt-0.5 h-4 w-4 shrink-0" />
                <span>{CONNECTION_GUIDES[platform].note}</span>
              </div>

              <div className="flex gap-2">
                <Button variant="outline" onClick={() => { setShowGuide(false); setStep(1); }} className="flex-1">
                  برگشت
                </Button>
                <Button onClick={() => setShowGuide(false)} className="flex-1 gap-2">
                  شروع اتصال
                  <ArrowLeft className="h-4 w-4" />
                </Button>
              </div>
            </div>
          )}

          {step === 2 && !showGuide && isBotPlatform && (
            <div className="space-y-4">
              <div className="flex items-center gap-2 p-3 bg-muted rounded-lg">
                {getPlatformIcon(platform)}
                <span className="text-sm font-medium">{PLATFORM_NAMES[platform]}</span>
              </div>

              <div className="space-y-2">
                <Label>نوع</Label>
                <div className="grid grid-cols-2 gap-2">
                  {(["channel", "group"] as const).map(t => (
                    <button
                      key={t}
                      onClick={() => setChannelType(t)}
                      className={`p-3 rounded-lg border-2 text-sm font-medium transition-all ${channelType === t ? "border-primary bg-primary/5 text-primary" : "border-border hover:border-muted-foreground"}`}
                    >
                      {TYPE_NAMES[t]}
                    </button>
                  ))}
                </div>
              </div>

              <div className="space-y-2">
                <Label htmlFor="ch-name">نام نمایشی</Label>
                <Input
                  id="ch-name"
                  placeholder="مثال: کانال اخبار ما"
                  value={channelName}
                  onChange={e => setChannelName(e.target.value)}
                  onKeyDown={e => {
                    const hasTelegramTarget = manualChatId.trim() || manualUsername.trim();
                    if (e.key === "Enter" && channelName.trim() && (platform !== "telegram" || hasTelegramTarget)) {
                      handleStartVerification();
                    }
                  }}
                />
              </div>

              {platform === "telegram" && (
                <div className="space-y-3 rounded-lg border border-blue-200 bg-blue-50 p-3">
                  <div>
                    <Label>شناسه کانال تلگرام</Label>
                    <p className="mt-1 text-xs text-muted-foreground">
                      ربات <span dir="ltr" className="font-semibold">{telegramBotUsername}</span> را اضافه و ادمین کنید، سپس یکی از موارد زیر را وارد کنید.
                    </p>
                  </div>
                  <div className="grid grid-cols-2 gap-2">
                    <Input
                      placeholder="chat_id مانند -100..."
                      value={manualChatId}
                      onChange={e => setManualChatId(e.target.value)}
                      className="dir-ltr"
                    />
                    <Input
                      placeholder="@username کانال"
                      value={manualUsername}
                      onChange={e => setManualUsername(e.target.value)}
                      className="dir-ltr"
                    />
                  </div>
                  <p className="text-xs text-blue-700">
                    سامانه مستقیماً ادمین بودن و مجوز ارسال پیام ربات را بررسی می‌کند.
                  </p>
                </div>
              )}

              <div className="flex gap-2 pt-2">
                <Button variant="outline" onClick={() => setStep(1)} className="flex-1">
                  برگشت
                </Button>
                <Button
                  onClick={handleStartVerification}
                  disabled={
                    !channelName.trim() ||
                    submitting ||
                    (platform === "telegram" && !manualChatId.trim() && !manualUsername.trim())
                  }
                  className="flex-1 gap-2"
                >
                  {submitting ? <Loader2 className="w-4 h-4 animate-spin" /> : null}
                  ادامه
                </Button>
              </div>
            </div>
          )}

          {step === 2 && !showGuide && isLinkedIn && (
            <div className="space-y-4">
              <div className="flex items-center gap-2 p-3 bg-muted rounded-lg">
                {getPlatformIcon("linkedin")}
                <span className="text-sm font-medium">LinkedIn</span>
              </div>

              <div className="space-y-2">
                <Label>هدف انتشار</Label>
                <div className="grid grid-cols-2 gap-2">
                  {(["personal", "organization"] as const).map(t => (
                    <button
                      key={t}
                      disabled={t === "organization"}
                      onClick={() => setLinkedinTarget(t)}
                      className={`p-3 rounded-lg border-2 text-sm font-medium transition-all ${t === "organization" ? "cursor-not-allowed opacity-50" : ""} ${linkedinTarget === t ? "border-primary bg-primary/5 text-primary" : "border-border hover:border-muted-foreground"}`}
                    >
                      {TYPE_NAMES[t]} {t === "organization" && <span className="text-[10px]">(نیازمند تأیید)</span>}
                    </button>
                  ))}
                </div>
                <p className="text-xs text-muted-foreground">
                  اتصال صفحه سازمانی به تأیید Community Management API از طرف LinkedIn نیاز دارد؛ پروفایل شخصی اکنون قابل اتصال است.
                </p>
              </div>

              <div className={`flex items-start gap-2 rounded-lg border p-3 text-xs leading-5 ${linkedinConfig?.configured ? "border-green-200 bg-green-50 text-green-800" : "border-amber-200 bg-amber-50 text-amber-900"}`}>
                {linkedinConfigLoading ? (
                  <Loader2 className="mt-0.5 h-4 w-4 shrink-0 animate-spin" />
                ) : linkedinConfig?.configured ? (
                  <CheckCircle2 className="mt-0.5 h-4 w-4 shrink-0" />
                ) : (
                  <AlertCircle className="mt-0.5 h-4 w-4 shrink-0" />
                )}
                <span>
                  {linkedinConfigLoading
                    ? "در حال بررسی تنظیمات سرور..."
                    : linkedinConfig?.configured
                      ? "تنظیمات سرور کامل است؛ Callback بالا باید عیناً در LinkedIn ثبت شده باشد."
                      : "اتصال LinkedIn هنوز توسط مدیر سامانه فعال نشده است؛ نیازی نیست شما Client ID یا Client Secret وارد کنید."}
                </span>
              </div>

              <div className="flex gap-2 pt-2">
                <Button variant="outline" onClick={() => setStep(1)} className="flex-1">
                  برگشت
                </Button>
                <Button
                  onClick={handleLinkedinStart}
                  disabled={submitting || linkedinConfigLoading || !linkedinConfig?.configured}
                  className="flex-1 gap-2"
                >
                  {submitting ? <Loader2 className="w-4 h-4 animate-spin" /> : <Linkedin className="w-4 h-4" />}
                  اتصال به LinkedIn
                </Button>
              </div>
            </div>
          )}

          {step === 2 && !showGuide && isWordPress && (
            <div className="space-y-4">
              <div className="flex items-center gap-2 p-3 bg-muted rounded-lg">
                {getPlatformIcon("wordpress")}
                <span className="text-sm font-medium">WordPress</span>
              </div>

              <div className="space-y-2">
                <Label htmlFor="wp-url">آدرس سایت (URL)</Label>
                <Input
                  id="wp-url"
                  placeholder="https://example.com"
                  value={wpSiteUrl}
                  onChange={e => setWpSiteUrl(e.target.value)}
                  className="dir-ltr"
                />
                <p className="text-xs text-muted-foreground">
                  فقط آدرس اصلی سایت را وارد کنید؛ مثل https://example.com. وردپرس روی هاست اشتراکی هم پشتیبانی می‌شود؛ آدرس wp-admin را وارد نکنید.
                </p>
              </div>

              <div className="flex gap-2 pt-2">
                <Button variant="outline" onClick={() => setStep(1)} className="flex-1">
                  برگشت
                </Button>
                <Button
                  onClick={handleWordpressStart}
                  disabled={!wpSiteUrl.trim() || submitting}
                  className="flex-1 gap-2"
                >
                  {submitting ? <Loader2 className="w-4 h-4 animate-spin" /> : <Globe className="w-4 h-4" />}
                  دریافت مجوز
                </Button>
              </div>
            </div>
          )}

          {step === 3 && (isLinkedIn || isWordPress) && (
            <div className="space-y-5">
              <div className="rounded-xl border-2 border-dashed border-primary/40 bg-primary/5 p-4 text-center space-y-2">
                <p className="text-sm font-medium">پنجره {PLATFORM_NAMES[platform]} باز شد</p>
                <p className="text-xs text-muted-foreground">
                  پس از ورود و تأیید دسترسی، این پنجره به‌صورت خودکار بسته می‌شود.
                </p>
              </div>

              <div className="flex items-center gap-2 text-sm text-muted-foreground">
                <Loader2 className="w-4 h-4 animate-spin" />
                در انتظار تأیید...
              </div>

              <Button
                onClick={checkForConnection}
                disabled={checkingConnection}
                className="w-full gap-2"
              >
                {checkingConnection ? <Loader2 className="w-4 h-4 animate-spin" /> : <RefreshCw className="w-4 h-4" />}
                بررسی دستی
              </Button>

              {oauthUrl && (
                <Button variant="outline" className="w-full" onClick={() => openOAuthPopup(oauthUrl)}>
                  باز کردن دوباره پنجره
                </Button>
              )}
            </div>
          )}

          {step === 3 && isBotPlatform && verification && (
            <div className="space-y-5">
              <VerificationCountdown expiresAt={verification.expires_at} />

              <div className="rounded-xl border-2 border-dashed border-primary/40 bg-primary/5 p-4 text-center space-y-2">
                <p className="text-xs text-muted-foreground">کد تأیید</p>
                <div className="flex items-center justify-center gap-2">
                  <code className="text-xl font-mono font-bold tracking-widest text-primary dir-ltr">
                    {verification.token}
                  </code>
                  <Button
                    variant="ghost"
                    size="icon"
                    className="w-8 h-8 shrink-0"
                    onClick={() => copyToken(verification.token)}
                  >
                    <Copy className="w-4 h-4" />
                  </Button>
                </div>
              </div>

              {verification.instructions && (
                <div className="rounded-lg bg-amber-50 border border-amber-200 p-3 text-sm text-amber-800 whitespace-pre-line leading-relaxed">
                  <AlertCircle className="w-4 h-4 inline ml-1" />
                  {verification.instructions}
                </div>
              )}

              {platform === "telegram" && botStatus && (
                <div
                  className={`rounded-lg border p-3 text-sm ${
                    botStatus.ok
                      ? "border-green-200 bg-green-50 text-green-800"
                      : botStatus.loading
                        ? "border-muted bg-muted text-muted-foreground"
                        : "border-red-200 bg-red-50 text-red-800"
                  }`}
                >
                  {botStatus.loading ? (
                    <span className="flex items-center gap-2">
                      <Loader2 className="w-4 h-4 animate-spin" />
                      در حال بررسی وضعیت ربات...
                    </span>
                  ) : botStatus.ok ? (
                    <span>ربات فعال: @{botStatus.bot?.username}</span>
                  ) : (
                    <span>مشکل در ربات تلگرام: {botStatus.error}</span>
                  )}
                </div>
              )}

              <div className="flex items-center gap-2 text-sm text-muted-foreground">
                <Loader2 className="w-4 h-4 animate-spin" />
                در انتظار تأیید خودکار...
              </div>

              <Button onClick={checkForConnection} disabled={checkingConnection} className="w-full gap-2">
                {checkingConnection ? <Loader2 className="w-4 h-4 animate-spin" /> : <RefreshCw className="w-4 h-4" />}
                بررسی وضعیت کانال
              </Button>

              <div className="rounded-lg border border-dashed p-3 space-y-3">
                <p className="text-sm font-medium">تأیید دستی</p>
                <p className="text-xs text-muted-foreground">
                  اگر تأیید خودکار انجام نشد، شناسه یا نام کاربری کانال را وارد کنید.
                </p>
                <div className="grid grid-cols-2 gap-2">
                  <Input
                    placeholder="chat_id"
                    value={manualChatId}
                    onChange={e => setManualChatId(e.target.value)}
                    className="dir-ltr"
                  />
                  <Input
                    placeholder="@username"
                    value={manualUsername}
                    onChange={e => setManualUsername(e.target.value)}
                    className="dir-ltr"
                  />
                </div>
                <Button
                  onClick={handleManualVerify}
                  disabled={manualVerifying || (!manualChatId.trim() && !manualUsername.trim())}
                  variant="outline"
                  className="w-full gap-2"
                >
                  {manualVerifying ? <Loader2 className="w-4 h-4 animate-spin" /> : <CheckCircle2 className="w-4 h-4" />}
                  تأیید دستی کانال
                </Button>
              </div>

              {verification.status === "expired" && (
                <Button onClick={handleRetryVerification} disabled={submitting} className="w-full gap-2">
                  {submitting ? <Loader2 className="w-4 h-4 animate-spin" /> : <RefreshCw className="w-4 h-4" />}
                  دریافت کد جدید
                </Button>
              )}
            </div>
          )}

          {step === 4 && (
            <div className="text-center space-y-4 py-4">
              <CheckCircle2 className="w-16 h-16 text-green-500 mx-auto" />
              <div>
                <h3 className="font-semibold text-lg">کانال با موفقیت متصل شد!</h3>
                <p className="text-sm text-muted-foreground mt-1">
                  {verification?.channel?.name || channelName || "کانال"} به سامانه اضافه شد
                </p>
              </div>
              <Button onClick={closeModal} className="w-full">
                بستن
              </Button>
            </div>
          )}
        </DialogContent>
      </Dialog>

      {/* Delete Confirm */}
      <AlertDialog open={!!deleteTarget} onOpenChange={open => !open && setDeleteTarget(null)}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>حذف کانال</AlertDialogTitle>
            <AlertDialogDescription>
              آیا مطمئنید که می‌خواهید کانال «{deleteTarget?.name}» را حذف کنید؟
              این عمل قابل بازگشت نیست.
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter className="flex-row-reverse gap-2">
            <AlertDialogAction
              onClick={handleDeleteChannel}
              className="bg-destructive text-destructive-foreground hover:bg-destructive/90"
            >
              {deletingId ? <Loader2 className="w-4 h-4 animate-spin ml-2" /> : null}
              حذف کانال
            </AlertDialogAction>
            <AlertDialogCancel>انصراف</AlertDialogCancel>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </div>
  );
}
