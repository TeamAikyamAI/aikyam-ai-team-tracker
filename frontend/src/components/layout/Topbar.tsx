import * as React from "react";
import { Menu, Search } from "lucide-react";
import { Button } from "@/components/ui/button";
import { ThemeToggle } from "@/components/layout/ThemeToggle";
import { UserMenu } from "@/components/layout/UserMenu";

interface TopbarProps {
  onMobileMenu: () => void;
  onOpenPalette: () => void;
  title?: string;
}

export function Topbar({ onMobileMenu, onOpenPalette, title }: TopbarProps) {
  const isMac = typeof navigator !== "undefined" && /Mac/i.test(navigator.platform ?? navigator.userAgent);

  return (
    <header className="sticky top-0 z-30 flex h-14 shrink-0 items-center gap-3 border-b border-border bg-background/85 px-4 backdrop-blur supports-[backdrop-filter]:bg-background/70">
      <Button variant="ghost" size="icon" className="lg:hidden" onClick={onMobileMenu} aria-label="Open menu">
        <Menu className="h-5 w-5" />
      </Button>

      {title && <h2 className="hidden truncate text-sm font-medium text-muted-foreground sm:block">{title}</h2>}

      <button
        onClick={onOpenPalette}
        className="ml-auto flex w-full max-w-sm items-center gap-2 rounded-md border border-input bg-muted/50 px-3 py-1.5 text-sm text-muted-foreground transition-colors hover:bg-muted sm:w-64"
      >
        <Search className="h-3.5 w-3.5" />
        <span className="truncate">Search or ask…</span>
        <kbd className="ml-auto hidden items-center gap-0.5 rounded border border-border bg-background px-1.5 py-0.5 text-[10px] font-medium text-muted-foreground sm:inline-flex">
          {isMac ? "⌘" : "Ctrl"}K
        </kbd>
      </button>

      <div className="flex items-center gap-1.5">
        <ThemeToggle />
        <UserMenu />
      </div>
    </header>
  );
}
