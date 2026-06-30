import { useState, useEffect, useRef } from "react";
import { useAuth } from "@/lib/auth";
import { apiFetch } from "@/lib/api";
import { Card } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { useToast } from "@/hooks/use-toast";
import { Bot, User, SendHorizontal, MessageSquare, Loader2, Sparkles, Plus, Trash2 } from "lucide-react";
import { ScrollArea } from "@/components/ui/scroll-area";

interface Message {
  id: string;
  role: "user" | "assistant";
  body: string;
  created_at: string;
}

interface Session {
  id: string;
  title: string;
  updated_at: string;
}

export default function AiChat() {
  const { selectedWorkspace } = useAuth();
  const { toast } = useToast();
  const [sessions, setSessions] = useState<Session[]>([]);
  const [activeSession, setActiveSession] = useState<Session | null>(null);
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState("");
  const [sending, setSending] = useState(false);
  const [loadingSessions, setLoadingSessions] = useState(false);
  const [loadingMessages, setLoadingMessages] = useState(false);
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (selectedWorkspace) fetchSessions();
  }, [selectedWorkspace]);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  const fetchSessions = async () => {
    setLoadingSessions(true);
    try {
      const response = await apiFetch(`/workspaces/${selectedWorkspace?.id}/ai/chat/sessions/`);
      const list = Array.isArray(response) ? response : (response?.data ?? []);
      setSessions(list);
      if (list.length > 0 && !activeSession) {
        loadSession(list[0]);
      }
    } catch {
      setSessions([]);
    } finally {
      setLoadingSessions(false);
    }
  };

  const loadSession = async (session: Session) => {
    setActiveSession(session);
    setLoadingMessages(true);
    try {
      const response = await apiFetch(`/workspaces/${selectedWorkspace?.id}/ai/chat/sessions/${session.id}/`);
      const data = response?.data ?? response;
      const msgs: Message[] = (data?.messages ?? []).map((m: any) => ({
        id: m.id,
        role: m.role,
        body: m.body,
        created_at: m.created_at,
      }));
      setMessages(msgs);
    } catch {
      setMessages([]);
    } finally {
      setLoadingMessages(false);
    }
  };

  const createNewSession = async () => {
    try {
      const response = await apiFetch(`/workspaces/${selectedWorkspace?.id}/ai/chat/sessions/`, {
        method: "POST",
        data: {}
      });
      const session = response?.data ?? response;
      setSessions(prev => [session, ...prev]);
      setActiveSession(session);
      setMessages([]);
    } catch (error: any) {
      toast({ title: "خطا", description: error.message || "خطا در ایجاد گفتگو", variant: "destructive" });
    }
  };

  const handleSend = async () => {
    if (!input.trim() || !activeSession) return;

    const userMsg: Message = {
      id: Date.now().toString(),
      role: "user",
      body: input,
      created_at: new Date().toISOString(),
    };
    setMessages(prev => [...prev, userMsg]);
    const sentInput = input;
    setInput("");
    setSending(true);

    try {
      const response = await apiFetch(
        `/workspaces/${selectedWorkspace?.id}/ai/chat/sessions/${activeSession.id}/messages/`,
        { method: "POST", data: { message: sentInput } }
      );
      const aiMsg = response?.data ?? response;
      setMessages(prev => [...prev, {
        id: aiMsg.id ?? (Date.now() + 1).toString(),
        role: "assistant",
        body: aiMsg.body,
        created_at: aiMsg.created_at ?? new Date().toISOString(),
      }]);
      setSessions(prev => prev.map(s =>
        s.id === activeSession.id
          ? { ...s, title: s.title === "New Chat" ? sentInput.slice(0, 40) : s.title }
          : s
      ));
    } catch (error: any) {
      toast({ title: "خطا", description: error.message || "خطا در ارسال پیام", variant: "destructive" });
      setMessages(prev => prev.filter(m => m.id !== userMsg.id));
      setInput(sentInput);
    } finally {
      setSending(false);
    }
  };

  return (
    <div className="h-[calc(100vh-10rem)] flex flex-col md:flex-row gap-4">
      <Card className="hidden md:flex flex-col w-64 shrink-0 overflow-hidden">
        <div className="p-3 border-b">
          <Button className="w-full gap-2" size="sm" onClick={createNewSession}>
            <Plus className="w-4 h-4" /> گفتگوی جدید
          </Button>
        </div>
        <ScrollArea className="flex-1">
          {loadingSessions ? (
            <div className="p-4 text-center text-sm text-muted-foreground">در حال بارگذاری...</div>
          ) : sessions.length === 0 ? (
            <div className="p-4 text-center text-sm text-muted-foreground">گفتگویی وجود ندارد</div>
          ) : (
            <div className="p-2 space-y-1">
              {sessions.map(s => (
                <button
                  key={s.id}
                  onClick={() => loadSession(s)}
                  className={`w-full text-right p-2.5 text-sm rounded-md transition-colors truncate ${
                    activeSession?.id === s.id
                      ? "bg-primary/10 text-primary font-medium"
                      : "hover:bg-muted text-foreground/70"
                  }`}
                >
                  <MessageSquare className="w-3.5 h-3.5 inline ml-2 opacity-60" />
                  {s.title || "گفتگوی جدید"}
                </button>
              ))}
            </div>
          )}
        </ScrollArea>
      </Card>

      <Card className="flex-1 flex flex-col overflow-hidden">
        <div className="p-4 border-b flex items-center gap-3 shrink-0">
          <div className="w-9 h-9 rounded-full bg-primary/10 flex items-center justify-center">
            <Sparkles className="w-4 h-4 text-primary" />
          </div>
          <div>
            <h2 className="font-semibold text-sm">دستیار هوشمند محتوا</h2>
            <p className="text-xs text-muted-foreground">GPT-4o · فارسی و انگلیسی</p>
          </div>
          <div className="mr-auto md:hidden">
            <Button size="sm" variant="outline" className="gap-1.5" onClick={createNewSession}>
              <Plus className="w-3.5 h-3.5" /> جدید
            </Button>
          </div>
        </div>

        <ScrollArea className="flex-1 p-4">
          <div className="space-y-5 max-w-3xl mx-auto py-2">
            {!activeSession && !loadingSessions && (
              <div className="text-center py-16 text-muted-foreground">
                <Bot className="w-12 h-12 mx-auto mb-3 opacity-20" />
                <p className="text-sm">یک گفتگوی جدید شروع کنید</p>
                <Button className="mt-4 gap-2" size="sm" onClick={createNewSession}>
                  <Plus className="w-4 h-4" /> شروع گفتگو
                </Button>
              </div>
            )}
            {loadingMessages && (
              <div className="text-center py-8">
                <Loader2 className="w-6 h-6 animate-spin mx-auto text-muted-foreground" />
              </div>
            )}
            {messages.map(msg => (
              <div key={msg.id} className={`flex gap-3 ${msg.role === "assistant" ? "" : "flex-row-reverse"}`}>
                <div className={`w-8 h-8 shrink-0 rounded-full flex items-center justify-center mt-1 ${
                  msg.role === "assistant" ? "bg-primary/10 text-primary" : "bg-secondary"
                }`}>
                  {msg.role === "assistant" ? <Bot className="w-4 h-4" /> : <User className="w-4 h-4" />}
                </div>
                <div className={`px-4 py-3 rounded-2xl max-w-[85%] text-sm leading-relaxed whitespace-pre-wrap ${
                  msg.role === "assistant"
                    ? "bg-card border shadow-sm rounded-tr-sm"
                    : "bg-primary text-primary-foreground rounded-tl-sm"
                }`}>
                  {msg.body}
                </div>
              </div>
            ))}
            {sending && (
              <div className="flex gap-3">
                <div className="w-8 h-8 shrink-0 rounded-full bg-primary/10 flex items-center justify-center">
                  <Bot className="w-4 h-4 text-primary" />
                </div>
                <div className="px-4 py-3 bg-card border shadow-sm rounded-2xl rounded-tr-sm flex items-center gap-1.5">
                  <span className="w-1.5 h-1.5 bg-primary/60 rounded-full animate-bounce" style={{ animationDelay: "0ms" }} />
                  <span className="w-1.5 h-1.5 bg-primary/60 rounded-full animate-bounce" style={{ animationDelay: "150ms" }} />
                  <span className="w-1.5 h-1.5 bg-primary/60 rounded-full animate-bounce" style={{ animationDelay: "300ms" }} />
                </div>
              </div>
            )}
            <div ref={bottomRef} />
          </div>
        </ScrollArea>

        <div className="p-4 border-t bg-card shrink-0">
          <div className="max-w-3xl mx-auto flex items-center gap-2">
            <Input
              placeholder={activeSession ? "پیام خود را بنویسید..." : "ابتدا یک گفتگو شروع کنید"}
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={(e) => e.key === "Enter" && !e.shiftKey && handleSend()}
              disabled={sending || !activeSession}
              className="flex-1 rounded-full bg-muted/50 border-transparent focus-visible:bg-background focus-visible:border-primary"
            />
            <Button
              size="icon"
              className="rounded-full shrink-0"
              onClick={handleSend}
              disabled={sending || !input.trim() || !activeSession}
            >
              <SendHorizontal className="w-4 h-4 rtl:-scale-x-100" />
            </Button>
          </div>
          <p className="text-center mt-2 text-[10px] text-muted-foreground">
            هوش مصنوعی ممکن است اشتباه کند. اطلاعات را بررسی کنید.
          </p>
        </div>
      </Card>
    </div>
  );
}
