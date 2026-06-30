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
  Trash2, Zap, AlertCircle, Loader2
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

const PLATFORM_NAMES: Record<string, string> = { telegram: "تلگرام", bale: "بله" };
const TYPE_NAMES: Record<string, string> = { channel: "کانال", group: "گروه" };

function getPlatformIcon(platform: string, size = "w-5 h-5") {
  if (platform === "telegram") return <Send className={`${size} text-blue-500`} />;
  if (platform === "bale") return <Share2 className={`${size} text-green-500`} />;
  return <Share2 className={`${size} text-muted-foreground`} />;
}

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
  const [deletingId, setDeletingId] = useState<string | null>(null);
  const [deleteTarget, setDeleteTarget] = useState<Channel | null>(null);

  // Modal state
  const [showModal, setShowModal] = useState(false);
  const [step, setStep] = useState<1 | 2 | 3 | 4>(1);
  const [platform, setPlatform] = useState<"telegram" | "bale">("telegram");
  const [channelType, setChannelType] = useState<"channel" | "group">("channel");
  const [channelName, setChannelName] = useState("");
  const [verification, setVerification] = useState<VerificationData | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const pollRef = useRef<ReturnType<typeof setInterval> | null>(null);

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

  useEffect(() => {
    if (selectedWorkspace) {
      setLoading(true);
      fetchChannels();
    }
  }, [selectedWorkspace]);

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
    }, 5000);
  };

  useEffect(() => () => stopPolling(), []);

  const closeModal = () => {
    stopPolling();
    setShowModal(false);
    setStep(1);
    setPlatform("telegram");
    setChannelType("channel");
    setChannelName("");
    setVerification(null);
    setSubmitting(false);
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
                <div className="flex items-center gap-2 mt-2">
                  <Badge variant="outline" className="text-xs">
                    {PLATFORM_NAMES[channel.platform] || channel.platform}
                  </Badge>
                  {channel.channel_type && (
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
                </div>
              </CardHeader>
              <CardContent>
                {channel.username && (
                  <p className="text-xs text-muted-foreground mb-3 dir-ltr text-right">@{channel.username}</p>
                )}
                <div className="flex items-center gap-2 flex-wrap">
                  {channel.is_verified && (
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
                      تست اتصال
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
        <DialogContent className="sm:max-w-md">
          <DialogHeader>
            <DialogTitle>افزودن کانال جدید</DialogTitle>
            <DialogDescription>
              {step === 1 && "پلتفرم مورد نظر خود را انتخاب کنید"}
              {step === 2 && "اطلاعات کانال را وارد کنید"}
              {step === 3 && "کد زیر را در کانال خود ارسال کنید"}
              {step === 4 && "کانال با موفقیت تأیید شد!"}
            </DialogDescription>
          </DialogHeader>

          {step === 1 && (
            <div className="space-y-4">
              <div className="grid grid-cols-2 gap-4">
                {(["telegram", "bale"] as const).map(p => (
                  <button
                    key={p}
                    onClick={() => { setPlatform(p); setStep(2); }}
                    className={`flex flex-col items-center gap-3 p-6 rounded-lg border-2 transition-all hover:border-primary hover:bg-primary/5 ${platform === p ? "border-primary bg-primary/5" : "border-border"}`}
                  >
                    {getPlatformIcon(p, "w-10 h-10")}
                    <span className="font-medium">{PLATFORM_NAMES[p]}</span>
                  </button>
                ))}
              </div>
            </div>
          )}

          {step === 2 && (
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
                  onKeyDown={e => e.key === "Enter" && channelName.trim() && handleStartVerification()}
                />
              </div>

              <div className="flex gap-2 pt-2">
                <Button variant="outline" onClick={() => setStep(1)} className="flex-1">
                  برگشت
                </Button>
                <Button
                  onClick={handleStartVerification}
                  disabled={!channelName.trim() || submitting}
                  className="flex-1 gap-2"
                >
                  {submitting ? <Loader2 className="w-4 h-4 animate-spin" /> : null}
                  ادامه
                </Button>
              </div>
            </div>
          )}

          {step === 3 && verification && (
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

              <div className="flex items-center gap-2 text-sm text-muted-foreground">
                <Loader2 className="w-4 h-4 animate-spin" />
                در انتظار تأیید...
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
                  {verification?.channel?.name || channelName} به سامانه اضافه شد
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
