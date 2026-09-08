import * as React from "react";
import { Outlet, useLocation } from "react-router-dom";
import { Sidebar } from "@/components/layout/Sidebar";
import { Topbar } from "@/components/layout/Topbar";
import { CommandPalette } from "@/components/layout/CommandPalette";
import { PageTransition } from "@/components/common/PageTransition";
import { TooltipProvider } from "@/components/ui/tooltip";
import { AssistantWidget } from "@/components/chat/AssistantWidget";
import { usePersistedState } from "@/hooks/usePersistedState";

export function AppShell() {
  const [collapsed, setCollapsed] = usePersistedState<boolean>("aikyam-sidebar-collapsed", false);
  const [mobileOpen, setMobileOpen] = React.useState(false);
  const [paletteOpen, setPaletteOpen] = React.useState(false);
  const location = useLocation();

  React.useEffect(() => {
    function handler(e: KeyboardEvent) {
      if ((e.metaKey || e.ctrlKey) && e.key.toLowerCase() === "k") {
        e.preventDefault();
        setPaletteOpen((v) => !v);
      }
    }
    document.addEventListener("keydown", handler);
    return () => document.removeEventListener("keydown", handler);
  }, []);

  React.useEffect(() => {
    setMobileOpen(false);
  }, [location.pathname]);

  return (
    <TooltipProvider>
      <a
        href="#main"
        className="sr-only focus:not-sr-only focus:fixed focus:left-4 focus:top-4 focus:z-[100] focus:rounded-md focus:bg-primary focus:px-3 focus:py-2 focus:text-sm focus:font-medium focus:text-primary-foreground"
      >
        Skip to content
      </a>
      <div className="flex min-h-screen bg-background">
        <Sidebar
          collapsed={collapsed}
          onToggle={() => setCollapsed((v) => !v)}
          mobileOpen={mobileOpen}
          onMobileClose={() => setMobileOpen(false)}
        />
        <div className="flex min-h-screen flex-1 flex-col overflow-x-hidden">
          <Topbar onMobileMenu={() => setMobileOpen(true)} onOpenPalette={() => setPaletteOpen(true)} />
          <main id="main" className="flex-1 px-4 py-6 sm:px-6 lg:px-8" tabIndex={-1}>
            {/* Enter-only transition. An exit animation here (AnimatePresence
                mode="wait") can leave the incoming page stuck at opacity 0 when
                a route change lands mid-animation, so pages simply fade in. */}
            <PageTransition key={location.pathname}>
              <Outlet />
            </PageTransition>
          </main>
        </div>
      </div>
      <CommandPalette open={paletteOpen} onOpenChange={setPaletteOpen} />
      <AssistantWidget />
    </TooltipProvider>
  );
}
