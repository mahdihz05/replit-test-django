import { FormEvent, useCallback, useEffect, useMemo, useState } from "react";
import { useAuth } from "@/lib/auth";
import { apiFetch } from "@/lib/api";
import { useToast } from "@/hooks/use-toast";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Avatar, AvatarFallback } from "@/components/ui/avatar";
import { Badge } from "@/components/ui/badge";
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from "@/components/ui/alert-dialog";
import { Loader2, RefreshCw, Trash2, UserPlus, Users } from "lucide-react";

type MemberRole = "admin" | "manager";

interface Member {
  id: number;
  user_id: string;
  user_name: string;
  user_phone: string;
  role: MemberRole;
  created_at: string;
}

const roleLabels: Record<MemberRole, string> = {
  admin: "مدیر کل",
  manager: "مدیر محتوا",
};

export default function Members() {
  const { user, selectedWorkspace, refreshWorkspaces } = useAuth();
  const { toast } = useToast();
  const [members, setMembers] = useState<Member[]>([]);
  const [loading, setLoading] = useState(false);
  const [loadError, setLoadError] = useState("");
  const [phoneNumber, setPhoneNumber] = useState("");
  const [newRole, setNewRole] = useState<MemberRole>("manager");
  const [adding, setAdding] = useState(false);
  const [updatingId, setUpdatingId] = useState<number | null>(null);
  const [deleteTarget, setDeleteTarget] = useState<Member | null>(null);
  const [deleting, setDeleting] = useState(false);

  const loadMembers = useCallback(async () => {
    if (!selectedWorkspace) {
      setMembers([]);
      return;
    }

    setLoading(true);
    setLoadError("");
    try {
      const response = await apiFetch(`/workspaces/${selectedWorkspace.id}/members/`);
      setMembers(Array.isArray(response) ? response : (response?.data ?? []));
    } catch (error: any) {
      const message = error.message || "دریافت اعضا ناموفق بود";
      setLoadError(message);
      toast({ title: "خطا", description: message, variant: "destructive" });
    } finally {
      setLoading(false);
    }
  }, [selectedWorkspace?.id, toast]);

  useEffect(() => {
    void loadMembers();
  }, [loadMembers]);

  const currentMember = useMemo(
    () => members.find((member) => member.user_id === user?.id),
    [members, user?.id],
  );
  const canManage = currentMember?.role === "admin";

  const addMember = async (event: FormEvent) => {
    event.preventDefault();
    if (!selectedWorkspace || adding) return;

    const phone = phoneNumber.trim();
    if (!/^09\d{9}$/.test(phone)) {
      toast({
        title: "شماره نامعتبر",
        description: "شماره موبایل باید با 09 شروع شود و 11 رقم باشد.",
        variant: "destructive",
      });
      return;
    }

    setAdding(true);
    try {
      const response = await apiFetch(`/workspaces/${selectedWorkspace.id}/members/`, {
        method: "POST",
        data: { phone_number: phone, role: newRole },
      });
      const member = response?.data ?? response;
      setMembers((current) => [...current, member]);
      setPhoneNumber("");
      setNewRole("manager");
      await refreshWorkspaces();
      toast({ title: "عضو اضافه شد", description: `${member.user_name || member.user_phone} به فضای کاری اضافه شد.` });
    } catch (error: any) {
      toast({ title: "افزودن عضو ناموفق بود", description: error.message, variant: "destructive" });
    } finally {
      setAdding(false);
    }
  };

  const updateRole = async (member: Member, role: MemberRole) => {
    if (!selectedWorkspace || member.role === role) return;
    setUpdatingId(member.id);
    try {
      const response = await apiFetch(`/workspaces/${selectedWorkspace.id}/members/${member.id}/`, {
        method: "PATCH",
        data: { role },
      });
      const updated = response?.data ?? response;
      setMembers((current) => current.map((item) => item.id === member.id ? updated : item));
      toast({ title: "نقش عضو تغییر کرد" });
    } catch (error: any) {
      toast({ title: "تغییر نقش ناموفق بود", description: error.message, variant: "destructive" });
    } finally {
      setUpdatingId(null);
    }
  };

  const deleteMember = async () => {
    if (!selectedWorkspace || !deleteTarget || deleting) return;
    setDeleting(true);
    try {
      await apiFetch(`/workspaces/${selectedWorkspace.id}/members/${deleteTarget.id}/`, {
        method: "DELETE",
      });
      setMembers((current) => current.filter((member) => member.id !== deleteTarget.id));
      setDeleteTarget(null);
      await refreshWorkspaces();
      toast({ title: "عضو حذف شد" });
    } catch (error: any) {
      toast({ title: "حذف عضو ناموفق بود", description: error.message, variant: "destructive" });
    } finally {
      setDeleting(false);
    }
  };

  if (!selectedWorkspace) {
    return <div className="p-8 text-center text-muted-foreground">ابتدا یک فضای کاری انتخاب کنید.</div>;
  }

  return (
    <div className="space-y-6 max-w-5xl mx-auto">
      <div className="flex justify-between items-center gap-4">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">اعضای تیم</h1>
          <p className="mt-1 text-sm text-muted-foreground">مدیریت اعضای فضای کاری «{selectedWorkspace.name}»</p>
        </div>
        <Button variant="outline" size="icon" onClick={() => void loadMembers()} disabled={loading} aria-label="به‌روزرسانی فهرست">
          <RefreshCw className={`w-4 h-4 ${loading ? "animate-spin" : ""}`} />
        </Button>
      </div>

      {canManage && (
        <Card>
          <CardHeader className="pb-4">
            <CardTitle>افزودن عضو جدید</CardTitle>
            <CardDescription>
              کاربری که قبلاً با این شماره در سامانه ثبت‌نام کرده است به فضای کاری اضافه می‌شود.
            </CardDescription>
          </CardHeader>
          <CardContent>
            <form onSubmit={addMember} className="flex flex-col sm:flex-row gap-4">
              <Input
                value={phoneNumber}
                onChange={(event) => setPhoneNumber(event.target.value.replace(/\D/g, "").slice(0, 11))}
                placeholder="شماره موبایل (مثلاً 09123456789)"
                className="flex-1"
                dir="ltr"
                inputMode="numeric"
                autoComplete="tel"
                disabled={adding}
              />
              <Select value={newRole} onValueChange={(value: MemberRole) => setNewRole(value)} disabled={adding}>
                <SelectTrigger className="w-full sm:w-[200px]">
                  <SelectValue placeholder="نقش" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="admin">مدیر کل</SelectItem>
                  <SelectItem value="manager">مدیر محتوا</SelectItem>
                </SelectContent>
              </Select>
              <Button type="submit" className="gap-2 shrink-0" disabled={adding || !phoneNumber}>
                {adding ? <Loader2 className="w-4 h-4 animate-spin" /> : <UserPlus className="w-4 h-4" />}
                افزودن عضو
              </Button>
            </form>
          </CardContent>
        </Card>
      )}

      <div className="space-y-4">
        <h2 className="text-lg font-medium">اعضای فعلی ({members.length})</h2>
        <div className="bg-card border rounded-lg overflow-hidden">
          {loading ? (
            <div className="p-10 flex items-center justify-center gap-2 text-muted-foreground">
              <Loader2 className="w-5 h-5 animate-spin" /> در حال بارگذاری...
            </div>
          ) : loadError ? (
            <div className="p-8 text-center">
              <p className="text-destructive mb-3">{loadError}</p>
              <Button variant="outline" onClick={() => void loadMembers()}>تلاش دوباره</Button>
            </div>
          ) : members.length === 0 ? (
            <div className="p-10 text-center text-muted-foreground">
              <Users className="w-9 h-9 mx-auto mb-3 opacity-50" />
              عضوی در این فضای کاری وجود ندارد.
            </div>
          ) : members.map((member, index) => {
            const isOwner = member.user_id === selectedWorkspace.owner;
            const isCurrentUser = member.user_id === user?.id;
            const editable = canManage && !isOwner && !isCurrentUser;
            return (
              <div key={member.id} className={`p-4 flex flex-col sm:flex-row sm:items-center justify-between gap-4 ${index !== members.length - 1 ? "border-b" : ""}`}>
                <div className="flex items-center gap-4 min-w-0">
                  <Avatar>
                    <AvatarFallback className="bg-primary/10 text-primary">
                      {member.user_name?.trim().substring(0, 2) || member.user_phone.slice(-2)}
                    </AvatarFallback>
                  </Avatar>
                  <div className="min-w-0">
                    <div className="flex items-center gap-2 flex-wrap">
                      <p className="font-medium truncate">{member.user_name || "کاربر بدون نام"}</p>
                      {isOwner && <Badge variant="outline">مالک</Badge>}
                      {isCurrentUser && <span className="text-xs text-muted-foreground">(شما)</span>}
                    </div>
                    <p className="text-sm text-muted-foreground text-left" dir="ltr">{member.user_phone}</p>
                  </div>
                </div>
                <div className="flex items-center gap-2 self-end sm:self-auto">
                  {editable ? (
                    <Select
                      value={member.role}
                      onValueChange={(value: MemberRole) => void updateRole(member, value)}
                      disabled={updatingId === member.id}
                    >
                      <SelectTrigger className="w-[145px]">
                        <SelectValue />
                      </SelectTrigger>
                      <SelectContent>
                        <SelectItem value="admin">مدیر کل</SelectItem>
                        <SelectItem value="manager">مدیر محتوا</SelectItem>
                      </SelectContent>
                    </Select>
                  ) : (
                    <Badge variant={member.role === "admin" ? "default" : "secondary"}>{roleLabels[member.role]}</Badge>
                  )}
                  {editable && (
                    <Button
                      variant="ghost"
                      size="icon"
                      onClick={() => setDeleteTarget(member)}
                      className="text-destructive hover:bg-destructive/10 hover:text-destructive"
                      aria-label={`حذف ${member.user_name || member.user_phone}`}
                    >
                      <Trash2 className="w-4 h-4" />
                    </Button>
                  )}
                </div>
              </div>
            );
          })}
        </div>
        {!loading && currentMember && !canManage && (
          <p className="text-sm text-muted-foreground">فقط مدیر کل می‌تواند عضو اضافه کند، نقش‌ها را تغییر دهد یا عضوی را حذف کند.</p>
        )}
      </div>

      <AlertDialog open={!!deleteTarget} onOpenChange={(open) => !open && !deleting && setDeleteTarget(null)}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>حذف عضو</AlertDialogTitle>
            <AlertDialogDescription>
              آیا از حذف «{deleteTarget?.user_name || deleteTarget?.user_phone}» از این فضای کاری مطمئن هستید؟ دسترسی او بلافاصله قطع می‌شود.
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter className="flex-row-reverse gap-2">
            <AlertDialogAction onClick={(event) => { event.preventDefault(); void deleteMember(); }} disabled={deleting} className="bg-destructive text-destructive-foreground hover:bg-destructive/90">
              {deleting && <Loader2 className="w-4 h-4 animate-spin ml-2" />}
              حذف عضو
            </AlertDialogAction>
            <AlertDialogCancel disabled={deleting}>انصراف</AlertDialogCancel>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </div>
  );
}
