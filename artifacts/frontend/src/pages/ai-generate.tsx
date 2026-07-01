import { useState } from "react";
import { useAuth } from "@/lib/auth";
import { apiFetch } from "@/lib/api";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { useToast } from "@/hooks/use-toast";
import { Wand2, Copy, Save, Loader2, CheckCheck } from "lucide-react";

type Tab = "text" | "rewrite" | "summary" | "scenario" | "title" | "hashtag" | "cta" | "idea";
type Mode = "standard" | "bundle" | "multi_variant";

interface GeneratedItem {
  id: string;
  item_type: "full_text" | "short_text" | "hashtags" | "title" | "variant";
  order: number;
  content: string;
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

  const wid = selectedWorkspace?.id;

  const estimatedCost = () => {
    if (mode === "bundle") return COSTS.ai_generate_bundle;
    if (mode === "multi_variant") {
      return variantCount === "2" ? COSTS.ai_generate_variant_2 : COSTS.ai_generate_variant_3;
    }
    switch (activeTab) {
      case "text":
      case "scenario":
        return COSTS.text_generation;
      case "rewrite":
      case "summary":
        return COSTS.content_rewrite;
      case "title":
      case "idea":
        return COSTS.title_suggestions;
      case "hashtag":
        return COSTS.hashtag_suggestions;
      case "cta":
        return COSTS.cta_generation;
      default:
        return 0;
    }
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
    switch (activeTab) {
      case "text":
        response = await apiFetch(`/workspaces/${wid}/ai/generate/text/`, {
          method: "POST", data: { goal, tone, platform, language: "fa", word_count: parseInt(wordCount) }
        });
        setResult(response?.data?.text ?? "");
        break;
      case "rewrite":
        response = await apiFetch(`/workspaces/${wid}/ai/generate/rewrite/`, {
          method: "POST", data: { text: inputText, tone }
        });
        setResult(response?.data?.text ?? "");
        break;
      case "summary":
        response = await apiFetch(`/workspaces/${wid}/ai/generate/summary/`, {
          method: "POST", data: { text: inputText, length: summaryLength }
        });
        setResult(response?.data?.text ?? "");
        break;
      case "scenario":
        response = await apiFetch(`/workspaces/${wid}/ai/generate/scenario/`, {
          method: "POST", data: { topic, platform, goal: scenarioGoal }
        });
        setResult(response?.data?.text ?? "");
        break;
      case "title":
        response = await apiFetch(`/workspaces/${wid}/ai/generate/titles/`, {
          method: "POST", data: { topic, count: parseInt(count) }
        });
        setResult(response?.data?.titles ?? []);
        break;
      case "hashtag":
        response = await apiFetch(`/workspaces/${wid}/ai/generate/hashtags/`, {
          method: "POST", data: { topic, platform, count: parseInt(count) }
        });
        setResult(response?.data?.hashtags ?? []);
        break;
      case "cta":
        response = await apiFetch(`/workspaces/${wid}/ai/generate/cta/`, {
          method: "POST", data: { goal, platform, count: parseInt(count) }
        });
        setResult(response?.data?.ctas ?? []);
        break;
      case "idea":
        response = await apiFetch(`/workspaces/${wid}/ai/generate/idea/`, {
          method: "POST", data: { niche, platform, count: parseInt(count) }
        });
        setResult(response?.data?.ideas ?? []);
        break;
    }
  };

  const handleBundleGenerate = async () => {
    if (!wid) return;
    const response = await apiFetch(`/workspaces/${wid}/ai/generate/bundle/`, {
      method: "POST",
      data: { topic: goal || topic, tone, platform }
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
        data: {}
      });
      setItems(prev => prev.map(i => i.id === item.id ? { ...i, saved_as_draft: true } : i));
      toast({ title: "ذخیره شد", description: "محتوا در پیش‌نویس‌ها ذخیره شد" });
    } catch (error: any) {
      toast({ title: "خطا", description: error.message || "خطا در ذخیره", variant: "destructive" });
    } finally {
      setSaving(prev => ({ ...prev, [item.id]: false }));
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
            {activeTab === "rewrite" && (
              <div>
                <label className="text-sm font-medium block mb-1.5">لحن بازنویسی</label>
                <Select value={tone} onValueChange={setTone}>
                  <SelectTrigger><SelectValue /></SelectTrigger>
                  <SelectContent>{TONES.map(t => <SelectItem key={t.value} value={t.value}>{t.label}</SelectItem>)}</SelectContent>
                </Select>
              </div>
            )}
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
        <p className="text-muted-foreground mt-1">تولید محتوا با GPT-4o برای تمام نیازهای بازاریابی</p>
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
            <div className="text-sm text-muted-foreground flex items-center justify-between">
              <span>هزینه تخمینی: <strong className="text-foreground">{estimatedCost()} تومان</strong></span>
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
              Array.isArray(result) ? (
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
              )
            )}
            {!loading && (mode === "bundle" || mode === "multi_variant") && items.length === 0 && (
              <div className="flex items-center justify-center h-48 text-muted-foreground border-2 border-dashed rounded-lg">
                <p className="text-sm">نتیجه اینجا نمایش داده می‌شود</p>
              </div>
            )}
            {!loading && (mode === "bundle" || mode === "multi_variant") && items.length > 0 && (
              <div className={`grid gap-4 ${mode === "multi_variant" ? "grid-cols-1" : "grid-cols-1"}`}>
                {items.map(item => (
                  <div key={item.id} className="p-4 bg-muted/50 rounded-lg border">
                    <div className="flex items-center justify-between mb-2">
                      <span className="text-xs font-semibold text-primary bg-primary/10 px-2 py-1 rounded">
                        {item.item_type === "variant" ? `نسخه ${item.order}` : ITEM_LABELS[item.item_type] || item.item_type}
                      </span>
                      <div className="flex gap-2">
                        <Button size="sm" variant="outline" className="gap-1.5 h-8" onClick={() => handleCopy(item.content, item.id)}>
                          {copied[item.id] ? <CheckCheck className="w-3.5 h-3.5 text-green-500" /> : <Copy className="w-3.5 h-3.5" />}
                          {copied[item.id] ? "کپی شد" : "کپی"}
                        </Button>
                        <Button
                          size="sm"
                          className="gap-1.5 h-8"
                          onClick={() => handleSaveItem(item)}
                          disabled={item.saved_as_draft || saving[item.id]}
                        >
                          {saving[item.id] ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <Save className="w-3.5 h-3.5" />}
                          {item.saved_as_draft ? "ذخیره شده" : "ذخیره"}
                        </Button>
                      </div>
                    </div>
                    <div className="text-sm leading-relaxed whitespace-pre-wrap">
                      {item.item_type === "hashtags" ? item.content.split("\n").map((h, i) => <div key={i} className="inline-block ml-2">{h}</div>) : item.content}
                    </div>
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
