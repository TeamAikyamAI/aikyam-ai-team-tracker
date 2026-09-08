import * as React from "react";
import { useParams, Link } from "react-router-dom";
import { ArrowLeft, CalendarDays, ClipboardList, UserRound, StickyNote, Trash2 } from "lucide-react";
import { useNavigate } from "react-router-dom";
import { toast } from "sonner";
import { Avatar, AvatarFallback } from "@/components/ui/avatar";
import { Tooltip, TooltipContent, TooltipTrigger } from "@/components/ui/tooltip";
import { Skeleton } from "@/components/ui/skeleton";
import { EmptyState } from "@/components/common/EmptyState";
import { StatusBadge } from "@/components/common/StatusBadge";
import { Button } from "@/components/ui/button";
import { useProjects, useDeleteProject } from "@/hooks/useProjects";
import { useStatuses } from "@/hooks/useStatuses";
import { useVerticals } from "@/hooks/useVerticals";
import { useUserDirectory } from "@/hooks/useUsers";
import { useProjectUpdates } from "@/hooks/useUpdates";
import { UpdateTimeline } from "@/components/project/UpdateTimeline";
import { AddUpdateForm } from "@/components/project/AddUpdateForm";
import { EditProjectDialog } from "@/components/project/EditProjectDialog";
import { ConfirmDialog } from "@/components/common/ConfirmDialog";
import { apiErrorMessage } from "@/lib/api";
import { formatDate, initials } from "@/lib/utils";
import { useCan } from "@/hooks/usePermissions";

