import { useEffect, useState } from "react";
import { apiFetch } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter } from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Card, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { useToast } from "@/hooks/use-toast";
import { Send, Share2, CheckCircle2, XCircle, Loader2, Clock, CalendarIcon, RadioIcon, AlertCircle, Image } from "lucide-react";

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
  message_id?: string;
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

function getPlatformIcon(platform: string) {
  if (platform === "telegram") return <Send className="w-4 h-4 text-blue-500" />;
  if (platform === "bale") return <Share2 className="w-4 h-4 text-green-500" />;
  return <Share2 className="w-4 h-4 text-muted-foreground" />;
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
  const [channels, setChannels] = useState<Channel[]>([]);
  const [content, setContent] = useState<Content | null>(null);
  const [loading, setLoading] = useState(false);
  const [selectedChannels, setSelectedChannels] = useState<string[]>([]);
  const [publishType, setPublishType] = useState<"now" | "schedule">("now");
  const [scheduledAt, setScheduledAt] = useState("");
  const [publishing, setPublishing] = useState(false);
  const [results, setResults] = useState<PublishResult[] | null>(null);
  const [overallStatus, setOverallStatus] = useState<string>("");
  const [attachment, setAttachment] = useState<PublishAttachment | null>(null);

  useEffect(() => {
    if (!open || !workspaceId || !contentId) return;
    setLoading(true);
    setResults(null);
    setOverallStatus("");
    setSelectedChannels([]);
    setPublishType("now");
    setScheduledAt("");
    setAttachment(null);
    Promise.all([
      apiFetch(`/workspaces/${workspaceId}/channels/?verified=true`).catch(() => null),
      apiFetch(`/workspaces/${workspaceId}/contents/${contentId}/`).catch(() => null),
    ])
      .then(([chRes, coRes]) => {
        setChannels(Array.isArray(chRes?.data) ? chRes.data : []);
        const c = coRes?.data ?? coRes ?? null;
        setContent(c);
        if (c?.image_url || c?.image) {
          apiFetch(`/workspaces/${workspaceId}/publish/attachments/from-content/`, {
            method: "POST",
            data: { content_id: contentId },
          })
            .then((res) => {
              if (res?.data) setAttachment(res.data);
            })
            .catch(() => {
              // Image attachment is optional; publishing can still proceed without it.
            });
        }
      })
      .finally(() => setLoading(false));
  }, [open, workspaceId, contentId]);

  const toggleChannel = (id: string) => {
    setSelectedChannels((prev) =>
      prev.includes(id) ? prev.filter((x) => x !== id) : [...prev, id]
    );
  };

  const canPublish = () => {
    const hasChannels = selectedChannels.length > 0;
    const hasTime = publishType === "now" || !!scheduledAt;
    return hasChannels && hasTime && !publishing;
  };

  const handlePublish = async () => {
    if (!workspaceId || !contentId || !canPublish()) return;
    setPublishing(true);
    setResults(null);

    const payload: any = {
      content_id: contentId,
      channel_ids: selectedChannels,
    };

    if (attachment) {
      payload.attachments = [{ id: attachment.id, media_type: attachment.media_type }];
    }

    try {
      if (publishType === "now") {
        const res = await apiFetch(`/workspaces/${workspaceId}/publish/now/`, {
          method: "POST",
          data: payload,
        });
        setResults(res?.data?.results || []);
        setOverallStatus(res?.data?.overall_status || "");
        const allOk = res?.data?.overall_status === "published";
        toast({
          title: allOk ? "✅ انتشار موفق" : "⚠️ انتشار با خطا",
          description: allOk ? "محتوا در کانال‌های انتخاب‌شده منتشر شد" : "برخی کانال‌ها با خطا مواجه شدند",
          variant: allOk ? "default" : "destructive",
        });
      } else {
        payload.scheduled_at = new Date(scheduledAt).toISOString();
        await apiFetch(`/workspaces/${workspaceId}/publish/schedule/`, {
          method: "POST",
          data: payload,
        });
        toast({ title: "✅ زمان‌بندی شد", description: "انتشار در زمان مشخص شده در صف قرار گرفت" });
        onOpenChange(false);
        onPublished?.();
      }
    } catch (e: any) {
      toast({ title: "خطا در انتشار", description: e.message || "خطای ناشناخته", variant: "destructive" });
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
      <DialogContent className="max-w-2xl max-h-[90vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <Send className="w-5 h-5" /> انتشار محتوا
          </DialogTitle>
        </DialogHeader>

        {loading ? (
          <div className="flex items-center justify-center h-48">
            <Loader2 className="w-8 h-8 animate-spin text-muted-foreground" />
          </div>
        ) : (
          <div className="space-y-5">
            {content && (
              <Card className="bg-muted/30">
                <CardContent className="p-4">
                  <p className="font-medium text-sm">{content.title || "بدون عنوان"}</p>
                  <p className="text-sm text-muted-foreground line-clamp-3 mt-1 whitespace-pre-wrap">{content.body}</p>
                  {content.image_url && (
                    <div className="flex items-center gap-2 mt-2 text-xs text-muted-foreground">
                      <Image className="w-3.5 h-3.5" /> تصویر پیوست شده
                    </div>
                  )}
                </CardContent>
              </Card>
            )}

            {results && (
              <Card className={`border-2 ${overallStatus === "published" ? "border-green-400" : "border-amber-400"}`}>
                <CardContent className="p-4 space-y-3">
                  <div className="flex items-center gap-2 font-medium text-sm">
                    {overallStatus === "published" ? (
                      <CheckCircle2 className="w-5 h-5 text-green-500" />
                    ) : (
                      <AlertCircle className="w-5 h-5 text-amber-500" />
                    )}
                    نتیجه انتشار
                  </div>
                  <div className="space-y-2">
                    {results.map((r, i) => (
                      <div key={i} className="flex items-center justify-between p-3 rounded-lg bg-muted/50">
                        <div className="flex items-center gap-2">
                          {getPlatformIcon(r.platform)}
                          <span className="font-medium text-sm">{r.channel_name}</span>
                        </div>
                        {r.status === "success" ? (
                          <Badge className="gap-1 bg-green-100 text-green-800 border-green-200">
                            <CheckCircle2 className="w-3 h-3" /> موفق
                          </Badge>
                        ) : (
                          <div className="flex items-center gap-2">
                            <span className="text-xs text-destructive">{r.error}</span>
                            <Badge className="gap-1 bg-destructive/10 text-destructive border-destructive/20">
                              <XCircle className="w-3 h-3" /> ناموفق
                            </Badge>
                          </div>
                        )}
                      </div>
                    ))}
                  </div>
                </CardContent>
              </Card>
            )}

            <div>
              <h3 className="text-sm font-medium mb-2">کانال‌های مقصد</h3>
              {channels.length === 0 ? (
                <div className="text-center py-6 text-muted-foreground text-sm bg-muted/30 rounded-lg">
                  <Share2 className="w-8 h-8 mx-auto mb-2 opacity-30" />
                  هنوز کانال تأیید‌شده‌ای ندارید.
                </div>
              ) : (
                <div className="space-y-2">
                  {channels.map((ch) => (
                    <button
                      key={ch.id}
                      onClick={() => toggleChannel(ch.id)}
                      className={`w-full flex items-center gap-3 p-3 rounded-lg border-2 transition-all text-right ${
                        selectedChannels.includes(ch.id)
                          ? "border-primary bg-primary/5"
                          : "border-border hover:border-muted-foreground"
                      }`}
                    >
                      <div
                        className={`w-5 h-5 rounded border-2 flex items-center justify-center shrink-0 ${
                          selectedChannels.includes(ch.id) ? "bg-primary border-primary" : "border-muted-foreground/40"
                        }`}
                      >
                        {selectedChannels.includes(ch.id) && <CheckCircle2 className="w-3 h-3 text-white" />}
                      </div>
                      {getPlatformIcon(ch.platform)}
                      <div className="flex-1 min-w-0">
                        <p className="text-sm font-medium truncate">{ch.name}</p>
                        <p className="text-xs text-muted-foreground">
                          {PLATFORM_NAMES[ch.platform] || ch.platform} · {TYPE_NAMES[ch.channel_type] || ch.channel_type}
                        </p>
                      </div>
                    </button>
                  ))}
                </div>
              )}
            </div>

            <div>
              <h3 className="text-sm font-medium mb-2">زمان انتشار</h3>
              <div className="grid grid-cols-2 gap-2">
                <button
                  onClick={() => setPublishType("now")}
                  className={`flex items-center gap-2 p-3 rounded-lg border-2 text-sm font-medium transition-all ${
                    publishType === "now" ? "border-primary bg-primary/5 text-primary" : "border-border hover:border-muted-foreground"
                  }`}
                >
                  <RadioIcon className="w-4 h-4" />
                  همین الان
                </button>
                <button
                  onClick={() => setPublishType("schedule")}
                  className={`flex items-center gap-2 p-3 rounded-lg border-2 text-sm font-medium transition-all ${
                    publishType === "schedule" ? "border-primary bg-primary/5 text-primary" : "border-border hover:border-muted-foreground"
                  }`}
                >
                  <CalendarIcon className="w-4 h-4" />
                  زمان‌بندی
                </button>
              </div>
              {publishType === "schedule" && (
                <div className="space-y-1 mt-3">
                  <Label>تاریخ و زمان انتشار</Label>
                  <Input
                    type="datetime-local"
                    value={scheduledAt}
                    onChange={(e) => setScheduledAt(e.target.value)}
                    min={new Date().toISOString().slice(0, 16)}
                    className="dir-ltr"
                  />
                </div>
              )}
            </div>
          </div>
        )}

        <DialogFooter className="flex-col sm:flex-row gap-2">
          {results ? (
            <Button className="w-full sm:w-auto" onClick={closeResults}>
              بستن
            </Button>
          ) : (
            <>
              <Button variant="outline" className="w-full sm:w-auto" onClick={() => onOpenChange(false)}>
                انصراف
              </Button>
              <Button
                className="w-full sm:w-auto gap-2"
                onClick={handlePublish}
                disabled={!canPublish()}
              >
                {publishing ? (
                  <><Loader2 className="w-4 h-4 animate-spin" /> در حال انتشار...</>
                ) : publishType === "now" ? (
                  <><Send className="w-4 h-4" /> انتشار</>
                ) : (
                  <><Clock className="w-4 h-4" /> زمان‌بندی انتشار</>
                )}
              </Button>
            </>
          )}
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
