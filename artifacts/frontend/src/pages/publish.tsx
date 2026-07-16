import { useState, useEffect } from "react";
import { useAuth } from "@/lib/auth";
import { apiFetch } from "@/lib/api";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Textarea } from "@/components/ui/textarea";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { useToast } from "@/hooks/use-toast";
import {
  Send, Share2, CheckCircle2, XCircle, Clock, Loader2, Search,
  FileText, Edit3, RadioIcon, CalendarIcon, AlertCircle, Linkedin, Globe,
  Image, Paperclip, X, FileVideo, FileAudio, File
} from "lucide-react";

interface Channel {
  id: string;
  platform: string;
  name: string;
  channel_type: string;
  is_verified: boolean;
  wordpress?: {
    status: string;
    site_name?: string;
    synced_at?: string | null;
    capabilities?: WordPressCapabilities;
  } | null;
}

interface WordPressPostType {
  slug: string;
  name: string;
  rest_base: string;
  supports: Record<string, boolean>;
  taxonomies: string[];
}

interface WordPressTaxonomy {
  slug: string;
  name: string;
  rest_base: string;
  hierarchical: boolean;
  types: string[];
  terms: { id: number; name: string; parent?: number }[];
}

interface WordPressCapabilities {
  post_types?: WordPressPostType[];
  taxonomies?: Record<string, WordPressTaxonomy>;
}

