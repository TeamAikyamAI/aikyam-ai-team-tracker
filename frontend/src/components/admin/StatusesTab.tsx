import * as React from "react";
import { GripVertical, Plus, Tag } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import { EmptyState } from "@/components/common/EmptyState";
import { StatusFormDialog } from "@/components/admin/StatusFormDialog";
import { useStatuses } from "@/hooks/useStatuses";
import type { Status } from "@/types";

export function StatusesTab() {
  const { data: statuses, isLoading } = useStatuses();
  const [dialogOpen, setDialogOpen] = React.useState(false);
  const [editing, setEditing] = React.useState<Status | null>(null);

  const sorted = React.useMemo(() => [...(statuses ?? [])].sort((a, b) => a.sort_order - b.sort_order), [statuses]);
  const nextSortOrder = sorted.length > 0 ? Math.max(...sorted.map((s) => s.sort_order)) + 1 : 0;

  return (
    <div>
      <div className="mb-4 flex items-center justify-between">
        <p className="text-sm text-muted-foreground">Configurable project statuses power the kanban board.</p>
        <Button
          size="sm"
          onClick={() => {
            setEditing(null);
            setDialogOpen(true);
          }}
        >
          <Plus className="h-3.5 w-3.5" />
          Add status
        </Button>
      </div>

      {isLoading && (
        <div className="space-y-2">
          {Array.from({ length: 4 }).map((_, i) => (
            <Skeleton key={i} className="h-12 w-full rounded-lg" />
          ))}
        </div>
      )}

      {!isLoading && sorted.length === 0 && (
        <EmptyState icon={<Tag className="h-6 w-6" />} title="No statuses configured" description="Add your first project status, e.g. Backlog or In Progress." />
      )}

      {!isLoading && sorted.length > 0 && (
        <div className="rounded-xl border border-border">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead className="w-10" />
                <TableHead>Status</TableHead>
                <TableHead>Color</TableHead>
                <TableHead>Terminal</TableHead>
                <TableHead>Status</TableHead>
                <TableHead />
              </TableRow>
            </TableHeader>
            <TableBody>
              {sorted.map((s) => (
                <TableRow key={s.id}>
                  <TableCell className="text-muted-foreground">
                    <GripVertical className="h-4 w-4" />
                  </TableCell>
                  <TableCell className="font-medium text-foreground">{s.name}</TableCell>
                  <TableCell>
                    <div className="flex items-center gap-2">
                      <span className="h-4 w-4 rounded-full border border-border/50" style={{ backgroundColor: s.color }} />
                      <span className="font-mono text-xs text-muted-foreground">{s.color}</span>
                    </div>
                  </TableCell>
                  <TableCell>{s.is_terminal ? <Badge variant="outline">Terminal</Badge> : <span className="text-muted-foreground">—</span>}</TableCell>
                  <TableCell>
                    <Badge variant={s.is_active ? "success" : "secondary"}>{s.is_active ? "Active" : "Inactive"}</Badge>
                  </TableCell>
                  <TableCell>
                    <Button
                      variant="ghost"
                      size="sm"
                      onClick={() => {
                        setEditing(s);
                        setDialogOpen(true);
                      }}
                    >
                      Edit
                    </Button>
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </div>
      )}

      <StatusFormDialog open={dialogOpen} onOpenChange={setDialogOpen} status={editing} nextSortOrder={nextSortOrder} />
    </div>
  );
}
