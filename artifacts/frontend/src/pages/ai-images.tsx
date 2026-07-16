import { useState, useEffect } from "react";
import { useAuth } from "@/lib/auth";
import { apiFetch } from "@/lib/api";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { useToast } from "@/hooks/use-toast";
import { ImageIcon, Loader2, Download, Wand2, Wallet, FileText } from "lucide-react";
import { Link } from "wouter";

const PLATFORMS = [
  { value: "", label: "عمومی" },
  { value: "telegram", label: "تلگرام" },
  { value: "bale", label: "بله" },
  { value: "instagram", label: "اینستاگرام" },
  { value: "linkedin", label: "لینکدین" },
  { value: "website", label: "وب‌سایت" },
];

interface ImageHistoryItem {
  url: string;
  prompt: string;
  platform: string;
  contentId?: string;
}

interface ImageContent {
  id: string;
  title: string;
  body: string;
  image_url: string | null;
}

export default function AiImages() {
  const { selectedWorkspace } = useAuth();
  const { toast } = useToast();
  const [prompt, setPrompt] = useState("");
  const [style, setStyle] = useState("vivid");
  const [platform, setPlatform] = useState("");
  const [loading, setLoading] = useState(false);
  const [generatedUrl, setGeneratedUrl] = useState<string | null>(null);
  const [contentId, setContentId] = useState<string | null>(null);
  const [history, setHistory] = useState<ImageHistoryItem[]>([]);
  const [historyLoading, setHistoryLoading] = useState(false);
  const [walletBalance, setWalletBalance] = useState<number | null>(null);
  const [imageCost, setImageCost] = useState<number | null>(null);

  useEffect(() => {
    if (!selectedWorkspace) {
      setHistory([]);
      setWalletBalance(null);
      setImageCost(null);
      return;
    }

    setGeneratedUrl(null);
    setContentId(null);
    setHistoryLoading(true);
    const walletRequest = apiFetch(`/workspaces/${selectedWorkspace.id}/wallet/`)
      .then((walletResponse) => {
        setWalletBalance(Number(walletResponse?.data?.balance ?? 0));
        const configuredCost = walletResponse?.data?.wallet_costs?.image_generation;
        setImageCost(configuredCost == null ? null : Number(configuredCost));
      })
      .catch(() => {
        setWalletBalance(null);
        setImageCost(null);
      });

    const historyRequest = apiFetch(`/workspaces/${selectedWorkspace.id}/contents/?has_image=true&source=ai`)
      .then((contentResponse) => {
        const contents: ImageContent[] = Array.isArray(contentResponse?.data) ? contentResponse.data : [];
        setHistory(contents
          .filter((content) => !!content.image_url)
          .slice(0, 12)
          .map((content) => ({
            url: content.image_url as string,
            prompt: content.body || content.title,
            platform: "",
            contentId: content.id,
          })));
      })
      .catch((error: any) => {
        toast({ title: "خطا", description: error.message || "دریافت اطلاعات تصاویر ناموفق بود", variant: "destructive" });
      });

    Promise.allSettled([walletRequest, historyRequest])
      .finally(() => setHistoryLoading(false));
  }, [selectedWorkspace]);

  const hasInsufficientBalance = walletBalance !== null && imageCost !== null && walletBalance < imageCost;

  const handleGenerate = async () => {
    if (!prompt.trim() || !selectedWorkspace || hasInsufficientBalance) return;
    setLoading(true);
    setGeneratedUrl(null);
    try {
      const response = await apiFetch(`/workspaces/${selectedWorkspace.id}/ai/generate/image/`, {
        method: "POST",
        data: { description: prompt, style, platform }
      });
      const url = response?.data?.image_url ?? response?.image_url;
      const id = response?.data?.content_id ?? response?.content_id;
      if (url) {
        setGeneratedUrl(url);
        setContentId(id || null);
        setHistory(prev => [{ url, prompt, platform, contentId: id }, ...prev.slice(0, 11)]);
        if (imageCost !== null) {
          setWalletBalance((balance) => balance === null ? null : Math.max(0, balance - imageCost));
        }
      }
    } catch (error: any) {
      toast({ title: "خطا", description: error.message || "خطا در تولید تصویر", variant: "destructive" });
    } finally {
      setLoading(false);
    }
  };

  const handleDownload = (url: string) => {
    const a = document.createElement("a");
    a.href = url;
    a.download = "ai-image.png";
    a.target = "_blank";
    a.click();
  };

  return (
    <div className="space-y-6 max-w-5xl mx-auto">
      <div>
        <h1 className="text-3xl font-bold tracking-tight">تولید تصویر با هوش مصنوعی</h1>
        <p className="text-muted-foreground mt-1">با GPT Image تصاویر خلاقانه بسازید</p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <Card>
          <CardHeader className="pb-3">
            <CardTitle className="text-base">توضیح تصویر</CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <Textarea
              placeholder="مثال: یک فنجان قهوه روی میز چوبی کنار پنجره، نور طلایی غروب آفتاب، عکاسی حرفه‌ای..."
              value={prompt}
              onChange={(e) => setPrompt(e.target.value)}
              className="min-h-[140px] text-sm"
            />
            <div>
              <label className="text-sm font-medium block mb-1.5">سبک تصویر</label>
              <Select value={style} onValueChange={setStyle}>
                <SelectTrigger>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="vivid">پرجنب‌وجوش (Vivid)</SelectItem>
                  <SelectItem value="natural">طبیعی (Natural)</SelectItem>
                </SelectContent>
              </Select>
            </div>
            <div>
              <label className="text-sm font-medium block mb-1.5">پلتفرم مقصد</label>
              <Select value={platform} onValueChange={setPlatform}>
                <SelectTrigger>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  {PLATFORMS.map(p => <SelectItem key={p.value} value={p.value}>{p.label}</SelectItem>)}
                </SelectContent>
              </Select>
            </div>
            <div className="p-3 bg-amber-50 dark:bg-amber-900/20 rounded-lg text-xs text-amber-800 dark:text-amber-400">
              ⚠️ هزینه هر بار تولید تصویر {imageCost === null ? "در حال دریافت..." : `${imageCost.toLocaleString("fa-IR")} تومان`} است
            </div>
            {walletBalance !== null && (
              <div className={`text-xs flex items-center justify-between ${hasInsufficientBalance ? "text-destructive font-medium" : "text-muted-foreground"}`}>
                <span className="flex items-center gap-1"><Wallet className="w-3.5 h-3.5" /> موجودی: {walletBalance.toLocaleString("fa-IR")} تومان</span>
                {hasInsufficientBalance && <span>موجودی کافی نیست</span>}
              </div>
            )}
            <Button
              className="w-full gap-2"
              size="lg"
              onClick={handleGenerate}
              disabled={loading || !prompt.trim() || hasInsufficientBalance || imageCost === null}
            >
              {loading
                ? <><Loader2 className="w-4 h-4 animate-spin" /> در حال تولید تصویر...</>
                : <><Wand2 className="w-4 h-4" /> تولید تصویر</>
              }
            </Button>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="pb-3">
            <CardTitle className="text-base">تصویر تولید شده</CardTitle>
          </CardHeader>
          <CardContent>
            {loading && (
              <div className="flex flex-col items-center justify-center h-64 gap-4 text-muted-foreground">
                <Loader2 className="w-10 h-10 animate-spin text-primary" />
                <p className="text-sm">در حال تولید تصویر... (معمولاً ۱۵-۳۰ ثانیه)</p>
              </div>
            )}
            {!loading && !generatedUrl && (
              <div className="flex flex-col items-center justify-center h-64 border-2 border-dashed rounded-lg gap-3 text-muted-foreground">
                <ImageIcon className="w-12 h-12 opacity-20" />
                <p className="text-sm">تصویر اینجا نمایش داده می‌شود</p>
              </div>
            )}
            {!loading && generatedUrl && (
              <div className="space-y-3">
                <img
                  src={generatedUrl}
                  alt="تصویر تولید شده"
                  className="w-full rounded-lg border shadow-sm object-cover"
                />
                <Button
                  variant="outline"
                  className="w-full gap-2"
                  onClick={() => handleDownload(generatedUrl)}
                >
                  <Download className="w-4 h-4" /> دانلود تصویر
                </Button>
                {contentId && (
                  <Link href={`/contents/${contentId}`}>
                    <Button className="w-full gap-2">
                      <FileText className="w-4 h-4" /> مشاهده در محتواها
                    </Button>
                  </Link>
                )}
                <p className="text-xs text-muted-foreground text-center">
                  این تصویر به عنوان پیش‌نویس در بخش محتواها ذخیره شد.
                </p>
              </div>
            )}
          </CardContent>
        </Card>
      </div>

      {historyLoading && (
        <Card>
          <CardContent className="py-10 flex items-center justify-center gap-2 text-muted-foreground">
            <Loader2 className="w-5 h-5 animate-spin" /> در حال دریافت تاریخچه تصاویر...
          </CardContent>
        </Card>
      )}

      {!historyLoading && history.length > 0 && (
        <div>
          <h2 className="text-lg font-semibold mb-4">تاریخچه تصاویر</h2>
          <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 gap-4">
            {history.map((item, i) => (
              <div key={i} className="group relative rounded-lg overflow-hidden border shadow-sm cursor-pointer" onClick={() => { setGeneratedUrl(item.url); setContentId(item.contentId || null); }}>
                <img src={item.url} alt={item.prompt} className="w-full aspect-square object-cover" />
                <div className="absolute inset-0 bg-black/60 opacity-0 group-hover:opacity-100 transition-opacity flex items-end p-2">
                  <p className="text-white text-xs line-clamp-2">{item.prompt}{item.platform ? ` • ${item.platform}` : ""}</p>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
