import { Link, useLocation } from "wouter";
import { useAuth } from "@/lib/auth";
import { useEffect } from "react";
import { 
  LayoutDashboard, FileText, Bot, Share2, 
  SendHorizontal, Wallet, BarChart3, Users, 
  Settings, LogOut, ChevronDown, Menu, Wand2, ImageIcon
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

const NAV_ITEMS = [
  { href: "/", label: "داشبورد", icon: LayoutDashboard },
  { href: "/contents", label: "محتوا", icon: FileText },
  { href: "/ai", label: "گفتگوی هوشمند", icon: Bot },
  { href: "/ai/generate", label: "تولید محتوا", icon: Wand2 },
  { href: "/ai/images", label: "تولید تصویر", icon: ImageIcon },
  { href: "/channels", label: "کانال‌ها", icon: Share2 },
  { href: "/publish", label: "انتشار", icon: SendHorizontal },
  { href: "/wallet", label: "کیف پول", icon: Wallet },
  { href: "/reports", label: "گزارش‌ها", icon: BarChart3 },
  { href: "/members", label: "اعضا", icon: Users },
  { href: "/settings", label: "تنظیمات", icon: Settings },
];

function SidebarContent({ currentLocation, onNavigate }: { currentLocation: string, onNavigate?: () => void }) {
  return (
    <div className="flex flex-col h-full bg-sidebar border-l border-sidebar-border text-sidebar-foreground w-64 shrink-0">
      <div className="p-6">
        <h1 className="text-xl font-bold flex items-center gap-2 text-primary">
          <Bot className="w-6 h-6" />
          <span>محتوا‌یار</span>
        </h1>
      </div>
      
      <div className="flex-1 px-4 py-2 space-y-1 overflow-y-auto">
        {NAV_ITEMS.map((item) => {
          const isActive = currentLocation === item.href || (item.href !== "/" && currentLocation.startsWith(item.href));
          return (
            <Link key={item.href} href={item.href}>
              <div 
                onClick={onNavigate}
                className={`flex items-center gap-3 px-3 py-2.5 rounded-md cursor-pointer transition-colors ${
                  isActive 
                    ? "bg-sidebar-accent text-sidebar-accent-foreground font-medium" 
                    : "hover:bg-sidebar-accent/50 text-sidebar-foreground/80"
                }`}
              >
                <item.icon className={`w-5 h-5 ${isActive ? "text-primary" : ""}`} />
                <span>{item.label}</span>
              </div>
            </Link>
          );
        })}
      </div>
    </div>
  );
}

export function AppLayout({ children }: { children: React.ReactNode }) {
  const { user, workspaces, selectedWorkspace, selectWorkspace, logout, isLoading } = useAuth();
  const [location, setLocation] = useLocation();

  useEffect(() => {
    if (!isLoading && !user) {
      setLocation("/login");
    }
  }, [isLoading, user, setLocation]);

  if (isLoading) {
    return <div className="min-h-screen flex items-center justify-center">در حال بارگذاری...</div>;
  }

  if (!user) {
    return null;
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
              {user.first_name ? `${user.first_name} ${user.last_name || ''}` : user.phone_number}
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
