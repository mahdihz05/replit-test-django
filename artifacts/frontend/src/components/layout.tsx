import { Link, useLocation } from "wouter";
import { useAuth } from "@/lib/auth";
import { useEffect, useState } from "react";
import { 
  LayoutDashboard, FileText, Bot, Share2, 
  SendHorizontal, Wallet, BarChart3, Users, 
  Settings, LogOut, ChevronDown, Menu, Wand2, ImageIcon,
  Clock, History, Plus, Building2
} from "lucide-react";
import { Button } from "@/components/ui/button";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { Sheet, SheetContent, SheetTrigger } from "@/components/ui/sheet";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { useToast } from "@/hooks/use-toast";

interface NavItem {
  href: string;
  label: string;
  icon: React.ComponentType<{ className?: string }>;
  section?: string;
}

const NAV_ITEMS: NavItem[] = [
  { href: "/", label: "داشبورد", icon: LayoutDashboard, section: "اصلی" },
  { href: "/contents", label: "محتوا", icon: FileText, section: "اصلی" },
  { href: "/ai", label: "گفتگوی هوشمند", icon: Bot, section: "هوش مصنوعی" },
  { href: "/ai/generate", label: "تولید محتوا", icon: Wand2, section: "هوش مصنوعی" },
  { href: "/ai/images", label: "تولید تصویر", icon: ImageIcon, section: "هوش مصنوعی" },
  { href: "/channels", label: "کانال‌ها", icon: Share2, section: "انتشار" },
  { href: "/publish", label: "انتشار محتوا", icon: SendHorizontal, section: "انتشار" },
  { href: "/publish/queue", label: "صف انتشار", icon: Clock, section: "انتشار" },
  { href: "/publish/history", label: "تاریخچه", icon: History, section: "انتشار" },
  { href: "/wallet", label: "کیف پول", icon: Wallet, section: "مدیریت" },
  { href: "/reports", label: "گزارش‌ها", icon: BarChart3, section: "مدیریت" },
  { href: "/members", label: "اعضا", icon: Users, section: "مدیریت" },
  { href: "/settings", label: "تنظیمات", icon: Settings, section: "مدیریت" },
];

