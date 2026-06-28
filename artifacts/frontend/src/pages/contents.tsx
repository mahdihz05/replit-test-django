import { useState, useEffect } from "react";
import { useAuth } from "@/lib/auth";
import { apiFetch } from "@/lib/api";
import { Link } from "wouter";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Card, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Search, Plus, Filter, MoreVertical, Edit, Eye, Trash2, FileText } from "lucide-react";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";

interface Content {
  id: string;
  title: string;
  status: string;
  created_at: string;
  tags?: string[];
}

export default function Contents() {
  const { selectedWorkspace } = useAuth();
  const [contents, setContents] = useState<Content[]>([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState("");

  useEffect(() => {
    if (selectedWorkspace) {
      fetchContents();
    }
  }, [selectedWorkspace]);

  const fetchContents = async () => {
    setLoading(true);
    try {
      const data = await apiFetch(`/workspaces/${selectedWorkspace?.id}/contents/`).catch(() => [
        { id: "1", title: "پست وبلاگ هوش مصنوعی", status: "draft", created_at: new Date().toISOString() },
        { id: "2", title: "اطلاعیه فروش ویژه", status: "published", created_at: new Date(Date.now() - 86400000).toISOString() },
        { id: "3", title: "معرفی محصول جدید", status: "scheduled", created_at: new Date().toISOString() },
      ]);
      setContents(data);
    } finally {
      setLoading(false);
    }
  };

  const getStatusBadge = (status: string) => {
    switch(status) {
      case "draft": return <Badge variant="outline" className="bg-gray-100 text-gray-800 dark:bg-gray-800 dark:text-gray-300">پیش‌نویس</Badge>;
      case "ready": return <Badge variant="outline" className="bg-blue-100 text-blue-800 dark:bg-blue-900/30 dark:text-blue-400">آماده</Badge>;
      case "scheduled": return <Badge variant="outline" className="bg-amber-100 text-amber-800 dark:bg-amber-900/30 dark:text-amber-400">زمان‌بندی شده</Badge>;
      case "published": return <Badge variant="outline" className="bg-green-100 text-green-800 dark:bg-green-900/30 dark:text-green-400">منتشر شده</Badge>;
      case "failed": return <Badge variant="destructive">ناموفق</Badge>;
      default: return <Badge variant="outline">{status}</Badge>;
    }
  };

  return (
    <div className="space-y-6">
      <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4">
        <h1 className="text-3xl font-bold tracking-tight">محتوا</h1>
        <Link href="/contents/new">
          <Button className="gap-2">
            <Plus className="w-4 h-4" />
            ایجاد محتوا
          </Button>
        </Link>
      </div>

      <div className="flex flex-col sm:flex-row gap-4 items-center justify-between bg-card p-4 rounded-lg border shadow-sm">
        <div className="relative w-full sm:w-96">
          <Search className="absolute right-3 top-1/2 -translate-y-1/2 w-4 h-4 text-muted-foreground" />
          <Input 
            placeholder="جستجو در عنوان محتوا..." 
            className="pr-9"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
          />
        </div>
        <div className="flex items-center gap-2 w-full sm:w-auto">
          <Button variant="outline" className="gap-2 w-full sm:w-auto">
            <Filter className="w-4 h-4" />
            فیلترها
          </Button>
        </div>
      </div>

      {loading ? (
        <div className="space-y-4">
          {[1, 2, 3].map(i => (
            <Card key={i} className="animate-pulse">
              <CardContent className="p-6">
                <div className="h-5 bg-muted rounded w-1/3 mb-4"></div>
                <div className="h-4 bg-muted rounded w-1/4"></div>
              </CardContent>
            </Card>
          ))}
        </div>
      ) : contents.length === 0 ? (
        <div className="text-center py-12 bg-card rounded-lg border border-dashed">
          <div className="w-12 h-12 rounded-full bg-muted mx-auto flex items-center justify-center mb-4">
            <FileText className="w-6 h-6 text-muted-foreground" />
          </div>
          <h3 className="text-lg font-medium mb-1">هیچ محتوایی یافت نشد</h3>
          <p className="text-muted-foreground text-sm mb-4">اولین محتوای خود را ایجاد کنید.</p>
          <Link href="/contents/new">
            <Button>ایجاد محتوای جدید</Button>
          </Link>
        </div>
      ) : (
        <div className="grid gap-4">
          {contents.map((item) => (
            <Card key={item.id} className="overflow-hidden hover:border-primary/50 transition-colors">
              <div className="flex flex-col sm:flex-row p-6 gap-4 sm:items-center justify-between">
                <div className="space-y-1">
                  <div className="flex items-center gap-2">
                    <Link href={`/contents/${item.id}`} className="font-medium text-lg hover:text-primary transition-colors">
                      {item.title}
                    </Link>
                    {getStatusBadge(item.status)}
                  </div>
                  <div className="text-sm text-muted-foreground flex items-center gap-2">
                    <span>ایجاد شده: {new Date(item.created_at).toLocaleDateString('fa-IR')}</span>
                  </div>
                </div>
                <div className="flex items-center gap-2">
                  <DropdownMenu>
                    <DropdownMenuTrigger asChild>
                      <Button variant="ghost" size="icon">
                        <MoreVertical className="w-4 h-4" />
                      </Button>
                    </DropdownMenuTrigger>
                    <DropdownMenuContent align="end">
                      <Link href={`/contents/${item.id}`}>
                        <DropdownMenuItem className="gap-2 cursor-pointer">
                          <Edit className="w-4 h-4" /> ویرایش
                        </DropdownMenuItem>
                      </Link>
                      <DropdownMenuItem className="gap-2 text-destructive focus:bg-destructive/10 cursor-pointer">
                        <Trash2 className="w-4 h-4" /> حذف
                      </DropdownMenuItem>
                    </DropdownMenuContent>
                  </DropdownMenu>
                </div>
              </div>
            </Card>
          ))}
        </div>
      )}
    </div>
  );
}
