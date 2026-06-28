import { useState, useEffect } from "react";
import { useAuth } from "@/lib/auth";
import { apiFetch } from "@/lib/api";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Plus, Send, RefreshCw, CheckCircle2, XCircle, Globe, Share2 } from "lucide-react";
import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle, DialogTrigger } from "@/components/ui/dialog";

export default function Channels() {
  const { selectedWorkspace } = useAuth();
  const [channels, setChannels] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (selectedWorkspace) {
      setLoading(true);
      setTimeout(() => {
        setChannels([
          { id: "1", platform: "telegram", name: "کانال اصلی تلگرام", is_verified: true, is_active: true },
          { id: "2", platform: "bale", name: "گروه مشتریان بله", is_verified: true, is_active: true },
          { id: "3", platform: "website", name: "وبلاگ سایت", is_verified: false, is_active: false }
        ]);
        setLoading(false);
      }, 500);
    }
  }, [selectedWorkspace]);

  const getPlatformIcon = (platform: string) => {
    switch(platform) {
      case "telegram": return <Send className="w-5 h-5 text-blue-500" />;
      case "bale": return <Share2 className="w-5 h-5 text-green-500" />;
      case "website": return <Globe className="w-5 h-5 text-purple-500" />;
      default: return <Share2 className="w-5 h-5" />;
    }
  };

  return (
    <div className="space-y-6">
      <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4">
        <h1 className="text-3xl font-bold tracking-tight">کانال‌ها</h1>
        <Dialog>
          <DialogTrigger asChild>
            <Button className="gap-2">
              <Plus className="w-4 h-4" />
              افزودن کانال جدید
            </Button>
          </DialogTrigger>
          <DialogContent>
            <DialogHeader>
              <DialogTitle>افزودن کانال جدید</DialogTitle>
              <DialogDescription>
                پلتفرم مورد نظر خود را برای اتصال انتخاب کنید.
              </DialogDescription>
            </DialogHeader>
            <div className="grid grid-cols-3 gap-4 py-4">
              {['telegram', 'bale', 'website'].map(platform => (
                <Button key={platform} variant="outline" className="h-24 flex flex-col gap-2">
                  {getPlatformIcon(platform)}
                  <span className="capitalize">{platform}</span>
                </Button>
              ))}
            </div>
          </DialogContent>
        </Dialog>
      </div>

      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
        {loading ? (
          [1, 2, 3].map(i => <Card key={i} className="animate-pulse h-32"></Card>)
        ) : channels.map(channel => (
          <Card key={channel.id}>
            <CardHeader className="flex flex-row items-center justify-between pb-2">
              <CardTitle className="text-base font-medium flex items-center gap-2">
                {getPlatformIcon(channel.platform)}
                {channel.name}
              </CardTitle>
              {channel.is_verified ? (
                <CheckCircle2 className="w-5 h-5 text-green-500" />
              ) : (
                <XCircle className="w-5 h-5 text-destructive" />
              )}
            </CardHeader>
            <CardContent>
              <div className="flex justify-between items-center mt-4">
                <Badge variant={channel.is_active ? "outline" : "secondary"}>
                  {channel.is_active ? "فعال" : "غیرفعال"}
                </Badge>
                <Button variant="ghost" size="sm" className="text-muted-foreground">
                  <RefreshCw className="w-4 h-4 ml-2" /> بررسی وضعیت
                </Button>
              </div>
            </CardContent>
          </Card>
        ))}
      </div>
    </div>
  );
}
