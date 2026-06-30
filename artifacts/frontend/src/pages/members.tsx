import { useState, useEffect } from "react";
import { useAuth } from "@/lib/auth";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Avatar, AvatarFallback } from "@/components/ui/avatar";
import { Badge } from "@/components/ui/badge";
import { Trash2, Plus, UserPlus } from "lucide-react";

export default function Members() {
  const { selectedWorkspace } = useAuth();
  const [members, setMembers] = useState<any[]>([]);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (selectedWorkspace) {
      setLoading(true);
      setTimeout(() => {
        setMembers([
          { id: "1", user_name: "علی احمدی", user_phone: "09123456789", role: "admin", created_at: new Date().toISOString() },
          { id: "2", user_name: "سارا حسینی", user_phone: "09198765432", role: "manager", created_at: new Date(Date.now() - 86400000).toISOString() },
        ]);
        setLoading(false);
      }, 500);
    }
  }, [selectedWorkspace]);

  return (
    <div className="space-y-6 max-w-5xl mx-auto">
      <div className="flex justify-between items-center gap-4">
        <h1 className="text-3xl font-bold tracking-tight">اعضای تیم</h1>
      </div>

      <Card>
        <CardHeader className="pb-4">
          <CardTitle>افزودن عضو جدید</CardTitle>
          <CardDescription>با وارد کردن شماره موبایل، اعضای جدید را به فضای کاری خود دعوت کنید.</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="flex flex-col sm:flex-row gap-4">
            <Input placeholder="شماره موبایل" className="flex-1" dir="ltr" />
            <Select defaultValue="manager">
              <SelectTrigger className="w-full sm:w-[200px]">
                <SelectValue placeholder="نقش" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="admin">مدیر کل (Admin)</SelectItem>
                <SelectItem value="manager">مدیر محتوا (Manager)</SelectItem>
              </SelectContent>
            </Select>
            <Button className="gap-2 shrink-0">
              <UserPlus className="w-4 h-4" /> دعوت عضو
            </Button>
          </div>
        </CardContent>
      </Card>

      <div className="space-y-4">
        <h3 className="text-lg font-medium">اعضای فعلی ({members.length})</h3>
        <div className="bg-card border rounded-lg overflow-hidden">
          {loading ? (
            <div className="p-8 text-center text-muted-foreground">در حال بارگذاری...</div>
          ) : members.map((member, i) => (
            <div key={member.id} className={`p-4 flex items-center justify-between ${i !== members.length - 1 ? 'border-b' : ''}`}>
              <div className="flex items-center gap-4">
                <Avatar>
                  <AvatarFallback className="bg-primary/10 text-primary">
                    {member.user_name ? member.user_name.substring(0, 2) : '?'}
                  </AvatarFallback>
                </Avatar>
                <div>
                  <p className="font-medium">{member.user_name || 'کاربر ناشناس'}</p>
                  <p className="text-sm text-muted-foreground" dir="ltr">{member.user_phone}</p>
                </div>
              </div>
              <div className="flex items-center gap-4">
                <Badge variant={member.role === 'admin' ? 'default' : 'secondary'}>
                  {member.role === 'admin' ? 'مدیر کل' : 'مدیر محتوا'}
                </Badge>
                {member.role !== 'admin' && (
                  <Button variant="ghost" size="icon" className="text-destructive hover:bg-destructive/10">
                    <Trash2 className="w-4 h-4" />
                  </Button>
                )}
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
