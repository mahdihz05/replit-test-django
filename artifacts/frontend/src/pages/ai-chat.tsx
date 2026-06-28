import { useState } from "react";
import { useAuth } from "@/lib/auth";
import { Card } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { Bot, User, SendHorizontal, MessageSquare, Loader2, Sparkles } from "lucide-react";
import { ScrollArea } from "@/components/ui/scroll-area";

interface Message {
  id: string;
  role: "user" | "ai";
  content: string;
}

export default function AiChat() {
  const [messages, setMessages] = useState<Message[]>([
    { id: "1", role: "ai", content: "سلام! من دستیار هوشمند شما هستم. چطور می‌توانم در تولید یا ویرایش محتوا به شما کمک کنم؟" }
  ]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);

  const handleSend = () => {
    if (!input.trim()) return;
    
    const newMsg: Message = { id: Date.now().toString(), role: "user", content: input };
    setMessages(prev => [...prev, newMsg]);
    setInput("");
    setLoading(true);

    // Mock response
    setTimeout(() => {
      setMessages(prev => [...prev, {
        id: (Date.now() + 1).toString(),
        role: "ai",
        content: "البته! من می‌توانم متن شما را به صورت حرفه‌ای بازنویسی کنم یا ایده‌های جدیدی برای شبکه‌های اجتماعی پیشنهاد دهم."
      }]);
      setLoading(false);
    }, 1500);
  };

  return (
    <div className="h-[calc(100vh-10rem)] flex flex-col md:flex-row gap-6">
      {/* Sessions Sidebar - hidden on mobile */}
      <Card className="hidden md:flex flex-col w-64 shrink-0 bg-muted/20">
        <div className="p-4 border-b border-border">
          <Button className="w-full gap-2">
            <MessageSquare className="w-4 h-4" /> گفتگوی جدید
          </Button>
        </div>
        <ScrollArea className="flex-1">
          <div className="p-2 space-y-1">
            {[1, 2, 3].map(i => (
              <div key={i} className={`p-3 text-sm rounded-md cursor-pointer transition-colors ${i === 1 ? 'bg-primary/10 text-primary font-medium' : 'hover:bg-muted'}`}>
                {i === 1 ? 'ایده پست اینستاگرام' : i === 2 ? 'بازنویسی مقاله' : 'کپشن تلگرام'}
              </div>
            ))}
          </div>
        </ScrollArea>
      </Card>

      {/* Chat Area */}
      <Card className="flex-1 flex flex-col overflow-hidden shadow-sm border-primary/10">
        <div className="p-4 border-b border-border bg-card flex items-center gap-3">
          <div className="w-10 h-10 rounded-full bg-primary/10 flex items-center justify-center">
            <Sparkles className="w-5 h-5 text-primary" />
          </div>
          <div>
            <h2 className="font-semibold">دستیار خلاق محتوا</h2>
            <p className="text-xs text-muted-foreground">پاسخگویی سریع بر پایه GPT-4</p>
          </div>
        </div>

        <ScrollArea className="flex-1 p-4 bg-muted/5">
          <div className="space-y-6 max-w-3xl mx-auto py-4">
            {messages.map(msg => (
              <div key={msg.id} className={`flex gap-4 ${msg.role === "ai" ? "" : "flex-row-reverse"}`}>
                <div className={`w-8 h-8 shrink-0 rounded-full flex items-center justify-center mt-1 ${
                  msg.role === "ai" ? "bg-primary/20 text-primary" : "bg-secondary text-secondary-foreground"
                }`}>
                  {msg.role === "ai" ? <Bot className="w-4 h-4" /> : <User className="w-4 h-4" />}
                </div>
                <div className={`px-4 py-3 rounded-2xl max-w-[85%] text-sm leading-relaxed ${
                  msg.role === "ai" 
                    ? "bg-card border shadow-sm rounded-tr-sm" 
                    : "bg-primary text-primary-foreground rounded-tl-sm"
                }`}>
                  {msg.content}
                </div>
              </div>
            ))}
            {loading && (
              <div className="flex gap-4">
                <div className="w-8 h-8 shrink-0 rounded-full bg-primary/20 text-primary flex items-center justify-center mt-1">
                  <Bot className="w-4 h-4" />
                </div>
                <div className="px-4 py-3 bg-card border shadow-sm rounded-2xl rounded-tr-sm flex items-center gap-2">
                  <span className="w-1.5 h-1.5 bg-primary/60 rounded-full animate-bounce" style={{ animationDelay: "0ms" }}></span>
                  <span className="w-1.5 h-1.5 bg-primary/60 rounded-full animate-bounce" style={{ animationDelay: "150ms" }}></span>
                  <span className="w-1.5 h-1.5 bg-primary/60 rounded-full animate-bounce" style={{ animationDelay: "300ms" }}></span>
                </div>
              </div>
            )}
          </div>
        </ScrollArea>

        <div className="p-4 bg-card border-t border-border">
          <div className="max-w-3xl mx-auto relative flex items-center">
            <Input 
              placeholder="درخواست خود را بنویسید..." 
              className="pr-4 pl-14 py-6 rounded-full bg-muted/50 border-transparent focus-visible:bg-background focus-visible:border-primary"
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={(e) => e.key === "Enter" && handleSend()}
            />
            <Button 
              size="icon" 
              className="absolute left-1.5 rounded-full w-9 h-9" 
              onClick={handleSend}
              disabled={loading || !input.trim()}
            >
              <SendHorizontal className="w-4 h-4 rtl:-scale-x-100" />
            </Button>
          </div>
          <div className="text-center mt-2">
            <span className="text-[10px] text-muted-foreground">هوش مصنوعی ممکن است اشتباه کند. اطلاعات را بررسی کنید.</span>
          </div>
        </div>
      </Card>
    </div>
  );
}
