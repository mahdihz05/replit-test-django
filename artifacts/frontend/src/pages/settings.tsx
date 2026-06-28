import { useState, useEffect } from "react";
import { useAuth } from "@/lib/auth";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { useToast } from "@/hooks/use-toast";

export default function Settings() {
  const { user, selectedWorkspace, refreshWorkspaces } = useAuth();
  const { toast } = useToast();
  const [workspaceName, setWorkspaceName] = useState("");
  const [firstName, setFirstName] = useState("");
  const [lastName, setLastName] = useState("");
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    if (selectedWorkspace) setWorkspaceName(selectedWorkspace.name);
    if (user) {
      setFirstName(user.first_name || "");
      setLastName(user.last_name || "");
    }
  }, [selectedWorkspace, user]);

  const handleSaveProfile = async () => {
    setSaving(true);
    setTimeout(() => {
      setSaving(false);
      toast({ title: "موفق", description: "پروفایل با موفقیت بروزرسانی شد." });
    }, 800);
  };

  const handleSaveWorkspace = async () => {
    setSaving(true);
    setTimeout(() => {
      setSaving(false);
      toast({ title: "موفق", description: "تنظیمات فضای کاری بروزرسانی شد." });
      refreshWorkspaces();
    }, 800);
  };

  return (
    <div className="space-y-8 max-w-4xl mx-auto pb-10">
      <div>
        <h1 className="text-3xl font-bold tracking-tight">تنظیمات</h1>
        <p className="text-muted-foreground mt-2">پروفایل کاربری و تنظیمات فضای کاری خود را مدیریت کنید.</p>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>پروفایل کاربری</CardTitle>
          <CardDescription>اطلاعات شخصی خود را ویرایش کنید.</CardDescription>
        </CardHeader>
        <CardContent className="space-y-6">
          <div className="grid sm:grid-cols-2 gap-4">
            <div className="space-y-2">
              <Label>نام</Label>
              <Input value={firstName} onChange={(e) => setFirstName(e.target.value)} />
            </div>
            <div className="space-y-2">
              <Label>نام خانوادگی</Label>
              <Input value={lastName} onChange={(e) => setLastName(e.target.value)} />
            </div>
          </div>
          <div className="space-y-2">
            <Label>شماره موبایل</Label>
            <Input value={user?.phone_number || ""} disabled dir="ltr" className="text-left bg-muted/50" />
            <p className="text-xs text-muted-foreground">شماره موبایل قابل تغییر نیست.</p>
          </div>
          <Button onClick={handleSaveProfile} disabled={saving}>ذخیره تغییرات</Button>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>فضای کاری: {selectedWorkspace?.name}</CardTitle>
          <CardDescription>تنظیمات مربوط به این فضای کاری.</CardDescription>
        </CardHeader>
        <CardContent className="space-y-6">
          <div className="space-y-2">
            <Label>نام فضای کاری</Label>
            <Input value={workspaceName} onChange={(e) => setWorkspaceName(e.target.value)} />
          </div>
          <Button onClick={handleSaveWorkspace} disabled={saving}>ذخیره نام</Button>
        </CardContent>
      </Card>
    </div>
  );
}