export default function ProjectDetailPage() {
  const { id } = useParams<{ id: string }>();
  const projectId = id ? Number(id) : undefined;

  const can = useCan();
  const navigate = useNavigate();
  const deleteProject = useDeleteProject();
  const [confirmDelete, setConfirmDelete] = React.useState(false);
  const { data: projects, isLoading: projectsLoading } = useProjects();
  const { data: statuses } = useStatuses();
  const { data: verticals } = useVerticals();
  const { data: users } = useUserDirectory();
  const { data: updates, isLoading: updatesLoading } = useProjectUpdates(projectId);

  const project = projects?.find((p) => p.id === projectId);
  const status = statuses?.find((s) => s.id === project?.status_id);
  const vertical = verticals?.find((v) => v.id === project?.vertical_id);
  const userById = React.useMemo(() => new Map((users ?? []).map((u) => [u.id, u])), [users]);
  const owners = (project?.owner_ids ?? []).map((uid) => userById.get(uid)).filter(Boolean) as NonNullable<
    ReturnType<typeof userById.get>
  >[];

  if (projectsLoading) {
    return (
      <div className="space-y-6">
        <Skeleton className="h-8 w-64" />
        <Skeleton className="h-32 w-full rounded-xl" />
        <Skeleton className="h-64 w-full rounded-xl" />
      </div>
    );
  }

  if (!project) {
    return (
      <EmptyState
        icon={<ClipboardList className="h-6 w-6" />}
        title="Project not found"
        description="It may have been removed, or you may not have access to it."
        action={
          <Button asChild variant="outline">
            <Link to="/">Back to dashboard</Link>
          </Button>
        }
      />
    );
  }

  return (
    <div>
      <Link to="/" className="mb-4 inline-flex items-center gap-1.5 text-sm text-muted-foreground hover:text-foreground">
        <ArrowLeft className="h-3.5 w-3.5" />
        Back to dashboard
      </Link>

      <div className="mb-6 flex flex-col gap-4 rounded-xl border border-border bg-card p-5 sm:flex-row sm:items-start sm:justify-between">
        <div className="min-w-0">
          <div className="flex flex-wrap items-center gap-2">
            <h1 className="text-xl font-semibold tracking-tight text-foreground">{project.name}</h1>
            {status && <StatusBadge name={status.name} color={status.color} />}
          </div>
          {project.description && (
            <p className="mt-2 max-w-2xl text-sm text-muted-foreground">{project.description}</p>
          )}
          {project.remarks && (
            <p className="mt-2 flex max-w-2xl items-start gap-1.5 rounded-lg border border-dashed border-border bg-muted/40 px-3 py-2 text-sm text-foreground/90">
              <StickyNote className="mt-0.5 h-3.5 w-3.5 shrink-0 text-muted-foreground" />
              <span className="whitespace-pre-wrap">{project.remarks}</span>
            </p>
          )}
          <div className="mt-4 flex flex-wrap items-center gap-x-6 gap-y-2 text-sm">
            {vertical && (
              <div className="flex items-center gap-1.5 text-muted-foreground">
                <span className="font-medium text-foreground">{vertical.name}</span>
              </div>
            )}
            <div className="flex items-center gap-1.5 text-muted-foreground">
              <CalendarDays className="h-3.5 w-3.5" />
              Target: <span className="text-foreground">{formatDate(project.target_date)}</span>
            </div>
            {project.actual_completion_date && (
              <div className="flex items-center gap-1.5 text-muted-foreground">
                Completed: <span className="text-foreground">{formatDate(project.actual_completion_date)}</span>
              </div>
            )}
            {project.assigned_by && (
              <div className="flex items-center gap-1.5 text-muted-foreground">
                <UserRound className="h-3.5 w-3.5" />
                Assigned by <span className="text-foreground">{project.assigned_by}</span>
                {project.assigned_on && <span>on {formatDate(project.assigned_on)}</span>}
              </div>
            )}
            <div className="flex items-center gap-2">
              <span className="text-muted-foreground">Owners:</span>
              {owners.length === 0 && <span className="text-muted-foreground">Unassigned</span>}
              <div className="flex -space-x-1.5">
                {owners.map((o) => (
                  <Tooltip key={o.id}>
                    <TooltipTrigger asChild>
                      <Avatar className="h-6 w-6 border-2 border-card">
                        <AvatarFallback className="text-[9px]">{initials(o.name)}</AvatarFallback>
                      </Avatar>
                    </TooltipTrigger>
                    <TooltipContent>{o.name}</TooltipContent>
                  </Tooltip>
                ))}
              </div>
            </div>
          </div>
        </div>
        <div className="flex shrink-0 items-center gap-2">
          {can("projects_manage") && <EditProjectDialog project={project} />}
          {can("projects_delete") && (
            <Button
              variant="outline"
              size="sm"
              className="text-destructive hover:border-destructive hover:text-destructive"
              onClick={() => setConfirmDelete(true)}
            >
              <Trash2 className="h-4 w-4" />
              Delete
            </Button>
          )}
        </div>
      </div>

      <ConfirmDialog
        open={confirmDelete}
        onOpenChange={setConfirmDelete}
        destructive
        title={`Delete "${project.name}"?`}
        description={
          <>
            This removes the project and its {updates?.length ?? 0} update
            {(updates?.length ?? 0) === 1 ? "" : "s"} for good. It cannot be undone, and the
            weekly digest will no longer report on it. The audit trail keeps a record of the
            deletion.
            <br />
            <br />
            If you only want it off the board, change its status instead.
          </>
        }
        confirmLabel="Delete project"
        loading={deleteProject.isPending}
        onConfirm={async () => {
          try {
            await deleteProject.mutateAsync(project.id);
            toast.success("Project deleted", { description: `"${project.name}" is gone.` });
            navigate("/");
          } catch (err) {
            toast.error("Couldn't delete the project", { description: apiErrorMessage(err) });
          }
        }}
      />

      <div className="grid gap-6 lg:grid-cols-2">
        <div>
          <h2 className="mb-4 text-sm font-semibold uppercase tracking-wide text-muted-foreground">
            Update log
          </h2>
          {updatesLoading ? (
            <div className="space-y-4">
              <Skeleton className="h-24 w-full rounded-xl" />
              <Skeleton className="h-24 w-full rounded-xl" />
            </div>
          ) : (
            <UpdateTimeline updates={updates ?? []} userById={userById} />
          )}
        </div>
        {can("projects_manage") && (
          <div>
            <h2 className="mb-4 text-sm font-semibold uppercase tracking-wide text-muted-foreground">
              Log a new update
            </h2>
            <AddUpdateForm projectId={project.id} />
          </div>
        )}
      </div>
    </div>
  );
}
