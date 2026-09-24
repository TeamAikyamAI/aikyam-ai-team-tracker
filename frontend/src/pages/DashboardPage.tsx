import * as React from "react";
import {
  CheckCircle2,
  FolderKanban,
  Hammer,
  Inbox,
  LayoutGrid,
  ListFilter,
  Rocket,
  Table as TableIcon,
  TimerReset,
  TriangleAlert,
} from "lucide-react";
import { Link } from "react-router-dom";
import { PageHeader } from "@/components/common/PageHeader";
import { StatCard } from "@/components/common/StatCard";
import { EmptyState } from "@/components/common/EmptyState";
import { Button } from "@/components/ui/button";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Skeleton } from "@/components/ui/skeleton";
import { cn } from "@/lib/utils";
import { useProjects } from "@/hooks/useProjects";
import { useStatuses } from "@/hooks/useStatuses";
import { useVerticals } from "@/hooks/useVerticals";
import { useUserDirectory } from "@/hooks/useUsers";
import { useRequests } from "@/hooks/useRequests";
import { useExpiringApiKeys } from "@/hooks/useApiKeys";
import { KanbanBoard } from "@/components/dashboard/KanbanBoard";
import { ProjectTable } from "@/components/dashboard/ProjectTable";
import { TrendChart } from "@/components/dashboard/TrendChart";
import { PipelineCard } from "@/components/dashboard/PipelineCard";
import { CreateProjectDialog } from "@/components/dashboard/CreateProjectDialog";
import { ExportProjectsButton } from "@/components/dashboard/ExportProjectsButton";
import { usePersistedState } from "@/hooks/usePersistedState";
import { useCan } from "@/hooks/usePermissions";

const ALL = "__all__";

