import { Switch, Route, useLocation } from "wouter";
import { lazy, Suspense } from "react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { Toaster } from "@/components/ui/toaster";
import { TooltipProvider } from "@/components/ui/tooltip";
import { AuthProvider } from "@/lib/auth";
import { AppLayout } from "@/components/layout";

const NotFound = lazy(() => import("@/pages/not-found"));
const Login = lazy(() => import("@/pages/login"));
const Dashboard = lazy(() => import("@/pages/dashboard"));
const Contents = lazy(() => import("@/pages/contents"));
const ContentNew = lazy(() => import("@/pages/contents-new"));
const ContentDetail = lazy(() => import("@/pages/contents-detail"));
const AiChat = lazy(() => import("@/pages/ai-chat"));
const AiGenerate = lazy(() => import("@/pages/ai-generate"));
const AiImages = lazy(() => import("@/pages/ai-images"));
const Channels = lazy(() => import("@/pages/channels"));
const Publish = lazy(() => import("@/pages/publish"));
const PublishQueue = lazy(() => import("@/pages/publish-queue"));
const PublishHistory = lazy(() => import("@/pages/publish-history"));
const Wallet = lazy(() => import("@/pages/wallet"));
const Reports = lazy(() => import("@/pages/reports"));
const Members = lazy(() => import("@/pages/members"));
const Settings = lazy(() => import("@/pages/settings"));
const Communication = lazy(() => import("@/pages/communication"));

const queryClient = new QueryClient();

function Router() {
  const [location] = useLocation();

  if (location === "/login") {
    return <Suspense fallback={<PageLoading />}><Route path="/login" component={Login} /></Suspense>;
  }

  return (
    <AppLayout>
      <Suspense fallback={<PageLoading />}>
      <Switch>
        <Route path="/" component={Dashboard} />
        <Route path="/contents" component={Contents} />
        <Route path="/contents/new" component={ContentNew} />
        <Route path="/contents/:id" component={ContentDetail} />
        <Route path="/ai" component={AiChat} />
        <Route path="/ai/generate" component={AiGenerate} />
        <Route path="/ai/images" component={AiImages} />
        <Route path="/channels" component={Channels} />
        <Route path="/publish" component={Publish} />
        <Route path="/publish/queue" component={PublishQueue} />
        <Route path="/publish/history" component={PublishHistory} />
        <Route path="/wallet" component={Wallet} />
        <Route path="/reports" component={Reports} />
        <Route path="/members" component={Members} />
        <Route path="/settings" component={Settings} />
        <Route path="/communication/campaigns" component={Communication} />
        <Route path="/communication/contacts" component={Communication} />
        <Route path="/communication/templates" component={Communication} />
        <Route path="/communication/providers" component={Communication} />
        <Route path="/communication" component={Communication} />
        <Route component={NotFound} />
      </Switch>
      </Suspense>
    </AppLayout>
  );
}

function PageLoading() {
  return (
    <div className="flex min-h-[40vh] items-center justify-center" role="status" aria-label="در حال بارگذاری">
      <div className="h-8 w-8 animate-spin rounded-full border-2 border-primary border-t-transparent" />
    </div>
  );
}

function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <TooltipProvider>
        <AuthProvider>
          <Router />
        </AuthProvider>
        <Toaster />
      </TooltipProvider>
    </QueryClientProvider>
  );
}

export default App;
