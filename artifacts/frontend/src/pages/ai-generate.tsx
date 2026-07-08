import { useState } from "react";
import { useAuth } from "@/lib/auth";
import { apiFetch } from "@/lib/api";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Checkbox } from "@/components/ui/checkbox";
import { Label } from "@/components/ui/label";
import { useToast } from "@/hooks/use-toast";
import { Wand2, Copy, Save, Loader2, CheckCheck, Image, RefreshCcw } from "lucide-react";

type Tab = "text" | "rewrite" | "summary" | "scenario" | "title" | "hashtag" | "cta" | "idea";
type Mode = "standard" | "bundle" | "multi_variant";

interface GeneratedItem {
  id: string;
  item_type: "full_text" | "short_text" | "hashtags" | "title" | "variant" | "image";
  order: number;
  content: string;
  image?: string;
  image_url?: string;
  saved_as_draft?: boolean;
}

const TABS: { id: Tab; label: string }[] = [
  { id: "text", label: "تولید متن" },
  { id: "scenario", label: "سناریو" },
  { id: "rewrite", label: "بازنویسی" },
  { id: "summary", label: "خلاصه" },
  { id: "title", label: "عنوان" },
  { id: "cta", label: "CTA" },
  { id: "hashtag", label: "هشتگ" },
  { id: "idea", label: "ایده" },
];

const TONES = [
  { value: "حرفه‌ای", label: "حرفه‌ای" },
  { value: "صمیمی", label: "صمیمی" },
  { value: "رسمی", label: "رسمی" },
  { value: "خلاقانه", label: "خلاقانه" },
  { value: "طنز", label: "طنز" },
];

const PLATFORMS = [
  { value: "telegram", label: "تلگرام" },
  { value: "instagram", label: "اینستاگرام" },
  { value: "linkedin", label: "لینکدین" },
  { value: "website", label: "وب‌سایت" },
  { value: "", label: "عمومی" },
];

const COSTS: Record<string, number> = {
  text_generation: 10,
  content_rewrite: 8,
  title_suggestions: 3,
  hashtag_suggestions: 2,
  cta_generation: 3,
  ai_generate_bundle: 25,
  ai_generate_variant_2: 16,
  ai_generate_variant_3: 22,
};

const ITEM_LABELS: Record<string, string> = {
  full_text: "متن کامل",
  short_text: "نسخه کوتاه",
  hashtags: "هشتگ‌ها",
  title: "عنوان",
  variant: "نسخه",
};