export default function DashboardPage() {
  const can = useCan();
  const { data: projects, isLoading: projectsLoading, isError: projectsError } = useProjects();
  const { data: statuses, isLoading: statusesLoading } = useStatuses();
  const { data: verticals } = useVerticals();
  const { data: users } = useUserDirectory();
  const { data: requests } = useRequests();
  // The register is the AI team's; a requestor never asks for it.
  const canSeeKeys = can("api_keys");
  const { data: expiringKeys } = useExpiringApiKeys(canSeeKeys);

  const [view, setView] = usePersistedState<"kanban" | "table">("aikyam-dashboard-view", "kanban");
  const [verticalFilter, setVerticalFilter] = usePersistedState("aikyam-dashboard-vertical", ALL);
  const [statusFilter, setStatusFilter] = usePersistedState("aikyam-dashboard-status", ALL);
  const [ownerFilter, setOwnerFilter] = usePersistedState("aikyam-dashboard-owner", ALL);
  const filtersActive = verticalFilter !== ALL || statusFilter !== ALL || ownerFilter !== ALL;

  const filtered = React.useMemo(() => {
    if (!projects) return [];
    return projects.filter((p) => {
      if (verticalFilter !== ALL && String(p.vertical_id) !== verticalFilter) return false;
      if (statusFilter !== ALL && String(p.status_id) !== statusFilter) return false;
      if (ownerFilter !== ALL && !(p.owner_ids ?? []).includes(Number(ownerFilter))) return false;
      return true;
    });
  }, [projects, verticalFilter, statusFilter, ownerFilter]);

  // Deactivated statuses stay out of the filter unless a project still uses one.
  const filterStatuses = React.useMemo(() => {
    const inUse = new Set((projects ?? []).map((p) => p.status_id));
    return (statuses ?? [])
      .filter((s) => s.is_active !== false || inUse.has(s.id))
      .sort((a, b) => a.sort_order - b.sort_order);
  }, [statuses, projects]);

  const terminalStatusIds = React.useMemo(
    () => new Set((statuses ?? []).filter((s) => s.is_terminal).map((s) => s.id)),
    [statuses]
  );

  // "Live" and "WIP" are statuses like any other (statuses are admin-configurable),
  // so they are resolved by name rather than a fixed id.
  const liveStatusId = React.useMemo(
    () => (statuses ?? []).find((s) => /\blive\b/i.test(s.name))?.id,
    [statuses]
  );
  const wipStatusId = React.useMemo(
    () => (statuses ?? []).find((s) => /\b(wip|work[\s-]?in[\s-]?progress)\b/i.test(s.name))?.id,
    [statuses]
  );

  const kpis = React.useMemo(() => {
    const total = projects?.length ?? 0;
    const ongoing = projects?.filter((p) => !terminalStatusIds.has(p.status_id)).length ?? 0;
    const live = liveStatusId != null ? projects?.filter((p) => p.status_id === liveStatusId).length ?? 0 : 0;
    const wip = wipStatusId != null ? projects?.filter((p) => p.status_id === wipStatusId).length ?? 0 : 0;
    const now = new Date();
    const completedThisMonth =
      projects?.filter((p) => {
        if (!p.actual_completion_date) return false;
        const d = new Date(p.actual_completion_date);
        return d.getMonth() === now.getMonth() && d.getFullYear() === now.getFullYear();
      }).length ?? 0;
    const openRequests =
      requests?.filter((r) => r.status === "submitted" || r.status === "under_review").length ?? 0;
    return { total, ongoing, live, wip, completedThisMonth, openRequests };
  }, [projects, terminalStatusIds, requests, liveStatusId, wipStatusId]);

  const trendData = React.useMemo(() => {
    const weeks: { label: string; value: number; start: Date }[] = [];
    const now = new Date();
    for (let i = 7; i >= 0; i--) {
      const start = new Date(now);
      start.setDate(now.getDate() - now.getDay() - i * 7);
      start.setHours(0, 0, 0, 0);
      weeks.push({
        label: start.toLocaleDateString("en-IN", { day: "2-digit", month: "short" }),
        value: 0,
        start,
      });
    }
    (requests ?? []).forEach((r) => {
      const created = new Date(r.created_at);
      for (let i = weeks.length - 1; i >= 0; i--) {
        if (created >= weeks[i]!.start) {
          weeks[i]!.value += 1;
          break;
        }
      }
    });
    return weeks.map(({ label, value }) => ({ label, value }));
  }, [requests]);

  const loading = projectsLoading || statusesLoading;

  return (
    <div>
      <PageHeader
        title="Dashboard"
        description="A live view of everything the AI & Automation team is running."
        actions={
          <div className="flex items-center gap-2">
            {can("projects_export") && <ExportProjectsButton />}
            {can("projects_manage") && <CreateProjectDialog />}
          </div>
        }
      />

      {canSeeKeys && expiringKeys && expiringKeys.length > 0 && (
        <Link
          to="/api-keys"
          className="mb-4 flex items-center gap-2 rounded-lg border border-warning/40 bg-warning/10 px-3 py-2 text-sm transition-colors hover:border-warning"
        >
          <TriangleAlert className="h-4 w-4 shrink-0 text-warning" />
          <span>
            <strong>{expiringKeys.length}</strong> API key{expiringKeys.length === 1 ? "" : "s"}{" "}
            expired or expiring within 30 days
          </span>
          <span className="ml-auto text-xs text-muted-foreground">Open the register</span>
        </Link>
      )}

      <div className="mb-6 grid grid-cols-2 gap-4 sm:grid-cols-3 lg:grid-cols-6">
        <StatCard label="Total projects" value={kpis.total} icon={<FolderKanban className="h-5 w-5" />} loading={loading} accent="primary" index={0} />
        <StatCard label="Ongoing" value={kpis.ongoing} icon={<TimerReset className="h-5 w-5" />} loading={loading} accent="default" index={1} />
        <StatCard label="Live" value={kpis.live} icon={<Rocket className="h-5 w-5" />} loading={loading} accent="success" index={2} hint={liveStatusId == null ? 'No "Live" status configured' : undefined} />
        <StatCard label="WIP" value={kpis.wip} icon={<Hammer className="h-5 w-5" />} loading={loading} accent="warning" index={3} hint={wipStatusId == null ? 'No "WIP" status configured' : undefined} />
        <StatCard label="Completed this month" value={kpis.completedThisMonth} icon={<CheckCircle2 className="h-5 w-5" />} loading={loading} accent="success" index={4} />
        <StatCard label="Requests awaiting review" value={kpis.openRequests} icon={<Inbox className="h-5 w-5" />} loading={loading} accent="warning" index={5} />
      </div>

      <div className="mb-6 grid gap-4 lg:grid-cols-5">
        <div className="lg:col-span-2">
          <PipelineCard
            projects={projects ?? []}
            statuses={statuses ?? []}
            verticals={verticals ?? []}
            onPickStatus={(id) => setStatusFilter(String(id))}
          />
        </div>
        <div className="lg:col-span-3">
          <TrendChart data={trendData} />
        </div>
      </div>

      <div className="mb-4 flex flex-wrap items-center gap-2">
        <ListFilter className="h-4 w-4 text-muted-foreground" />
        <Select value={verticalFilter} onValueChange={setVerticalFilter}>
          <SelectTrigger className="h-8 w-40 text-xs">
            <SelectValue placeholder="Vertical" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value={ALL}>All verticals</SelectItem>
            {(verticals ?? []).map((v) => (
              <SelectItem key={v.id} value={String(v.id)}>
                {v.name}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
        <Select value={statusFilter} onValueChange={setStatusFilter}>
          <SelectTrigger className="h-8 w-40 text-xs">
            <SelectValue placeholder="Status" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value={ALL}>All statuses</SelectItem>
            {filterStatuses.map((s) => (
              <SelectItem key={s.id} value={String(s.id)}>
                {s.name}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
        <Select value={ownerFilter} onValueChange={setOwnerFilter}>
          <SelectTrigger className="h-8 w-40 text-xs">
            <SelectValue placeholder="Owner" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value={ALL}>All owners</SelectItem>
            {(users ?? []).map((u) => (
              <SelectItem key={u.id} value={String(u.id)}>
                {u.name}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>

        {filtersActive && (
          <Button
            variant="ghost"
            size="sm"
            className="h-8 text-xs"
            onClick={() => {
              setVerticalFilter(ALL);
              setStatusFilter(ALL);
              setOwnerFilter(ALL);
            }}
          >
            Clear filters
          </Button>
        )}

        <div
          className="ml-auto flex items-center rounded-md border border-input bg-card p-0.5"
          role="group"
          aria-label="Choose how projects are shown"
        >
          <Button
            variant={view === "kanban" ? "secondary" : "ghost"}
            size="icon-sm"
            onClick={() => setView("kanban")}
            aria-label="Board view"
            aria-pressed={view === "kanban"}
            title="Board view"
            className={cn("h-7 w-7")}
          >
            <LayoutGrid className="h-3.5 w-3.5" />
          </Button>
          <Button
            variant={view === "table" ? "secondary" : "ghost"}
            size="icon-sm"
            onClick={() => setView("table")}
            aria-label="Table view"
            aria-pressed={view === "table"}
            title="Table view"
            className={cn("h-7 w-7")}
          >
            <TableIcon className="h-3.5 w-3.5" />
          </Button>
        </div>
      </div>

      {loading && (
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
          {Array.from({ length: 4 }).map((_, i) => (
            <Skeleton key={i} className="h-40 rounded-xl" />
          ))}
        </div>
      )}

      {projectsError && (
        <EmptyState
          icon={<FolderKanban className="h-6 w-6" />}
          title="Couldn't load projects"
          description="Check that the backend is running and reachable, then refresh the page."
        />
      )}

      {!loading && !projectsError && filtered.length === 0 && (
        <EmptyState
          icon={<FolderKanban className="h-6 w-6" />}
          title={projects && projects.length > 0 ? "No projects match your filters" : "No projects yet"}
          description={
            projects && projects.length > 0
              ? "Try clearing a filter to see more results."
              : "Create your first project, or approve a service request to get one started."
          }
        />
      )}

      {!loading && !projectsError && filtered.length > 0 && (
        <>
          {view === "kanban" ? (
            <KanbanBoard projects={filtered} statuses={statuses ?? []} verticals={verticals ?? []} users={users ?? []} />
          ) : (
            <ProjectTable projects={filtered} statuses={statuses ?? []} verticals={verticals ?? []} users={users ?? []} />
          )}
        </>
      )}
    </div>
  );
}
