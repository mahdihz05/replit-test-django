import { useEffect, useMemo, useRef, useState } from "react";
import { apiFetch } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Dialog, DialogContent, DialogFooter, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Card, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { useToast } from "@/hooks/use-toast";
import {
  AlertCircle,
  CalendarIcon,
  Check,
  CheckCircle2,
  Clock,
  FileText,
  Image as ImageIcon,
  Loader2,
  Music2,
  RadioIcon,
  Send,
  Share2,
  UploadCloud,
  Video,
  X,
  XCircle,
} from "lucide-react";

interface Channel {
  id: string;
  platform: string;
  name: string;
  channel_type: string;
  is_verified: boolean;
}

interface Content {
  id: string;
  title: string;
  body: string;
  image?: string;
  image_url?: string;
}

interface PublishResult {
  channel_id: string;
  channel_name: string;
  platform: string;
  status: "success" | "failed" | "skipped";
  error?: string;
}

interface PublishAttachment {
  id: string;
  media_type: "image" | "video" | "voice" | "document";
  file_path: string;
  file_url?: string;
  original_filename: string;
  file_size_bytes: number;
  mime_type?: string;
}

const PLATFORM_NAMES: Record<string, string> = {
  telegram: "تلگرام",
  bale: "بله",
  linkedin: "لینکدین",
  wordpress: "وردپرس",
  website: "وب‌سایت",
};

const TYPE_NAMES: Record<string, string> = {
  channel: "کانال",
  group: "گروه",
  personal: "پروفایل شخصی",
  organization: "صفحه سازمانی",
  site: "سایت",
};

const MEDIA_NAMES: Record<PublishAttachment["media_type"], string> = {
  image: "تصویر",
  video: "ویدیو",
  voice: "صدا",
  document: "سند",
};

function getPlatformIcon(platform: string) {
  if (platform === "telegram") return <Send className="h-4 w-4 text-blue-500" />;
  if (platform === "bale") return <Share2 className="h-4 w-4 text-green-500" />;
  return <Share2 className="h-4 w-4 text-muted-foreground" />;
}

function getMediaIcon(type: PublishAttachment["media_type"], className = "h-5 w-5") {
  if (type === "image") return <ImageIcon className={className} />;
  if (type === "video") return <Video className={className} />;
  if (type === "voice") return <Music2 className={className} />;
  return <FileText className={className} />;
}

function formatBytes(bytes: number) {
  if (!bytes) return "";
  if (bytes < 1024 * 1024) return `${Math.ceil(bytes / 1024).toLocaleString("fa-IR")} کیلوبایت`;
  return `${(bytes / (1024 * 1024)).toLocaleString("fa-IR", { maximumFractionDigits: 1 })} مگابایت`;
}

function localDateTimeMin() {
  const date = new Date(Date.now() + 60_000);
  const offset = date.getTimezoneOffset() * 60_000;
  return new Date(date.getTime() - offset).toISOString().slice(0, 16);
}

function mergeAttachments(current: PublishAttachment[], incoming: PublishAttachment[]) {
  const key = (item: PublishAttachment) => `${item.media_type}:${item.file_path || item.id}`;
  const map = new Map(current.map((item) => [key(item), item]));
  incoming.forEach((item) => map.set(key(item), item));
  return Array.from(map.values());
}

interface PublishDialogProps {
  workspaceId: string;
  contentId: string | null;
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onPublished?: () => void;
}

