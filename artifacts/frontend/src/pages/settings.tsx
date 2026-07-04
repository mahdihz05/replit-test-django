import { useState, useEffect } from "react";
import { useAuth } from "@/lib/auth";
import { apiFetch } from "@/lib/api";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { useToast } from "@/hooks/use-toast";
import { Plus } from "lucide-react";

export default function Settings() {
  const { user, selectedWorkspace, refreshWorkspaces, createWorkspace, updateUser } = useAuth();
  const { toast } = useToast();
  const [workspaceName, setWorkspaceName] = useState("");
  const [fullName, setFullName] = useState("");
  const [newWorkspaceName, setNewWorkspaceName] = useState("");
  const [saving, setSaving] = useState(false);
  const [creating, setCreating] = useState(false);

  useEffect(() => {
    if (selectedWorkspace) setWorkspaceName(selectedWorkspace.name);
    if (user) {
      setFullName(user.full_name || "");
    }
  }, [selectedWorkspace, user]);

  const handleSaveProfile = async () => {
    setSaving(true);
    try {
      const response = await apiFetch("/auth/me/", {
        method: "PATCH",
        data: { full_name: fullName },
      });
      const updated = response?.data ?? response;
      if (updated && user) {
        updateUser({ ...user, full_name: updated.full_name });
      }
      toast({ title: "موفق", description: "پروفایل با موفقیت بروزرسانی شد." });
    } catch (error) {
      toast({
        title: "خطا",
        description: error instanceof Error ? error.message : "بروزرسانی پروفایل با مشکل مواجه شد.",
        variant: "destructive",
      });
    } finally {
      setSaving(false);
    }
  };

  const handleSaveWorkspace = async () => {
    if (!selectedWorkspace || !workspaceName.trim()) return;
    setSaving(true);
    try {
      await apiFetch(`/workspaces/${selectedWorkspace.id}/`, {
        method: "PATCH",
        data: { name: workspaceName.trim() },
      });
      await refreshWorkspaces();
      toast({ title: "موفق", description: "نام فضای کاری بروزرسانی شد." });
    } catch (error) {
      toast({
        title: "خطا",
        description: error instanceof Error ? error.message : "بروزرسانی فضای کاری با مشکل مواجه شد.",
        variant: "destructive",
      });
    } finally {
      setSaving(false);
    }
  };

  const handleCreateWorkspace = async () => {
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

  return (
    <div className="space-y-8 max-w-4xl mx-auto pb-10">
      <div>
        <h1 className="text-3xl font-bold tracking-tight">تنظیمات</h1>
        <p className="text-muted-foreground mt-2">پروفایل کاربری و فضاهای کاری خود را مدیریت کنید.</p>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>پروفایل کاربری</CardTitle>
          <CardDescription>اطلاعات شخصی خود را ویرایش کنید.</CardDescription>
        </CardHeader>
        <CardContent className="space-y-6">
          <div className="space-y-2">
            <Label>نام و نام خانوادگی</Label>
            <Input value={fullName} onChange={(e) => setFullName(e.target.value)} />
          </div>
          <div className="space-y-2">
            <Label>شماره موبایل</Label>
            <Input value={user?.phone_number || ""} disabled dir="ltr" className="text-left bg-muted/50" />
            <p className="text-xs text-muted-foreground">شماره موبایل قابل تغییر نیست.</p>
          </div>
          <Button onClick={handleSaveProfile} disabled={saving}>ذخیره تغییرات</Button>
        </CardContent>
      </Card>

      {selectedWorkspace && (
        <Card>
          <CardHeader>
            <CardTitle>فضای کاری فعلی: {selectedWorkspace.name}</CardTitle>
            <CardDescription>تنظیمات مربوط به این فضای کاری.</CardDescription>
          </CardHeader>
          <CardContent className="space-y-6">
            <div className="space-y-2">
              <Label>نام فضای کاری</Label>
              <Input value={workspaceName} onChange={(e) => setWorkspaceName(e.target.value)} />
            </div>
            <Button onClick={handleSaveWorkspace} disabled={saving || !workspaceName.trim()}>
              ذخیره نام
            </Button>
          </CardContent>
        </Card>
      )}

      <Card>
        <CardHeader>
          <CardTitle>فضای کاری جدید</CardTitle>
          <CardDescription>می‌توانید فضای کاری دیگری بسازید.</CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="space-y-2">
            <Label>نام فضای کاری</Label>
            <Input
              placeholder="مثال: تیم محتوا"
              value={newWorkspaceName}
              onChange={(e) => setNewWorkspaceName(e.target.value)}
            />
          </div>
          <Button onClick={handleCreateWorkspace} disabled={creating || !newWorkspaceName.trim()}>
            <Plus className="w-4 h-4 ml-2" />
            {creating ? "در حال ساخت..." : "ساخت فضای کاری"}
          </Button>
        </CardContent>
      </Card>
    </div>
  );
}