export default function AiGenerate() {
  const { selectedWorkspace } = useAuth();
  const { toast } = useToast();
  const [mode, setMode] = useState<Mode>("standard");
  const [activeTab, setActiveTab] = useState<Tab>("text");
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<string | string[]>("");
  const [items, setItems] = useState<GeneratedItem[]>([]);
  const [copied, setCopied] = useState<Record<string, boolean>>({});
  const [saving, setSaving] = useState<Record<string, boolean>>({});

  const [goal, setGoal] = useState("");
  const [tone, setTone] = useState("حرفه‌ای");
  const [platform, setPlatform] = useState("");
  const [wordCount, setWordCount] = useState("300");
  const [inputText, setInputText] = useState("");
  const [topic, setTopic] = useState("");
  const [summaryLength, setSummaryLength] = useState("brief");
  const [scenarioGoal, setScenarioGoal] = useState("");
  const [count, setCount] = useState("5");
  const [niche, setNiche] = useState("");
  const [variantCount, setVariantCount] = useState("2");
  const [generateImage, setGenerateImage] = useState(false);
  const [includeImage, setIncludeImage] = useState(false);
  const [imageRegenerating, setImageRegenerating] = useState<Record<string, boolean>>({});
  const [imagePreviewOpen, setImagePreviewOpen] = useState<string | null>(null);

  const wid = selectedWorkspace?.id;

  const IMAGE_COST = 12;

  const estimatedCost = () => {
    let base = 0;
    if (mode === "bundle") base = COSTS.ai_generate_bundle;
    else if (mode === "multi_variant") {
      base = variantCount === "2" ? COSTS.ai_generate_variant_2 : COSTS.ai_generate_variant_3;
    } else {
      switch (activeTab) {
        case "text":
        case "scenario":
          base = COSTS.text_generation; break;
        case "rewrite":
        case "summary":
          base = COSTS.content_rewrite; break;
        case "title":
        case "idea":
          base = COSTS.title_suggestions; break;
        case "hashtag":
          base = COSTS.hashtag_suggestions; break;
        case "cta":
          base = COSTS.cta_generation; break;
        default:
          base = 0;
      }
    }
    return base + (generateImage ? IMAGE_COST : 0);
  };

  const resetResults = () => {
    setResult("");
    setItems([]);
  };

  const handleModeChange = (newMode: Mode) => {
    setMode(newMode);
    resetResults();
  };

  const handleStandardGenerate = async () => {
    if (!wid) return;
    let response: any;
    const img = { generate_image: generateImage };
    switch (activeTab) {
      case "text":
        response = await apiFetch(`/workspaces/${wid}/ai/generate/text/`, {
          method: "POST", data: { goal, tone, platform, language: "fa", word_count: parseInt(wordCount), ...img }
        });
        break;
      case "rewrite":
        response = await apiFetch(`/workspaces/${wid}/ai/generate/rewrite/`, {
          method: "POST", data: { text: inputText, tone, platform, ...img }
        });
        break;
      case "summary":
        response = await apiFetch(`/workspaces/${wid}/ai/generate/summary/`, {
          method: "POST", data: { text: inputText, length: summaryLength, platform, ...img }
        });
        break;
      case "scenario":
        response = await apiFetch(`/workspaces/${wid}/ai/generate/scenario/`, {
          method: "POST", data: { topic, platform, goal: scenarioGoal, ...img }
        });
        break;
      case "title":
        response = await apiFetch(`/workspaces/${wid}/ai/generate/titles/`, {
          method: "POST", data: { topic, count: parseInt(count), platform, ...img }
        });
        break;
      case "hashtag":
        response = await apiFetch(`/workspaces/${wid}/ai/generate/hashtags/`, {
          method: "POST", data: { topic, platform, count: parseInt(count), ...img }
        });
        break;
      case "cta":
        response = await apiFetch(`/workspaces/${wid}/ai/generate/cta/`, {
          method: "POST", data: { goal, platform, count: parseInt(count), ...img }
        });
        break;
      case "idea":
        response = await apiFetch(`/workspaces/${wid}/ai/generate/idea/`, {
          method: "POST", data: { niche, platform, count: parseInt(count), ...img }
        });
        break;
    }

    // When generate_image is on, backend returns a batch with items (including the image item)
    if (response?.data?.items) {
      setItems(response.data.items);
      // Also keep the first text item in result for legacy text display
      const textItem = response.data.items.find((i: GeneratedItem) => ["full_text", "variant"].includes(i.item_type));
      setResult(textItem ? textItem.content : "");
    } else {
      if (activeTab === "title") setResult(response?.data?.titles ?? []);
      else if (activeTab === "hashtag") setResult(response?.data?.hashtags ?? []);
      else if (activeTab === "cta") setResult(response?.data?.ctas ?? []);
      else if (activeTab === "idea") setResult(response?.data?.ideas ?? []);
      else setResult(response?.data?.text ?? "");
      setItems([]);
    }
  };

  const handleBundleGenerate = async () => {
    if (!wid) return;
    const response = await apiFetch(`/workspaces/${wid}/ai/generate/bundle/`, {
      method: "POST",
      data: { topic: goal || topic, tone, platform, generate_image: generateImage }
    });
    setItems(response?.data?.items ?? []);
  };

  const handleMultiVariantGenerate = async () => {
    if (!wid) return;
    const payload: any = {
      capability: activeTab,
      variant_count: parseInt(variantCount),
      tone,
      platform,
      generate_image: generateImage,
    };
    switch (activeTab) {
      case "text":
        payload.goal = goal;
        payload.word_count = parseInt(wordCount);
        break;
      case "rewrite":
        payload.text = inputText;
        break;
      case "summary":
        payload.text = inputText;
        payload.length = summaryLength;
        break;
      case "scenario":
        payload.topic = topic;
        payload.goal = scenarioGoal;
        break;
      case "title":
      case "hashtag":
        payload.topic = topic;
        break;
      case "cta":
        payload.goal = goal;
        break;
      case "idea":
        payload.niche = niche;
        break;
    }
    const response = await apiFetch(`/workspaces/${wid}/ai/generate/multi-variant/`, {
      method: "POST",
      data: payload
    });
    setItems(response?.data?.items ?? []);
  };

  const handleGenerate = async () => {
    if (!wid) return;
    setLoading(true);
    resetResults();
    try {
      if (mode === "standard") await handleStandardGenerate();
      else if (mode === "bundle") await handleBundleGenerate();
      else if (mode === "multi_variant") await handleMultiVariantGenerate();
    } catch (error: any) {
      toast({ title: "خطا", description: error.message || "خطا در تولید محتوا", variant: "destructive" });
    } finally {
      setLoading(false);
    }
  };

  const handleCopy = (text: string, key: string) => {
    navigator.clipboard.writeText(text);
    setCopied(prev => ({ ...prev, [key]: true }));
    setTimeout(() => setCopied(prev => ({ ...prev, [key]: false })), 2000);
  };

  const handleSaveItem = async (item: GeneratedItem) => {
    if (!wid || item.saved_as_draft) return;
    setSaving(prev => ({ ...prev, [item.id]: true }));
    try {
      await apiFetch(`/workspaces/${wid}/ai/generate/items/${item.id}/save/`, {
        method: "POST",
        data: { include_image: includeImage }
      });
      setItems(prev => prev.map(i => i.id === item.id ? { ...i, saved_as_draft: true } : i));
      toast({ title: "ذخیره شد", description: "محتوا در پیش‌نویس‌ها ذخیره شد" });
    } catch (error: any) {
      toast({ title: "خطا", description: error.message || "خطا در ذخیره", variant: "destructive" });
    } finally {
      setSaving(prev => ({ ...prev, [item.id]: false }));
    }
  };

  const handleRegenerateImage = async (item: GeneratedItem) => {
    if (!wid || item.item_type !== "variant") return;
    setImageRegenerating(prev => ({ ...prev, [item.id]: true }));
    try {
      const res = await apiFetch(`/workspaces/${wid}/ai/generate/items/${item.id}/regenerate-image/`, {
        method: "POST",
      });
      const imageItem = res?.data;
      if (imageItem) {
        setItems(prev => [...prev, imageItem]);
        toast({ title: "تصویر جدید", description: "تصویر جدید برای این نسخه تولید شد" });
      }
    } catch (error: any) {
      toast({ title: "خطا", description: error.message || "تولید تصویر با خطا مواجه شد", variant: "destructive" });
    } finally {
      setImageRegenerating(prev => ({ ...prev, [item.id]: false }));
    }
  };

  const handleSaveStandard = async () => {
    if (!result || !wid) return;
    const body = Array.isArray(result) ? result.join("\n") : result;
    try {
      await apiFetch(`/workspaces/${wid}/contents/`, {
        method: "POST",
        data: { title: (goal || topic || niche || "محتوای تولید شده").slice(0, 100), body, status: "draft" }
      });
      toast({ title: "ذخیره شد", description: "محتوا در پیش‌نویس‌ها ذخیره شد" });
    } catch (error: any) {
      toast({ title: "خطا", description: error.message || "خطا در ذخیره", variant: "destructive" });
    }
  };

  const renderStandardForm = () => {
    switch (activeTab) {
      case "text":
        return (
          <div className="space-y-4">
            <div>
              <label className="text-sm font-medium block mb-1.5">موضوع یا هدف محتوا *</label>
              <Textarea placeholder="مثال: معرفی محصول جدید کرم ضدآفتاب برای پوست حساس..." value={goal} onChange={e => setGoal(e.target.value)} className="min-h-[80px]" />
            </div>
            <div className="grid grid-cols-2 gap-3">
              <div>
                <label className="text-sm font-medium block mb-1.5">لحن</label>
                <Select value={tone} onValueChange={setTone}>
                  <SelectTrigger><SelectValue /></SelectTrigger>
                  <SelectContent>{TONES.map(t => <SelectItem key={t.value} value={t.value}>{t.label}</SelectItem>)}</SelectContent>
                </Select>
              </div>
              <div>
                <label className="text-sm font-medium block mb-1.5">پلتفرم</label>
                <Select value={platform} onValueChange={setPlatform}>
                  <SelectTrigger><SelectValue placeholder="انتخاب کنید" /></SelectTrigger>
                  <SelectContent>{PLATFORMS.map(p => <SelectItem key={p.value} value={p.value}>{p.label}</SelectItem>)}</SelectContent>
                </Select>
              </div>
            </div>
            <div>
              <label className="text-sm font-medium block mb-1.5">تعداد کلمات تقریبی</label>
              <Select value={wordCount} onValueChange={setWordCount}>
                <SelectTrigger><SelectValue /></SelectTrigger>
                <SelectContent>
                  <SelectItem value="100">کوتاه (~۱۰۰)</SelectItem>
                  <SelectItem value="300">متوسط (~۳۰۰)</SelectItem>
                  <SelectItem value="600">بلند (~۶۰۰)</SelectItem>
                  <SelectItem value="1000">مفصل (~۱۰۰۰)</SelectItem>
                </SelectContent>
              </Select>
            </div>
          </div>
        );
      case "rewrite":
      case "summary":
        return (
          <div className="space-y-4">
            <div>
              <label className="text-sm font-medium block mb-1.5">متن ورودی *</label>
              <Textarea placeholder="متنی که می‌خواهید پردازش شود را اینجا وارد کنید..." value={inputText} onChange={e => setInputText(e.target.value)} className="min-h-[150px]" />
            </div>
            <div className="grid grid-cols-2 gap-3">
              {activeTab === "rewrite" && (
                <div>
                  <label className="text-sm font-medium block mb-1.5">لحن بازنویسی</label>
                  <Select value={tone} onValueChange={setTone}>
                    <SelectTrigger><SelectValue /></SelectTrigger>
                    <SelectContent>{TONES.map(t => <SelectItem key={t.value} value={t.value}>{t.label}</SelectItem>)}</SelectContent>
                  </Select>
                </div>
              )}
              <div>
                <label className="text-sm font-medium block mb-1.5">پلتفرم مقصد</label>
                <Select value={platform} onValueChange={setPlatform}>
                  <SelectTrigger><SelectValue placeholder="انتخاب کنید" /></SelectTrigger>
                  <SelectContent>{PLATFORMS.map(p => <SelectItem key={p.value} value={p.value}>{p.label}</SelectItem>)}</SelectContent>
                </Select>
              </div>
              {activeTab === "summary" && (
                <div>
                  <label className="text-sm font-medium block mb-1.5">طول خلاصه</label>
                  <Select value={summaryLength} onValueChange={setSummaryLength}>
                    <SelectTrigger><SelectValue /></SelectTrigger>
                    <SelectContent>
                      <SelectItem value="brief">کوتاه و فشرده</SelectItem>
                      <SelectItem value="detailed">جامع و کامل</SelectItem>
                    </SelectContent>
                  </Select>
                </div>
              )}
            </div>
          </div>
        );
      case "scenario":
        return (
          <div className="space-y-4">
            <div>
              <label className="text-sm font-medium block mb-1.5">موضوع *</label>
              <Input placeholder="موضوع اصلی محتوا..." value={topic} onChange={e => setTopic(e.target.value)} />
            </div>
            <div className="grid grid-cols-2 gap-3">
              <div>
                <label className="text-sm font-medium block mb-1.5">پلتفرم</label>
                <Select value={platform} onValueChange={setPlatform}>
                  <SelectTrigger><SelectValue placeholder="انتخاب..." /></SelectTrigger>
                  <SelectContent>{PLATFORMS.map(p => <SelectItem key={p.value} value={p.value}>{p.label}</SelectItem>)}</SelectContent>
                </Select>
              </div>
              <div>
                <label className="text-sm font-medium block mb-1.5">هدف</label>
                <Input placeholder="جذب مخاطب، فروش، آموزش..." value={scenarioGoal} onChange={e => setScenarioGoal(e.target.value)} />
              </div>
            </div>
          </div>
        );
      case "title":
      case "hashtag":
        return (
          <div className="space-y-4">
            <div>
              <label className="text-sm font-medium block mb-1.5">موضوع *</label>
              <Input placeholder="موضوع محتوا..." value={topic} onChange={e => setTopic(e.target.value)} />
            </div>
            <div className="grid grid-cols-2 gap-3">
              {activeTab === "hashtag" && (
                <div>
                  <label className="text-sm font-medium block mb-1.5">پلتفرم</label>
                  <Select value={platform} onValueChange={setPlatform}>
                    <SelectTrigger><SelectValue placeholder="انتخاب..." /></SelectTrigger>
                    <SelectContent>{PLATFORMS.map(p => <SelectItem key={p.value} value={p.value}>{p.label}</SelectItem>)}</SelectContent>
                  </Select>
                </div>
              )}
              <div>
                <label className="text-sm font-medium block mb-1.5">تعداد</label>
                <Select value={count} onValueChange={setCount}>
                  <SelectTrigger><SelectValue /></SelectTrigger>
                  <SelectContent>
                    <SelectItem value="3">۳ مورد</SelectItem>
                    <SelectItem value="5">۵ مورد</SelectItem>
                    <SelectItem value="10">۱۰ مورد</SelectItem>
                  </SelectContent>
                </Select>
              </div>
            </div>
          </div>
        );
      case "cta":
        return (
          <div className="space-y-4">
            <div>
              <label className="text-sm font-medium block mb-1.5">هدف یا محصول *</label>
              <Input placeholder="مثال: ثبت‌نام در دوره آموزشی طراحی سایت..." value={goal} onChange={e => setGoal(e.target.value)} />
            </div>
            <div className="grid grid-cols-2 gap-3">
              <div>
                <label className="text-sm font-medium block mb-1.5">پلتفرم</label>
                <Select value={platform} onValueChange={setPlatform}>
                  <SelectTrigger><SelectValue placeholder="انتخاب..." /></SelectTrigger>
                  <SelectContent>{PLATFORMS.map(p => <SelectItem key={p.value} value={p.value}>{p.label}</SelectItem>)}</SelectContent>
                </Select>
              </div>
              <div>
                <label className="text-sm font-medium block mb-1.5">تعداد</label>
                <Select value={count} onValueChange={setCount}>
                  <SelectTrigger><SelectValue /></SelectTrigger>
                  <SelectContent>
                    <SelectItem value="3">۳ مورد</SelectItem>
                    <SelectItem value="5">۵ مورد</SelectItem>
                  </SelectContent>
                </Select>
              </div>
            </div>
          </div>
        );
      case "idea":
        return (
          <div className="space-y-4">
            <div>
              <label className="text-sm font-medium block mb-1.5">حوزه کاری *</label>
              <Input placeholder="مثال: فروشگاه پوشاک، کلینیک زیبایی، آموزش زبان..." value={niche} onChange={e => setNiche(e.target.value)} />
            </div>
            <div className="grid grid-cols-2 gap-3">
              <div>
                <label className="text-sm font-medium block mb-1.5">پلتفرم</label>
                <Select value={platform} onValueChange={setPlatform}>
                  <SelectTrigger><SelectValue placeholder="انتخاب..." /></SelectTrigger>
                  <SelectContent>{PLATFORMS.map(p => <SelectItem key={p.value} value={p.value}>{p.label}</SelectItem>)}</SelectContent>
                </Select>
              </div>
              <div>
                <label className="text-sm font-medium block mb-1.5">تعداد ایده</label>
                <Select value={count} onValueChange={setCount}>
                  <SelectTrigger><SelectValue /></SelectTrigger>
                  <SelectContent>
                    <SelectItem value="3">۳ ایده</SelectItem>
                    <SelectItem value="5">۵ ایده</SelectItem>
                    <SelectItem value="10">۱۰ ایده</SelectItem>
                  </SelectContent>
                </Select>
              </div>
            </div>
          </div>
        );
      default:
        return null;
    }
  };

  const renderBundleForm = () => (
    <div className="space-y-4">
      <div>
        <label className="text-sm font-medium block mb-1.5">موضوع یا هدف محتوا *</label>
        <Textarea placeholder="مثال: معرفی محصول جدید کرم ضدآفتاب برای پوست حساس..." value={goal} onChange={e => setGoal(e.target.value)} className="min-h-[120px]" />
      </div>
      <div className="grid grid-cols-2 gap-3">
        <div>
          <label className="text-sm font-medium block mb-1.5">لحن</label>
          <Select value={tone} onValueChange={setTone}>
            <SelectTrigger><SelectValue /></SelectTrigger>
            <SelectContent>{TONES.map(t => <SelectItem key={t.value} value={t.value}>{t.label}</SelectItem>)}</SelectContent>
          </Select>
        </div>
        <div>
          <label className="text-sm font-medium block mb-1.5">پلتفرم</label>
          <Select value={platform} onValueChange={setPlatform}>
            <SelectTrigger><SelectValue placeholder="انتخاب کنید" /></SelectTrigger>
            <SelectContent>{PLATFORMS.map(p => <SelectItem key={p.value} value={p.value}>{p.label}</SelectItem>)}</SelectContent>
          </Select>
        </div>
      </div>
    </div>
  );

  const renderMultiVariantForm = () => (
    <div className="space-y-4">
      {renderStandardForm()}
      <div>
        <label className="text-sm font-medium block mb-1.5">تعداد نسخه</label>
        <Select value={variantCount} onValueChange={setVariantCount}>
          <SelectTrigger><SelectValue /></SelectTrigger>
          <SelectContent>
            <SelectItem value="2">۲ نسخه</SelectItem>
            <SelectItem value="3">۳ نسخه</SelectItem>
          </SelectContent>
        </Select>
      </div>
    </div>
  );

  const renderForm = () => {
    if (mode === "bundle") return renderBundleForm();
    if (mode === "multi_variant") return renderMultiVariantForm();
    return renderStandardForm();
  };

  const isGenerateDisabled = () => {
    if (mode === "bundle") return !goal && !topic;
    if (mode === "multi_variant" || mode === "standard") {
      if (activeTab === "text") return !goal;
      if (activeTab === "rewrite" || activeTab === "summary") return !inputText;
      if (activeTab === "scenario") return !topic;
      if (activeTab === "title" || activeTab === "hashtag") return !topic;
      if (activeTab === "cta") return !goal;
      if (activeTab === "idea") return !niche;
    }
    return false;
  };

  const resultText = Array.isArray(result) ? result.join("\n") : result;

  return (
    <div className="space-y-6 max-w-5xl mx-auto">
      <div>
        <h1 className="text-3xl font-bold tracking-tight">ابزارهای هوش مصنوعی</h1>
        <p className="text-muted-foreground mt-1">تولید محتوا با GPT-4.1 mini برای تمام نیازهای بازاریابی</p>
      </div>

      <div className="flex gap-2 overflow-x-auto pb-1 scrollbar-none">
        {[
          { id: "standard", label: "استاندارد" },
          { id: "bundle", label: "بازتولید همزمان" },
          { id: "multi_variant", label: "چندگزینه‌ای" },
        ].map(m => (
          <button
            key={m.id}
            onClick={() => handleModeChange(m.id as Mode)}
            className={`px-4 py-2 rounded-full text-sm font-medium whitespace-nowrap transition-colors shrink-0 ${
              mode === m.id
                ? "bg-primary text-primary-foreground"
                : "bg-muted hover:bg-muted/80 text-foreground/70"
            }`}
          >
            {m.label}
          </button>
        ))}
      </div>

      {mode !== "bundle" && (
        <div className="flex gap-2 overflow-x-auto pb-1 scrollbar-none">
          {TABS.map(tab => (
            <button
              key={tab.id}
              onClick={() => { setActiveTab(tab.id); resetResults(); }}
              className={`px-4 py-2 rounded-full text-sm font-medium whitespace-nowrap transition-colors shrink-0 ${
                activeTab === tab.id
                  ? "bg-primary/10 text-primary border border-primary/20"
                  : "bg-muted hover:bg-muted/80 text-foreground/70"
              }`}
            >
              {tab.label}
            </button>
          ))}
        </div>
      )}

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <Card>
          <CardHeader className="pb-3">
            <CardTitle className="text-base">
              {mode === "bundle" ? "ورودی بازتولید همزمان" : mode === "multi_variant" ? "ورودی چندگزینه‌ای" : "ورودی"}
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            {renderForm()}
            <div className="space-y-2 pt-2">
              <div className="flex items-center gap-2">
                <Checkbox id="generateImage" checked={generateImage} onCheckedChange={v => setGenerateImage(!!v)} />
                <Label htmlFor="generateImage" className="text-sm font-normal flex items-center gap-1.5">
                  <Image className="w-3.5 h-3.5" /> تولید تصویر همزمان با متن (+{IMAGE_COST} تومان)
                </Label>
              </div>
              <div className="text-sm text-muted-foreground flex items-center justify-between">
                <span>هزینه تخمینی: <strong className="text-foreground">{estimatedCost()} تومان</strong></span>
              </div>
            </div>
            <Button
              className="w-full gap-2 mt-2"
              onClick={handleGenerate}
              disabled={loading || isGenerateDisabled()}
              size="lg"
            >
              {loading
                ? <><Loader2 className="w-4 h-4 animate-spin" /> در حال تولید...</>
                : <><Wand2 className="w-4 h-4" /> تولید با هوش مصنوعی</>
              }
            </Button>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="pb-3">
            <div className="flex items-center justify-between">
              <CardTitle className="text-base">نتیجه</CardTitle>
              <div className="flex items-center gap-3">
                {items.some(i => i.item_type === "image") && (
                  <div className="flex items-center gap-2">
                    <Checkbox id="includeImage" checked={includeImage} onCheckedChange={v => setIncludeImage(!!v)} />
                    <Label htmlFor="includeImage" className="text-xs font-normal">هنگام ذخیره، تصویر هم ضمیمه شود</Label>
                  </div>
                )}
                {mode === "standard" && result && (
                  <div className="flex gap-2">
                    <Button size="sm" variant="outline" className="gap-1.5 h-8" onClick={() => handleCopy(resultText, "standard")}>
                      {copied["standard"] ? <CheckCheck className="w-3.5 h-3.5 text-green-500" /> : <Copy className="w-3.5 h-3.5" />}
                      {copied["standard"] ? "کپی شد" : "کپی"}
                    </Button>
                    <Button size="sm" className="gap-1.5 h-8" onClick={handleSaveStandard}>
                      <Save className="w-3.5 h-3.5" /> ذخیره
                    </Button>
                  </div>
                )}
              </div>
            </div>
          </CardHeader>
          <CardContent>
            {loading && (
              <div className="flex items-center justify-center h-48 text-muted-foreground">
                <div className="text-center space-y-3">
                  <Loader2 className="w-8 h-8 animate-spin mx-auto text-primary" />
                  <p className="text-sm">هوش مصنوعی در حال کار است...</p>
                </div>
              </div>
            )}
            {!loading && mode === "standard" && !result && (
              <div className="flex items-center justify-center h-48 text-muted-foreground border-2 border-dashed rounded-lg">
                <p className="text-sm">نتیجه اینجا نمایش داده می‌شود</p>
              </div>
            )}
            {mode === "standard" && result && (
              <div className="space-y-4">
                {Array.isArray(result) ? (
                  <ul className="space-y-2">
                    {result.map((item, i) => (
                      <li key={i} className="p-3 bg-muted/50 rounded-lg text-sm flex items-start gap-2">
                        <span className="text-primary font-bold shrink-0">{i + 1}.</span>
                        <span>{item}</span>
                      </li>
                    ))}
                  </ul>
                ) : (
                  <Textarea
                    value={result as string}
                    onChange={e => setResult(e.target.value)}
                    className="min-h-[280px] text-sm leading-relaxed resize-none"
                  />
                )}
                {items.filter(i => i.item_type === "image").map(img => (
                  <div key={img.id} className="relative rounded-lg overflow-hidden border group">
                    <img src={img.image_url || img.image} alt="تصویر تولیدشده" className="w-full h-auto max-h-80 object-contain" />
                    <div className="absolute top-2 right-2 opacity-0 group-hover:opacity-100 transition-opacity">
                      <Button size="sm" variant="outline" className="bg-white/90" onClick={() => handleCopy(img.image_url || img.image || "", img.id)}>
                        {copied[img.id] ? <CheckCheck className="w-3.5 h-3.5 text-green-500" /> : <Copy className="w-3.5 h-3.5" />}
                      </Button>
                    </div>
                  </div>
                ))}
              </div>
            )}
            {!loading && (mode === "bundle" || mode === "multi_variant") && items.length === 0 && (
              <div className="flex items-center justify-center h-48 text-muted-foreground border-2 border-dashed rounded-lg">
                <p className="text-sm">نتیجه اینجا نمایش داده می‌شود</p>
              </div>
            )}
            {!loading && (mode === "bundle" || mode === "multi_variant") && items.length > 0 && (
              <div className="grid gap-4 grid-cols-1">
                {items.map(item => (
                  <div key={item.id} className="p-4 bg-muted/50 rounded-lg border">
                    <div className="flex items-center justify-between mb-2">
                      <span className="text-xs font-semibold text-primary bg-primary/10 px-2 py-1 rounded">
                        {item.item_type === "variant" ? `نسخه ${item.order}` : item.item_type === "image" ? "تصویر" : ITEM_LABELS[item.item_type] || item.item_type}
                      </span>
                      <div className="flex gap-2">
                        {item.item_type === "image" ? (
                          <Button size="sm" variant="outline" className="gap-1.5 h-8" onClick={() => handleCopy(item.image_url || item.image || "", item.id)}>
                            {copied[item.id] ? <CheckCheck className="w-3.5 h-3.5 text-green-500" /> : <Copy className="w-3.5 h-3.5" />}
                            {copied[item.id] ? "کپی شد" : "کپی"}
                          </Button>
                        ) : (
                          <>
                            <Button size="sm" variant="outline" className="gap-1.5 h-8" onClick={() => handleCopy(item.content, item.id)}>
                              {copied[item.id] ? <CheckCheck className="w-3.5 h-3.5 text-green-500" /> : <Copy className="w-3.5 h-3.5" />}
                              {copied[item.id] ? "کپی شد" : "کپی"}
                            </Button>
                            {mode === "multi_variant" && item.item_type === "variant" && (
                              <Button
                                size="sm"
                                variant="outline"
                                className="gap-1.5 h-8"
                                onClick={() => handleRegenerateImage(item)}
                                disabled={imageRegenerating[item.id]}
                              >
                                {imageRegenerating[item.id] ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <RefreshCcw className="w-3.5 h-3.5" />}
                                تصویر برای این نسخه
                              </Button>
                            )}
                            <Button
                              size="sm"
                              className="gap-1.5 h-8"
                              onClick={() => handleSaveItem(item)}
                              disabled={item.saved_as_draft || saving[item.id]}
                            >
                              {saving[item.id] ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <Save className="w-3.5 h-3.5" />}
                              {item.saved_as_draft ? "ذخیره شده" : "ذخیره"}
                            </Button>
                          </>
                        )}
                      </div>
                    </div>
                    {item.item_type === "image" ? (
                      <div className="relative rounded-lg overflow-hidden border group">
                        <img src={item.image_url || item.image} alt="تصویر تولیدشده" className="w-full h-auto max-h-80 object-contain" />
                      </div>
                    ) : (
                      <div className="text-sm leading-relaxed whitespace-pre-wrap">
                        {item.item_type === "hashtags" ? item.content.split("\n").map((h, i) => <div key={i} className="inline-block ml-2">{h}</div>) : item.content}
                      </div>
                    )}
                  </div>
                ))}
              </div>
            )}
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