export default function PublishDialog({ workspaceId, contentId, open, onOpenChange, onPublished }: PublishDialogProps) {
  const { toast } = useToast();
  const fileInputRef = useRef<HTMLInputElement>(null);
  const [channels, setChannels] = useState<Channel[]>([]);
  const [content, setContent] = useState<Content | null>(null);
  const [library, setLibrary] = useState<PublishAttachment[]>([]);
  const [selectedAttachments, setSelectedAttachments] = useState<PublishAttachment[]>([]);
  const [selectedChannels, setSelectedChannels] = useState<string[]>([]);
  const [publishType, setPublishType] = useState<"now" | "schedule">("now");
  const [scheduledAt, setScheduledAt] = useState("");
  const [loading, setLoading] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [dragging, setDragging] = useState(false);
  const [publishing, setPublishing] = useState(false);
  const [results, setResults] = useState<PublishResult[] | null>(null);
  const [overallStatus, setOverallStatus] = useState("");

  useEffect(() => {
    if (!open || !workspaceId || !contentId) return;
    let cancelled = false;
    setLoading(true);
    setResults(null);
    setOverallStatus("");
    setSelectedChannels([]);
    setSelectedAttachments([]);
    setPublishType("now");
    setScheduledAt("");

    Promise.all([
      apiFetch(`/workspaces/${workspaceId}/channels/?verified=true`),
      apiFetch(`/workspaces/${workspaceId}/contents/${contentId}/`),
      apiFetch(`/workspaces/${workspaceId}/publish/attachments/list/?content_id=${contentId}`).catch(() => ({ data: [] })),
    ])
      .then(async ([channelResponse, contentResponse, mediaResponse]) => {
        if (cancelled) return;
        const loadedContent = contentResponse?.data ?? contentResponse ?? null;
        const loadedMedia: PublishAttachment[] = Array.isArray(mediaResponse?.data) ? mediaResponse.data : [];
        setChannels(Array.isArray(channelResponse?.data) ? channelResponse.data : []);
        setContent(loadedContent);
        const uniqueMedia = mergeAttachments([], loadedMedia);
        setLibrary(uniqueMedia);
        setSelectedAttachments(uniqueMedia);

        if ((loadedContent?.image_url || loadedContent?.image) && loadedMedia.length === 0) {
          try {
            const response = await apiFetch(`/workspaces/${workspaceId}/publish/attachments/from-content/`, {
              method: "POST",
              data: { content_id: contentId },
            });
            if (!cancelled && response?.data) {
              setLibrary((items) => mergeAttachments(items, [response.data]));
              setSelectedAttachments((items) => mergeAttachments(items, [response.data]));
            }
          } catch {
            // Publishing text remains available if the legacy image cannot be prepared.
          }
        }
      })
      .catch((error: Error) => {
        if (!cancelled) toast({ title: "خطا در آماده‌سازی انتشار", description: error.message, variant: "destructive" });
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });

    return () => {
      cancelled = true;
    };
  }, [open, workspaceId, contentId, toast]);

  const selectedChannelObjects = useMemo(
    () => channels.filter((channel) => selectedChannels.includes(channel.id)),
    [channels, selectedChannels],
  );
  const hasLinkedIn = selectedChannelObjects.some((channel) => channel.platform === "linkedin");
  const hasWebsite = selectedChannelObjects.some((channel) => channel.platform === "website");
  const hasLinkedInVoice = hasLinkedIn && selectedAttachments.some((item) => item.media_type === "voice");
  const linkedInExtraMedia = hasLinkedIn && selectedAttachments.filter((item) => item.media_type !== "voice").length > 1;

  const toggleChannel = (id: string) => {
    setSelectedChannels((items) => (items.includes(id) ? items.filter((item) => item !== id) : [...items, id]));
  };

  const toggleAttachment = (attachment: PublishAttachment) => {
    setSelectedAttachments((items) =>
      items.some((item) => item.id === attachment.id)
        ? items.filter((item) => item.id !== attachment.id)
        : [...items, attachment],
    );
  };

  const uploadFiles = async (files: File[]) => {
    if (!files.length) return;
    const tooLarge = files.find((file) => file.size > 500 * 1024 * 1024);
    if (tooLarge) {
      toast({ title: "فایل بیش از حد بزرگ است", description: `${tooLarge.name} بیشتر از ۵۰۰ مگابایت است.`, variant: "destructive" });
      return;
    }

    setUploading(true);
    const uploaded: PublishAttachment[] = [];
    try {
      for (const file of files) {
        const formData = new FormData();
        formData.append("file", file);
        const response = await apiFetch(`/workspaces/${workspaceId}/publish/attachments/`, {
          method: "POST",
          data: formData,
        });
        if (response?.data) uploaded.push(response.data);
      }
      setLibrary((items) => mergeAttachments(items, uploaded));
      setSelectedAttachments((items) => mergeAttachments(items, uploaded));
      toast({ title: "رسانه آماده شد", description: `${uploaded.length.toLocaleString("fa-IR")} فایل برای انتشار انتخاب شد.` });
    } catch (error: any) {
      if (uploaded.length > 0) {
        setLibrary((items) => mergeAttachments(items, uploaded));
        setSelectedAttachments((items) => mergeAttachments(items, uploaded));
      }
      toast({
        title: "آپلود کامل نشد",
        description: uploaded.length > 0
          ? `${uploaded.length.toLocaleString("fa-IR")} فایل آماده شد؛ فایل بعدی با خطا مواجه شد.`
          : error.message || "آپلود فایل با خطا مواجه شد.",
        variant: "destructive",
      });
    } finally {
      setUploading(false);
      if (fileInputRef.current) fileInputRef.current.value = "";
    }
  };

  const canPublish = selectedChannels.length > 0
    && (publishType === "now" || Boolean(scheduledAt))
    && !publishing
    && !uploading;

  const handlePublish = async () => {
    if (!workspaceId || !contentId || !canPublish) return;
    if (publishType === "schedule" && new Date(scheduledAt).getTime() <= Date.now()) {
      toast({ title: "زمان نامعتبر است", description: "زمان انتشار باید در آینده باشد.", variant: "destructive" });
      return;
    }

    setPublishing(true);
    setResults(null);
    const payload: any = {
      content_id: contentId,
      channel_ids: selectedChannels,
      attachments: selectedAttachments.map(({ id, media_type }) => ({ id, media_type })),
    };

    try {
      if (publishType === "now") {
        const response = await apiFetch(`/workspaces/${workspaceId}/publish/now/`, { method: "POST", data: payload });
        const status = response?.data?.overall_status || "";
        setResults(response?.data?.results || []);
        setOverallStatus(status);
        toast({
          title: status === "published" ? "انتشار موفق" : "انتشار با خطا",
          description: status === "published" ? "متن نهایی در مقصدهای انتخاب‌شده منتشر شد." : "نتیجه هر مقصد را بررسی کنید.",
          variant: status === "published" ? "default" : "destructive",
        });
      } else {
        payload.scheduled_at = new Date(scheduledAt).toISOString();
        const response = await apiFetch(`/workspaces/${workspaceId}/publish/schedule/`, { method: "POST", data: payload });
        const jobs = response?.data?.jobs?.length || selectedChannels.length;
        toast({
          title: "انتشار زمان‌بندی شد",
          description: `${jobs.toLocaleString("fa-IR")} مقصد در صف قرار گرفت. متن نهایی نمایش‌داده‌شده ارسال خواهد شد.`,
        });
        onOpenChange(false);
        onPublished?.();
      }
    } catch (error: any) {
      toast({ title: "خطا در انتشار", description: error.message || "خطای ناشناخته", variant: "destructive" });
    } finally {
      setPublishing(false);
    }
  };

  const closeResults = () => {
    setResults(null);
    setOverallStatus("");
    onOpenChange(false);
    onPublished?.();
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-h-[92vh] max-w-3xl overflow-y-auto">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <Send className="h-5 w-5" /> آماده‌سازی انتشار
          </DialogTitle>
        </DialogHeader>

        {loading ? (
          <div className="flex h-56 items-center justify-center">
            <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
          </div>
        ) : (
          <div className="space-y-5">
            {content && (
              <Card className="overflow-hidden border-primary/20 bg-primary/[0.03]">
                <CardContent className="p-4">
                  <div className="mb-2 flex items-center justify-between gap-3">
                    <p className="text-sm font-semibold">متن نهایی قابل انتشار</p>
                    <Badge variant="outline">عنوان داخلی ارسال نمی‌شود</Badge>
                  </div>
                  <p className="max-h-32 overflow-y-auto whitespace-pre-wrap text-sm leading-7 text-foreground/80">
                    {content.body || "متن این محتوا خالی است."}
                  </p>
                </CardContent>
              </Card>
            )}

            {results && (
              <Card className={overallStatus === "published" ? "border-green-400" : "border-amber-400"}>
                <CardContent className="space-y-3 p-4">
                  <div className="flex items-center gap-2 font-medium">
                    {overallStatus === "published" ? <CheckCircle2 className="h-5 w-5 text-green-500" /> : <AlertCircle className="h-5 w-5 text-amber-500" />}
                    نتیجه انتشار
                  </div>
                  {results.map((result) => (
                    <div key={result.channel_id} className="flex items-center justify-between gap-3 rounded-lg bg-muted/50 p-3">
                      <div className="flex items-center gap-2">
                        {getPlatformIcon(result.platform)}
                        <span className="text-sm font-medium">{result.channel_name}</span>
                      </div>
                      {result.status === "success" ? (
                        <Badge className="gap-1 bg-green-100 text-green-800"><CheckCircle2 className="h-3 w-3" /> موفق</Badge>
                      ) : (
                        <div className="flex items-center gap-2 text-left">
                          <span className="text-xs text-destructive">{result.error}</span>
                          <Badge variant="destructive" className="gap-1"><XCircle className="h-3 w-3" /> ناموفق</Badge>
                        </div>
                      )}
                    </div>
                  ))}
                </CardContent>
              </Card>
            )}

            <section>
              <h3 className="mb-2 text-sm font-medium">۱. مقصد انتشار</h3>
              {channels.length === 0 ? (
                <div className="rounded-lg bg-muted/40 py-6 text-center text-sm text-muted-foreground">هنوز کانال تأییدشده‌ای ندارید.</div>
              ) : (
                <div className="grid gap-2 sm:grid-cols-2">
                  {channels.map((channel) => {
                    const selected = selectedChannels.includes(channel.id);
                    return (
                      <button
                        type="button"
                        key={channel.id}
                        onClick={() => toggleChannel(channel.id)}
                        className={`flex items-center gap-3 rounded-lg border-2 p-3 text-right transition ${selected ? "border-primary bg-primary/5" : "border-border hover:border-primary/40"}`}
                      >
                        <span className={`flex h-5 w-5 shrink-0 items-center justify-center rounded border ${selected ? "border-primary bg-primary text-primary-foreground" : "border-muted-foreground/40"}`}>
                          {selected && <Check className="h-3.5 w-3.5" />}
                        </span>
                        {getPlatformIcon(channel.platform)}
                        <span className="min-w-0 flex-1">
                          <span className="block truncate text-sm font-medium">{channel.name}</span>
                          <span className="block text-xs text-muted-foreground">{PLATFORM_NAMES[channel.platform] || channel.platform} · {TYPE_NAMES[channel.channel_type] || channel.channel_type}</span>
                        </span>
                      </button>
                    );
                  })}
                </div>
              )}
            </section>

            <section>
              <div className="mb-2 flex items-center justify-between gap-3">
                <h3 className="text-sm font-medium">۲. تصویر یا فایل همراه</h3>
                <span className="text-xs text-muted-foreground">اختیاری · امکان انتخاب چند فایل</span>
              </div>
              <div
                onDragEnter={(event) => { event.preventDefault(); setDragging(true); }}
                onDragOver={(event) => event.preventDefault()}
                onDragLeave={() => setDragging(false)}
                onDrop={(event) => {
                  event.preventDefault();
                  setDragging(false);
                  void uploadFiles(Array.from(event.dataTransfer.files));
                }}
                className={`rounded-xl border-2 border-dashed p-4 transition ${dragging ? "border-primary bg-primary/5" : "border-border"}`}
              >
                <div className="flex flex-col items-center justify-center gap-2 py-2 text-center sm:flex-row sm:text-right">
                  {uploading ? <Loader2 className="h-7 w-7 animate-spin text-primary" /> : <UploadCloud className="h-7 w-7 text-primary" />}
                  <div className="flex-1">
                    <p className="text-sm font-medium">فایل‌ها را اینجا رها کنید یا از دستگاه انتخاب کنید</p>
                    <p className="text-xs text-muted-foreground">تصویر، ویدیو، فایل صوتی و سند تا سقف ۵۰۰ مگابایت</p>
                  </div>
                  <Button type="button" variant="outline" size="sm" disabled={uploading} onClick={() => fileInputRef.current?.click()}>
                    انتخاب فایل
                  </Button>
                  <input
                    ref={fileInputRef}
                    type="file"
                    multiple
                    className="hidden"
                    accept="image/*,video/*,audio/*,.pdf,.doc,.docx,.ppt,.pptx,.xls,.xlsx,.txt"
                    onChange={(event) => void uploadFiles(Array.from(event.target.files || []))}
                  />
                </div>
              </div>

              {library.length > 0 && (
                <div className="mt-3 grid gap-2 sm:grid-cols-2">
                  {library.map((item) => {
                    const selected = selectedAttachments.some((attachment) => attachment.id === item.id);
                    return (
                      <button
                        type="button"
                        key={item.id}
                        onClick={() => toggleAttachment(item)}
                        className={`group flex min-w-0 items-center gap-3 rounded-lg border p-2.5 text-right transition ${selected ? "border-primary bg-primary/5" : "hover:border-primary/40"}`}
                      >
                        {item.media_type === "image" && item.file_url ? (
                          <img src={item.file_url} alt="" className="h-14 w-14 shrink-0 rounded-md border object-cover" />
                        ) : (
                          <span className="flex h-14 w-14 shrink-0 items-center justify-center rounded-md bg-muted text-muted-foreground">{getMediaIcon(item.media_type)}</span>
                        )}
                        <span className="min-w-0 flex-1">
                          <span className="block truncate text-sm font-medium">{item.original_filename || MEDIA_NAMES[item.media_type]}</span>
                          <span className="block text-xs text-muted-foreground">{MEDIA_NAMES[item.media_type]} {formatBytes(item.file_size_bytes) && `· ${formatBytes(item.file_size_bytes)}`}</span>
                        </span>
                        <span className={`flex h-6 w-6 shrink-0 items-center justify-center rounded-full ${selected ? "bg-primary text-primary-foreground" : "bg-muted text-muted-foreground"}`}>
                          {selected ? <Check className="h-4 w-4" /> : <X className="h-3.5 w-3.5" />}
                        </span>
                      </button>
                    );
                  })}
                </div>
              )}

              {(hasLinkedInVoice || linkedInExtraMedia || hasWebsite) && selectedAttachments.length > 0 && (
                <div className="mt-3 flex gap-2 rounded-lg border border-amber-300 bg-amber-50 p-3 text-xs leading-6 text-amber-900">
                  <AlertCircle className="mt-0.5 h-4 w-4 shrink-0" />
                  <span>
                    {hasLinkedInVoice && "فایل صوتی در لینکدین ارسال نمی‌شود. "}
                    {linkedInExtraMedia && "نسخه فعلی لینکدین اولین رسانه سازگار را ارسال می‌کند. "}
                    {hasWebsite && "اتصال وب‌سایت در حال حاضر رسانه همراه دریافت نمی‌کند."}
                  </span>
                </div>
              )}
            </section>

            <section>
              <h3 className="mb-2 text-sm font-medium">۳. زمان انتشار</h3>
              <div className="grid grid-cols-2 gap-2">
                <button type="button" onClick={() => setPublishType("now")} className={`flex items-center gap-2 rounded-lg border-2 p-3 text-sm font-medium ${publishType === "now" ? "border-primary bg-primary/5 text-primary" : "border-border"}`}>
                  <RadioIcon className="h-4 w-4" /> همین حالا
                </button>
                <button type="button" onClick={() => setPublishType("schedule")} className={`flex items-center gap-2 rounded-lg border-2 p-3 text-sm font-medium ${publishType === "schedule" ? "border-primary bg-primary/5 text-primary" : "border-border"}`}>
                  <CalendarIcon className="h-4 w-4" /> زمان‌بندی
                </button>
              </div>
              {publishType === "schedule" && (
                <div className="mt-3 space-y-1.5 rounded-lg bg-muted/40 p-3">
                  <Label htmlFor="publish-at">تاریخ و ساعت به وقت محلی شما</Label>
                  <Input id="publish-at" type="datetime-local" value={scheduledAt} onChange={(event) => setScheduledAt(event.target.value)} min={localDateTimeMin()} dir="ltr" />
                  {scheduledAt && <p className="text-xs text-muted-foreground">ارسال در {new Date(scheduledAt).toLocaleString("fa-IR")} انجام می‌شود.</p>}
                </div>
              )}
            </section>
          </div>
        )}

        <DialogFooter className="gap-2 sm:gap-0">
          {results ? (
            <Button onClick={closeResults}>بستن</Button>
          ) : (
            <>
              <Button variant="outline" onClick={() => onOpenChange(false)}>انصراف</Button>
              <Button className="gap-2" onClick={handlePublish} disabled={!canPublish}>
                {publishing ? <><Loader2 className="h-4 w-4 animate-spin" /> در حال ثبت...</> : publishType === "now" ? <><Send className="h-4 w-4" /> انتشار</> : <><Clock className="h-4 w-4" /> ثبت زمان‌بندی</>}
              </Button>
            </>
          )}
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
