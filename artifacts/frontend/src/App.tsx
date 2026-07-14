import { Switch, Route, useLocation } from "wouter";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { Toaster } from "@/components/ui/toaster";
import { TooltipProvider } from "@/components/ui/tooltip";
import NotFound from "@/pages/not-found";

import { AuthProvider } from "@/lib/auth";
import { AppLayout } from "@/components/layout";

import Login from "@/pages/login";
import Dashboard from "@/pages/dashboard";
import Contents from "@/pages/contents";
import ContentNew from "@/pages/contents-new";
import ContentDetail from "@/pages/contents-detail";
import AiChat from "@/pages/ai-chat";
import AiGenerate from "@/pages/ai-generate";
import AiImages from "@/pages/ai-images";
import Channels from "@/pages/channels";
import Publish from "@/pages/publish";
import PublishQueue from "@/pages/publish-queue";
import PublishHistory from "@/pages/publish-history";
import Wallet from "@/pages/wallet";
import Reports from "@/pages/reports";
import Members from "@/pages/members";
import Settings from "@/pages/settings";
import Communication from "@/pages/communication";

const queryClient = new QueryClient();

function Router() {
  const [location] = useLocation();

  if (location === "/login") {
    return <Route path="/login" component={Login} />;
  }

  return (
    <AppLayout>
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
    </AppLayout>
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
