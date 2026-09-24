import * as React from "react";
import { NavLink } from "react-router-dom";
import {
  LayoutDashboard,
  ListChecks,
  FileStack,
  FolderKanban,
  Inbox,
  CalendarCheck,
  Sparkles,
  Users,
  ShieldCheck,
  ChevronsLeft,
  ChevronsRight,
  KeyRound,
} from "lucide-react";
import { cn } from "@/lib/utils";
import { useCan } from "@/hooks/usePermissions";
import { Tooltip, TooltipContent, TooltipTrigger } from "@/components/ui/tooltip";
import { Logo } from "@/components/common/Logo";
import { usePublicSettings } from "@/hooks/useSettings";
import type { FeatureKey } from "@/types";

interface NavItem {
  to: string;
  label: string;
  icon: React.ComponentType<{ className?: string }>;
  /** Shown when the person has any one of these, per the Admin access grid. */
  features: FeatureKey[];
  end?: boolean;
}

const NAV_ITEMS: NavItem[] = [
  { to: "/", label: "Dashboard", icon: LayoutDashboard, features: ["dashboard"], end: true },
  { to: "/my-day", label: "My Day", icon: CalendarCheck, features: ["my_day", "team_day"] },
  { to: "/queue", label: "Project Queue", icon: ListChecks, features: ["queue"] },
  { to: "/apply", label: "Apply for Service", icon: FileStack, features: ["apply"] },
  { to: "/my-requests", label: "My Requests", icon: Inbox, features: ["my_requests"] },
  { to: "/requests", label: "Requests Review", icon: FolderKanban, features: ["requests_review"] },
  { to: "/ask", label: "Ask the Tracker", icon: Sparkles, features: ["ask"] },
  { to: "/api-keys", label: "API Keys", icon: KeyRound, features: ["api_keys"] },
  { to: "/admin", label: "Admin Panel", icon: Users, features: ["admin_panel"] },
  { to: "/audit", label: "Audit Trail", icon: ShieldCheck, features: ["audit_trail"] },
];

interface SidebarProps {
  collapsed: boolean;
  onToggle: () => void;
  mobileOpen: boolean;
  onMobileClose: () => void;
}

export function Sidebar({ collapsed, onToggle, mobileOpen, onMobileClose }: SidebarProps) {
  const can = useCan();
  const { settings } = usePublicSettings();
  const items = NAV_ITEMS.filter((item) => item.features.some(can));

  return (
    <>
      {mobileOpen && (
        <div
          className="fixed inset-0 z-40 bg-black/50 lg:hidden"
          onClick={onMobileClose}
          aria-hidden="true"
        />
      )}
      <aside
        className={cn(
          "fixed inset-y-0 left-0 z-50 flex flex-col bg-sidebar text-sidebar-foreground transition-all duration-200 ease-in-out lg:sticky lg:top-0 lg:z-0 lg:h-screen",
          collapsed ? "lg:w-[68px]" : "lg:w-64",
          "w-64",
          mobileOpen ? "translate-x-0" : "-translate-x-full lg:translate-x-0"
        )}
      >
        <div
          className={cn(
            "relative flex h-14 shrink-0 items-center gap-2.5 border-b border-sidebar-border px-4",
            collapsed && "lg:justify-center lg:px-0"
          )}
        >
          <span aria-hidden="true" className="brand-gradient absolute inset-x-0 top-0 h-[2px] opacity-90" />
          <Logo className="h-7 w-7 shrink-0" alt={settings.app_name} />
          {!collapsed && (
            <div className="min-w-0">
              <span className="block truncate text-sm font-semibold tracking-tight text-white">{settings.app_name}</span>
              <span className="block truncate text-[10px] uppercase tracking-[0.14em] text-sidebar-foreground/55">{settings.org_name}</span>
            </div>
          )}
        </div>

        <nav className="flex-1 space-y-1 overflow-y-auto px-2.5 py-2 scrollbar-thin">
          {items.map((item) => {
            const Icon = item.icon;
            const link = (
              <NavLink
                key={item.to}
                to={item.to}
                end={item.end}
                onClick={onMobileClose}
                className={({ isActive }) =>
                  cn(
                    "group relative flex items-center gap-3 rounded-md px-2.5 py-2 text-sm font-medium transition-colors focus-visible:outline-sidebar-ring",
                    collapsed && "lg:justify-center lg:px-0",
                    isActive
                      ? "bg-sidebar-primary/15 text-sidebar-primary"
                      : "text-sidebar-foreground/75 hover:bg-sidebar-accent hover:text-sidebar-accent-foreground"
                  )
                }
              >
                {({ isActive }) => (
                  <>
                    {isActive && (
                      <span
                        aria-hidden="true"
                        className="absolute -left-2.5 top-1/2 h-5 w-[3px] -translate-y-1/2 rounded-r-full bg-sidebar-primary"
                      />
                    )}
                    <Icon className="h-[18px] w-[18px] shrink-0 transition-transform group-hover:scale-105" />
                    {!collapsed && <span className="truncate">{item.label}</span>}
                  </>
                )}
              </NavLink>
            );

            if (collapsed) {
              return (
                <Tooltip key={item.to} delayDuration={200}>
                  <TooltipTrigger asChild>{link}</TooltipTrigger>
                  <TooltipContent side="right">{item.label}</TooltipContent>
                </Tooltip>
              );
            }
            return link;
          })}
        </nav>

        <div className="border-t border-sidebar-border p-2.5">
          <button
            onClick={onToggle}
            aria-label={collapsed ? "Expand sidebar" : "Collapse sidebar"}
            aria-expanded={!collapsed}
            className={cn(
              "hidden w-full items-center gap-2 rounded-md px-2.5 py-2 text-sm text-sidebar-foreground/70 transition-colors hover:bg-sidebar-accent hover:text-sidebar-accent-foreground lg:flex",
              collapsed && "justify-center"
            )}
          >
            {collapsed ? <ChevronsRight className="h-4 w-4" /> : <ChevronsLeft className="h-4 w-4" />}
            {!collapsed && <span>Collapse</span>}
          </button>
        </div>
      </aside>
    </>
  );
}
