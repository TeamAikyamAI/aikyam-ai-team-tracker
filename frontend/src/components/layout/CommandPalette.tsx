import * as React from "react";
import { useNavigate } from "react-router-dom";
import {
  LayoutDashboard,
  ListChecks,
  FolderKanban,
  FileStack,
  ShieldCheck,
  Users,
  Sparkles,
  Moon,
  Sun,
  Search,
  ArrowRight,
} from "lucide-react";
import {
  CommandDialog,
  CommandEmpty,
  CommandGroup,
  CommandInput,
  CommandItem,
  CommandList,
  CommandSeparator,
} from "@/components/ui/command";
import { useAuth } from "@/context/AuthContext";
import { useTheme } from "@/context/ThemeContext";
import { useProjects } from "@/hooks/useProjects";

interface CommandPaletteProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
}

export function CommandPalette({ open, onOpenChange }: CommandPaletteProps) {
  const navigate = useNavigate();
  const { user } = useAuth();
  const { theme, toggleTheme } = useTheme();
  const [search, setSearch] = React.useState("");
  const canSeeProjects = user?.role === "admin" || user?.role === "member";
  const { data: projects } = useProjects();

  const go = (path: string) => {
    onOpenChange(false);
    setSearch("");
    navigate(path);
  };

  return (
    <CommandDialog open={open} onOpenChange={onOpenChange}>
      <CommandInput placeholder="Search pages, projects, or ask a question…" value={search} onValueChange={setSearch} />
      <CommandList>
        <CommandEmpty>No results. Press Enter to ask the tracker instead.</CommandEmpty>

        {search.trim().length > 0 && (
          <CommandGroup heading="Ask the Tracker">
            <CommandItem
              value={`ask ${search}`}
              onSelect={() => go(`/ask?q=${encodeURIComponent(search)}`)}
            >
              <Sparkles className="h-4 w-4 text-primary" />
              <span className="truncate">
                Ask: <span className="font-medium text-foreground">&ldquo;{search}&rdquo;</span>
              </span>
              <ArrowRight className="ml-auto h-3.5 w-3.5 text-muted-foreground" />
            </CommandItem>
          </CommandGroup>
        )}

        <CommandGroup heading="Navigate">
          {canSeeProjects && (
            <CommandItem value="dashboard home overview" onSelect={() => go("/")}>
              <LayoutDashboard className="h-4 w-4" />
              Dashboard
            </CommandItem>
          )}
          <CommandItem value="queue project queue browse services" onSelect={() => go("/queue")}>
            <ListChecks className="h-4 w-4" />
            Project Queue
          </CommandItem>
          <CommandItem value="apply for service request new brd" onSelect={() => go("/apply")}>
            <FileStack className="h-4 w-4" />
            Apply for Service
          </CommandItem>
          {canSeeProjects && (
            <CommandItem value="requests review approve reject brd" onSelect={() => go("/requests")}>
              <FolderKanban className="h-4 w-4" />
              Requests Review
            </CommandItem>
          )}
          {canSeeProjects && (
            <CommandItem value="ask the tracker ai chat" onSelect={() => go("/ask")}>
              <Sparkles className="h-4 w-4" />
              Ask the Tracker
            </CommandItem>
          )}
          {user?.role === "admin" && (
            <CommandItem value="admin panel users verticals statuses" onSelect={() => go("/admin")}>
              <Users className="h-4 w-4" />
              Admin Panel
            </CommandItem>
          )}
          {user?.role === "admin" && (
            <CommandItem value="audit trail logs activity" onSelect={() => go("/audit")}>
              <ShieldCheck className="h-4 w-4" />
              Audit Trail
            </CommandItem>
          )}
        </CommandGroup>

        {canSeeProjects && projects && projects.length > 0 && search.trim().length > 0 && (
          <>
            <CommandSeparator />
            <CommandGroup heading="Projects">
              {projects
                .filter((p) => p.name.toLowerCase().includes(search.toLowerCase()))
                .slice(0, 6)
                .map((p) => (
                  <CommandItem key={p.id} value={`project ${p.name}`} onSelect={() => go(`/projects/${p.id}`)}>
                    <Search className="h-4 w-4" />
                    {p.name}
                  </CommandItem>
                ))}
            </CommandGroup>
          </>
        )}

        <CommandSeparator />
        <CommandGroup heading="Preferences">
          <CommandItem value="toggle theme dark light mode" onSelect={() => toggleTheme()}>
            {theme === "dark" ? <Sun className="h-4 w-4" /> : <Moon className="h-4 w-4" />}
            Toggle {theme === "dark" ? "light" : "dark"} mode
          </CommandItem>
        </CommandGroup>
      </CommandList>
    </CommandDialog>
  );
}