interface WordPressPublishOptions {
  post_type: string;
  status: "draft" | "pending" | "publish";
  excerpt: string;
  slug: string;
  taxonomy_terms: Record<string, number[]>;
  featured_attachment_id: string;
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

interface Content {
  id: string;
  title: string;
  body: string;
  status: string;
  created_at: string;
  image?: string;
  image_url?: string;
  attachments?: PublishAttachment[];
}

interface PublishResult {
  channel_id: string;
  channel_name: string;
  platform: string;
  status: "success" | "failed" | "skipped";
  error?: string;
  message_id?: string;
  wordpress?: {
    post_id?: number;
    url?: string;
    edit_url?: string;
    status?: string;
    post_type?: string;
  };
}

const PLATFORM_NAMES: Record<string, string> = {
  telegram: "تلگرام",
  bale: "بله",
  linkedin: "LinkedIn",
  wordpress: "WordPress",
  website: "وب‌سایت",
};

const MEDIA_LIMITS: Record<string, { label: string; bytes: number }> = {
  telegram: { label: "۵۰ مگابایت", bytes: 50 * 1024 * 1024 },
  bale: { label: "۵۰ مگابایت", bytes: 50 * 1024 * 1024 },
  linkedin: { label: "۵ گیگابایت (ویدیو)", bytes: 5 * 1024 * 1024 * 1024 },
  wordpress: { label: "بستگی به تنظیمات وردپرس", bytes: 100 * 1024 * 1024 },
};

const SUPPORTED_MEDIA: Record<string, Set<string>> = {
  telegram: new Set(["image", "video", "voice", "document"]),
  bale: new Set(["image", "video", "voice", "document"]),
  linkedin: new Set(["image", "video", "document"]),
  wordpress: new Set(["image", "video", "voice", "document"]),
  website: new Set([]),
};

function guessMediaType(filename: string, mimeType: string): string {
  if (mimeType.startsWith("image/")) return "image";
  if (mimeType.startsWith("video/")) return "video";
  if (mimeType.startsWith("audio/")) return "voice";
  const ext = filename.split(".").pop()?.toLowerCase() || "";
  if (["jpg", "jpeg", "png", "gif", "webp", "bmp"].includes(ext)) return "image";
  if (["mp4", "mov", "avi", "mkv", "webm"].includes(ext)) return "video";
  if (["mp3", "ogg", "wav", "m4a", "aac", "oga"].includes(ext)) return "voice";
  return "document";
}

function getMediaIcon(mediaType: string) {
  if (mediaType === "image") return <Image className="w-4 h-4" />;
  if (mediaType === "video") return <FileVideo className="w-4 h-4" />;
  if (mediaType === "voice") return <FileAudio className="w-4 h-4" />;
  return <File className="w-4 h-4" />;
}

function formatBytes(bytes: number) {
  if (!bytes) return "0 B";
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

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
  if (platform === "linkedin") return <Linkedin className="w-4 h-4 text-blue-700" />;
  if (platform === "wordpress") return <Globe className="w-4 h-4 text-blue-600" />;
  return <Share2 className="w-4 h-4 text-muted-foreground" />;
}

export default function Publish() {
  const { selectedWorkspace } = useAuth();
  const { toast } = useToast();

  const [channels, setChannels] = useState<Channel[]>([]);
  const [contents, setContents] = useState<Content[]>([]);
  const [loadingData, setLoadingData] = useState(false);

  const [contentTab, setContentTab] = useState<"saved" | "direct">("saved");
  const [contentSearch, setContentSearch] = useState("");
  const [selectedContent, setSelectedContent] = useState<Content | null>(null);
  const [customText, setCustomText] = useState("");

  const [selectedChannels, setSelectedChannels] = useState<string[]>([]);
  const [wordpressOptions, setWordpressOptions] = useState<Record<string, WordPressPublishOptions>>({});
  const [loadingWordpress, setLoadingWordpress] = useState<string | null>(null);
  const [publishType, setPublishType] = useState<"now" | "schedule">("now");
  const [scheduledAt, setScheduledAt] = useState("");
  const [attachments, setAttachments] = useState<PublishAttachment[]>([]);
  const [uploading, setUploading] = useState(false);

  const [publishing, setPublishing] = useState(false);
  const [results, setResults] = useState<PublishResult[] | null>(null);
  const [overallStatus, setOverallStatus] = useState<string>("");

  useEffect(() => {
    if (!selectedWorkspace) return;
    Promise.all([
      apiFetch(`/workspaces/${selectedWorkspace.id}/channels/?verified=true`).catch(() => null),
      apiFetch(`/workspaces/${selectedWorkspace.id}/contents/`).catch(() => null),
    ]).then(([chRes, coRes]) => {
      setChannels(Array.isArray(chRes?.data) ? chRes.data : []);
      setContents(Array.isArray(coRes?.data) ? coRes.data : []);
    }).finally(() => setLoadingData(false));
  }, [selectedWorkspace]);

  useEffect(() => {
    // Auto-attach the draft image when a content with image is selected, but only if not already present
    if (contentTab === "saved" && selectedContent?.image_url && !attachments.some(a => a.file_path === selectedContent.image)) {
      handleAutoAttachImage();
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [selectedContent, contentTab]);

  const filteredContents = contents.filter(c =>
    c.title?.toLowerCase().includes(contentSearch.toLowerCase()) ||
    c.body?.toLowerCase().includes(contentSearch.toLowerCase())
  );

  const defaultWordpressOptions = (channel: Channel): WordPressPublishOptions => ({
    post_type: channel.wordpress?.capabilities?.post_types?.[0]?.slug || "post",
    status: "draft",
    excerpt: "",
    slug: "",
    taxonomy_terms: {},
    featured_attachment_id: "",
  });

  const loadWordpressCapabilities = async (channel: Channel) => {
    if (!selectedWorkspace || channel.platform !== "wordpress") return;
    if (channel.wordpress?.capabilities?.post_types?.length) return;
    setLoadingWordpress(channel.id);
    try {
      const res = await apiFetch(`/workspaces/${selectedWorkspace.id}/channels/${channel.id}/wordpress/capabilities/`);
      setChannels(prev => prev.map(item => item.id === channel.id
        ? { ...item, wordpress: { ...(item.wordpress || { status: "active" }), ...res.data } }
        : item));
      const firstType = res?.data?.capabilities?.post_types?.[0]?.slug || "post";
      setWordpressOptions(prev => ({
        ...prev,
        [channel.id]: { ...(prev[channel.id] || defaultWordpressOptions(channel)), post_type: firstType },
      }));
    } catch (e: any) {
      toast({ title: "خطا در دریافت اطلاعات وردپرس", description: e.message || "دوباره تلاش کنید", variant: "destructive" });
    } finally {
      setLoadingWordpress(null);
    }
  };

  const toggleChannel = (id: string) => {
    const channel = channels.find(item => item.id === id);
    const selecting = !selectedChannels.includes(id);
    setSelectedChannels(prev => selecting ? [...prev, id] : prev.filter(x => x !== id));
    if (selecting && channel?.platform === "wordpress") {
      setWordpressOptions(prev => ({ ...prev, [id]: prev[id] || defaultWordpressOptions(channel) }));
      void loadWordpressCapabilities(channel);
    }
  };

  const updateWordpressOptions = (channelId: string, patch: Partial<WordPressPublishOptions>) => {
    const channel = channels.find(item => item.id === channelId);
    if (!channel) return;
    setWordpressOptions(prev => ({
      ...prev,
      [channelId]: { ...(prev[channelId] || defaultWordpressOptions(channel)), ...patch },
    }));
  };

  const removeAttachment = (id: string) => {
    setAttachments(prev => prev.filter(a => a.id !== id));
  };

  const handleFileUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const files = e.target.files;
    if (!files || !selectedWorkspace) return;
    setUploading(true);
    try {
      for (const file of Array.from(files)) {
        const mediaType = guessMediaType(file.name, file.type);
        const form = new FormData();
        form.append("file", file);
        form.append("media_type", mediaType);
        const res = await apiFetch(`/workspaces/${selectedWorkspace.id}/publish/attachments/`, {
          method: "POST",
          data: form,
        });
        if (res?.data) {
          setAttachments(prev => [...prev, res.data]);
        }
      }
    } catch (e: any) {
      toast({ title: "خطا در آپلود", description: e.message || "خطا", variant: "destructive" });
    } finally {
      setUploading(false);
      if (e.target) e.target.value = "";
    }
  };

  const handleAutoAttachImage = async () => {
    if (!selectedContent || !selectedWorkspace) return;
    try {
      const res = await apiFetch(`/workspaces/${selectedWorkspace.id}/publish/attachments/from-content/`, {
        method: "POST",
        data: { content_id: selectedContent.id },
      });
      if (res?.data) {
        setAttachments(prev => [...prev, res.data]);
      }
    } catch (e: any) {
      toast({ title: "خطا", description: e.message || "خطا در ضمیمه تصویر", variant: "destructive" });
    }
  };

  const canPublish = () => {
    const hasText = contentTab === "saved" ? !!selectedContent : customText.trim().length > 0;
    const hasChannels = selectedChannels.length > 0;
    const hasTime = publishType === "now" || !!scheduledAt;
    return hasText && hasChannels && hasTime && !publishing && !uploading;
  };

  const handlePublish = async () => {
    if (!selectedWorkspace || !canPublish()) return;
    setPublishing(true);
    setResults(null);

    const payload: any = {
      channel_ids: selectedChannels,
      attachments: attachments.map(a => ({ id: a.id, media_type: a.media_type })),
      wordpress_options: Object.fromEntries(
        selectedChannels.filter(id => channels.find(channel => channel.id === id)?.platform === "wordpress")
          .map(id => [id, wordpressOptions[id]])
      ),
    };

    if (contentTab === "saved" && selectedContent) {
      payload.content_id = selectedContent.id;
    } else {
      payload.custom_text = customText.trim();
    }

    try {
      if (publishType === "now") {
        const res = await apiFetch(`/workspaces/${selectedWorkspace.id}/publish/now/`, {
          method: "POST",
          data: payload,
        });
        setResults(res?.data?.results || []);
        setOverallStatus(res?.data?.overall_status || "");
        const allOk = res?.data?.overall_status === "published";
        toast({
          title: allOk ? "✅ انتشار موفق" : "⚠️ انتشار با خطا",
          description: allOk ? "محتوا با موفقیت در همه کانال‌ها منتشر شد" : "برخی کانال‌ها با خطا مواجه شدند",
          variant: allOk ? "default" : "destructive",
        });
      } else {
        payload.scheduled_at = new Date(scheduledAt).toISOString();
        await apiFetch(`/workspaces/${selectedWorkspace.id}/publish/schedule/`, {
          method: "POST",
          data: payload,
        });
        toast({ title: "✅ زمان‌بندی شد", description: "انتشار در زمان مشخص شده در صف قرار گرفت" });
        setSelectedChannels([]);
        setSelectedContent(null);
        setCustomText("");
        setScheduledAt("");
      }
    } catch (e: any) {
      toast({ title: "خطا در انتشار", description: e.message || "خطای ناشناخته", variant: "destructive" });
    } finally {
      setPublishing(false);
    }
  };

  const textPreview = contentTab === "saved" ? (selectedContent?.body || "") : customText;
  const titlePreview = contentTab === "saved" ? (selectedContent?.title || "") : "";

  if (loadingData) {
    return (
      <div className="flex items-center justify-center h-64">
        <Loader2 className="w-8 h-8 animate-spin text-muted-foreground" />
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-bold tracking-tight">انتشار محتوا</h1>
        <p className="text-muted-foreground mt-1">محتوا را در کانال‌های خود منتشر کنید</p>
      </div>

      {/* Results panel */}
      {results && (
        <Card className={`border-2 ${overallStatus === "published" ? "border-green-400" : "border-amber-400"}`}>
          <CardHeader className="pb-3">
            <CardTitle className="text-base flex items-center gap-2">
              {overallStatus === "published"
                ? <CheckCircle2 className="w-5 h-5 text-green-500" />
                : <AlertCircle className="w-5 h-5 text-amber-500" />}
              نتیجه انتشار
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-2">
              {results.map((r, i) => (
                <div key={i} className="p-3 rounded-lg bg-muted/50 space-y-2">
                  <div className="flex items-center justify-between gap-3">
                    <div className="flex items-center gap-2">
                      {getPlatformIcon(r.platform)}
                      <span className="font-medium text-sm">{r.channel_name}</span>
                    </div>
                    {r.status === "success" ? (
                      <Badge className="gap-1 bg-green-100 text-green-800 border-green-200">
                        <CheckCircle2 className="w-3 h-3" /> موفق
                      </Badge>
                    ) : (
                      <Badge className="gap-1 bg-destructive/10 text-destructive border-destructive/20">
                        <XCircle className="w-3 h-3" /> ناموفق
                      </Badge>
                    )}
                  </div>
                  {r.error && <p className="text-xs text-destructive">{r.error}</p>}
                  {r.wordpress && r.status === "success" && (
                    <div className="flex flex-wrap items-center gap-2 text-xs">
                      <span className="text-muted-foreground">شناسه: {r.wordpress.post_id} · {r.wordpress.status === "draft" ? "پیش‌نویس" : "ارسال‌شده"}</span>
                      {r.wordpress.edit_url && <a className="text-primary underline" href={r.wordpress.edit_url} target="_blank" rel="noreferrer">ویرایش در وردپرس</a>}
                      {r.wordpress.url && r.wordpress.status === "publish" && <a className="text-primary underline" href={r.wordpress.url} target="_blank" rel="noreferrer">مشاهده نوشته</a>}
                    </div>
                  )}
                </div>
              ))}
            </div>
            <Button variant="outline" size="sm" className="mt-3" onClick={() => setResults(null)}>
              بستن نتیجه
            </Button>
          </CardContent>
        </Card>
      )}

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Left: Content */}
        <div className="space-y-4">
          <Card>
            <CardHeader className="pb-3">
              <CardTitle className="text-base">محتوا</CardTitle>
            </CardHeader>
            <CardContent>
              <Tabs value={contentTab} onValueChange={v => setContentTab(v as any)}>
                <TabsList className="w-full mb-4">
                  <TabsTrigger value="saved" className="flex-1 gap-2">
                    <FileText className="w-4 h-4" /> محتوای ذخیره‌شده
                  </TabsTrigger>
                  <TabsTrigger value="direct" className="flex-1 gap-2">
                    <Edit3 className="w-4 h-4" /> نوشتن مستقیم
                  </TabsTrigger>
                </TabsList>

                <TabsContent value="saved" className="space-y-3 mt-0">
                  <div className="relative">
                    <Search className="absolute right-3 top-1/2 -translate-y-1/2 w-4 h-4 text-muted-foreground" />
                    <Input
                      placeholder="جستجو در محتواها..."
                      value={contentSearch}
                      onChange={e => setContentSearch(e.target.value)}
                      className="pr-9"
                    />
                  </div>
                  {filteredContents.length === 0 ? (
                    <div className="text-center py-8 text-muted-foreground text-sm">
                      محتوایی یافت نشد
                    </div>
                  ) : (
                    <div className="space-y-2 max-h-64 overflow-y-auto">
                      {filteredContents.map(c => (
                        <button
                          key={c.id}
                          onClick={() => setSelectedContent(c)}
                          className={`w-full text-right p-3 rounded-lg border-2 transition-all hover:border-primary/50 ${selectedContent?.id === c.id ? "border-primary bg-primary/5" : "border-border"}`}
                        >
                          <p className="font-medium text-sm">{c.title || "بدون عنوان"}</p>
                          <p className="text-xs text-muted-foreground mt-1 line-clamp-2">{c.body}</p>
                        </button>
                      ))}
                    </div>
                  )}
                </TabsContent>

                <TabsContent value="direct" className="mt-0">
                  <Textarea
                    placeholder="متن پیام خود را اینجا بنویسید..."
                    value={customText}
                    onChange={e => setCustomText(e.target.value)}
                    rows={8}
                  />
                  <p className="text-xs text-muted-foreground mt-1 text-left dir-ltr">
                    {customText.length} کاراکتر
                  </p>
                </TabsContent>
              </Tabs>
            </CardContent>
          </Card>

          {/* Preview */}
          {textPreview && (
            <Card className="bg-muted/30">
              <CardHeader className="pb-2">
                <CardTitle className="text-sm text-muted-foreground">پیش‌نمایش</CardTitle>
              </CardHeader>
              <CardContent>
                {titlePreview && <p className="font-bold text-sm mb-1">{titlePreview}</p>}
                <p className="text-sm whitespace-pre-wrap line-clamp-5">{textPreview}</p>
              </CardContent>
            </Card>
          )}

          {/* Attachments */}
          <Card>
            <CardHeader className="pb-3">
              <CardTitle className="text-base flex items-center gap-2">
                <Paperclip className="w-4 h-4" /> رسانه‌های ضمیمه
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-3">
              <div className="flex items-center gap-2">
                <Button variant="outline" className="gap-2" asChild disabled={uploading}>
                  <label>
                    <Image className="w-4 h-4" /> {uploading ? "در حال آپلود..." : "افزودن فایل"}
                    <input type="file" className="hidden" multiple onChange={handleFileUpload} disabled={uploading} />
                  </label>
                </Button>
                {selectedContent?.image_url && !attachments.some(a => a.file_path === selectedContent.image) && (
                  <Button variant="outline" className="gap-2" onClick={handleAutoAttachImage} disabled={uploading}>
                    <Image className="w-4 h-4" /> تصویر پیش‌نویس
                  </Button>
                )}
              </div>

              {attachments.length === 0 ? (
                <p className="text-sm text-muted-foreground">فایلی ضمیمه نشده است.</p>
              ) : (
                <div className="space-y-2">
                  {attachments.map(att => (
                    <div key={att.id} className="flex items-center gap-2 p-2 rounded-lg border bg-muted/30">
                      {getMediaIcon(att.media_type)}
                      <div className="flex-1 min-w-0">
                        <p className="text-sm font-medium truncate">{att.original_filename}</p>
                        <p className="text-xs text-muted-foreground">{formatBytes(att.file_size_bytes)} · {att.media_type}</p>
                      </div>
                      <button onClick={() => removeAttachment(att.id)} className="text-muted-foreground hover:text-destructive">
                        <X className="w-4 h-4" />
                      </button>
                    </div>
                  ))}
                </div>
              )}

              {selectedChannels.length > 0 && attachments.length > 0 && (
                <div className="space-y-1 text-xs text-muted-foreground bg-muted/50 p-2 rounded-lg">
                  <p className="font-medium text-foreground">محدودیت‌های پلتفرم:</p>
                  {selectedChannels.map(chId => {
                    const ch = channels.find(c => c.id === chId);
                    if (!ch) return null;
                    const unsupported = attachments.filter(a => !SUPPORTED_MEDIA[ch.platform]?.has(a.media_type));
                    const limit = MEDIA_LIMITS[ch.platform];
                    return (
                      <div key={ch.id} className="flex flex-col gap-0.5">
                        <span className="font-medium">{PLATFORM_NAMES[ch.platform]}:</span>
                        {limit && <span>• حداکثر حجم: {limit.label}</span>}
                        {unsupported.length > 0 && (
                          <span className="text-amber-600">
                            • {unsupported.map(a => a.media_type).join("، ")} در این پلتفرم پشتیبانی نمی‌شود و رد می‌شود.
                          </span>
                        )}
                      </div>
                    );
                  })}
                </div>
              )}
            </CardContent>
          </Card>
        </div>

        {/* Right: Options */}
        <div className="space-y-4">
          {/* Channels */}
          <Card>
            <CardHeader className="pb-3">
              <CardTitle className="text-base">کانال‌های مقصد</CardTitle>
            </CardHeader>
            <CardContent>
              {channels.length === 0 ? (
                <div className="text-center py-6 text-muted-foreground text-sm">
                  <Share2 className="w-8 h-8 mx-auto mb-2 opacity-30" />
                  هنوز کانال تأیید‌شده‌ای ندارید.{" "}
                  <a href="/channels" className="text-primary underline">کانال اضافه کنید</a>
                </div>
              ) : (
                <div className="space-y-2">
                  {channels.map(ch => (
                    <button
                      key={ch.id}
                      onClick={() => toggleChannel(ch.id)}
                      className={`w-full flex items-center gap-3 p-3 rounded-lg border-2 transition-all text-right ${selectedChannels.includes(ch.id) ? "border-primary bg-primary/5" : "border-border hover:border-muted-foreground"}`}
                    >
                      <div className={`w-5 h-5 rounded border-2 flex items-center justify-center shrink-0 ${selectedChannels.includes(ch.id) ? "bg-primary border-primary" : "border-muted-foreground/40"}`}>
                        {selectedChannels.includes(ch.id) && (
                          <CheckCircle2 className="w-3 h-3 text-white" />
                        )}
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
            </CardContent>
          </Card>

          {selectedChannels.map(channelId => {
            const channel = channels.find(item => item.id === channelId);
            if (!channel || channel.platform !== "wordpress") return null;
            const options = wordpressOptions[channelId] || defaultWordpressOptions(channel);
            const capabilities = channel.wordpress?.capabilities || {};
            const postTypes = capabilities.post_types || [];
            const selectedType = postTypes.find(item => item.slug === options.post_type) || postTypes[0];
            const taxonomies = (selectedType?.taxonomies || [])
              .map(slug => capabilities.taxonomies?.[slug])
              .filter((item): item is WordPressTaxonomy => !!item);
            const imageAttachments = attachments.filter(item => item.media_type === "image");
            return (
              <Card key={`wordpress-${channelId}`} className="border-blue-200">
                <CardHeader className="pb-3">
                  <CardTitle className="text-base flex items-center gap-2">
                    <Globe className="w-4 h-4 text-blue-600" /> تنظیمات وردپرس
                  </CardTitle>
                  <p className="text-xs text-muted-foreground">{channel.wordpress?.site_name || channel.name}</p>
                </CardHeader>
                <CardContent className="space-y-4">
                  {loadingWordpress === channelId ? (
                    <div className="flex items-center gap-2 text-sm text-muted-foreground">
                      <Loader2 className="w-4 h-4 animate-spin" /> در حال دریافت تنظیمات سایت...
                    </div>
                  ) : postTypes.length === 0 ? (
                    <div className="rounded-lg border border-amber-200 bg-amber-50 p-3 text-xs text-amber-900">
                      اطلاعات نوع محتوا در دسترس نیست. از صفحه کانال‌ها «به‌روزرسانی اطلاعات» را بزنید.
                    </div>
                  ) : (
                    <>
                      <div className="space-y-2">
                        <Label htmlFor={`wp-type-${channelId}`}>نوع محتوا</Label>
                        <select
                          id={`wp-type-${channelId}`}
                          value={options.post_type}
                          onChange={event => updateWordpressOptions(channelId, {
                            post_type: event.target.value,
                            taxonomy_terms: {},
                          })}
                          className="flex h-10 w-full rounded-md border border-input bg-background px-3 py-2 text-sm"
                        >
                          {postTypes.map(item => <option key={item.slug} value={item.slug}>{item.name}</option>)}
                        </select>
                      </div>

                      <div className="space-y-2">
                        <Label>وضعیت در وردپرس</Label>
                        <div className="grid grid-cols-3 gap-2">
                          {([['draft', 'پیش‌نویس'], ['pending', 'در انتظار'], ['publish', 'انتشار']] as const).map(([value, label]) => (
                            <button
                              type="button"
                              key={value}
                              onClick={() => updateWordpressOptions(channelId, { status: value })}
                              className={`rounded-lg border p-2 text-xs ${options.status === value ? "border-primary bg-primary/5 text-primary" : "border-border"}`}
                            >{label}</button>
                          ))}
                        </div>
                        {options.status === "draft" && <p className="text-xs text-muted-foreground">محتوا منتشر نمی‌شود و ابتدا برای بازبینی وارد وردپرس خواهد شد.</p>}
                      </div>

                      <details className="rounded-lg border p-3">
                        <summary className="cursor-pointer text-sm font-medium">تنظیمات پیشرفته وردپرس</summary>
                        <div className="mt-4 space-y-4">
                          {taxonomies.map(taxonomy => (
                            <div key={taxonomy.slug} className="space-y-2">
                              <Label>{taxonomy.name}</Label>
                              {taxonomy.terms.length ? (
                                <div className="max-h-36 space-y-2 overflow-y-auto rounded-md border p-2">
                                  {taxonomy.terms.map(term => {
                                    const selected = options.taxonomy_terms[taxonomy.slug] || [];
                                    return (
                                      <label key={term.id} className="flex cursor-pointer items-center gap-2 text-sm">
                                        <input
                                          type="checkbox"
                                          checked={selected.includes(term.id)}
                                          onChange={() => updateWordpressOptions(channelId, {
                                            taxonomy_terms: {
                                              ...options.taxonomy_terms,
                                              [taxonomy.slug]: selected.includes(term.id)
                                                ? selected.filter(id => id !== term.id)
                                                : [...selected, term.id],
                                            },
                                          })}
                                        />
                                        <span>{term.name}</span>
                                      </label>
                                    );
                                  })}
                                </div>
                              ) : <p className="text-xs text-muted-foreground">موردی در سایت تعریف نشده است.</p>}
                            </div>
                          ))}

                          {(!selectedType?.supports || selectedType.supports.excerpt) && (
                            <div className="space-y-2">
                              <Label htmlFor={`wp-excerpt-${channelId}`}>خلاصه</Label>
                              <Textarea id={`wp-excerpt-${channelId}`} rows={3} value={options.excerpt}
                                onChange={event => updateWordpressOptions(channelId, { excerpt: event.target.value })}
                                placeholder="خلاصه کوتاه محتوا (اختیاری)" />
                            </div>
                          )}
                          <div className="space-y-2">
                            <Label htmlFor={`wp-slug-${channelId}`}>نامک</Label>
                            <Input id={`wp-slug-${channelId}`} dir="ltr" value={options.slug}
                              onChange={event => updateWordpressOptions(channelId, { slug: event.target.value })}
                              placeholder="my-post-slug" />
                          </div>
                          {imageAttachments.length > 0 && (
                            <div className="space-y-2">
                              <Label htmlFor={`wp-featured-${channelId}`}>تصویر شاخص</Label>
                              <select id={`wp-featured-${channelId}`} value={options.featured_attachment_id}
                                onChange={event => updateWordpressOptions(channelId, { featured_attachment_id: event.target.value })}
                                className="flex h-10 w-full rounded-md border border-input bg-background px-3 py-2 text-sm">
                                <option value="">اولین تصویر ضمیمه‌شده</option>
                                {imageAttachments.map(item => <option key={item.id} value={item.id}>{item.original_filename}</option>)}
                              </select>
                            </div>
                          )}
                        </div>
                      </details>

                      <details className="rounded-lg bg-blue-50 p-3 text-xs text-blue-950">
                        <summary className="cursor-pointer font-medium">راهنمای انتشار در وردپرس</summary>
                        <ol className="mt-2 list-decimal space-y-1 pr-4 leading-6">
                          <li>نوع محتوا و وضعیت را انتخاب کنید؛ حالت امن پیش‌فرض «پیش‌نویس» است.</li>
                          <li>در صورت نیاز تنظیمات پیشرفته، دسته‌ها و تصویر شاخص را مشخص کنید.</li>
                          <li>پس از ارسال، از لینک نتیجه برای بازبینی یا ویرایش در وردپرس استفاده کنید.</li>
                        </ol>
                      </details>

                      <div className="rounded-lg bg-muted/50 p-3 text-xs leading-6">
                        <span className="font-medium">خلاصه: </span>
                        {channel.wordpress?.site_name || channel.name} · {selectedType?.name} · {options.status === "draft" ? "پیش‌نویس" : options.status === "pending" ? "در انتظار بررسی" : "انتشار مستقیم"}
                      </div>
                    </>
                  )}
                </CardContent>
              </Card>
            );
          })}

          {/* Publish Time */}
          <Card>
            <CardHeader className="pb-3">
              <CardTitle className="text-base">زمان انتشار</CardTitle>
            </CardHeader>
            <CardContent className="space-y-3">
              <div className="grid grid-cols-2 gap-2">
                <button
                  onClick={() => setPublishType("now")}
                  className={`flex items-center gap-2 p-3 rounded-lg border-2 text-sm font-medium transition-all ${publishType === "now" ? "border-primary bg-primary/5 text-primary" : "border-border hover:border-muted-foreground"}`}
                >
                  <RadioIcon className="w-4 h-4" />
                  همین الان
                </button>
                <button
                  onClick={() => setPublishType("schedule")}
                  className={`flex items-center gap-2 p-3 rounded-lg border-2 text-sm font-medium transition-all ${publishType === "schedule" ? "border-primary bg-primary/5 text-primary" : "border-border hover:border-muted-foreground"}`}
                >
                  <CalendarIcon className="w-4 h-4" />
                  زمان‌بندی
                </button>
              </div>

              {publishType === "schedule" && (
                <div className="space-y-1">
                  <Label>تاریخ و زمان انتشار</Label>
                  <Input
                    type="datetime-local"
                    value={scheduledAt}
                    onChange={e => setScheduledAt(e.target.value)}
                    min={new Date().toISOString().slice(0, 16)}
                    className="dir-ltr"
                  />
                </div>
              )}
            </CardContent>
          </Card>

          {/* Submit */}
          <Button
            className="w-full gap-2 h-12 text-base"
            onClick={handlePublish}
            disabled={!canPublish()}
          >
            {publishing ? (
              <><Loader2 className="w-5 h-5 animate-spin" /> در حال انتشار...</>
            ) : publishType === "now" ? (
              <><Send className="w-5 h-5" /> {
                selectedChannels.some(id => channels.find(channel => channel.id === id)?.platform === "wordpress") &&
                selectedChannels.filter(id => channels.find(channel => channel.id === id)?.platform === "wordpress")
                  .every(id => (wordpressOptions[id]?.status || "draft") === "draft")
                  ? "ارسال (وردپرس به‌صورت پیش‌نویس)"
                  : "انتشار"
              }</>
            ) : (
              <><Clock className="w-5 h-5" /> زمان‌بندی انتشار</>
            )}
          </Button>

          {selectedChannels.length > 0 && (
            <p className="text-xs text-center text-muted-foreground">
              {selectedChannels.length} کانال انتخاب شده
            </p>
          )}
        </div>
      </div>
    </div>
  );
}
