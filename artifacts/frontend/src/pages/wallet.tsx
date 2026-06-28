import { useState, useEffect } from "react";
import { useAuth } from "@/lib/auth";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Wallet as WalletIcon, ArrowDownRight, ArrowUpRight, Plus } from "lucide-react";
import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle, DialogTrigger } from "@/components/ui/dialog";

export default function Wallet() {
  const { selectedWorkspace } = useAuth();
  const [transactions, setTransactions] = useState<any[]>([]);
  const [balance, setBalance] = useState(0);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (selectedWorkspace) {
      setLoading(true);
      setTimeout(() => {
        setBalance(1250000);
        setTransactions([
          { id: "1", type: "charge", amount: 500000, description: "شارژ حساب از طریق درگاه پرداخت", created_at: new Date().toISOString() },
          { id: "2", type: "deduct", amount: 45000, description: "هزینه تولید ۳ مقاله با هوش مصنوعی", created_at: new Date(Date.now() - 86400000).toISOString() },
          { id: "3", type: "deduct", amount: 15000, description: "هزینه بازنویسی پست تلگرام", created_at: new Date(Date.now() - 172800000).toISOString() }
        ]);
        setLoading(false);
      }, 500);
    }
  }, [selectedWorkspace]);

  return (
    <div className="space-y-6 max-w-4xl mx-auto">
      <div className="flex justify-between items-center gap-4">
        <h1 className="text-3xl font-bold tracking-tight">کیف پول</h1>
      </div>

      <Card className="bg-primary text-primary-foreground border-transparent overflow-hidden relative">
        <div className="absolute right-0 top-0 w-64 h-64 bg-white/10 rounded-full blur-3xl -translate-y-1/2 translate-x-1/2 pointer-events-none"></div>
        <CardContent className="p-8 relative z-10">
          <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-6">
            <div className="space-y-2">
              <p className="text-primary-foreground/80 flex items-center gap-2">
                <WalletIcon className="w-5 h-5" /> موجودی فعلی
              </p>
              <div className="text-4xl font-bold">
                {loading ? "..." : balance.toLocaleString('fa-IR')} <span className="text-lg font-normal opacity-80">تومان</span>
              </div>
            </div>
            <Dialog>
              <DialogTrigger asChild>
                <Button size="lg" className="bg-white text-primary hover:bg-white/90 gap-2 shrink-0">
                  <Plus className="w-5 h-5" /> افزایش موجودی
                </Button>
              </DialogTrigger>
              <DialogContent>
                <DialogHeader>
                  <DialogTitle>افزایش موجودی</DialogTitle>
                  <DialogDescription>مبلغ مورد نظر برای شارژ حساب را وارد کنید.</DialogDescription>
                </DialogHeader>
                <div className="space-y-4 py-4">
                  <div className="grid grid-cols-3 gap-2">
                    {[100000, 200000, 500000].map(amount => (
                      <Button key={amount} variant="outline" className="font-mono">
                        {amount.toLocaleString('fa-IR')}
                      </Button>
                    ))}
                  </div>
                  <div className="relative">
                    <Input type="number" placeholder="مبلغ دلخواه" className="pl-16 font-mono text-left" dir="ltr" />
                    <span className="absolute left-4 top-1/2 -translate-y-1/2 text-muted-foreground text-sm">تومان</span>
                  </div>
                  <Button className="w-full">پرداخت</Button>
                </div>
              </DialogContent>
            </Dialog>
          </div>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>تراکنش‌های اخیر</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="space-y-0 divide-y">
            {loading ? (
              <div className="py-8 text-center text-muted-foreground">در حال بارگذاری...</div>
            ) : transactions.length === 0 ? (
              <div className="py-8 text-center text-muted-foreground">تراکنشی یافت نشد.</div>
            ) : transactions.map(tx => (
              <div key={tx.id} className="py-4 flex items-center justify-between">
                <div className="flex items-center gap-4">
                  <div className={`w-10 h-10 rounded-full flex items-center justify-center shrink-0 ${
                    tx.type === 'charge' ? 'bg-green-100 text-green-600' : 'bg-destructive/10 text-destructive'
                  }`}>
                    {tx.type === 'charge' ? <ArrowDownRight className="w-5 h-5" /> : <ArrowUpRight className="w-5 h-5" />}
                  </div>
                  <div>
                    <p className="font-medium">{tx.description}</p>
                    <p className="text-xs text-muted-foreground mt-1">{new Date(tx.created_at).toLocaleString('fa-IR')}</p>
                  </div>
                </div>
                <div className={`font-bold whitespace-nowrap ${tx.type === 'charge' ? 'text-green-600' : ''}`}>
                  {tx.type === 'charge' ? '+' : '-'} {tx.amount.toLocaleString('fa-IR')} <span className="text-xs font-normal text-muted-foreground">تومان</span>
                </div>
              </div>
            ))}
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
