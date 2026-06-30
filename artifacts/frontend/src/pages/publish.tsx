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
  FileText, Edit3, RadioIcon, CalendarIcon, AlertCircle
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
  status: string;
  created_at: string;
}

interface PublishResult {
  channel_id: string;
  channel_name: string;
  platform: string;
  status: "success" | "failed";
  error?: string;
  message_id?: string;
}

function getPlatformIcon(platform: string) {
  if (platform === "telegram") return <Send className="w-4 h-4 text-blue-500" />;
  if (platform === "bale") return <Share2 className="w-4 h-4 text-green-500" />;
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
  const [publishType, setPublishType] = useState<"now" | "schedule">("now");
  const [scheduledAt, setScheduledAt] = useState("");

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

  const filteredContents = contents.filter(c =>
    c.title?.toLowerCase().includes(contentSearch.toLowerCase()) ||
    c.body?.toLowerCase().includes(contentSearch.toLowerCase())
  );

  const toggleChannel = (id: string) => {
    setSelectedChannels(prev =>
      prev.includes(id) ? prev.filter(x => x !== id) : [...prev, id]
    );
  };

  const canPublish = () => {
    const hasText = contentTab === "saved" ? !!selectedContent : customText.trim().length > 0;
    const hasChannels = selectedChannels.length > 0;
    const hasTime = publishType === "now" || !!scheduledAt;
    return hasText && hasChannels && hasTime && !publishing;
  };

  const handlePublish = async () => {
    if (!selectedWorkspace || !canPublish()) return;
    setPublishing(true);
    setResults(null);

    const payload: any = {
      channel_ids: selectedChannels,
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
                          {ch.platform === "telegram" ? "تلگرام" : "بله"} · {ch.channel_type === "channel" ? "کانال" : "گروه"}
                        </p>
                      </div>
                    </button>
                  ))}
                </div>
              )}
            </CardContent>
          </Card>

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
              <><Send className="w-5 h-5" /> انتشار</>
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
