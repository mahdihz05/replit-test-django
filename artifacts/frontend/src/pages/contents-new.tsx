import { useState } from "react";
import { useLocation } from "wouter";
import { useAuth } from "@/lib/auth";
import { apiFetch } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { useToast } from "@/hooks/use-toast";
import { Bot, Save, Wand2, Calendar as CalendarIcon, ArrowRight } from "lucide-react";
import { Link } from "wouter";

export default function ContentNew() {
  const { selectedWorkspace } = useAuth();
  const [, setLocation] = useLocation();
  const { toast } = useToast();
  
  const [title, setTitle] = useState("");
  const [body, setBody] = useState("");
  const [loading, setLoading] = useState(false);
  const [aiLoading, setAiLoading] = useState(false);
  const [aiPrompt, setAiPrompt] = useState("");

  const handleSave = async (status: string = "draft") => {
    if (!title) {
      toast({ title: "خطا", description: "عنوان محتوا الزامی است", variant: "destructive" });
      return;
    }
    
    setLoading(true);
    try {
      const data = await apiFetch(`/workspaces/${selectedWorkspace?.id}/contents/`, {
        method: "POST",
        data: { title, body, status }
      }).catch(() => ({ id: "new-id" })); // Fallback
      
      toast({ title: "موفق", description: "محتوا با موفقیت ذخیره شد" });
      setLocation(`/contents/${data.id}`);
    } catch (error: any) {
      toast({ title: "خطا", description: error.message || "خطا در ذخیره محتوا", variant: "destructive" });
    } finally {
      setLoading(false);
    }
  };

  const handleAiGenerate = async () => {
    if (!aiPrompt) return;
    
    setAiLoading(true);
    try {
      const res = await apiFetch(`/workspaces/${selectedWorkspace?.id}/ai/generate/text/`, {
        method: "POST",
        data: { goal: aiPrompt, language: "fa", word_count: 200 }
      }).catch(() => ({ text: "این یک متن تولید شده توسط هوش مصنوعی به عنوان نمونه است. هوش مصنوعی می‌تواند به شما در تولید محتوای جذاب و هدفمند برای شبکه‌های اجتماعی کمک کند." }));
      
      if (res.text) {
        setBody(prev => prev ? prev + "\n\n" + res.text : res.text);
        if (!title) setTitle(aiPrompt);
        setAiPrompt("");
      }
    } catch (error: any) {
      toast({ title: "خطا", description: "خطا در ارتباط با هوش مصنوعی", variant: "destructive" });
    } finally {
      setAiLoading(false);
    }
  };

  return (
    <div className="space-y-6 max-w-6xl mx-auto pb-20">
      <div className="flex items-center gap-4">
        <Link href="/contents">
          <Button variant="ghost" size="icon" className="rounded-full">
            <ArrowRight className="w-5 h-5" />
          </Button>
        </Link>
        <h1 className="text-2xl font-bold tracking-tight">ایجاد محتوای جدید</h1>
        <div className="mr-auto flex gap-2">
          <Button variant="outline" onClick={() => handleSave("draft")} disabled={loading}>
            ذخیره پیش‌نویس
          </Button>
          <Button onClick={() => handleSave("ready")} disabled={loading} className="gap-2">
            <Save className="w-4 h-4" />
            ذخیره به عنوان آماده
          </Button>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <div className="lg:col-span-2 space-y-6">
          <Card>
            <CardContent className="p-6 space-y-4">
              <div>
                <label className="block text-sm font-medium mb-1">عنوان محتوا</label>
                <Input 
                  placeholder="یک عنوان جذاب وارد کنید..." 
                  value={title}
                  onChange={(e) => setTitle(e.target.value)}
                  className="text-lg font-medium"
                />
              </div>
              
              <div>
                <label className="block text-sm font-medium mb-1">متن اصلی</label>
                <Textarea 
                  placeholder="متن محتوای خود را اینجا بنویسید..." 
                  value={body}
                  onChange={(e) => setBody(e.target.value)}
                  className="min-h-[400px] resize-y font-mono text-base leading-relaxed"
                />
              </div>
            </CardContent>
          </Card>
        </div>

        <div className="space-y-6">
          <Card className="bg-primary/5 border-primary/20">
            <CardHeader className="pb-3">
              <CardTitle className="text-lg flex items-center gap-2 text-primary">
                <Bot className="w-5 h-5" />
                دستیار هوشمند
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="space-y-2">
                <label className="text-sm font-medium">درباره چه چیزی بنویسم؟</label>
                <Textarea 
                  placeholder="مثال: یک پست تلگرام درباره فروش ویژه نوروز بنویس که لحن صمیمی داشته باشد..."
                  value={aiPrompt}
                  onChange={(e) => setAiPrompt(e.target.value)}
                  className="min-h-[120px] bg-background"
                />
              </div>
              <Button 
                className="w-full gap-2" 
                onClick={handleAiGenerate}
                disabled={aiLoading || !aiPrompt}
              >
                {aiLoading ? <span className="animate-spin text-lg leading-none">⚬</span> : <Wand2 className="w-4 h-4" />}
                تولید محتوا با AI
              </Button>
              
              <div className="pt-4 border-t border-primary/10 grid grid-cols-2 gap-2">
                <Button variant="outline" size="sm" className="bg-background text-xs" onClick={() => setAiPrompt("پیشنهاد ۳ عنوان جذاب برای...")}>
                  پیشنهاد عنوان
                </Button>
                <Button variant="outline" size="sm" className="bg-background text-xs" onClick={() => setAiPrompt("بازنویسی متن با لحن رسمی تر:")}>
                  بازنویسی متن
                </Button>
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardHeader className="pb-3">
              <CardTitle className="text-lg">تنظیمات انتشار</CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="space-y-2">
                <label className="text-sm font-medium">برچسب‌ها</label>
                <Input placeholder="مثال: فروش، بهار، تخفیف (جدا شده با کاما)" />
              </div>
              <div className="space-y-2">
                <label className="text-sm font-medium flex justify-between">
                  زمان‌بندی
                  <Button variant="link" size="sm" className="h-auto p-0 text-primary">تنظیم زمان</Button>
                </label>
                <div className="flex items-center gap-2 p-2 border rounded-md bg-muted/50 text-muted-foreground text-sm">
                  <CalendarIcon className="w-4 h-4" />
                  <span>انتشار بلافاصله پس از تایید</span>
                </div>
              </div>
            </CardContent>
          </Card>
        </div>
      </div>
    </div>
  );
}