function SidebarContent({ currentLocation, onNavigate }: { currentLocation: string; onNavigate?: () => void }) {
  const sections = Array.from(new Set(NAV_ITEMS.map(i => i.section)));

  const isActive = (href: string) =>
    href === "/"
      ? currentLocation === "/"
      : currentLocation === href || currentLocation.startsWith(href + "/");

  return (
    <div className="flex flex-col h-full bg-sidebar border-l border-sidebar-border text-sidebar-foreground w-64 shrink-0">
      <div className="p-6 pb-4">
        <h1 className="text-xl font-bold flex items-center gap-2 text-primary">
          <Bot className="w-6 h-6" />
          <span>محتوا‌یار</span>
        </h1>
      </div>

      <div className="flex-1 px-3 py-1 overflow-y-auto space-y-4">
        {sections.map(section => {
          const items = NAV_ITEMS.filter(i => i.section === section);
          return (
            <div key={section}>
              <p className="text-xs font-semibold text-sidebar-foreground/40 uppercase tracking-wider px-3 mb-1">
                {section}
              </p>
              <div className="space-y-0.5">
                {items.map(item => {
                  const active = isActive(item.href);
                  return (
                    <Link key={item.href} href={item.href}>
                      <div
                        onClick={onNavigate}
                        className={`flex items-center gap-3 px-3 py-2 rounded-md cursor-pointer transition-colors ${
                          active
                            ? "bg-sidebar-accent text-sidebar-accent-foreground font-medium"
                            : "hover:bg-sidebar-accent/50 text-sidebar-foreground/80"
                        }`}
                      >
                        <item.icon className={`w-4 h-4 ${active ? "text-primary" : ""}`} />
                        <span className="text-sm">{item.label}</span>
                      </div>
                    </Link>
                  );
                })}
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}

export function AppLayout({ children }: { children: React.ReactNode }) {
  const { user, workspaces, selectedWorkspace, selectWorkspace, logout, isLoading, createWorkspace } = useAuth();
  const [location, setLocation] = useLocation();
  const [newWorkspaceName, setNewWorkspaceName] = useState("");
  const [creating, setCreating] = useState(false);
  const { toast } = useToast();

  useEffect(() => {
    if (!isLoading && !user) {
      setLocation("/login");
    }
  }, [isLoading, user, setLocation]);

  const handleCreateWorkspace = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!newWorkspaceName.trim()) return;
    setCreating(true);
    try {
      await createWorkspace(newWorkspaceName.trim());
      toast({ title: "موفق", description: "فضای کاری جدید ساخته شد." });
      setNewWorkspaceName("");
    } catch (error) {
      toast({
        title: "خطا",
        description: error instanceof Error ? error.message : "ساخت فضای کاری با مشکل مواجه شد.",
        variant: "destructive",
      });
    } finally {
      setCreating(false);
    }
  };

  if (isLoading) {
    return <div className="min-h-screen flex items-center justify-center">در حال بارگذاری...</div>;
  }

  if (!user) {
    return null;
  }

  if (workspaces.length === 0) {
    return (
      <div className="min-h-screen bg-background text-foreground flex items-center justify-center p-4" dir="rtl">
        <Card className="w-full max-w-md">
          <CardHeader className="text-center">
            <div className="mx-auto w-12 h-12 rounded-full bg-primary/10 flex items-center justify-center mb-4">
              <Building2 className="w-6 h-6 text-primary" />
            </div>
            <CardTitle>خوش آمدید</CardTitle>
            <CardDescription>
              برای استفاده از محتوا‌یار، ابتدا یک فضای کاری بسازید.
            </CardDescription>
          </CardHeader>
          <CardContent>
            <form onSubmit={handleCreateWorkspace} className="space-y-4">
              <div className="space-y-2">
                <Label htmlFor="workspace-name">نام فضای کاری</Label>
                <Input
                  id="workspace-name"
                  placeholder="مثال: تیم محتوا"
                  value={newWorkspaceName}
                  onChange={(e) => setNewWorkspaceName(e.target.value)}
                  autoFocus
                />
              </div>
              <Button type="submit" className="w-full" disabled={creating || !newWorkspaceName.trim()}>
                <Plus className="w-4 h-4 ml-2" />
                {creating ? "در حال ساخت..." : "ساخت فضای کاری"}
              </Button>
            </form>
          </CardContent>
        </Card>
      </div>
    );
  }

  return (
    <div className="flex min-h-screen bg-background text-foreground" dir="rtl">
      {/* Desktop Sidebar */}
      <div className="hidden md:block">
        <SidebarContent currentLocation={location} />
      </div>

      <div className="flex-1 flex flex-col min-w-0">
        <header className="h-16 border-b border-border bg-card flex items-center justify-between px-4 lg:px-6 shrink-0 z-10">
          <div className="flex items-center gap-4">
            {/* Mobile Sidebar */}
            <Sheet>
              <SheetTrigger asChild>
                <Button variant="ghost" size="icon" className="md:hidden">
                  <Menu className="w-5 h-5" />
                </Button>
              </SheetTrigger>
              <SheetContent side="right" className="p-0 w-64 border-l-0">
                <SidebarContent currentLocation={location} />
              </SheetContent>
            </Sheet>

            {workspaces.length > 0 && selectedWorkspace && (
              <DropdownMenu>
                <DropdownMenuTrigger asChild>
                  <Button variant="outline" className="gap-2 border-dashed">
                    {selectedWorkspace.name}
                    <ChevronDown className="w-4 h-4 opacity-50" />
                  </Button>
                </DropdownMenuTrigger>
                <DropdownMenuContent align="end" className="w-48">
                  <DropdownMenuLabel>فضاهای کاری</DropdownMenuLabel>
                  <DropdownMenuSeparator />
                  {workspaces.map(w => (
                    <DropdownMenuItem
                      key={w.id}
                      onClick={() => selectWorkspace(w.id)}
                      className={w.id === selectedWorkspace.id ? "bg-accent" : ""}
                    >
                      {w.name}
                    </DropdownMenuItem>
                  ))}
                  <DropdownMenuSeparator />
                  <DropdownMenuItem onClick={() => setLocation("/settings")}>
                    مدیریت فضاهای کاری
                  </DropdownMenuItem>
                </DropdownMenuContent>
              </DropdownMenu>
            )}
          </div>

          <div className="flex items-center gap-4">
            <span className="text-sm font-medium hidden sm:block">
              {user.full_name || user.phone_number}
            </span>
            <Button variant="ghost" size="icon" onClick={logout} title="خروج">
              <LogOut className="w-5 h-5 text-muted-foreground hover:text-destructive" />
            </Button>
          </div>
        </header>

        <main className="flex-1 overflow-auto p-4 lg:p-8">
          <div className="max-w-7xl mx-auto h-full">
            {children}
          </div>
        </main>
      </div>
    </div>
  );
}
