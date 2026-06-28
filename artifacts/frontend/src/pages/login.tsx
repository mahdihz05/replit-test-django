import { useState } from "react";
import { useLocation } from "wouter";
import { useAuth } from "@/lib/auth";
import { apiFetch } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { useToast } from "@/hooks/use-toast";
import { Bot, Loader2, KeyRound, MessageSquare } from "lucide-react";

type LoginMode = "otp" | "password";
type OtpStep = 1 | 2;

export default function Login() {
  const [mode, setMode] = useState<LoginMode>("password");
  const [phone, setPhone] = useState("");
  const [password, setPassword] = useState("");
  const [code, setCode] = useState("");
  const [otpStep, setOtpStep] = useState<OtpStep>(1);
  const [loading, setLoading] = useState(false);
  const { login } = useAuth();
  const [, setLocation] = useLocation();
  const { toast } = useToast();

  const handlePasswordLogin = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!phone || !password) {
      toast({ title: "خطا", description: "شماره موبایل و رمز عبور را وارد کنید", variant: "destructive" });
      return;
    }
    setLoading(true);
    try {
      const response = await apiFetch("/auth/login/", {
        method: "POST",
        data: { phone_number: phone, password }
      });
      if (response?.data?.access) {
        login(response.data.access, response.data.user);
        toast({ title: "خوش آمدید", description: "ورود با موفقیت انجام شد" });
        setLocation("/");
      }
    } catch (error: any) {
      toast({ title: "خطا", description: error.message || "شماره موبایل یا رمز عبور اشتباه است", variant: "destructive" });
    } finally {
      setLoading(false);
    }
  };

  const handleRequestOtp = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!phone || phone.length < 10) {
      toast({ title: "خطا", description: "لطفا شماره موبایل معتبر وارد کنید", variant: "destructive" });
      return;
    }
    setLoading(true);
    try {
      await apiFetch("/auth/otp/request/", {
        method: "POST",
        data: { phone_number: phone }
      });
      setOtpStep(2);
      toast({ title: "موفق", description: "کد تایید ارسال شد" });
    } catch (error: any) {
      toast({ title: "خطا", description: error.message || "خطا در ارسال کد", variant: "destructive" });
    } finally {
      setLoading(false);
    }
  };

  const handleVerifyOtp = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!code || code.length < 4) {
      toast({ title: "خطا", description: "لطفا کد معتبر وارد کنید", variant: "destructive" });
      return;
    }
    setLoading(true);
    try {
      const response = await apiFetch("/auth/otp/verify/", {
        method: "POST",
        data: { phone_number: phone, code }
      });
      if (response?.data?.access) {
        login(response.data.access, response.data.user);
        toast({ title: "خوش آمدید", description: "ورود با موفقیت انجام شد" });
        setLocation("/");
      }
    } catch (error: any) {
      toast({ title: "خطا", description: error.message || "کد نامعتبر است", variant: "destructive" });
    } finally {
      setLoading(false);
    }
  };

  const switchMode = (newMode: LoginMode) => {
    setMode(newMode);
    setPhone("");
    setPassword("");
    setCode("");
    setOtpStep(1);
  };

  return (
    <div className="min-h-screen flex items-center justify-center bg-muted/30 p-4" dir="rtl">
      <div className="w-full max-w-md space-y-8">
        <div className="text-center">
          <div className="mx-auto w-16 h-16 bg-primary/10 text-primary flex items-center justify-center rounded-2xl mb-6">
            <Bot className="w-8 h-8" />
          </div>
          <h1 className="text-3xl font-bold text-foreground">محتوا‌یار</h1>
          <p className="text-muted-foreground mt-2">پلتفرم مدیریت محتوا با هوش مصنوعی</p>
        </div>

        <Card className="border-border/50 shadow-lg">
          <CardHeader className="pb-2">
            <CardTitle>
              {mode === "password" ? "ورود با رمز عبور" : (otpStep === 1 ? "ورود با کد تایید" : "تایید شماره")}
            </CardTitle>
            <CardDescription>
              {mode === "password"
                ? "شماره موبایل و رمز عبور خود را وارد کنید"
                : otpStep === 1
                ? "شماره موبایل خود را وارد کنید تا کد ارسال شود"
                : `کد ارسال شده به ${phone} را وارد کنید`}
            </CardDescription>
          </CardHeader>

          <div className="px-6 pb-2">
            <div className="flex rounded-lg border border-border overflow-hidden">
              <button
                type="button"
                onClick={() => switchMode("password")}
                className={`flex-1 flex items-center justify-center gap-2 py-2 text-sm font-medium transition-colors ${
                  mode === "password"
                    ? "bg-primary text-primary-foreground"
                    : "text-muted-foreground hover:text-foreground hover:bg-muted/50"
                }`}
              >
                <KeyRound className="w-4 h-4" />
                رمز عبور
              </button>
              <button
                type="button"
                onClick={() => switchMode("otp")}
                className={`flex-1 flex items-center justify-center gap-2 py-2 text-sm font-medium transition-colors ${
                  mode === "otp"
                    ? "bg-primary text-primary-foreground"
                    : "text-muted-foreground hover:text-foreground hover:bg-muted/50"
                }`}
              >
                <MessageSquare className="w-4 h-4" />
                کد پیامکی
              </button>
            </div>
          </div>

          <CardContent className="pt-4">
            {mode === "password" && (
              <form onSubmit={handlePasswordLogin} className="space-y-4">
                <Input
                  placeholder="شماره موبایل: 09123456789"
                  type="tel"
                  value={phone}
                  onChange={(e) => setPhone(e.target.value)}
                  dir="ltr"
                  className="text-left"
                  disabled={loading}
                  data-testid="input-phone"
                />
                <Input
                  placeholder="رمز عبور"
                  type="password"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  disabled={loading}
                  data-testid="input-password"
                />
                <Button type="submit" className="w-full" disabled={loading} data-testid="button-login">
                  {loading && <Loader2 className="w-4 h-4 ml-2 animate-spin" />}
                  ورود
                </Button>
              </form>
            )}

            {mode === "otp" && otpStep === 1 && (
              <form onSubmit={handleRequestOtp} className="space-y-4">
                <Input
                  placeholder="مثال: 09123456789"
                  type="tel"
                  value={phone}
                  onChange={(e) => setPhone(e.target.value)}
                  dir="ltr"
                  className="text-left"
                  disabled={loading}
                  data-testid="input-phone-otp"
                />
                <Button type="submit" className="w-full" disabled={loading} data-testid="button-send-otp">
                  {loading && <Loader2 className="w-4 h-4 ml-2 animate-spin" />}
                  دریافت کد تایید
                </Button>
              </form>
            )}

            {mode === "otp" && otpStep === 2 && (
              <form onSubmit={handleVerifyOtp} className="space-y-4">
                <Input
                  placeholder="کد ۶ رقمی"
                  type="text"
                  value={code}
                  onChange={(e) => setCode(e.target.value)}
                  dir="ltr"
                  className="text-center tracking-widest text-lg"
                  maxLength={6}
                  disabled={loading}
                  data-testid="input-otp-code"
                  autoFocus
                />
                <Button type="submit" className="w-full" disabled={loading} data-testid="button-verify-otp">
                  {loading && <Loader2 className="w-4 h-4 ml-2 animate-spin" />}
                  تایید و ورود
                </Button>
                <Button type="button" variant="ghost" className="w-full" onClick={() => setOtpStep(1)} disabled={loading}>
                  تغییر شماره
                </Button>
              </form>
            )}
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
